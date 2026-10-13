"""The frontend and the CDK agree with the backend on error codes, limits and names."""

import os
import re
from pathlib import Path
from typing import get_args

os.environ.setdefault("WEBSOCKET_SESSION_TABLE_NAME", "test-websocket-session")

from app import websocket  # noqa: E402
from app.usecases.chat import MAX_CONVERSATION_BYTES  # noqa: E402
from app.utils import (  # noqa: E402
    API_PUBLISHMENT_STACK_PREFIX,
    CUSTOM_BOT_STACK_PREFIX,
)

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend" / "src"


def test_websocket_codes_match_the_frontend():
    source = (FRONTEND / "hooks" / "usePostMessageStreaming.ts").read_text()
    block = re.search(r"PREDICT_ERROR_CODES = \[(.*?)\] as const", source, re.S)
    assert block is not None
    assert set(re.findall(r"'([a-z_]+)'", block.group(1))) == set(
        get_args(websocket.type_error_code)
    )


def test_rest_codes_have_translations():
    raised = {
        code
        for path in (BACKEND / "app").rglob("*.py")
        for code in re.findall(r'\bcode=\(?\s*"([a-z_]+)"', path.read_text())
    }
    assert raised

    source = (FRONTEND / "i18n" / "en" / "index.ts").read_text()
    block = re.search(r"\n(\s+)api: \{\n(.*?)\n\1\}", source, re.S)
    assert block is not None
    translated = set(re.findall(r"^\s+([a-z_]+):", block.group(2), re.M))
    assert raised <= translated, raised - translated


def test_one_message_fits_in_a_conversation():
    source = (FRONTEND / "components" / "InputChatContent.tsx").read_text()
    limit = re.search(r"MAX_FILE_SIZE_TO_SEND_MB = ([\d.]+);", source)
    assert limit is not None
    # Counted in base64. The rest leaves room for the earlier messages and answers.
    assert float(limit.group(1)) * 1024 * 1024 * 4 / 3 <= MAX_CONVERSATION_BYTES * 0.8


def test_stack_names_match_the_cdk():
    source = (BACKEND.parent / "cdk" / "lib" / "utils" / "stack-names.ts").read_text()
    prefixes = dict(re.findall(r'export const (\w+StackPrefix) = "(\w+)";', source))
    assert prefixes == {
        "apiPublishmentStackPrefix": API_PUBLISHMENT_STACK_PREFIX,
        "customBotStackPrefix": CUSTOM_BOT_STACK_PREFIX,
    }
