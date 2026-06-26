from fastapi import Request, Response

from app.core.security import SESSION_COOKIE, create_oauth_state, read_session_cookie, set_session_cookie, verify_oauth_state


def test_session_cookie_is_signed_and_http_only():
    response = Response()
    set_session_cookie(response, "session-id", "test-secret-value-long-enough", secure=False)

    cookie = response.headers["set-cookie"]
    assert SESSION_COOKIE in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "session-id" not in cookie


def test_signed_cookie_round_trip():
    response = Response()
    set_session_cookie(response, "session-id", "test-secret-value-long-enough", secure=False)
    signed = response.headers["set-cookie"].split("=", 1)[1].split(";", 1)[0]
    request = Request({"type": "http", "headers": [(b"cookie", f"{SESSION_COOKIE}={signed}".encode())]})

    assert read_session_cookie(request, "test-secret-value-long-enough") == "session-id"


def test_oauth_state_is_signed_and_verifiable_without_cookie():
    state = create_oauth_state("test-secret-value-long-enough")

    assert verify_oauth_state("test-secret-value-long-enough", state)
    assert not verify_oauth_state("different-secret-value", state)
