# core/notifications.py
#
# Wrapper semplice per inviare notifiche FCM (Firebase Cloud Messaging)
# dal backend Streamlit (Python).
#
# Ritorna sempre una tupla:
#   (success_count, total_tokens, error_msg | None)

from __future__ import annotations

import os
from typing import Iterable, Tuple, Optional, Dict

import firebase_admin
from firebase_admin import credentials, messaging

# Percorso del file JSON del service account.
# Metti firebase_service_account.json nella root del progetto (stesso livello di streamlit_app.py)
SERVICE_ACCOUNT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),  # salgo da core/ a root
    "firebase_service_account.json",
)

_firebase_app: Optional[firebase_admin.App] = None


def _init_firebase_app() -> firebase_admin.App:
    """Inizializza l'SDK Admin di Firebase una volta sola (singleton)."""
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    if not os.path.exists(SERVICE_ACCOUNT_PATH):
        raise RuntimeError(
            f"File service account Firebase non trovato: {SERVICE_ACCOUNT_PATH}"
        )

    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    _firebase_app = firebase_admin.initialize_app(cred)
    return _firebase_app


def send_push_to_tokens(
    tokens: Iterable[str],
    title: str,
    body: str,
    data: Optional[Dict[str, str]] = None,
) -> Tuple[int, int, Optional[str]]:
    """
    Invia una notifica push a una lista di token FCM.

    :param tokens: lista/iterabile di token (stringhe)
    :param title: titolo della notifica
    :param body: testo della notifica
    :param data: dizionario opzionale di dati extra (solo stringhe)
    :return: (success_count, total_tokens, error_msg | None)
    """
    # Normalizzo la lista di token
    token_list = [t.strip() for t in tokens if t and str(t).strip()]
    total = len(token_list)

    if total == 0:
        return 0, 0, "Nessun token valido fornito."

    try:
        _init_firebase_app()

        # Data: deve essere {str: str}
        clean_data: Dict[str, str] = {}
        if data:
            for k, v in data.items():
                clean_data[str(k)] = str(v)

        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            tokens=token_list,
            data=clean_data or None,
        )

        response = messaging.send_multicast(message)

        success = response.success_count
        failures = response.failure_count

        error_msg: Optional[str] = None
        if failures:
            # raccolgo qualche dettaglio degli errori (max 3 per non esagerare)
            details = []
            for idx, resp in enumerate(response.responses):
                if not resp.success:
                    token_preview = token_list[idx][:16] + "…" if len(token_list[idx]) > 16 else token_list[idx]
                    details.append(f"{token_preview}: {resp.exception}")
            if details:
                error_msg = "; ".join(details[:3])

        return success, total, error_msg

    except Exception as e:
        # Qualsiasi errore interno viene catturato e rimandato su error_msg,
        # così lo vediamo a schermo invece di spaccare l'app.
        return 0, total, f"Errore invio FCM: {e}"
