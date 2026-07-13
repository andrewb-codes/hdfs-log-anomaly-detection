from httpx import AsyncClient

from tests.helpers import make_admin, register_and_login

ADMIN_PROFILE_RESPONSE_FIELDS = {
    "id",
    "email",
    "status",
    "role",
    "version",
    "created_at",
}


async def test_admin_profiles_without_token_returns_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/admin/profiles")

    assert response.status_code == 401
    assert response.json() == {"detail": "error.auth.unauthorized"}


async def test_user_cannot_search_admin_profiles(client: AsyncClient) -> None:
    token = await register_and_login(client)

    response = await client.get(
        "/api/v1/admin/profiles",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "error.auth.forbidden"}


async def test_admin_can_search_profiles(client: AsyncClient) -> None:
    admin_token = await register_and_login(client, email="admin@mail.com")
    await register_and_login(client, email="user@mail.com")

    await make_admin(profile_id=1)

    response = await client.get(
        "/api/v1/admin/profiles",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    body = response.json()

    assert response.status_code == 200
    assert set(body) == {"items", "has_next"}
    assert body["has_next"] is False
    assert len(body["items"]) == 2
    assert set(body["items"][0]) == ADMIN_PROFILE_RESPONSE_FIELDS


async def test_admin_search_profiles_filters_by_email_prefix(
    client: AsyncClient,
) -> None:
    admin_token = await register_and_login(client, email="admin@mail.com")
    await register_and_login(client, email="alice@mail.com")
    await register_and_login(client, email="bob@mail.com")

    await make_admin(profile_id=1)

    response = await client.get(
        "/api/v1/admin/profiles?email_starts_with=ali",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    body = response.json()

    assert response.status_code == 200
    assert len(body["items"]) == 1
    assert body["items"][0]["email"] == "alice@mail.com"


async def test_admin_search_profiles_filters_by_role(client: AsyncClient) -> None:
    admin_token = await register_and_login(client, email="admin@mail.com")
    await register_and_login(client, email="user@mail.com")

    await make_admin(profile_id=1)

    response = await client.get(
        "/api/v1/admin/profiles?role=ADMIN",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    body = response.json()

    assert response.status_code == 200
    assert len(body["items"]) == 1
    assert body["items"][0]["email"] == "admin@mail.com"
    assert body["items"][0]["role"] == "ADMIN"


async def test_admin_search_profiles_filters_by_status(client: AsyncClient) -> None:
    admin_token = await register_and_login(client, email="admin@mail.com")
    await client.post(
        "/api/v1/registration",
        json={"email": "inactive@mail.com", "password": "123456"},
    )

    await make_admin(profile_id=1)

    response = await client.get(
        "/api/v1/admin/profiles?status=INACTIVE",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    body = response.json()

    assert response.status_code == 200
    assert len(body["items"]) == 1
    assert body["items"][0]["email"] == "inactive@mail.com"
    assert body["items"][0]["status"] == "INACTIVE"


async def test_admin_profiles_pagination_has_next(client: AsyncClient) -> None:
    admin_token = await register_and_login(client, email="admin@mail.com")
    await register_and_login(client, email="user1@mail.com")
    await register_and_login(client, email="user2@mail.com")

    await make_admin(profile_id=1)

    first_page_response = await client.get(
        "/api/v1/admin/profiles?page=1&page_size=2",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    second_page_response = await client.get(
        "/api/v1/admin/profiles?page=2&page_size=2",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    first_page = first_page_response.json()
    second_page = second_page_response.json()

    assert first_page_response.status_code == 200
    assert second_page_response.status_code == 200
    assert len(first_page["items"]) == 2
    assert first_page["has_next"] is True
    assert len(second_page["items"]) == 1
    assert second_page["has_next"] is False


async def test_admin_can_change_profile_status(client: AsyncClient) -> None:
    admin_token = await register_and_login(client, email="admin@mail.com")
    await client.post(
        "/api/v1/registration",
        json={"email": "user@mail.com", "password": "123456"},
    )

    await make_admin(profile_id=1)

    response = await client.patch(
        "/api/v1/admin/profiles/2/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "ACTIVE", "version": 0},
    )

    body = response.json()

    assert response.status_code == 200
    assert set(body) == ADMIN_PROFILE_RESPONSE_FIELDS
    assert body["id"] == 2
    assert body["status"] == "ACTIVE"
    assert body["version"] == 1


async def test_admin_can_change_profile_role(client: AsyncClient) -> None:
    admin_token = await register_and_login(client, email="admin@mail.com")
    await register_and_login(client, email="user@mail.com")

    await make_admin(profile_id=1)

    response = await client.patch(
        "/api/v1/admin/profiles/2/role",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role": "ADMIN", "version": 0},
    )

    body = response.json()

    assert response.status_code == 200
    assert set(body) == ADMIN_PROFILE_RESPONSE_FIELDS
    assert body["id"] == 2
    assert body["role"] == "ADMIN"
    assert body["version"] == 1


async def test_admin_cannot_change_own_status(client: AsyncClient) -> None:
    admin_token = await register_and_login(client, email="admin@mail.com")

    await make_admin(profile_id=1)

    response = await client.patch(
        "/api/v1/admin/profiles/1/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "ACTIVE", "version": 0},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "error.admin.self_modification"}


async def test_admin_cannot_change_own_role(client: AsyncClient) -> None:
    admin_token = await register_and_login(client, email="admin@mail.com")

    await make_admin(profile_id=1)

    response = await client.patch(
        "/api/v1/admin/profiles/1/role",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role": "USER", "version": 0},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "error.admin.self_modification"}


async def test_admin_change_profile_status_with_wrong_version_returns_409(
    client: AsyncClient,
) -> None:
    admin_token = await register_and_login(client, email="admin@mail.com")
    await register_and_login(client, email="user@mail.com")

    await make_admin(profile_id=1)

    response = await client.patch(
        "/api/v1/admin/profiles/2/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "ACTIVE", "version": 999},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "error.profile.version_conflict"}


async def test_admin_change_profile_role_with_wrong_version_returns_409(
    client: AsyncClient,
) -> None:
    admin_token = await register_and_login(client, email="admin@mail.com")
    await register_and_login(client, email="user@mail.com")

    await make_admin(profile_id=1)

    response = await client.patch(
        "/api/v1/admin/profiles/2/role",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role": "ADMIN", "version": 999},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "error.profile.version_conflict"}


async def test_admin_change_missing_profile_status_returns_404(
    client: AsyncClient,
) -> None:
    admin_token = await register_and_login(client, email="admin@mail.com")

    await make_admin(profile_id=1)

    response = await client.patch(
        "/api/v1/admin/profiles/999/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "ACTIVE", "version": 0},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "error.profile.not_found"}


async def test_admin_change_missing_profile_role_returns_404(
    client: AsyncClient,
) -> None:
    admin_token = await register_and_login(client, email="admin@mail.com")

    await make_admin(profile_id=1)

    response = await client.patch(
        "/api/v1/admin/profiles/999/role",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role": "ADMIN", "version": 0},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "error.profile.not_found"}
