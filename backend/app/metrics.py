import json
from datetime import datetime

# Shared with cdk/lib/constructs/monitoring.ts (DailyChatCost alarm).
CHAT_METRICS_NAMESPACE = "BedrockChat"


def emit_chat_cost(price: float) -> None:
    """Publish the price of an answer for the daily chat cost alarm.

    Lambda turns embedded metric format lines on stdout into CloudWatch metrics
    without an API call, so this goes to stdout rather than the logger. Without
    dimensions, the chat and published API handlers add up to one metric.
    """
    print(
        json.dumps(
            {
                "_aws": {
                    "Timestamp": int(datetime.now().timestamp() * 1000),
                    "CloudWatchMetrics": [
                        {
                            "Namespace": CHAT_METRICS_NAMESPACE,
                            "Dimensions": [[]],
                            "Metrics": [{"Name": "ChatCost", "Unit": "None"}],
                        }
                    ],
                },
                "ChatCost": price,
            }
        ),
        flush=True,
    )
