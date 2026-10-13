"""The frontend translates the error codes that the backend sends."""

import os
import re
from pathlib import Path
from typing import get_args

import pytest

os.environ.setdefault("WEBSOCKET_SESSION_TABLE_NAME", "test-websocket-session")

from app import websocket  # noqa: E402

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend" / "src"

pytestmark = pytest.mark.xfail(
    strict=False, reason="frontend keys land in fix/r10-frontend"
)


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
        for code in re.findall(r'\bcode="([a-z_]+)"', path.read_text())
    }
    assert raised

    source = (FRONTEND / "i18n" / "en" / "index.ts").read_text()
    block = re.search(r"\n(\s+)api: \{\n(.*?)\n\1\}", source, re.S)
    assert block is not None
    translated = set(re.findall(r"^\s+([a-z_]+):", block.group(2), re.M))
    assert raised <= translated, raised - translated
