from httpx import AsyncClient

from tests.helpers import activate_profile


async def test_register_create_profile(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/registration",
        json={"email": "user@mail.com", "password": "123456"},
    )

    assert response.status_code == 201
    assert response.json() == {"id": 1}


async def test_register_duplicate_email_returns_409(client: AsyncClient) -> None:
    payload = {"email": "user@mail.com", "password": "123456"}

    first_response = await client.post("/api/v1/registration", json=payload)
    second_response = await client.post("/api/v1/registration", json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json() == {"detail": "error.email.already_exists"}


async def test_login_inactive_user_returns_401(client: AsyncClient) -> None:
    payload = {"email": "user@mail.com", "password": "123456"}

    await client.post("/api/v1/registration", json=payload)

    response = await client.post("/api/v1/auth/login", json=payload)

    assert response.status_code == 401
    assert response.json() == {"detail": "error.auth.invalid_credentials"}


async def test_login_active_user_returns_access_token(client: AsyncClient) -> None:
    payload = {"email": "user@mail.com", "password": "123456"}

    registration_response = await client.post("/api/v1/registration", json=payload)
    await activate_profile(profile_id=registration_response.json()["id"])

    response = await client.post("/api/v1/auth/login", json=payload)

    body = response.json()

    assert response.status_code == 200
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 3600
    assert isinstance(body["access_token"], str)
    assert body["access_token"]


async def test_login_with_wrong_password_returns_401(client: AsyncClient) -> None:
    payload = {"email": "user@mail.com", "password": "123456"}

    registration_response = await client.post("/api/v1/registration", json=payload)
    await activate_profile(profile_id=registration_response.json()["id"])

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "user@mail.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "error.auth.invalid_credentials"}
