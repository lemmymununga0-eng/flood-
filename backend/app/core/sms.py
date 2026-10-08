"""SMS delivery for flood alerts.

Providers: "simulated" (default, sends nothing), "twilio", "africastalking". The provider
is chosen by settings.sms_provider. Phone numbers are used for the one request and are
never persisted or logged in full. A delivery failure is reported per recipient and never
raises, so a provider outage cannot stop an alert from being recorded.
"""
import logging
import re
from dataclasses import dataclass

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

E164 = re.compile(r"^\+[1-9]\d{7,14}$")
MAX_BODY = 320
_TIMEOUT = 10.0


@dataclass
class SmsResult:
    to: str
    status: str  # sent | simulated | failed | rejected
    detail: str = ""

    def as_dict(self) -> dict:
        return {"to": mask(self.to), "status": self.status, "detail": self.detail}


def mask(number: str) -> str:
    return number[:4] + "***" + number[-2:] if len(number) > 6 else "***"


def normalise(raw: str) -> str:
    return re.sub(r"[\s\-()]", "", raw.strip())


def build_body(risk_level: str, location: str, message: str) -> str:
    body = f"FloodShield DEMO [{risk_level.upper()}] {location}: {message}"
    return body if len(body) <= MAX_BODY else body[: MAX_BODY - 1] + "…"


def send_sms(recipients: list[str], body: str) -> list[SmsResult]:
    cfg = get_settings()
    results: list[SmsResult] = []
    valid: list[str] = []
    allowed = cfg.sms_allowed_list
    for raw in dict.fromkeys(normalise(r) for r in recipients if r.strip()):
        if not E164.match(raw):
            results.append(SmsResult(raw, "rejected", "not an international (+...) number"))
        elif allowed and raw not in allowed:
            results.append(SmsResult(raw, "rejected", "number not on the demo allowlist"))
        else:
            valid.append(raw)
    if len(valid) > cfg.sms_max_recipients:
        for raw in valid[cfg.sms_max_recipients:]:
            results.append(
                SmsResult(raw, "rejected", f"over the {cfg.sms_max_recipients}-recipient limit")
            )
        valid = valid[: cfg.sms_max_recipients]

    provider = cfg.sms_provider.lower()
    for number in valid:
        try:
            if provider == "twilio":
                results.append(_twilio(cfg, number, body))
            elif provider == "africastalking":
                results.append(_africastalking(cfg, number, body))
            else:
                results.append(
                    SmsResult(number, "simulated", "no message sent (SMS_PROVIDER=simulated)")
                )
        except Exception as exc:  # a provider/network failure must not break alert creation
            logger.warning("SMS to %s failed: %s", mask(number), type(exc).__name__)
            results.append(SmsResult(number, "failed", "provider unreachable"))
    return results


def _twilio(cfg, number: str, body: str) -> SmsResult:
    if not (cfg.twilio_account_sid and cfg.twilio_auth_token and cfg.twilio_from_number):
        return SmsResult(number, "failed", "Twilio credentials are not configured")
    r = httpx.post(
        f"https://api.twilio.com/2010-04-01/Accounts/{cfg.twilio_account_sid}/Messages.json",
        data={"To": number, "From": cfg.twilio_from_number, "Body": body},
        auth=(cfg.twilio_account_sid, cfg.twilio_auth_token),
        timeout=_TIMEOUT,
    )
    if r.status_code in (200, 201):
        return SmsResult(number, "sent", "accepted by Twilio")
    logger.warning("Twilio rejected SMS to %s: HTTP %s", mask(number), r.status_code)
    return SmsResult(number, "failed", f"Twilio HTTP {r.status_code}")


def _africastalking(cfg, number: str, body: str) -> SmsResult:
    if not (cfg.africastalking_username and cfg.africastalking_api_key):
        return SmsResult(number, "failed", "Africa's Talking credentials are not configured")
    sandbox = cfg.africastalking_username == "sandbox"
    host = "api.sandbox.africastalking.com" if sandbox else "api.africastalking.com"
    data = {"username": cfg.africastalking_username, "to": number, "message": body}
    if cfg.africastalking_sender_id:
        data["from"] = cfg.africastalking_sender_id
    r = httpx.post(
        f"https://{host}/version1/messaging",
        data=data,
        headers={"apiKey": cfg.africastalking_api_key, "Accept": "application/json"},
        timeout=_TIMEOUT,
    )
    if r.status_code not in (200, 201):
        logger.warning("Africa's Talking HTTP %s for %s", r.status_code, mask(number))
        return SmsResult(number, "failed", f"Africa's Talking HTTP {r.status_code}")
    recips = r.json().get("SMSMessageData", {}).get("Recipients", [])
    status = recips[0].get("status", "") if recips else ""
    return SmsResult(
        number, "sent" if status == "Success" else "failed", status or "no recipient status"
    )
