"""SMS provider layer for manually triggered flood alerts.

Providers: "simulated" (default; sends nothing) and "africastalking". Nothing in this
module decides WHO is texted or WHEN - callers pass an explicit recipient list, and the
only caller is the administrator-triggered broadcast endpoint.

Two things are deliberately kept apart:
  * submission  - did the provider accept the message for sending? (answered here, by the
                  provider's synchronous response)
  * delivery    - did it reach the handset? (answered later, only by the provider's
                  delivery-report callback; never inferred from submission)

A network failure or timeout is reported as "unknown", not "failed": the request may have
reached the provider, so the caller must not assume the message was not sent.
"""
import logging
import re
from dataclasses import dataclass

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

E164 = re.compile(r"^\+[1-9]\d{7,14}$")
MAX_BODY = 320
_TIMEOUT = 15.0

# Africa's Talking per-recipient statusCode values that mean "accepted for sending".
# 100 Processed, 101 Sent, 102 Queued. Everything else (e.g. 402 InvalidSenderId,
# 403 InvalidPhoneNumber, 405 InsufficientBalance, 406 UserInBlacklist) is a rejection.
_AT_ACCEPTED = {100, 101, 102}

SUBMISSION_STATUSES = ("pending", "accepted", "rejected", "failed", "unknown", "simulated")


@dataclass
class ProviderResult:
    phone: str
    submission: str  # accepted | rejected | failed | unknown | simulated
    detail: str = ""
    message_id: str | None = None
    provider_status: str = ""
    status_code: int | None = None
    cost: str | None = None


def mask(number: str) -> str:
    return number[:4] + "***" + number[-2:] if len(number) > 6 else "***"


def normalise(raw: str) -> str:
    return re.sub(r"[\s\-()]", "", raw.strip())


def count_segments(body: str) -> int:
    """Approximate SMS parts. GSM-7 text is 160 chars (153 when split); anything outside
    plain ASCII is assumed UCS-2: 70 chars (67 when split). An estimate - carriers decide."""
    n = len(body)
    if body.isascii():
        return 1 if n <= 160 else -(-n // 153)
    return 1 if n <= 70 else -(-n // 67)


def provider_status(cfg: Settings | None = None) -> dict:
    """What is configured, and exactly what is missing. Never contains a secret."""
    cfg = cfg or get_settings()
    provider = cfg.sms_provider
    missing: list[str] = []
    if provider == "africastalking":
        env = cfg.africastalking_environment
        if env not in ("sandbox", "production"):
            missing.append("AFRICASTALKING_ENVIRONMENT must be 'sandbox' or 'production'")
        if not cfg.africastalking_username:
            missing.append("AFRICASTALKING_USERNAME")
        if not cfg.africastalking_api_key:
            missing.append("AFRICASTALKING_API_KEY")
        if env == "sandbox" and cfg.africastalking_username not in ("", "sandbox"):
            missing.append("sandbox environment requires AFRICASTALKING_USERNAME=sandbox")
        if env == "production" and cfg.africastalking_username == "sandbox":
            missing.append("production environment cannot use the 'sandbox' username")
    elif provider != "simulated":
        missing.append(f"SMS_PROVIDER '{provider}' is not supported (use simulated or africastalking)")
    return {
        "provider": provider,
        "environment": cfg.africastalking_environment if provider == "africastalking" else "none",
        "real": provider == "africastalking",
        "configured": not missing,
        "missing": missing,
        "broadcast_enabled": cfg.sms_broadcast_enabled,
        "sender_id_set": bool(cfg.africastalking_sender_id),
        "delivery_reports_enabled": bool(cfg.sms_webhook_secret),
        "stop_reply_enabled": bool(cfg.sms_webhook_secret),
    }


def build_body(risk_level: str, location: str, message: str, *, test: bool = False) -> str:
    cfg = get_settings()
    head = f"{cfg.sms_message_prefix} {'TEST ' if test else ''}[{risk_level.upper()}] {location}: {message}"
    # Only advertise STOP when the inbound callback is actually configured to act on it.
    if cfg.sms_webhook_secret and not test:
        head += " Reply STOP to opt out."
    return head


def is_allowed(number: str) -> bool:
    allowed = get_settings().sms_allowed_list
    return not allowed or number in allowed


def submit(numbers: list[str], body: str) -> list[ProviderResult]:
    """Submit one body to explicit E.164 numbers. Never raises: every failure is a result."""
    cfg = get_settings()
    status = provider_status(cfg)
    if cfg.sms_provider == "simulated":
        return [
            ProviderResult(n, "simulated", "no message sent (SMS_PROVIDER=simulated)",
                           provider_status="simulated")
            for n in numbers
        ]
    if not status["configured"]:
        why = "; ".join(status["missing"])
        return [ProviderResult(n, "failed", f"provider not configured: {why}") for n in numbers]
    try:
        return _africastalking(cfg, numbers, body)
    except Exception as exc:  # network/parse failure: outcome is genuinely unknown
        logger.warning("Africa's Talking request failed: %s", type(exc).__name__)
        return [
            ProviderResult(n, "unknown", f"no usable response from provider ({type(exc).__name__}); "
                           "the message may or may not have been sent")
            for n in numbers
        ]


def _africastalking(cfg: Settings, numbers: list[str], body: str) -> list[ProviderResult]:
    sandbox = cfg.africastalking_environment == "sandbox"
    host = "api.sandbox.africastalking.com" if sandbox else "api.africastalking.com"
    data = {"username": cfg.africastalking_username, "to": ",".join(numbers), "message": body}
    if cfg.africastalking_sender_id:
        data["from"] = cfg.africastalking_sender_id
    r = httpx.post(
        f"https://{host}/version1/messaging",
        data=data,
        headers={"apiKey": cfg.africastalking_api_key, "Accept": "application/json"},
        timeout=_TIMEOUT,
    )
    if r.status_code not in (200, 201):
        logger.warning("Africa's Talking HTTP %s", r.status_code)
        # 4xx = the request was refused outright, so nothing was sent. 5xx is ambiguous.
        kind = "failed" if r.status_code < 500 else "unknown"
        return [ProviderResult(n, kind, f"provider HTTP {r.status_code}") for n in numbers]
    recipients = r.json().get("SMSMessageData", {}).get("Recipients", [])
    by_number = {normalise(str(x.get("number", ""))): x for x in recipients}
    results: list[ProviderResult] = []
    for n in numbers:
        x = by_number.get(n)
        if x is None:
            results.append(ProviderResult(n, "unknown", "provider response did not mention this number"))
            continue
        code = x.get("statusCode")
        accepted = code in _AT_ACCEPTED
        results.append(
            ProviderResult(
                n,
                "accepted" if accepted else "rejected",
                "accepted by Africa's Talking for sending" if accepted
                else f"rejected: {x.get('status', 'unknown reason')}",
                message_id=x.get("messageId") or None,
                provider_status=str(x.get("status", "")),
                status_code=code if isinstance(code, int) else None,
                cost=x.get("cost") or None,
            )
        )
    return results
