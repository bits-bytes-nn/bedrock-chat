"""
Limit on the model calls of one answer.
"""

import logging

from app.metrics import emit_metric
from strands.hooks import BeforeModelCallEvent, HookProvider, HookRegistry

logger = logging.getLogger(__name__)

# Each tool round trip sends the whole, growing context again, so a model that
# keeps calling tools would run up cost until the Lambda timeout.
MAX_MODEL_CALLS_PER_ANSWER = 20

STOPPED_ANSWER = (
    "I stopped after {count} steps without finishing the answer. "
    "Please ask again with a narrower question."
)


class ModelCallLimit(HookProvider):
    """End the answer with a note instead of calling the model again past the limit."""

    def __init__(self, max_calls: int = MAX_MODEL_CALLS_PER_ANSWER):
        self.max_calls = max_calls
        self.calls = 0

    def register_hooks(self, registry: HookRegistry, **kwargs) -> None:
        registry.add_callback(BeforeModelCallEvent, self.before_model_call)

    def before_model_call(self, event: BeforeModelCallEvent) -> None:
        self.calls += 1
        if self.calls > self.max_calls:
            logger.warning("Stopped an answer after %d model calls", self.max_calls)
            emit_metric("ModelCallLimitReached", 1)
            # The cancellation text becomes the final answer, with stop reason
            # end_turn, so the conversation is saved as usual.
            event.cancel = STOPPED_ANSWER.format(count=self.max_calls)
