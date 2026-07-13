from httpx import AsyncClient

from hdfs_anomaly.app.core.security import create_access_token
from tests.helpers import register_and_login

PROFILE_RESPONSE_FIELDS = {
    "id",
    "email",
    "status",
    "role",
    "version",
    "created_at",
}


async def test_get_profile_without_token_returns_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/profile")

    assert response.status_code == 401
    assert response.json() == {"detail": "error.auth.unauthorized"}


async def test_get_profile_with_inactive_token_returns_401(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/registration",
        json={"email": "user@mail.com", "password": "123456"},
    )
    token = create_access_token(profile_id=1, role="USER")

    response = await client.get(
        "/api/v1/profile",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "error.auth.unauthorized"}


async def test_get_profile_returns_current_active_profile(client: AsyncClient) -> None:
    token = await register_and_login(client)

    response = await client.get(
        "/api/v1/profile",
        headers={"Authorization": f"Bearer {token}"},
    )

    body = response.json()

    assert response.status_code == 200
    assert set(body) == PROFILE_RESPONSE_FIELDS
    assert body["id"] == 1
    assert body["email"] == "user@mail.com"
    assert body["role"] == "USER"
    assert body["status"] == "ACTIVE"
    assert body["version"] == 0
    assert isinstance(body["created_at"], str)


async def test_change_email_updates_email(client: AsyncClient) -> None:
    token = await register_and_login(client)

    response = await client.patch(
        "/api/v1/profile/email",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "new_email": "new@mail.com",
            "current_password": "123456",
            "version": 0,
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert set(body) == PROFILE_RESPONSE_FIELDS
    assert body["email"] == "new@mail.com"
    assert body["version"] == 1


async def test_change_email_with_wrong_password_returns_400(
    client: AsyncClient,
) -> None:
    token = await register_and_login(client)

    response = await client.patch(
        "/api/v1/profile/email",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "new_email": "new@mail.com",
            "current_password": "wrong-password",
            "version": 0,
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "error.password.invalid_current"}


async def test_change_email_to_same_email_returns_400(client: AsyncClient) -> None:
    token = await register_and_login(client)

    response = await client.patch(
        "/api/v1/profile/email",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "new_email": "user@mail.com",
            "current_password": "123456",
            "version": 0,
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "error.email.same_as_current"}


async def test_change_email_to_existing_email_returns_409(client: AsyncClient) -> None:
    token = await register_and_login(client)
    await register_and_login(client, email="existing@mail.com")

    response = await client.patch(
        "/api/v1/profile/email",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "new_email": "existing@mail.com",
            "current_password": "123456",
            "version": 0,
        },
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "error.email.already_exists"}


async def test_change_email_with_wrong_version_returns_409(client: AsyncClient) -> None:
    token = await register_and_login(client)

    response = await client.patch(
        "/api/v1/profile/email",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "new_email": "new@mail.com",
            "current_password": "123456",
            "version": 999,
        },
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "error.profile.version_conflict"}


async def test_change_password_updates_password(client: AsyncClient) -> None:
    token = await register_and_login(client)

    response = await client.patch(
        "/api/v1/profile/password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "123456",
            "new_password": "new-password",
            "version": 0,
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert set(body) == PROFILE_RESPONSE_FIELDS
    assert body["email"] == "user@mail.com"
    assert body["version"] == 1

    old_password_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "user@mail.com", "password": "123456"},
    )
    new_password_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "user@mail.com", "password": "new-password"},
    )

    assert old_password_response.status_code == 401
    assert old_password_response.json() == {"detail": "error.auth.invalid_credentials"}
    assert new_password_response.status_code == 200


async def test_change_password_with_wrong_current_password_returns_400(
    client: AsyncClient,
) -> None:
    token = await register_and_login(client)

    response = await client.patch(
        "/api/v1/profile/password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "wrong-password",
            "new_password": "new-password",
            "version": 0,
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "error.password.invalid_current"}


async def test_change_password_to_same_password_returns_400(
    client: AsyncClient,
) -> None:
    token = await register_and_login(client)

    response = await client.patch(
        "/api/v1/profile/password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "123456",
            "new_password": "123456",
            "version": 0,
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "error.password.same_as_current"}


async def test_change_password_with_wrong_version_returns_409(
    client: AsyncClient,
) -> None:
    token = await register_and_login(client)

    response = await client.patch(
        "/api/v1/profile/password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "123456",
            "new_password": "new-password",
            "version": 999,
        },
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "error.profile.version_conflict"}


async def test_delete_profile_returns_204_and_invalidates_token(client: AsyncClient) -> None:
    token = await register_and_login(client)

    delete_response = await client.delete(
        "/api/v1/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    profile_response = await client.get(
        "/api/v1/profile",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert delete_response.status_code == 204
    assert profile_response.status_code == 401
    assert profile_response.json() == {"detail": "error.auth.unauthorized"}
