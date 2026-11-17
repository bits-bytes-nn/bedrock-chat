"""The Bedrock runtime clients are created once and shared across threads."""

from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from app import utils


def test_clients_are_reused_per_region_and_attempts():
    utils._runtime_clients.clear()
    with patch.object(
        utils.boto3, "client", side_effect=lambda *a, **k: object()
    ) as create:
        with ThreadPoolExecutor(max_workers=8) as executor:
            clients = list(
                executor.map(
                    lambda _: utils.get_bedrock_runtime_client("r", 3), range(16)
                )
            )
        other = utils.get_bedrock_runtime_client("r", 1)
    utils._runtime_clients.clear()

    assert len({id(client) for client in clients}) == 1
    assert other is not clients[0]
    assert create.call_count == 2
