import json
import os
from datetime import datetime

# Set per environment by cdk/lib/utils/metrics.ts, which the alarms also use.
CHAT_METRICS_NAMESPACE = os.environ.get("METRICS_NAMESPACE", "BedrockChat")


def emit_metric(
    name: str, value: float, dimensions: dict[str, str] | None = None
) -> None:
    """Publish a metric value for the alarms.

    Lambda turns embedded metric format lines on stdout into CloudWatch metrics
    without an API call, so this goes to stdout rather than the logger.

    Args:
        name: The metric name.
        value: The value to add to the metric.
        dimensions: Dimension names and values. Without dimensions, every handler
            adds to one metric.
    """
    dimensions = dimensions or {}
    print(
        json.dumps(
            {
                "_aws": {
                    "Timestamp": int(datetime.now().timestamp() * 1000),
                    "CloudWatchMetrics": [
                        {
                            "Namespace": CHAT_METRICS_NAMESPACE,
                            "Dimensions": [list(dimensions)],
                            "Metrics": [{"Name": name, "Unit": "None"}],
                        }
                    ],
                },
                **dimensions,
                name: value,
            }
        ),
        flush=True,
    )


def emit_chat_cost(price: float) -> None:
    """Publish the price of a model call for the daily chat cost alarm."""
    emit_metric("ChatCost", price)
