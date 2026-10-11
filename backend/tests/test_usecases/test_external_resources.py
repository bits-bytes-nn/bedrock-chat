import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, ".")

from app.usecases.bot import validate_external_resource_references
from app.user import User

USER = User(id="user", name="user", email="user@example.com", groups=[])
ADMIN = User(id="admin", name="admin", email="admin@example.com", groups=["Admin"])


def bot(s3_urls=(), existing_kb_id=None, agent_ids=()):
    return SimpleNamespace(
        knowledge=SimpleNamespace(s3_urls=list(s3_urls)),
        bedrock_knowledge_base=SimpleNamespace(exist_knowledge_base_id=existing_kb_id),
        agent=SimpleNamespace(
            tools=[
                SimpleNamespace(
                    tool_type="bedrock_agent",
                    bedrockAgentConfig=SimpleNamespace(agent_id=agent_id),
                )
                for agent_id in agent_ids
            ]
        ),
    )


class TestValidateExternalResourceReferences(unittest.TestCase):
    def test_rejects_new_s3_url_from_user(self):
        with self.assertRaises(PermissionError):
            validate_external_resource_references(USER, bot(s3_urls=["s3://other/"]), None)  # type: ignore[arg-type]

    def test_rejects_existing_knowledge_base_from_user(self):
        with self.assertRaises(PermissionError):
            validate_external_resource_references(USER, bot(existing_kb_id="KB1"), None)  # type: ignore[arg-type]

    def test_rejects_new_bedrock_agent_from_user(self):
        with self.assertRaises(PermissionError):
            validate_external_resource_references(USER, bot(agent_ids=["AGENT1"]), None)  # type: ignore[arg-type]

    def test_keeps_references_the_bot_already_has(self):
        current = bot(
            s3_urls=["s3://docs/"], existing_kb_id="KB1", agent_ids=["AGENT1"]
        )
        validate_external_resource_references(USER, current, current)  # type: ignore[arg-type]

    def test_allows_admin(self):
        new = bot(s3_urls=["s3://other/"], existing_kb_id="KB1", agent_ids=["AGENT1"])
        validate_external_resource_references(ADMIN, new, None)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
