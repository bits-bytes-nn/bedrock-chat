import pytest
import sys
import unittest

sys.path.insert(0, ".")


from app.config import DEFAULT_GENERATION_CONFIG
from app.config import GenerationParams as GenerationParamsConfig
from app.repositories.models.custom_bot import (
    ActiveModelsModel,
    AgentModel,
    BotModel,
    ConversationQuickStarterModel,
    GenerationParamsModel,
    KnowledgeModel,
    PlainToolModel,
    ReasoningParamsModel,
    ToolModel,
    UsageStatsModel,
)
from app.repositories.models.custom_bot_guardrails import BedrockGuardrailsModel
from app.repositories.models.custom_bot_kb import (
    BedrockKnowledgeBaseModel,
    OpenSearchParamsModel,
    SearchParamsModel,
    WebCrawlingFiltersModel,
)
from app.routes.schemas.bot import (
    BotInput,
    GenerationParams,
    Knowledge,
    ReasoningParams,
)
from tests.test_repositories.utils.bot_factory import create_test_private_bot
from tests.test_usecases.utils.user_factory import (
    create_test_admin_user,
    create_test_user,
)

OWNER = create_test_user("test_owner")
OTHER_USER = create_test_user("test_user")
USER_IN_GROUP = create_test_user("test_user_in_group", groups=["test_group"])
ADMIN = create_test_admin_user("test_admin")


class TestBotModel(unittest.TestCase):
    def setUp(self) -> None:
        # Fully configured BotModel shared with "test_group".
        self.bot = BotModel(
            id="test",
            title="test",
            description="test",
            instruction="instruction",
            create_time=1627984879.9,
            last_used_time=1627984879.9,
            shared_scope="partial",
            shared_status="shared",
            allowed_cognito_users=[],
            allowed_cognito_groups=["test_group"],
            is_starred=False,
            owner_user_id=OWNER.id,
            generation_params=GenerationParamsModel(
                max_tokens=2000,
                top_k=250,
                top_p=0.999,
                temperature=0.6,
                stop_sequences=["Human: ", "Assistant: "],
                reasoning_params=ReasoningParamsModel(
                    budget_tokens=2000,
                ),
            ),
            agent=AgentModel(
                tools=[
                    PlainToolModel(
                        tool_type="plain",
                        name="internet_search",
                        description="Search the internet for information.",
                    )
                ]
            ),
            knowledge=(
                KnowledgeModel(
                    source_urls=["https://aws.amazon.com/"],
                    sitemap_urls=["https://aws.amazon.sitemap.xml"],
                    filenames=["test.txt"],
                    s3_urls=["s3://test-user/test-bot/"],
                )
            ),
            prompt_caching_enabled=False,
            sync_status="RUNNING",
            sync_status_reason="reason",
            sync_last_exec_id="xxxx",
            published_api_stack_name=None,
            published_api_datetime=None,
            published_api_codebuild_id=None,
            display_retrieved_chunks=True,
            conversation_quick_starters=[
                ConversationQuickStarterModel(
                    title="title",
                    example="example",
                )
            ],
            bedrock_knowledge_base=(
                BedrockKnowledgeBaseModel(
                    type="dedicated",
                    embeddings_model="titan_v2",
                    open_search=OpenSearchParamsModel(analyzer=None),
                    chunking_configuration=None,
                    search_params=SearchParamsModel(
                        max_results=10, search_type="hybrid"
                    ),
                    knowledge_base_id="test-knowledge-base-id",
                    data_source_ids=["data-source-1", "data-source-2"],
                    parsing_model="disabled",
                    web_crawling_scope="DEFAULT",
                    web_crawling_filters=WebCrawlingFiltersModel(
                        exclude_patterns=["exclude-pattern"],
                        include_patterns=["include-pattern"],
                    ),
                )
            ),
            bedrock_guardrails=BedrockGuardrailsModel(
                is_guardrail_enabled=True,
                hate_threshold=5,
                insults_threshold=5,
                sexual_threshold=5,
                violence_threshold=5,
                misconduct_threshold=5,
                grounding_threshold=0.5,
                relevance_threshold=0.5,
                guardrail_arn="guardrail_arn",
                guardrail_version="guardrail_version",
            ),
            active_models=ActiveModelsModel(
                claude_v4_5_sonnet=False,
            ),
            usage_stats=UsageStatsModel(usage_count=0),
        )

    def test_to_output(self):
        output = self.bot.to_output()

        self.assertEqual(output.id, "test")
        self.assertEqual(output.allowed_cognito_groups, ["test_group"])
        self.assertFalse(output.active_models.claude_v4_5_sonnet)
        self.assertTrue(output.active_models.claude_v5_sonnet)

    def test_is_owned_by_user(self):
        self.assertTrue(self.bot.is_owned_by_user(OWNER))
        self.assertFalse(self.bot.is_owned_by_user(OTHER_USER))
        self.assertFalse(self.bot.is_owned_by_user(ADMIN))


def _bot(shared_scope: str, users: list[str] = [], groups: list[str] = []):
    return BotModel.model_validate(
        create_test_private_bot("bot", False, OWNER.id).model_dump()
        | {
            "shared_scope": shared_scope,
            "shared_status": "unshared" if shared_scope == "private" else "shared",
            "allowed_cognito_users": users,
            "allowed_cognito_groups": groups,
        }
    )


@pytest.mark.parametrize(
    "bot, user, accessible, editable",
    [
        pytest.param(_bot("private"), OWNER, True, True, id="owner"),
        pytest.param(_bot("private"), ADMIN, True, True, id="admin"),
        pytest.param(_bot("private"), OTHER_USER, False, False, id="private-other"),
        pytest.param(_bot("all"), OTHER_USER, True, False, id="shared-all"),
        pytest.param(
            _bot("partial", users=[OTHER_USER.id]),
            OTHER_USER,
            True,
            False,
            id="partial-by-user",
        ),
        pytest.param(
            _bot("partial", groups=["test_group"]),
            USER_IN_GROUP,
            True,
            False,
            id="partial-by-group",
        ),
        pytest.param(
            _bot("partial", users=["someone"], groups=["other_group"]),
            USER_IN_GROUP,
            False,
            False,
            id="partial-not-listed",
        ),
    ],
)
def test_bot_access(bot, user, accessible, editable):
    assert bot.is_accessible_by_user(user) is accessible
    assert bot.is_editable_by_user(user) is editable


class TestBotModelFromInput(unittest.TestCase):
    def setUp(self):

        # Create a basic bot input
        self.bot_input = BotInput(
            id="test-bot",
            title="Test Bot",
            instruction="Test instruction",
            description="Test description",
            display_retrieved_chunks=True,
            active_models={field: True for field in DEFAULT_GENERATION_CONFIG},
            # No generation_params provided initially
            generation_params=None,
            knowledge=Knowledge(
                source_urls=[], sitemap_urls=[], filenames=[], s3_urls=[]
            ),
            prompt_caching_enabled=False,
            conversation_quick_starters=[],
        )

        self.owner_user_id = "test-owner"
        self.knowledge = KnowledgeModel(
            source_urls=[], sitemap_urls=[], filenames=[], s3_urls=[]
        )

    def test_from_input_with_default_generation_params(self):
        """Test creating BotModel with default generation parameters"""
        bot_model = BotModel.from_input(
            bot_input=self.bot_input,
            owner_user_id=self.owner_user_id,
            knowledge=self.knowledge,
        )

        # Check that default generation params were used
        self.assertEqual(
            bot_model.generation_params.max_tokens,
            DEFAULT_GENERATION_CONFIG["max_tokens"],
        )
        self.assertEqual(
            bot_model.generation_params.top_k, DEFAULT_GENERATION_CONFIG["top_k"]
        )
        self.assertEqual(
            bot_model.generation_params.top_p, DEFAULT_GENERATION_CONFIG["top_p"]
        )
        self.assertEqual(
            bot_model.generation_params.temperature,
            DEFAULT_GENERATION_CONFIG["temperature"],
        )
        self.assertEqual(
            bot_model.generation_params.stop_sequences,
            DEFAULT_GENERATION_CONFIG["stop_sequences"],
        )
        self.assertEqual(
            bot_model.generation_params.reasoning_params.budget_tokens,
            DEFAULT_GENERATION_CONFIG["reasoning_params"]["budget_tokens"],
        )

    def test_from_input_with_custom_generation_params(self):
        """Test creating BotModel with custom generation parameters"""
        # Create custom generation params
        custom_params = GenerationParams(
            max_tokens=2000,
            top_k=150,
            top_p=0.8,
            temperature=0.7,
            stop_sequences=["Stop1", "Stop2"],
            reasoning_params=ReasoningParams(budget_tokens=1500),
        )

        # Update bot input with custom params
        self.bot_input.generation_params = custom_params

        # Create bot model
        bot_model = BotModel.from_input(
            bot_input=self.bot_input,
            owner_user_id=self.owner_user_id,
            knowledge=self.knowledge,
        )

        # Check that custom generation params were used
        self.assertEqual(bot_model.generation_params.max_tokens, 2000)
        self.assertEqual(bot_model.generation_params.top_k, 150)
        self.assertEqual(bot_model.generation_params.top_p, 0.8)
        self.assertEqual(bot_model.generation_params.temperature, 0.7)
        self.assertEqual(bot_model.generation_params.stop_sequences, ["Stop1", "Stop2"])
        self.assertEqual(
            bot_model.generation_params.reasoning_params.budget_tokens, 1500
        )

    def test_from_input_validates_reasoning_params(self):
        """Test that budget_tokens validation works correctly"""
        # Create invalid generation params with budget_tokens < 1024
        invalid_params = GenerationParams(
            max_tokens=2000,
            top_k=150,
            top_p=0.8,
            temperature=0.7,
            stop_sequences=["Stop"],
            reasoning_params=ReasoningParams(
                budget_tokens=1
            ),  # Invalid budget_tokens (too small)
        )

        # Update bot input with invalid params
        self.bot_input.generation_params = invalid_params

        # Creating bot model should raise ValueError
        with self.assertRaises(ValueError) as context:
            BotModel.from_input(
                bot_input=self.bot_input,
                owner_user_id=self.owner_user_id,
                knowledge=self.knowledge,
            )

        self.assertIn(
            "budget_tokens must be greater than or equal to 1024",
            str(context.exception),
        )


if __name__ == "__main__":
    unittest.main()
