from unittest.mock import MagicMock, patch

import pytest
from app import main
from app.dependencies import (
    check_admin,
    check_creating_bot_allowed,
    check_publish_allowed,
    get_current_user,
)
from app.user import User
from fastapi import HTTPException
from fastapi.testclient import TestClient
from tests.test_repositories.utils.bot_factory import create_test_private_bot
from tests.test_usecases.utils.user_factory import (
    create_test_admin_user,
    create_test_user,
)

NO_GROUPS = create_test_user("plain_user")
ADMIN = create_test_admin_user("admin_user")


@pytest.fixture
def client_as():
    """Return a function that makes a TestClient whose requests run as `user`.

    The middleware puts the user in `request.state` and the `check_*` dependencies
    read it again through `get_current_user`; both are replaced.
    """
    patches = []

    def make(user: User) -> TestClient:
        main.app.dependency_overrides[get_current_user] = lambda: user
        p = patch.object(main, "_user_from_authorization", return_value=user)
        p.start()
        patches.append(p)
        return TestClient(main.app, headers={"Authorization": "Bearer token"})

    yield make
    for p in patches:
        p.stop()
    main.app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "method, path, reason",
    [
        ("GET", "/admin/published-bots", "Only admin"),
        ("GET", "/admin/public-bots", "Only admin"),
        ("GET", "/admin/users", "Only admin"),
        ("GET", "/admin/bot/public/bot1", "Only admin"),
        ("PATCH", "/admin/bot/bot1/pushed", "Only admin"),
        (
            "GET",
            "/bot/bot1/presigned-url?filename=a.txt&contentType=text/plain",
            "not allowed to create bot",
        ),
        ("GET", "/bot/bot1/publication", "not allowed to publish bot"),
        # The user routes raise PermissionError themselves.
        ("GET", "/user/search?prefix=a", "Search user is not allowed"),
        ("GET", "/user/group/search?prefix=a", "Search user group is not allowed"),
        ("GET", "/user/someone", "Get user is not allowed"),
    ],
)
def test_user_without_groups_gets_403(client_as, method, path, reason):
    with (
        patch("app.routes.admin.find_bot_by_id") as find_bot,
        patch("app.routes.user.search_user_by_email_prefix") as search_user,
        patch("app.routes.user.search_group_by_name_prefix") as search_group,
        patch("app.routes.user.get_user_by_id") as get_user,
    ):
        response = client_as(NO_GROUPS).request(method, path, json={})

    assert response.status_code == 403
    assert reason in response.text
    for lookup in (find_bot, search_user, search_group, get_user):
        lookup.assert_not_called()


@pytest.mark.parametrize(
    "check, groups, allowed",
    [
        (check_admin, [], False),
        (check_admin, ["CreatingBotAllowed", "PublishAllowed"], False),
        (check_admin, ["Admin"], True),
        (check_creating_bot_allowed, [], False),
        (check_creating_bot_allowed, ["PublishAllowed"], False),
        (check_creating_bot_allowed, ["CreatingBotAllowed"], True),
        (check_creating_bot_allowed, ["Admin"], True),
        (check_publish_allowed, [], False),
        (check_publish_allowed, ["CreatingBotAllowed"], False),
        (check_publish_allowed, ["PublishAllowed"], True),
        (check_publish_allowed, ["Admin"], True),
    ],
)
def test_check_dependencies(check, groups, allowed):
    user = create_test_user("user", groups=groups)
    if allowed:
        check(user=user)
    else:
        with pytest.raises(HTTPException) as e:
            check(user=user)
        assert e.value.status_code == 403


@pytest.mark.parametrize(
    "user, status",
    [
        (create_test_user("owner"), 200),
        (create_test_user("other"), 403),
        # The route checks ownership only, so an admin is refused too.
        (ADMIN, 403),
    ],
)
def test_get_private_bot_checks_owner(client_as, user, status):
    bot = create_test_private_bot("bot1", False, "owner")
    with patch("app.routes.bot.find_bot_by_id", return_value=bot):
        response = client_as(user).get("/bot/private/bot1")

    assert response.status_code == status
    if status == 200:
        assert response.json()["id"] == "bot1"


def test_unpublished_bot_returns_a_coded_404(client_as):
    # The frontend translates error.api.<code>.
    bot = MagicMock(published_api_codebuild_id=None)
    with patch("app.usecases.publication.find_bot_by_id", return_value=bot):
        response = client_as(ADMIN).get("/bot/bot1/publication")

    assert response.status_code == 404
    assert response.json()["code"] == "bot_not_published"
    assert "is not published" in response.json()["errors"][0]
