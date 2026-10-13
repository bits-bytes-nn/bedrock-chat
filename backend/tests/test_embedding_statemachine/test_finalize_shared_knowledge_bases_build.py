from unittest.mock import patch

import pytest
from botocore.stub import Stubber
from embedding_statemachine.bedrock_knowledge_base import (
    finalize_shared_knowledge_bases_build as finalize,
)

STACK_NAME = "dev-BrChatSharedKbStack"


@pytest.fixture
def cfn():
    with Stubber(finalize.cfn) as stubber:
        yield stubber
        stubber.assert_no_pending_responses()


def _stack(outputs: list[dict]) -> dict:
    return {
        "Stacks": [
            {
                "StackName": STACK_NAME,
                "CreationTime": "2026-01-01T00:00:00Z",
                "StackStatus": "UPDATE_COMPLETE",
                "Outputs": outputs,
            }
        ]
    }


def test_reads_the_stack_of_the_environment(cfn):
    cfn.add_response(
        "describe_stacks",
        _stack(
            [
                {"OutputKey": "KnowledgeBaseIdhash", "OutputValue": "kb-1"},
                {"OutputKey": "DataSourcehash0", "OutputValue": "ds-1"},
            ]
        ),
        {"StackName": STACK_NAME},
    )
    with patch.dict("os.environ", {"SHARED_KNOWLEDGE_BASES_STACK_NAME": STACK_NAME}):
        result = finalize.handler(
            {"QueuedBots": [], "SharedKnowledgeBases": [{"KnowledgeBaseHash": "hash"}]},
            None,
        )

    assert result["DataSources"] == [
        {"KnowledgeBaseId": "kb-1", "DataSourceId": "ds-1", "FilesDiffs": []}
    ]


def test_fails_without_the_stack_name(cfn):
    with patch.dict("os.environ", clear=False) as environ:
        environ.pop("SHARED_KNOWLEDGE_BASES_STACK_NAME", None)
        with pytest.raises(KeyError):
            finalize.handler({"QueuedBots": [], "SharedKnowledgeBases": []}, None)
