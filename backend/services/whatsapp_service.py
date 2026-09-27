"""WhatsApp Cloud API — same pack text as email, no Web bots."""

from __future__ import annotations

import os
from typing import Any

import httpx

from logger import logger

GRAPH_VERSION = os.getenv("WHATSAPP_GRAPH_VERSION", "v21.0")


def whatsapp_configured() -> bool:
    return bool(os.getenv("WHATSAPP_TOKEN") and os.getenv("WHATSAPP_PHONE_NUMBER_ID") and os.getenv("WHATSAPP_TO"))


def send_whatsapp_text(body: str) -> dict[str, Any]:
    token = os.getenv("WHATSAPP_TOKEN")
    phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    to = os.getenv("WHATSAPP_TO")
    if not token or not phone_id or not to:
        msg = "WhatsApp not configured (WHATSAPP_TOKEN / WHATSAPP_PHONE_NUMBER_ID / WHATSAPP_TO)"
        logger.info(f"Arrr! {msg}")
        return {"success": False, "configured": False, "detail": msg}

    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{phone_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"preview_url": True, "body": body[:4096]},
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, json=payload, headers={"Authorization": f"Bearer {token}"})
        if resp.status_code >= 400:
            detail = resp.text[:500]
            logger.error(
                "Arrr! WhatsApp send failed",
                context={"status": resp.status_code, "detail": detail},
            )
            return {"success": False, "configured": True, "detail": detail}
        return {"success": True, "configured": True, "detail": resp.json()}
    except httpx.HTTPError as exc:
        logger.error("Arrr! WhatsApp HTTP error", context={"error": str(exc)})
        return {"success": False, "configured": True, "detail": str(exc)}
