# ui_parent.py
from datetime import date, datetime

import streamlit as st
from sqlalchemy.orm import Session

from core.models import (
    User,
    Category,
    Athlete,
    ParentAthlete,
    Event,
    EventAttendance,
    Message,
    AthleteReport,
    DeviceToken,
)

status_label_map = {
    "undecided": "Da confermare",
    "present": "Presente",
    "absent": "Assente",
}
reverse_status_map = {v: k for k, v in status_label_map.items()}


def render_parent_dashboard(db: Session, user: User):
    st.header("Pannello Genitore")

    links = (
        db.query(ParentAthlete)
        .filter(ParentAthlete.parent_id == user.id)
        .all()
    )
    if not links:
        st.info("Nessun atleta collegato.")
        return

    athlete_ids = [l.athlete_id for l in links]
    athletes = db.query(Athlete).filter(Athlete.id.in_(athlete_ids)).all()

    st.subheader("I tuoi atleti")
    st.write(", ".join(a.name for a in athletes))

    cat_ids = list({a.category_id for a in athletes if a.category_id})

    tab_eventi, tab_messaggi, tab_report, tab_settings = st.tabs(
        ["Eventi", "Messaggi", "Report", "Impostazioni"]
    )

    with tab_eventi:
        _render_events_view(db, user, athletes, cat_ids)

    with tab_messaggi:
        _render_messages_view(db, user, athletes, athlete_ids, cat_ids)

    with tab_report:
        _render_reports_view(db, user, athletes, athlete_ids, cat_ids)

    with tab_settings:
        _render_settings_view(db, user)


# ---------- EVENTI + PRESENZE ----------

def _render_events_view(db: Session, user: User, athletes, cat_ids):
    today = date.today()
    events = (
        db.query(Event)
        .filter(Event.category_id.in_(cat_ids), Event.date >= today)
        .order_by(Event.date.asc())
        .all()
    )

    if not events:
        st.subheader("Prossimi eventi per i tuoi figli")
        st.info("Nessun evento futuro.")
        return

    st.subheader("Prossimi eventi per i tuoi figli")

    categories = db.query(Category).filter(Category.id.in_(cat_ids)).all()
    cat_map = {c.id: c for c in categories}

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

            if ev.ask_skiroom:
                st.caption("👉 L'allenatore ha chiesto di lasciare gli sci in ski-room.")
            if is_race and ev.ask_carpool:
                st.caption("👉 L'allenatore ha chiesto di indicare se siete automuniti.")

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

                if att is None:
                    att = EventAttendance(
                        event_id=ev.id,
                        athlete_id=ath.id,
                        status="undecided",
                    )
                    db.add(att)
                    db.commit()

                st.markdown(f"#### {ath.name}")

                col1, col2 = st.columns([2, 1])

                current_status_label = status_label_map.get(
                    att.status, "Da confermare"
                )

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

                    skis_flag = att.skis_in_skiroom
                    if ev.ask_skiroom:
                        skis_flag = st.checkbox(
                            "Sci in ski-room",
                            value=att.skis_in_skiroom,
                            key=f"skiroom_{ev.id}_{ath.id}",
                        )

                car_flag = att.car_available
                car_seats = att.car_seats or 0

                if is_race and ev.ask_carpool:
                    with col2:
                        car_flag = st.checkbox(
                            "Automunito",
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
                    car_flag = False
                    car_seats = 0

                if st.button("Salva", key=f"save_{ev.id}_{ath.id}"):
                    att.status = reverse_status_map[chosen_label]
                    att.skis_in_skiroom = skis_flag if ev.ask_skiroom else False
                    att.car_available = car_flag if (is_race and ev.ask_carpool) else False
                    att.car_seats = car_seats if (is_race and ev.ask_carpool) else 0

                    att.updated_by = user.id
                    att.updated_at = datetime.utcnow()

                    db.commit()
                    st.success("Dati aggiornati per questo atleta.")

            st.markdown("---")


# ---------- MESSAGGI ----------

def _render_messages_view(
    db: Session,
    user: User,
    athletes,
    athlete_ids,
    cat_ids,
):
    st.subheader("Messaggi dagli allenatori")

    categories = db.query(Category).filter(Category.id.in_(cat_ids)).all()
    cat_map = {c.id: c for c in categories}
    athlete_map = {a.id: a for a in athletes}

    msgs = (
        db.query(Message)
        .order_by(Message.created_at.desc())
        .limit(50)
        .all()
    )

    # filtro: solo quelli che riguardano te
    filtered = []
    for msg in msgs:
        if msg.athlete_id and msg.athlete_id in athlete_ids:
            filtered.append(msg)
        elif msg.category_id and msg.category_id in cat_ids:
            filtered.append(msg)
        elif not msg.athlete_id and not msg.category_id:
            # broadcast a tutto il club
            filtered.append(msg)

    if not filtered:
        st.info("Non hai ancora messaggi.")
        return

    for msg in filtered:
        if msg.athlete_id:
            ath = athlete_map.get(msg.athlete_id)
            target = f"Personale per {ath.name if ath else msg.athlete_id}"
        elif msg.category_id:
            cat = cat_map.get(msg.category_id)
            target = f"Categoria: {cat.name if cat else msg.category_id}"
        else:
            target = "Tutto il club"

        st.markdown(f"**{msg.title}**")
        st.caption(f"{target} · {msg.created_at.strftime('%d/%m/%Y %H:%M')}")
        st.write(msg.content)
        st.markdown("---")


# ---------- REPORT (GENITORE) ----------

def _render_reports_view(
    db: Session,
    user: User,
    athletes,
    athlete_ids,
    cat_ids,
):
    st.subheader("Report allenamenti / gare")

    categories = db.query(Category).filter(Category.id.in_(cat_ids)).all()
    cat_map = {c.id: c for c in categories}
    athlete_map = {a.id: a for a in athletes}

    events = (
        db.query(Event)
        .filter(Event.category_id.in_(cat_ids))
        .order_by(Event.date.desc())
        .all()
    )

    if not events:
        st.info("Nessun evento con report.")
        return

    any_report = False

    for ev in events:
        athlete_reports = (
            db.query(AthleteReport)
            .filter(
                AthleteReport.event_id == ev.id,
                AthleteReport.athlete_id.in_(athlete_ids),
            )
            .order_by(AthleteReport.created_at.desc())
            .all()
        )

        if not athlete_reports:
            continue

        any_report = True
        cat = cat_map.get(ev.category_id)
        with st.expander(
            f"{ev.date} · {ev.title} ({cat.name if cat else '-'})",
            expanded=False,
        ):
            st.markdown("### Report personali")
            for rep in athlete_reports:
                ath = athlete_map.get(rep.athlete_id)
                st.markdown(f"**Per {ath.name if ath else rep.athlete_id}**")
                st.caption(
                    f"Inserito il {rep.created_at.strftime('%d/%m/%Y %H:%M')} "
                    f"da {rep.coach.name}"
                )
                st.write(rep.content or "—")
                st.markdown("---")

    if not any_report:
        st.info("Non ci sono ancora report per i tuoi figli.")


# ---------- IMPOSTAZIONI (FCM TOKEN) ----------

def _render_settings_view(db: Session, user: User):
    st.subheader("Impostazioni notifiche")

    st.markdown(
        "Per ricevere notifiche push sul tuo telefono o browser, "
        "incolla qui il tuo **Firebase device token**."
    )

    existing = (
        db.query(DeviceToken)
        .filter(DeviceToken.user_id == user.id)
        .order_by(DeviceToken.created_at.desc())
        .first()
    )
    default_token = existing.token if existing else ""

    with st.form("fcm_token_form_parent"):
        token = st.text_input("FCM device token", value=default_token)
        submitted = st.form_submit_button("Salva token")

    if submitted:
        token = token.strip()
        if not token:
            st.error("Il token non può essere vuoto.")
            return

        row = (
            db.query(DeviceToken)
            .filter(DeviceToken.user_id == user.id)
            .first()
        )
        if row:
            row.token = token
            row.last_used_at = datetime.utcnow()
        else:
            row = DeviceToken(user_id=user.id, platform="web", token=token)
            db.add(row)

        db.commit()
        st.success("Token salvato. Ora puoi ricevere notifiche push.")
