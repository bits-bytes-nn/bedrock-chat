import json
import logging
import os
from datetime import datetime
from decimal import Decimal as decimal
from queue import Empty, SimpleQueue
from threading import Thread
from typing import Literal, TypedDict

import boto3
from app.agents.tools.agent_tool import ToolRunResult
from app.auth import verify_token
from app.repositories.conversation import RecordNotFoundError
from app.routes.schemas.conversation import ChatInput
from app.stream import OnStopInput, OnThinking
from app.usecases.chat import chat
from app.user import User
from boto3.dynamodb.conditions import Attr, Key
from botocore.config import Config

WEBSOCKET_SESSION_TABLE_NAME = os.environ["WEBSOCKET_SESSION_TABLE_NAME"]

# Consecutive tokens are merged into one frame while the sender is busy, which keeps
# the number of post_to_connection calls bounded for fast models. The limit keeps a
# merged frame well below the API Gateway WebSocket frame size (32 KB).
MAX_MERGED_COMPLETION_CHARS = 8 * 1024

# Time reserved for Lambda to return after the sender has drained.
SENDER_DRAIN_MARGIN_SECONDS = 5

dynamodb_client = boto3.resource("dynamodb")
table = dynamodb_client.Table(WEBSOCKET_SESSION_TABLE_NAME)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class _NotifyCommand(TypedDict):
    type: Literal["notify"]
    payload: bytes


class _CompletionCommand(TypedDict):
    type: Literal["completion"]
    status: Literal["STREAMING", "REASONING"]
    completion: str


class _FinishCommand(TypedDict):
    type: Literal["finish"]


_Command = _NotifyCommand | _CompletionCommand | _FinishCommand


class NotificationSender:
    def __init__(self, endpoint_url: str, connection_id: str) -> None:
        self.commands = SimpleQueue[_Command]()
        self.endpoint_url = endpoint_url
        self.connection_id = connection_id
        self.stream_ended = False

    def run(self):
        gatewayapi = boto3.client(
            "apigatewaymanagementapi",
            endpoint_url=self.endpoint_url,
            config=Config(
                connect_timeout=5,
                read_timeout=10,
                retries={"mode": "standard", "max_attempts": 5},
            ),
        )

        pending: _Command | None = None
        while True:
            command = pending if pending is not None else self.commands.get()
            pending = None

            if command["type"] == "finish":
                break

            if command["type"] == "completion":
                payload, pending = self._merge_completions(command)
            else:
                payload = command["payload"]

            try:
                gatewayapi.post_to_connection(
                    ConnectionId=self.connection_id,
                    Data=payload,
                )

            except (
                gatewayapi.exceptions.GoneException,
                gatewayapi.exceptions.ForbiddenException,
            ):
                logger.warning(
                    "Connection %s is closed. Stop sending notifications.",
                    self.connection_id,
                )
                break

            except Exception:
                logger.exception(
                    "Failed to send a notification of %d bytes", len(payload)
                )

    def _merge_completions(
        self, first: _CompletionCommand
    ) -> tuple[bytes, _Command | None]:
        """Merge queued completions of the same status into one payload.

        Returns:
            The encoded payload and the first queued command that was not merged.
        """
        completion = first["completion"]
        pending: _Command | None = None
        while len(completion) < MAX_MERGED_COMPLETION_CHARS:
            try:
                command = self.commands.get_nowait()
            except Empty:
                break

            if command["type"] == "completion" and command["status"] == first["status"]:
                completion += command["completion"]
            else:
                pending = command
                break

        payload = json.dumps(
            dict(status=first["status"], completion=completion)
        ).encode("utf-8")
        return payload, pending

    def finish(self):
        self.commands.put({"type": "finish"})

    def notify(self, payload: bytes):
        self.commands.put({"type": "notify", "payload": payload})

    def on_stream(self, token: str):
        self.commands.put(
            {"type": "completion", "status": "STREAMING", "completion": token}
        )

    def on_stop(self, arg: OnStopInput):
        payload = json.dumps(
            dict(
                status="STREAMING_END",
                completion="",
                stop_reason=arg["stop_reason"],
                token_count=dict(
                    input=arg["input_token_count"],
                    output=arg["output_token_count"],
                    cache_read_input=arg["cache_read_input_count"],
                    cache_write_input=arg["cache_write_input_count"],
                ),
                price=arg["price"],
            )
        ).encode("utf-8")

        self.stream_ended = True
        self.notify(payload=payload)

    def on_agent_thinking(self, tool_use: OnThinking):
        payload = json.dumps(
            dict(
                status="AGENT_THINKING",
                log={
                    tool_use["tool_use_id"]: {
                        "name": tool_use["name"],
                        "input": tool_use["input"],
                    },
                },
            )
        ).encode("utf-8")

        self.notify(payload=payload)

    def on_agent_tool_result(self, run_result: ToolRunResult):
        self.notify(
            payload=json.dumps(
                dict(
                    status="AGENT_TOOL_RESULT",
                    result={
                        "toolUseId": run_result["tool_use_id"],
                        "status": run_result["status"],
                    },
                )
            ).encode("utf-8")
        )

        for related_document in run_result["related_documents"]:
            self.notify(
                payload=json.dumps(
                    dict(
                        status="AGENT_RELATED_DOCUMENT",
                        result={
                            "toolUseId": run_result["tool_use_id"],
                            "relatedDocument": related_document.to_schema().model_dump(
                                by_alias=True
                            ),
                        },
                    )
                ).encode("utf-8")
            )

    def on_reasoning(self, token: str):
        self.commands.put(
            {"type": "completion", "status": "REASONING", "completion": token}
        )

    def on_error(self, reason: str):
        """Send an error to the client unless the stream has already ended.

        The route response cannot carry errors after the API Gateway integration
        timeout (29 seconds), so errors are also pushed over the connection.
        """
        if self.stream_ended:
            return

        self.notify(
            payload=json.dumps(dict(status="ERROR", reason=reason)).encode("utf-8")
        )


def process_chat_input(
    user: User,
    chat_input: ChatInput,
    notificator: NotificationSender,
) -> dict:
    """Process chat input and send the message to the client."""
    logger.info(
        "Received chat input: conversation_id=%s, bot_id=%s, model=%s",
        chat_input.conversation_id,
        chat_input.bot_id,
        chat_input.message.model,
    )

    def error_response(status_code: int, reason: str) -> dict:
        notificator.on_error(reason)
        return {
            "statusCode": status_code,
            "body": json.dumps(dict(status="ERROR", reason=reason)),
        }

    try:
        chat(
            user=user,
            chat_input=chat_input,
            on_stream=lambda token: notificator.on_stream(
                token=token,
            ),
            on_stop=lambda arg: notificator.on_stop(arg=arg),
            on_thinking=lambda tool_use: notificator.on_agent_thinking(
                tool_use=tool_use,
            ),
            on_tool_result=lambda run_result: notificator.on_agent_tool_result(
                run_result=run_result
            ),
            on_reasoning=lambda token: notificator.on_reasoning(
                token=token,
            ),
        )

        return {"statusCode": 200, "body": "Message sent."}

    except RecordNotFoundError:
        if chat_input.bot_id:
            return error_response(404, f"bot {chat_input.bot_id} not found.")
        else:
            return error_response(400, "Invalid request.")

    except (PermissionError, ValueError) as e:
        logger.exception("Rejected chat input")
        return error_response(400, str(e))

    except Exception:
        # Unexpected errors may contain resource names and account details.
        logger.exception("Failed to run stream handler")
        return error_response(500, "Failed to generate the answer.")


def handler(event, context):
    route_key = event["requestContext"]["routeKey"]
    logger.info(
        "Received event: route_key=%s, connection_id=%s",
        route_key,
        event["requestContext"].get("connectionId"),
    )

    if route_key == "$connect":
        return {"statusCode": 200, "body": "Connected."}
    elif route_key == "$disconnect":
        return {"statusCode": 200, "body": "Disconnected."}

    connection_id = event["requestContext"]["connectionId"]
    domain_name = event["requestContext"]["domainName"]
    stage = event["requestContext"]["stage"]
    endpoint_url = f"https://{domain_name}/{stage}"
    notificator = NotificationSender(
        endpoint_url=endpoint_url,
        connection_id=connection_id,
    )

    now = datetime.now()
    expire = int(now.timestamp()) + 60 * 2  # 2 minute from now
    body = json.loads(event["body"])
    step = body.get("step")
    token = body.get("token")

    notification_thread = Thread(
        target=lambda: notificator.run(),
        daemon=True,
    )
    notification_thread.start()
    try:
        # API Gateway (websocket) has hard limit of 32KB per message, so if the message is larger than that,
        # need to concatenate chunks and send as a single full message.
        # To do that, we store the chunks in DynamoDB and when the message is complete, send it to SNS.
        # The life cycle of the message is as follows:
        # 1. Client sends `START` message to the WebSocket API.
        # 2. This handler receives the `Session started` message.
        # 3. Client sends message parts to the WebSocket API.
        # 4. This handler receives the message parts and appends them to the item in DynamoDB with index.
        # 5. Client sends `END` message to the WebSocket API.
        # 6. This handler receives the `END` message, concatenates the parts and sends the message to Bedrock.
        if step == "START":
            try:
                # Verify JWT token
                decoded = verify_token(token)
            except Exception:
                logger.exception("Invalid token")
                return {
                    "statusCode": 403,
                    "body": json.dumps(
                        dict(
                            status="ERROR",
                            reason="Invalid token.",
                        )
                    ),
                }

            user_id = decoded["sub"]

            # Store user id
            response = table.put_item(
                Item={
                    "ConnectionId": connection_id,
                    # Store as zero
                    "MessagePartId": decimal(0),
                    "UserId": user_id,
                    "expire": expire,
                }
            )
            return {"statusCode": 200, "body": "Session started."}
        elif step == "END":
            decoded = verify_token(token)
            user = User.from_decoded_token(decoded)

            # Retrieve user id
            response = table.query(
                KeyConditionExpression=Key("ConnectionId").eq(connection_id),
                FilterExpression=Attr("UserId").exists(),
            )
            user_id = response["Items"][0]["UserId"]

            # Concatenate the message parts
            message_parts = []
            last_evaluated_key = None

            while True:
                if last_evaluated_key:
                    response = table.query(
                        KeyConditionExpression=Key("ConnectionId").eq(connection_id)
                        # Zero is reserved for user id, so start from 1
                        & Key("MessagePartId").gte(1),
                        ExclusiveStartKey=last_evaluated_key,
                    )
                else:
                    response = table.query(
                        KeyConditionExpression=Key("ConnectionId").eq(connection_id)
                        & Key("MessagePartId").gte(1),
                    )

                message_parts.extend(response["Items"])

                if "LastEvaluatedKey" in response:
                    last_evaluated_key = response["LastEvaluatedKey"]
                else:
                    break

            logger.info("Number of message chunks: %d", len(message_parts))
            message_parts.sort(key=lambda x: x["MessagePartId"])
            full_message = "".join(item["MessagePart"] for item in message_parts)

            # Process the concatenated full message
            chat_input = ChatInput(**json.loads(full_message))
            return process_chat_input(
                user=user,
                chat_input=chat_input,
                notificator=notificator,
            )

        else:
            # Store the message part of full message
            # Zero is reserved for user id, so start from 1
            part_index = body["index"] + 1
            message_part = body["part"]

            # Store the message part with its index
            table.put_item(
                Item={
                    "ConnectionId": connection_id,
                    "MessagePartId": decimal(part_index),
                    "MessagePart": message_part,
                    "expire": expire,
                }
            )
            return {"statusCode": 200, "body": "Message part received."}

    except Exception as e:
        logger.exception("Operation failed")
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "status": "ERROR",
                    "reason": str(e),
                }
            ),
        }

    finally:
        notificator.finish()
        # Wait until every queued notification is delivered. Returning earlier freezes
        # the sender thread and drops the tail of the response, including STREAMING_END.
        drain_timeout = (
            context.get_remaining_time_in_millis() / 1000 - SENDER_DRAIN_MARGIN_SECONDS
        )
        notification_thread.join(timeout=max(drain_timeout, 0))
        if notification_thread.is_alive():
            logger.error("Notification sender did not drain before the deadline")
