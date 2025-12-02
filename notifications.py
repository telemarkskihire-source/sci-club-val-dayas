# core/notifications.py
#
# Integrazione Firebase Cloud Messaging (FCM) per l'app Sci Club Val d'Ayas.
# Usa il service account salvato nei secrets Streamlit:
#
# FIREBASE_PROJECT_ID
# FIREBASE_SERVICE_ACCOUNT_JSON
#
# Funzioni principali:
# - send_push_to_tokens(tokens, title, body, data)
# - send_push_to_user_ids(db, user_ids, title, body, data)  [per il futuro]

from __future__ import annotations

import json
from typing import Iterable, Dict, Any, Tuple, List

import streamlit as st
import firebase_admin
from firebase_admin import credentials, messaging
from sqlalchemy.orm import Session

from core.models import DeviceToken


# ---------- INIT FIREBASE APP ----------

def _get_firebase_app():
    """
    Inizializza Firebase Admin usando il JSON del service account
    presente nei secrets Streamlit.

    Ritorna:
        - istanza di firebase_admin.App se ok
        - None se non configurato
    """
    # Se è già inizializzato, lo riuso
    if firebase_admin._apps:
        return firebase_admin.get_app()

    sa_json = st.secrets.get("FIREBASE_SERVICE_ACCOUNT_JSON", None)
    if not sa_json:
        # Nessuna configurazione trovata
        return None

    # Nei secrets lo abbiamo salvato come stringona JSON
    if isinstance(sa_json, str):
        try:
            data = json.loads(sa_json)
        except json.JSONDecodeError:
            # Config sbagliata
            return None
    elif isinstance(sa_json, dict):
        data = sa_json
    else:
        return None

    try:
        cred = credentials.Certificate(data)
        app = firebase_admin.initialize_app(cred)
        return app
    except Exception as e:
        # In caso di errore di inizializzazione mostro un messaggio nell'interfaccia
        st.warning(f"Errore inizializzazione Firebase Admin: {e}")
        return None


# ---------- FUNZIONI PUBBLICHE ----------

def send_push_to_tokens(
    tokens: Iterable[str],
    title: str,
    body: str,
    data: Dict[str, Any] | None = None,
) -> Tuple[int, int, str | None]:
    """
    Invia una notifica push a una lista di token FCM.

    Ritorna:
        (success_count, total_tokens, error_message)
    """
    # Pulizia token vuoti / spaziati
    token_list: List[str] = [t.strip() for t in tokens if t and t.strip()]
    total = len(token_list)
    if total == 0:
        return 0, 0, "Nessun token valido specificato."

    app = _get_firebase_app()
    if app is None:
        return 0, total, "Firebase Admin non è configurato (controlla i secrets)."

    data = data or {}
    # Tutti i valori in data devono essere stringhe
    data = {str(k): str(v) for k, v in data.items()}

    messages: List[messaging.Message] = []
    for t in token_list:
        msg = messaging.Message(
            token=t,
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data,
        )
        messages.append(msg)

    try:
        # send_all invia in batch
        response = messaging.send_all(messages, app=app)
        success = response.success_count
        failure = response.failure_count

        if failure > 0:
            # Raccolgo un breve messaggio di errore generico
            error_msg = f"{success} inviati, {failure} falliti."
        else:
            error_msg = None

        return success, total, error_msg

    except Exception as e:
        return 0, total, f"Errore nell'invio delle notifiche: {e}"


def send_push_to_user_ids(
    db: Session,
    user_ids: Iterable[int],
    title: str,
    body: str,
    data: Dict[str, Any] | None = None,
) -> Tuple[int, int, str | None]:
    """
    Versione che prende gli ID utente, recupera i token registrati
    in tabella DeviceToken e poi chiama send_push_to_tokens.
    (Utile per dopo, quando avremo il salvataggio dei token per ogni genitore.)
    """
    user_ids = list(user_ids)
    if not user_ids:
        return 0, 0, "Nessun utente specificato."

    tokens = (
        db.query(DeviceToken.token)
        .filter(DeviceToken.user_id.in_(user_ids))
        .all()
    )
    token_list = [t[0] for t in tokens]  # each row is a tuple (token,)

    return send_push_to_tokens(token_list, title, body, data=data)
