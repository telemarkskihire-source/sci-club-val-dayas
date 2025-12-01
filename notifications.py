# notifications.py
"""
Gestione notifiche push via Firebase Cloud Messaging (FCM).

IMPORTANTE:
- Imposta la variabile d'ambiente FIREBASE_SERVER_KEY
  negli "Secrets" di Streamlit Cloud.
"""

import os
from datetime import datetime
from typing import Iterable, Sequence

import requests

from core.models import (
    User,
    DeviceToken,
    Message,
    TeamReport,
    AthleteReport,
    Event,
    ParentAthlete,
    Athlete,
)


FCM_ENDPOINT = "https://fcm.googleapis.com/fcm/send"


def _get_server_key() -> str | None:
    return os.environ.get("FIREBASE_SERVER_KEY")


def _get_tokens_for_users(db, user_ids: Sequence[int]) -> list[str]:
    if not user_ids:
        return []

    rows = (
        db.query(DeviceToken)
        .filter(DeviceToken.user_id.in_(list(user_ids)))
        .all()
    )
    tokens: list[str] = []
    for row in rows:
        if row.token and row.token not in tokens:
            tokens.append(row.token)
            row.last_used_at = datetime.utcnow()
    if rows:
        db.commit()
    return tokens


def send_fcm_notification(
    tokens: Iterable[str],
    title: str,
    body: str,
    data: dict | None = None,
) -> None:
    """Invia una notifica FCM a una lista di device tokens."""
    tokens = list(tokens)
    if not tokens:
        return

    server_key = _get_server_key()
    if not server_key:
        # Nessuna server key configurata: esco in silenzio
        print("FCM: FIREBASE_SERVER_KEY non impostata, nessuna notifica inviata.")
        return

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
        "data": data or {},
    }

    try:
        resp = requests.post(FCM_ENDPOINT, json=payload, headers=headers, timeout=5)
        print("FCM response:", resp.status_code, resp.text[:200])
    except Exception as exc:
        print("FCM error:", exc)


# ---------- NOTIFICHE DI ALTO LIVELLO ----------

def notify_message_created(db, msg: Message):
    """Nuova comunicazione allenatore -> genitori."""
    # Destinatari: genitori dipende da category_id / athlete_id
    parent_user_ids: set[int] = set()

    if msg.athlete_id:
        links = (
            db.query(ParentAthlete)
            .filter(ParentAthlete.athlete_id == msg.athlete_id)
            .all()
        )
        parent_user_ids.update(l.parent_id for l in links)

    elif msg.category_id:
        athletes = (
            db.query(Athlete)
            .filter(Athlete.category_id == msg.category_id)
            .all()
        )
        ath_ids = [a.id for a in athletes]
        if ath_ids:
            links = (
                db.query(ParentAthlete)
                .filter(ParentAthlete.athlete_id.in_(ath_ids))
                .all()
            )
            parent_user_ids.update(l.parent_id for l in links)
    else:
        # messaggio a tutto il club -> tutti i genitori
        parents = db.query(User).filter(User.role == "parent").all()
        parent_user_ids.update(p.id for p in parents)

    tokens = _get_tokens_for_users(db, list(parent_user_ids))
    if not tokens:
        return

    title = msg.title
    body = msg.content[:120] + ("…" if len(msg.content) > 120 else "")
    send_fcm_notification(tokens, title, body, data={"type": "message", "message_id": msg.id})


def notify_logistics_changed(db, ev: Event):
    """Richieste ski-room / carpool aggiornate per un evento."""
    # Destinatari: tutti i genitori degli atleti della categoria
    athletes = db.query(Athlete).filter(Athlete.category_id == ev.category_id).all()
    ath_ids = [a.id for a in athletes]
    if not ath_ids:
        return

    links = (
        db.query(ParentAthlete)
        .filter(ParentAthlete.athlete_id.in_(ath_ids))
        .all()
    )
    parent_ids = list({l.parent_id for l in links})
    tokens = _get_tokens_for_users(db, parent_ids)
    if not tokens:
        return

    parts = []
    if ev.ask_skiroom:
        parts.append("sci in ski-room")
    if ev.ask_carpool:
        parts.append("auto disponibili")
    if not parts:
        body = "Richieste logistiche aggiornate."
    else:
        body = "L'allenatore ha chiesto: " + " e ".join(parts)

    title = f"Aggiornamento {ev.date} · {ev.title}"
    send_fcm_notification(tokens, title, body, data={"type": "logistics", "event_id": ev.id})


def notify_team_report(db, report: TeamReport):
    """Report di squadra: a tutti i genitori della categoria dell'evento."""
    ev = report.event
    if not ev:
        return

    athletes = db.query(Athlete).filter(Athlete.category_id == ev.category_id).all()
    ath_ids = [a.id for a in athletes]
    if not ath_ids:
        return

    links = (
        db.query(ParentAthlete)
        .filter(ParentAthlete.athlete_id.in_(ath_ids))
        .all()
    )
    parent_ids = list({l.parent_id for l in links})
    tokens = _get_tokens_for_users(db, parent_ids)
    if not tokens:
        return

    title = f"Report squadra: {ev.date} · {ev.title}"
    body = report.content[:160] + ("…" if report.content and len(report.content) > 160 else "")
    send_fcm_notification(tokens, title, body, data={"type": "team_report", "event_id": ev.id})


def notify_athlete_report(db, report: AthleteReport):
    """Report personale atleta: solo ai genitori di quell'atleta."""
    links = (
        db.query(ParentAthlete)
        .filter(ParentAthlete.athlete_id == report.athlete_id)
        .all()
    )
    parent_ids = list({l.parent_id for l in links})
    tokens = _get_tokens_for_users(db, parent_ids)
    if not tokens:
        return

    ev = report.event
    title = f"Report per {report.athlete.name} – {ev.date} · {ev.title}"
    body = report.content[:160] + ("…" if report.content and len(report.content) > 160 else "")
    send_fcm_notification(tokens, title, body, data={"type": "athlete_report", "event_id": ev.id})
