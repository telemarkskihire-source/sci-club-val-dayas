# ui_parent.py
# Pannello Genitore – Sci Club Val d'Ayas
#
# Tab:
# - Eventi: gestisce presenze, sci in ski-room, auto (per le gare)
# - Messaggi: placeholder per messaggi ricevuti
# - Report: placeholder per report personali
# - Impostazioni: salva il token FCM per le notifiche push

from datetime import date, datetime

import streamlit as st
from sqlalchemy.orm import Session

from core.models import (
    User,
    Athlete,
    ParentAthlete,
    Category,
    Event,
    EventAttendance,
    DeviceToken,
)


def _load_family_data(db: Session, user: User):
    links = (
        db.query(ParentAthlete)
        .filter(ParentAthlete.parent_id == user.id)
        .all()
    )
    if not links:
        return [], [], []

    athlete_ids = [l.athlete_id for l in links]
    athletes = db.query(Athlete).filter(Athlete.id.in_(athlete_ids)).all()
    cat_ids = list({a.category_id for a in athletes if a.category_id})

    categories = db.query(Category).filter(Category.id.in_(cat_ids)).all()
    cat_map = {c.id: c for c in categories}

    return athletes, cat_ids, cat_map


def _render_events_tab(db: Session, user: User, athletes, cat_ids, cat_map):
    st.subheader("Prossimi eventi per i tuoi figli")

    if not cat_ids:
        st.info("Nessuna categoria collegata ai tuoi atleti.")
        return

    today = date.today()
    events = (
        db.query(Event)
        .filter(Event.category_id.in_(cat_ids), Event.date >= today)
        .order_by(Event.date.asc())
        .all()
    )

    if not events:
        st.info("Nessun evento futuro.")
        return

    for ev in events:
        cat = cat_map.get(ev.category_id)
        is_race = ev.type == "race"

        with st.expander(
            f"{ev.date} · {ev.title} "
            f"({cat.name if cat else '-'}) "
            f"- {'Gara' if is_race else 'Allenamento'}",
            expanded=False,
        ):
            if ev.description:
                st.caption(ev.description)
            if ev.location:
                st.caption(f"Località: {ev.location}")

            for ath in athletes:
                if ath.category_id != ev.category_id:
                    continue

                att = (
                    db.query(EventAttendance)
                    .filter(
                        EventAttendance.event_id == ev.id,
                        EventAttendance.athlete_id == ath.id,
                    )
                    .first()
                )

                # se manca, creiamo record base
                if att is None:
                    att = EventAttendance(
                        event_id=ev.id,
                        athlete_id=ath.id,
                        status="undecided",
                    )
                    db.add(att)
                    db.commit()

                st.markdown(f"#### {ath.name}")

                status_label_map = {
                    "undecided": "Da confermare",
                    "present": "Presente",
                    "absent": "Assente",
                }
                reverse_status_map = {v: k for k, v in status_label_map.items()}
                current_status_label = status_label_map.get(
                    att.status, "Da confermare"
                )

                col1, col2 = st.columns([2, 1])

                with col1:
                    chosen_label = st.radio(
                        "Presenza",
                        options=list(status_label_map.values()),
                        index=list(status_label_map.values()).index(
                            current_status_label
                        ),
                        key=f"status_{ev.id}_{ath.id}",
                        horizontal=True,
                    )

                    skis_flag = st.checkbox(
                        "Sci in ski-room",
                        value=att.skis_in_skiroom,
                        key=f"skiroom_{ev.id}_{ath.id}",
                    )

                car_flag = att.car_available
                car_seats = att.car_seats or 0

                if is_race:
                    with col2:
                        car_flag = st.checkbox(
                            "Automunito (per questa gara)",
                            value=att.car_available,
                            key=f"car_{ev.id}_{ath.id}",
                        )
                        if car_flag:
                            car_seats = st.number_input(
                                "Posti liberi auto",
                                min_value=0,
                                max_value=8,
                                step=1,
                                value=car_seats,
                                key=f"seats_{ev.id}_{ath.id}",
                            )
                        else:
                            car_seats = 0
                else:
                    with col2:
                        st.caption("Automunito non richiesto per gli allenamenti.")

                if st.button("Salva", key=f"save_{ev.id}_{ath.id}"):
                    att.status = reverse_status_map[chosen_label]
                    att.skis_in_skiroom = skis_flag
                    if is_race:
                        att.car_available = car_flag
                        att.car_seats = car_seats
                    else:
                        att.car_available = False
                        att.car_seats = 0

                    att.updated_by = user.id
                    att.updated_at = datetime.utcnow()

                    db.commit()
                    st.success("Dati aggiornati per questo atleta.")

            st.markdown("---")


def _render_messages_tab(db: Session, user: User):
    st.subheader("Messaggi dallo staff")
    st.info("In questa versione demo i messaggi sono ancora in sola lettura / placeholder.")


def _render_reports_tab(db: Session, user: User):
    st.subheader("Report personali atleta")
    st.info("In questa versione demo i report sono ancora in sola lettura / placeholder.")


def _render_settings_tab(db: Session, user: User):
    st.subheader("Impostazioni notifiche")

    existing = (
        db.query(DeviceToken)
        .filter(DeviceToken.user_id == user.id, DeviceToken.platform == "web")
        .order_by(DeviceToken.created_at.desc())
        .first()
    )

    current_token = existing.token if existing else ""

    st.write(
        "Incolla qui il **device token FCM** che hai ottenuto dalla pagina "
        "`token.html`. Questo collega il tuo telefono alle notifiche dello Sci Club."
    )

    token_input = st.text_area(
        "FCM device token",
        value=current_token,
        height=120,
    )

    if st.button("Salva token"):
        token_str = token_input.strip()
        if not token_str:
            st.warning("Inserisci un token valido prima di salvare.")
            return

        if existing:
            existing.token = token_str
            existing.updated_at = datetime.utcnow()
        else:
            db.add(
                DeviceToken(
                    user_id=user.id,
                    token=token_str,
                    platform="web",
                )
            )
        db.commit()
        st.success("Token salvato. Questo dispositivo ora può ricevere notifiche push.")


def render_parent_dashboard(db: Session, user: User):
    st.header("Pannello Genitore")

    athletes, cat_ids, cat_map = _load_family_data(db, user)
    if not athletes:
        st.info("Nessun atleta collegato a questo genitore.")
        return

    st.subheader("I tuoi atleti")
    st.write(", ".join(a.name for a in athletes))

    tab_eventi, tab_messaggi, tab_report, tab_impostazioni = st.tabs(
        ["Eventi", "Messaggi", "Report", "Impostazioni"]
    )

    with tab_eventi:
        _render_events_tab(db, user, athletes, cat_ids, cat_map)

    with tab_messaggi:
        _render_messages_tab(db, user)

    with tab_report:
        _render_reports_tab(db, user)

    with tab_impostazioni:
        _render_settings_tab(db, user)
