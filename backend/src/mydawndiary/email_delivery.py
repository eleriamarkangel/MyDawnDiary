"""Send transactional email without storing credentials or codes in logs."""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import get_settings


class EmailDeliveryError(Exception):
    pass


def send_verification_email(address: str, code: str) -> None:
    _send_code_email(address, code, "Verify your MyDawnDiary email",
                     "Your MyDawnDiary verification code is", "create an account")


def send_password_reset_email(address: str, code: str) -> None:
    _send_code_email(address, code, "Reset your MyDawnDiary password",
                     "Your MyDawnDiary password reset code is", "request a password reset")


def _send_code_email(address: str, code: str, subject: str, introduction: str, action: str) -> None:
    settings = get_settings()
    if not settings.resend_api_key or not settings.resend_from_email:
        raise EmailDeliveryError("Resend API key or sender address is missing")
    payload = {
        "from": settings.resend_from_email,
        "to": [address],
        "subject": subject,
        "html": (f"<p>{introduction} <strong>{code}</strong>.</p>"
                 "<p>It expires in 10 minutes. Never share this code.</p>"
                 f"<p>If you did not {action}, you can ignore this email.</p>"),
    }
    request = Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json",
            "User-Agent": "MyDawnDiary/0.1",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=10):
            pass
    except HTTPError as exc:
        detail = f"Resend rejected the request (HTTP {exc.code})"
        try:
            error = json.loads(exc.read(4096))
        except (OSError, UnicodeError, ValueError):
            error = None
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            message = " ".join(error["message"].split())
            if message:
                message = message.replace(settings.resend_api_key, "[redacted]")
                message = message.replace(code, "[redacted]")[:300]
                detail = f"{detail}: {message}"
        raise EmailDeliveryError(detail) from None
    except (URLError, TimeoutError):
        raise EmailDeliveryError("Could not reach Resend") from None
