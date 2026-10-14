import logging
from typing import Callable, Literal

from app.stream import ToolRunResult
from app.strands_integration.chat_strands import converse_with_strands
from app.bedrock import (
    calculate_price,
    call_converse_api,
    get_text_from_converse_response,
    get_model_id,
    is_prefill_supported,
    is_tooluse_supported,
)
from app.metrics import emit_chat_cost, emit_metric
from app.model_registry import get_model_spec
from mypy_boto3_bedrock_runtime.type_defs import MessageTypeDef
from app.prompt import (
    KNOWLEDGE_BASE_PROMPT,
    build_rag_prompt,
    get_prompt_to_cite_tool_results,
)
from app.repositories.conversation import (
    RecordNotFoundError,
    find_conversation_by_id,
    store_conversation,
    store_related_documents,
)
from app.repositories.conversation_search import find_conversations_by_query
from app.repositories.custom_bot import alias_exists, store_alias
from app.repositories.models.conversation import (
    ConversationModel,
    MessageModel,
    RelatedDocumentModel,
    SimpleMessageModel,
    TextContentModel,
    TextToolResultModel,
    ToolResultContentModel,
    ToolUseContentModel,
)
from app.repositories.models.custom_bot import (
    BotAliasModel,
    BotModel,
)
from app.routes.schemas.conversation import (
    ChatInput,
    ChatOutput,
    Chunk,
    Conversation,
    ConversationSearchResult,
    FeedbackOutput,
    MessageOutput,
    SearchHighlight,
    active_model_field_name,
)
from app.stream import OnStopInput, OnThinking
from app.usecases.bot import fetch_bot, modify_bot_last_used_time, modify_bot_stats
from app.usecases.global_config import get_global_available_models, get_title_model
from app.user import User
from app.utils import get_current_time
from app.vector_search import (
    SearchResult,
    search_related_docs,
    search_result_to_related_document,
)
from ulid import ULID

logger = logging.getLogger(__name__)

# Characters of the conversation that title generation reads, from the beginning.
TITLE_CONTEXT_CHARS = 4000

# Loading a conversation returns it whole, so it must stay within the Lambda response
# limit (6 MB). The margin leaves room for the answer and the response envelope.
MAX_CONVERSATION_BYTES = 5 * 1024 * 1024


OMITTED_TOOL_RESULT = (
    "The result was omitted because the conversation became too large."
)


class ConversationTooLargeError(ValueError):
    """The conversation would become too large to load."""


class MessageTooLargeError(ConversationTooLargeError):
    """The message alone is too large for any conversation."""


def prepare_conversation(
    user: User,
    chat_input: ChatInput,
) -> tuple[str, ConversationModel, BotModel | None]:
    current_time = get_current_time()
    bot = None

    is_new_conversation = False
    try:
        # Fetch existing conversation
        conversation = find_conversation_by_id(user.id, chat_input.conversation_id)
        parent_id = chat_input.message.parent_message_id
        if chat_input.message.parent_message_id == "system" and chat_input.bot_id:
            # The case editing first user message and use bot
            parent_id = "instruction"
        elif chat_input.message.parent_message_id is None:
            parent_id = conversation.last_message_id
        # The bot is fixed when a conversation starts. Switching it would skip the
        # bot's model allowlist and instruction.
        if chat_input.bot_id != conversation.bot_id:
            raise ValueError("The bot does not match the conversation.")
        if chat_input.bot_id:
            logger.info("Bot id is provided. Fetching bot.")
            owned, bot = fetch_bot(user, chat_input.bot_id)
    except RecordNotFoundError:
        # The case for new conversation. Note that editing first user message is not considered as new conversation.
        is_new_conversation = True
        logger.info(
            f"No conversation found with id: {chat_input.conversation_id}. Creating new conversation."
        )

        initial_message_map = {
            # Dummy system message, which is used for root node of the message tree.
            "system": MessageModel(
                role="system",
                content=[
                    TextContentModel(
                        content_type="text",
                        body="",
                    )
                ],
                model=chat_input.message.model,
                children=[],
                parent=None,
                create_time=current_time,
                feedback=None,
                used_chunks=None,
                thinking_log=None,
            )
        }
        parent_id = "system"
        if chat_input.bot_id:
            logger.info("Bot id is provided. Fetching bot.")
            parent_id = "instruction"
            # Fetch bot and append instruction
            owned, bot = fetch_bot(user, chat_input.bot_id)
            initial_message_map["instruction"] = MessageModel(
                role="instruction",
                content=[
                    TextContentModel(
                        content_type="text",
                        body=bot.instruction,
                    )
                ],
                model=chat_input.message.model,
                children=[],
                parent="system",
                create_time=current_time,
                feedback=None,
                used_chunks=None,
                thinking_log=None,
            )
            initial_message_map["system"].children.append("instruction")

            if not owned and not alias_exists(user.id, chat_input.bot_id):
                logger.info(
                    "Bot is not owned by the user. Creating alias to shared bot."
                )
                store_alias(user.id, BotAliasModel.from_bot_for_initial_alias(bot))

        # Create new conversation
        conversation = ConversationModel(
            id=chat_input.conversation_id,
            title="New conversation",
            total_price=0.0,
            create_time=current_time,
            message_map=initial_message_map,
            last_message_id="",
            bot_id=chat_input.bot_id,
            should_continue=False,
        )

    # Append user chat input to the conversation
    if not chat_input.continue_generate:
        new_message = MessageModel.from_message_input(chat_input.message)
        new_message.parent = parent_id
        new_message.create_time = current_time
        # A new conversation would not help either.
        if len(new_message.model_dump_json().encode("utf-8")) > MAX_CONVERSATION_BYTES:
            raise MessageTooLargeError(
                "The message is too large. Remove some attachments."
            )

        if chat_input.message.message_id:
            message_id = chat_input.message.message_id
            # Reusing an existing id would overwrite a message or create a cycle.
            # "system" and "instruction" are the roots of every conversation.
            if message_id in conversation.message_map or message_id in (
                "system",
                "instruction",
            ):
                raise ValueError(f"Message id {message_id} already exists.")
        else:
            message_id = str(ULID())

        conversation.message_map[message_id] = new_message
        conversation.message_map[parent_id].children.append(message_id)  # type: ignore

    # If the "Generate continue" button is pressed, a new_message is not generated.
    else:
        message_id = (
            conversation.message_map[conversation.last_message_id].parent
            or "instruction"
        )

    # The stored model serializes about like the conversation response (attachments
    # in base64), plus the instruction and the price, so it is a close upper estimate.
    if len(conversation.model_dump_json().encode("utf-8")) > MAX_CONVERSATION_BYTES:
        if is_new_conversation:
            # With the instruction, the message does not fit any conversation.
            raise MessageTooLargeError(
                "The message is too large. Remove some attachments."
            )
        raise ConversationTooLargeError(
            "The conversation is too large. Start a new conversation."
        )

    return (message_id, conversation, bot)


def trace_to_root(
    node_id: str | None, message_map: dict[str, MessageModel]
) -> list[SimpleMessageModel]:
    """Trace message map from leaf node to root node."""
    result: list[SimpleMessageModel] = []
    if not node_id or node_id == "system":
        node_id = "instruction" if "instruction" in message_map else "system"

    visited: set[str] = set()
    current_node = message_map.get(node_id)
    while current_node:
        if node_id in visited:
            raise ValueError(f"Message tree has a cycle at {node_id}.")
        visited.add(node_id)

        result.append(SimpleMessageModel.from_message_model(message=current_node))
        if current_node.thinking_log:
            result.extend(
                log
                for log in reversed(current_node.thinking_log)
                if any(
                    isinstance(content, ToolUseContentModel)
                    or isinstance(content, ToolResultContentModel)
                    for content in log.content
                )
            )

        if current_node.parent is None:
            break
        node_id = current_node.parent
        current_node = message_map.get(node_id)

    return result[::-1]


def validate_model_is_available(model: str, bot: BotModel | None) -> None:
    """Enforce the model allowlists that the UI applies, so that API clients cannot
    bypass them.

    Raises:
        ValueError: If the model is retired or unknown.
        PermissionError: If the model is disabled globally or for the bot.
    """
    get_model_spec(model)

    global_models = get_global_available_models()
    if global_models and model not in global_models:
        raise PermissionError(f"Model {model} is not available.")

    if bot is not None:
        # A model without a field cannot have been activated, so fail closed.
        if not getattr(bot.active_models, active_model_field_name(model), False):
            raise PermissionError(f"Model {model} is not active for this bot.")


def chat(
    user: User,
    chat_input: ChatInput,
    on_stream: Callable[[str], None] | None = None,
    on_stop: Callable[[OnStopInput], None] | None = None,
    on_thinking: Callable[[OnThinking], None] | None = None,
    on_tool_result: Callable[[ToolRunResult], None] | None = None,
    on_reasoning: Callable[[str], None] | None = None,
) -> tuple[ConversationModel, MessageModel]:
    user_msg_id, conversation, bot = prepare_conversation(user, chat_input)
    validate_model_is_available(chat_input.message.model, bot)
    display_citation = bot is not None and bot.display_retrieved_chunks

    message_map = conversation.message_map
    instructions: list[str] = (
        [
            content.body
            for content in message_map["instruction"].content
            if isinstance(content, TextContentModel)
        ]
        if "instruction" in message_map
        else []
    )

    related_documents: list[RelatedDocumentModel] = []
    search_results: list[SearchResult] = []
    if bot is not None:
        if bot.is_agent_enabled() and is_tooluse_supported(chat_input.message.model):
            if bot.has_knowledge():
                instructions.append(KNOWLEDGE_BASE_PROMPT)
            if display_citation:
                instructions.append(
                    get_prompt_to_cite_tool_results(
                        model=chat_input.message.model,
                    )
                )
        elif bot.has_knowledge() and not is_tooluse_supported(chat_input.message.model):
            # Fetch most related documents from vector store
            # NOTE: Currently embedding not support multi-modal. For now, use the last content.
            content = conversation.message_map[user_msg_id].content[-1]
            if isinstance(content, TextContentModel):
                pseudo_tool_use_id = "new-message-assistant"

                if on_thinking:
                    on_thinking(
                        {
                            "tool_use_id": pseudo_tool_use_id,
                            "name": "knowledge_base_tool",
                            "input": {
                                "query": content.body,
                            },
                        }
                    )

                search_results = search_related_docs(bot=bot, query=content.body)
                logger.info("Found %d related documents", len(search_results))

                if on_tool_result:
                    on_tool_result(
                        {
                            "tool_use_id": pseudo_tool_use_id,
                            "status": "success",
                            "related_documents": [
                                search_result_to_related_document(
                                    search_result=result,
                                    source_id_base=pseudo_tool_use_id,
                                )
                                for result in search_results
                            ],
                        }
                    )

                # Insert contexts to instruction
                instructions.append(
                    build_rag_prompt(
                        search_results=search_results,
                        model=chat_input.message.model,
                        display_citation=display_citation,
                    )
                )

    # Leaf node id
    # If `continue_generate` is True, note that new message is not added to the message map.
    node_id = (
        chat_input.message.parent_message_id
        if chat_input.continue_generate
        else message_map[user_msg_id].parent
    )
    if node_id is None:
        raise ValueError("parent_message_id or parent is None")

    messages = trace_to_root(
        node_id=node_id,
        message_map=message_map,
    )

    if chat_input.continue_generate:
        message_for_continue_generate = SimpleMessageModel.from_message_model(
            message=message_map[conversation.last_message_id],
        )

    else:
        messages.append(
            SimpleMessageModel.from_message_model(message=message_map[user_msg_id]),
        )
        message_for_continue_generate = None

    generation_params = bot.generation_params if bot else None

    # Guardrails
    guardrail = bot.bedrock_guardrails if bot else None

    def on_tool_run_result(run_result: ToolRunResult):
        if run_result["status"] == "success":
            related_documents.extend(run_result["related_documents"])

        if on_tool_result:
            on_tool_result(run_result)

    result = converse_with_strands(
        bot=bot,
        chat_input=chat_input,
        instructions=instructions,
        generation_params=generation_params,
        guardrail=guardrail,
        display_citation=display_citation,
        messages=messages,
        search_results=search_results,
        on_stream=on_stream,
        on_thinking=on_thinking,
        on_tool_result=on_tool_run_result,
        on_reasoning=on_reasoning,
    )

    # Post handling: process the result and update conversation
    return post_process_result(
        result=result,
        message_for_continue_generate=message_for_continue_generate,
        conversation=conversation,
        user_msg_id=user_msg_id,
        bot=bot,
        user=user,
        chat_input=chat_input,
        search_results=search_results,
        related_documents=related_documents,
        on_stop=on_stop,
    )


def fit_answer(
    conversation: ConversationModel,
    message: MessageModel,
    related_documents: list[RelatedDocumentModel],
) -> None:
    """Drop the tool results of the answer if they make the conversation too large.

    Messages are checked before the model is called, but the answer is not: its
    text is bounded by the output tokens and fits the headroom below the response
    limit, while tool results such as fetched pages are not bounded. The related
    documents of the answer hold the same results, so their content is dropped too.
    """
    if (
        not message.thinking_log
        or len(conversation.model_dump_json().encode("utf-8")) <= MAX_CONVERSATION_BYTES
    ):
        return
    logger.warning("Omitting the tool results of an answer that is too large to load")
    for log in message.thinking_log:
        for content in log.content:
            if isinstance(content, ToolResultContentModel):
                content.body.content = [TextToolResultModel(text=OMITTED_TOOL_RESULT)]
    for related_document in related_documents:
        related_document.content = TextToolResultModel(text=OMITTED_TOOL_RESULT)


def post_process_result(
    result: OnStopInput,
    message_for_continue_generate: SimpleMessageModel | None,
    conversation: ConversationModel,
    user_msg_id: str,
    bot: BotModel | None,
    user: User,
    chat_input: ChatInput,
    search_results: list[SearchResult],
    related_documents: list[RelatedDocumentModel],
    on_stop: Callable[[OnStopInput], None] | None = None,
):
    """Post-process OnStopInput and update conversation."""

    # Every chat entrypoint finalizes its answer here. The model has billed the
    # answer even if storing it fails below.
    emit_chat_cost(result["price"])

    message = result["message"]
    stop_reason = result["stop_reason"]

    conversation.total_price += result["price"]
    conversation.should_continue = stop_reason == "max_tokens" and is_prefill_supported(
        chat_input.message.model
    )

    # Set message parent and generate assistant message ID
    message.parent = user_msg_id

    # Generate assistant message ID
    if chat_input.continue_generate and not message.thinking_log:
        if message_for_continue_generate is not None:
            message.continue_from(message_for_continue_generate)

        assistant_msg_id = conversation.last_message_id
        conversation.message_map[assistant_msg_id] = message

    else:
        if chat_input.continue_generate and message.thinking_log:
            if message_for_continue_generate is not None:
                message.thinking_log[0].continue_from(message_for_continue_generate)

            # Remove old assistant message and create new one
            old_assistant_msg_id = conversation.last_message_id
            conversation.message_map[user_msg_id].children.remove(old_assistant_msg_id)
            del conversation.message_map[old_assistant_msg_id]

        # Issue id for new assistant message
        assistant_msg_id = str(ULID())
        conversation.message_map[assistant_msg_id] = message

        # Append children to parent
        conversation.message_map[user_msg_id].children.append(assistant_msg_id)
        conversation.last_message_id = assistant_msg_id

        # Create related documents with consistent source_id format
        search_results_as_related_documents = [
            search_result_to_related_document(
                search_result=result,
                source_id_base=assistant_msg_id,
            )
            for result in search_results
        ]

        # Store RAG results in ToolResultCapture for citation support
        related_documents.extend(search_results_as_related_documents)

    fit_answer(conversation, message, related_documents)
    # Store conversation before finish streaming so that front-end can avoid 404 issue
    store_conversation(user.id, conversation)
    if related_documents:
        store_related_documents(
            user_id=user.id,
            conversation_id=conversation.id,
            related_documents=related_documents,
        )

    # Call on_stop callback
    if on_stop:
        on_stop(result)

    # The answer is stored, so bookkeeping must not fail the chat: a published API
    # client would see a failure for a stored answer, and its retry would be
    # rejected because the message id already exists.
    if bot:
        try:
            modify_bot_last_used_time(user, bot)
            modify_bot_stats(user, bot, increment=1)
        except Exception:
            logger.exception("Failed to update the usage of bot %s", bot.id)
            # Counted by the BotUsageUpdateFailures alarm, so that a lasting
            # failure (a missing permission, for example) does not go unnoticed.
            emit_metric("BotUsageUpdateFailures", 1)

    return conversation, message


def chat_output_from_message(
    conversation: ConversationModel,
    message: MessageModel,
) -> ChatOutput:
    return ChatOutput(
        conversation_id=conversation.id,
        create_time=conversation.create_time,
        message=MessageOutput(
            role=message.role,
            content=[c.to_content() for c in message.content],
            model=message.model,
            children=message.children,
            parent=message.parent,
            feedback=None,
            used_chunks=(
                [
                    Chunk(
                        content=c.content,
                        content_type=c.content_type,
                        source=c.source,
                        rank=c.rank,
                    )
                    for c in message.used_chunks
                ]
                if message.used_chunks
                else None
            ),
            thinking_log=(
                [m.to_schema() for m in message.thinking_log]
                if message.thinking_log
                else None
            ),
        ),
        bot_id=conversation.bot_id,
    )


def propose_conversation_title(
    user_id: str,
    conversation_id: str,
) -> str:
    # Use the configured title model for generating conversation titles
    model = get_title_model()

    PROMPT = """Reading the conversation above, what is the appropriate title for the conversation? When answering the title, please follow the rules below:
<rules>
- Title length must be from 15 to 20 characters.
- Prefer more specific title than general. Your title should always be distinct from others.
- Return the conversation title only. DO NOT include any strings other than the title.
- Title must be in the same language as the conversation.
</rules>
"""
    # Fetch existing conversation
    conversation = find_conversation_by_id(user_id, conversation_id)

    messages = trace_to_root(
        node_id=conversation.last_message_id,
        message_map=conversation.message_map,
    )

    # Titles only need the beginning of the conversation, without tool use or
    # reasoning; the route can be called repeatedly on long conversations.
    title_messages: list[MessageTypeDef] = []
    remaining = TITLE_CONTEXT_CHARS
    for message in messages:
        text = "\n".join(
            content.body
            for content in message.content
            if isinstance(content, TextContentModel)
        )[:remaining]
        if message.role not in ("user", "assistant") or not text:
            continue
        remaining -= len(text)
        role: Literal["user", "assistant"] = (
            "user" if message.role == "user" else "assistant"
        )
        if title_messages and title_messages[-1]["role"] == role:
            # Converse requires alternating roles.
            title_messages[-1]["content"] = [
                {"text": title_messages[-1]["content"][0]["text"] + "\n" + text}
            ]
        else:
            title_messages.append({"role": role, "content": [{"text": text}]})

    if title_messages and title_messages[-1]["role"] == "user":
        title_messages[-1]["content"] = [
            {"text": title_messages[-1]["content"][0]["text"] + "\n\n" + PROMPT}
        ]
    else:
        title_messages.append({"role": "user", "content": [{"text": PROMPT}]})

    response = call_converse_api(
        {
            "modelId": get_model_id(model),
            "messages": title_messages,
            # Leaves room for models that always reason before answering.
            "inferenceConfig": {"maxTokens": 2048},
        }
    )
    usage = response.get("usage", {})
    emit_chat_cost(
        calculate_price(
            model,
            input_tokens=usage.get("inputTokens", 0),
            output_tokens=usage.get("outputTokens", 0),
            cache_read_input_tokens=usage.get("cacheReadInputTokens", 0),
            cache_write_input_tokens=usage.get("cacheWriteInputTokens", 0),
        )
    )
    return get_text_from_converse_response(response)


def fetch_conversation(user_id: str, conversation_id: str) -> Conversation:
    conversation = find_conversation_by_id(user_id, conversation_id)

    message_map = {
        message_id: MessageOutput(
            role=message.role,
            content=[c.to_content() for c in message.content],
            model=message.model,
            children=message.children,
            parent=message.parent,
            feedback=(
                FeedbackOutput(
                    thumbs_up=message.feedback.thumbs_up,
                    category=message.feedback.category,
                    comment=message.feedback.comment,
                )
                if message.feedback
                else None
            ),
            used_chunks=(
                [
                    Chunk(
                        content=c.content,
                        content_type=c.content_type,
                        source=c.source,
                        rank=c.rank,
                    )
                    for c in message.used_chunks
                ]
                if message.used_chunks
                else None
            ),
            thinking_log=(
                [m.to_schema() for m in message.thinking_log]
                if message.thinking_log
                else None
            ),
        )
        for message_id, message in conversation.message_map.items()
    }
    # Omit instruction
    if "instruction" in message_map:
        for c in message_map["instruction"].children:
            message_map[c].parent = "system"
        message_map["system"].children = message_map["instruction"].children

        del message_map["instruction"]

    output = Conversation(
        id=conversation_id,
        title=conversation.title,
        create_time=conversation.create_time,
        last_message_id=conversation.last_message_id,
        message_map=message_map,
        bot_id=conversation.bot_id,
        should_continue=conversation.should_continue,
    )
    return output


def search_conversations(query: str, user: User) -> list[ConversationSearchResult]:
    """Search conversations by keyword"""
    conversations = find_conversations_by_query(query, user)
    output = []

    for conversation in conversations:
        # Convert model SearchHighlightModel to schema SearchHighlight
        schema_highlights = None
        if conversation.highlights:
            schema_highlights = [
                SearchHighlight(
                    field_name=highlight.field_name, fragments=highlight.fragments
                )
                for highlight in conversation.highlights
            ]

        # Create ConversationSearchResult with properly converted highlights
        output.append(
            ConversationSearchResult(
                id=conversation.id,
                title=conversation.title,
                last_updated_time=conversation.last_updated_time,
                bot_id=conversation.bot_id,
                highlights=schema_highlights,
            )
        )

    return output
