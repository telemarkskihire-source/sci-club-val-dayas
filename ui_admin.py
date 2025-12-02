# ui_admin.py
#
# Pannello Admin per l'app Sci Club Val d'Ayas.
# - Metriche rapide
# - Elenco prossimi eventi
# - Sezione test notifiche push (FCM) manuale con token

from __future__ import annotations

from datetime import date

import streamlit as st
from sqlalchemy.orm import Session

from core.models import User, Category, Athlete, Event
from core.notifications import send_push_to_tokens


def render_admin_dashboard(db: Session, user: User):
    st.header("Pannello Admin")

    # ---------- METRICHE RAPIDE ----------
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Utenti", db.query(User).count())
    col2.metric("Categorie", db.query(Category).count())
    col3.metric("Atleti", db.query(Athlete).count())
    col4.metric("Eventi", db.query(Event).count())

    # ---------- PROSSIMI EVENTI ----------
    today = date.today()
    events = (
        db.query(Event)
        .filter(Event.date >= today)
        .order_by(Event.date.asc())
        .all()
    )

    st.subheader("Prossimi eventi del club")
    if not events:
        st.info("Nessun evento futuro.")
    else:
        for ev in events:
            cat = db.query(Category).get(ev.category_id)
            tipo = "Gara" if ev.type == "race" else "Allenamento"
            with st.expander(
                f"{ev.date} · {ev.title} "
                f"({cat.name if cat else '-'}) · {tipo}",
                expanded=False,
            ):
                if ev.description:
                    st.caption(ev.description)
                if ev.location:
                    st.caption(f"Località: {ev.location}")
                st.write(f"Richiesta sci in ski-room: {'✅' if ev.ask_skiroom else '❌'}")
                st.write(f"Richiesta auto/carpooling: {'✅' if ev.ask_carpool else '❌'}")

    st.markdown("---")

    # ---------- SEZIONE TEST NOTIFICHE PUSH ----------
    with st.expander("Test notifiche push (FCM)", expanded=False):
        st.caption(
            "Per ora test manuale: incolla un token FCM ottenuto dalla pagina token.html "
            "e invia una notifica di prova al tuo telefono."
        )

        token = st.text_input(
            "Token dispositivo FCM",
            value="",
            key="fcm_test_token",
        )

        default_title = "Test notifica Sci Club"
        default_body = "Questa è una notifica di prova dall'app Sci Club Val d'Ayas."

        col_titolo, col_vuoto = st.columns([2, 1])
        with col_titolo:
            title = st.text_input(
                "Titolo notifica",
                value=default_title,
                key="fcm_test_title",
            )
        body = st.text_area(
            "Messaggio",
            value=default_body,
            key="fcm_test_body",
        )

        if st.button("Invia notifica di test", key="fcm_test_send"):
            if not token.strip():
                st.warning("Inserisci prima un token FCM valido.")
            else:
                success, total, error_msg = send_push_to_tokens(
                    [token.strip()],
                    title=title,
                    body=body,
                    data={"type": "test", "source": "admin_panel"},
                )
                if success > 0:
                    st.success(f"Notifica inviata correttamente ({success}/{total}).")
                else:
                    if error_msg:
                        st.error(error_msg)
                    else:
                        st.error("Nessuna notifica inviata. Controlla token e configurazione FCM.")
