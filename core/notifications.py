# core/notifications.py
# Invio notifiche push via Firebase Cloud Messaging (FCM)

from __future__ import annotations

import os
import logging
from typing import List, Dict, Any

import requests
import streamlit as st


FCM_API_URL = "https://fcm.googleapis.com/fcm/send"


def _get_server_key() -> str:
    """
    Legge la chiave server FCM da:
    - st.secrets["fcm_server_key"] (consigliato su Streamlit Cloud)
    - oppure variabile d'ambiente FCM_SERVER_KEY (fallback)
    """
    key = ""
    try:
        key = st.secrets.get("fcm_server_key", "")
    except Exception:
        pass

    if not key:
        key = os.environ.get("FCM_SERVER_KEY", "")

    return key or ""


def send_push_to_tokens(
    tokens: List[str],
    title: str,
    body: str,
) -> Dict[str, Any]:
    """
    Invia una notifica push (title + body) alla lista di token indicata.
    Ritorna un dizionario con info di debug.
    """
    server_key = _get_server_key()
    if not server_key:
        logging.warning("FCM server key mancante.")
        return {"ok": False, "reason": "missing_server_key"}

    if not tokens:
        return {"ok": False, "reason": "no_tokens"}

    headers = {
        "Authorization": f"key={server_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "registration_ids": tokens,
        "notification": {
            "title": title,
            "body": body,
        },
    }

    try:
        resp = requests.post(FCM_API_URL, headers=headers, json=payload, timeout=10)
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text[:500]}

        logging.info("FCM response: %s", data)

        return {
            "ok": resp.ok,
            "status_code": resp.status_code,
            "response": data,
        }
    except Exception as exc:
        logging.exception("Errore nell'invio FCM: %s", exc)
        return {"ok": False, "reason": "exception", "error": str(exc)}
