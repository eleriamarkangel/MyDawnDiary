"""Small single-process traffic guard and privacy-safe request metrics."""

from dataclasses import dataclass
from email.message import EmailMessage
import json
import logging
import os
import smtplib
from threading import Lock, Thread
from time import monotonic
from urllib.request import Request, urlopen

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


# Uvicorn already configures this logger for both console and systemd/journald.
logger = logging.getLogger("uvicorn.error")


def _positive_int(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value < 1:
        raise ValueError(f"{name} must be positive")
    return value


@dataclass(frozen=True)
class TrafficConfig:
    requests_per_minute: int = 120
    auth_requests_per_minute: int = 10
    alert_requests_per_minute: int = 300
    alert_cooldown_minutes: int = 15
    resend_api_key: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    mail_from: str = ""
    mail_to: tuple[str, ...] = ()

    @classmethod
    def from_env(cls) -> "TrafficConfig":
        return cls(
            requests_per_minute=_positive_int("REQUESTS_PER_MINUTE", 120),
            auth_requests_per_minute=_positive_int("AUTH_REQUESTS_PER_MINUTE", 10),
            alert_requests_per_minute=_positive_int("ALERT_REQUESTS_PER_MINUTE", 300),
            alert_cooldown_minutes=_positive_int("ALERT_COOLDOWN_MINUTES", 15),
            resend_api_key=os.getenv("RESEND_API_KEY", ""),
            smtp_host=os.getenv("ALERT_SMTP_HOST", ""),
            smtp_port=_positive_int("ALERT_SMTP_PORT", 587),
            smtp_username=os.getenv("ALERT_SMTP_USERNAME", ""),
            smtp_password=os.getenv("ALERT_SMTP_PASSWORD", ""),
            mail_from=os.getenv("ALERT_EMAIL_FROM", ""),
            mail_to=tuple(address.strip() for address in os.getenv("ALERT_EMAIL_TO", "").split(",") if address.strip()),
        )


def send_spike_email(config: TrafficConfig, count: int) -> None:
    body = (
        f"The API received {count} requests in the current minute, "
        f"reaching the configured threshold of {config.alert_requests_per_minute}.\n"
        "Check the API and reverse proxy logs for the cause.\n"
    )
    if config.resend_api_key:
        payload = json.dumps({
            "from": config.mail_from,
            "to": list(config.mail_to),
            "subject": "MyDawnDiary API traffic alert",
            "text": body,
        }).encode("utf-8")
        request = Request(
            "https://api.resend.com/emails",
            data=payload,
            headers={"Authorization": f"Bearer {config.resend_api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=5):
                pass
        except Exception:
            logger.exception("Traffic alert email could not be sent through Resend")
        return

    message = EmailMessage()
    message["Subject"] = "MyDawnDiary API traffic alert"
    message["From"] = config.mail_from
    message["To"] = ", ".join(config.mail_to)
    message.set_content(body)
    try:
        with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=5) as server:
            server.starttls()
            server.login(config.smtp_username, config.smtp_password)
            server.send_message(message)
    except Exception:
        logger.exception("Traffic alert email could not be sent")


class TrafficMiddleware:
    """Fixed minute limits per direct client and aggregate traffic alerts.

    Use a single API worker, or put shared rate limits at the reverse proxy.
    """

    def __init__(self, app: ASGIApp, config: TrafficConfig | None = None) -> None:
        self.app = app
        self.config = config or TrafficConfig.from_env()
        self._lock = Lock()
        self._window = -1
        self._clients: dict[str, tuple[int, int]] = {}
        self._total = 0
        self._rejected = 0
        self._server_errors = 0
        self._last_alert_at = float("-inf")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        now = monotonic()
        window = int(now // 60)
        client = scope.get("client")
        client_key = client[0] if client else "unknown"
        is_auth = scope.get("path", "").startswith("/auth/")
        rejected = False
        alert_count = 0

        with self._lock:
            if window != self._window:
                if self._window != -1:
                    logger.info(
                        "traffic minute=%s requests=%s throttled=%s server_errors=%s",
                        self._window, self._total, self._rejected, self._server_errors,
                    )
                self._window = window
                self._clients.clear()
                self._total = self._rejected = self._server_errors = 0

            self._total += 1
            general, auth = self._clients.get(client_key, (0, 0))
            general += 1
            auth += int(is_auth)
            # Bound memory when traffic comes from many distinct addresses.
            rejected = (
                (client_key not in self._clients and len(self._clients) >= 10_000)
                or general > self.config.requests_per_minute
                or (is_auth and auth > self.config.auth_requests_per_minute)
            )
            if rejected:
                self._rejected += 1
            else:
                self._clients[client_key] = (general, auth)

            if self._total >= self.config.alert_requests_per_minute and now - self._last_alert_at >= self.config.alert_cooldown_minutes * 60:
                self._last_alert_at = now
                alert_count = self._total

        if alert_count:
            logger.warning("Traffic spike: %s requests in the current minute", alert_count)
            mail_ready = self.config.mail_from and self.config.mail_to and (
                self.config.resend_api_key or all((self.config.smtp_host, self.config.smtp_username, self.config.smtp_password))
            )
            if mail_ready:
                Thread(target=send_spike_email, args=(self.config, alert_count), daemon=True).start()

        if rejected:
            response = JSONResponse({"detail": "Too many requests"}, status_code=429, headers={"Retry-After": "60"})
            await response(scope, receive, send)
            return

        async def track_status(message: dict) -> None:
            if message["type"] == "http.response.start" and message["status"] >= 500:
                with self._lock:
                    self._server_errors += 1
            await send(message)

        try:
            await self.app(scope, receive, track_status)
        except Exception:
            with self._lock:
                self._server_errors += 1
            logger.exception("Unhandled API request error")
            raise
