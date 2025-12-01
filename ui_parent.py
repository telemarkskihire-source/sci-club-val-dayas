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
)


# ---------- LABELS ----------
status_label_map = {
    "undecided": "Da confermare",
    "present": "Presente",
    "absent": "Assente",
}
reverse_status_map = {v: k for k, v in status_label_map.items()}


# ---------- ENTRYPOINT ----------
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
    athlete_map = {a.id: a for a in athletes}

    st.subheader("I tuoi atleti")
    st.write(", ".join(a.name for a in athletes))

    cat_ids = list({a.category_id for a in athletes if a.category_id})

    events_tab, messages_tab, reports_tab = st.tabs(
        ["Eventi", "Messaggi", "Report"]
    )

    with events_tab:
        _render_events_view(db, user, athletes, cat_ids)

    with messages_tab:
        _render_messages_view(db, user)

    with reports_tab:
        _render_reports_view(db, user, athletes)


# ---------- EVENTI ----------
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
def _render_messages_view(db: Session, user: User):
    st.subheader("Messaggi ricevuti")

    msgs = (
        db.query(Message)
        .filter((Message.athlete_id != None) | (Message.category_id != None))
        .order_by(Message.created_at.desc())
        .all()
    )

    if not msgs:
        st.info("Nessun messaggio.")
        return

    for msg in msgs:
        st.markdown(f"### {msg.title}")
        st.caption(f"{msg.created_at} — da {msg.sender.name}")
        st.write(msg.content)
        st.markdown("---")


# ---------- REPORT ----------
def _render_reports_view(db: Session, user: User, athletes):
    st.subheader("Report personali dei tuoi atleti")

    athlete_ids = [a.id for a in athletes]

    reports = (
        db.query(AthleteReport)
        .filter(AthleteReport.athlete_id.in_(athlete_ids))
        .order_by(AthleteReport.created_at.desc())
        .all()
    )

    if not reports:
        st.info("Ancora nessun report.")
        return

    for rep in reports:
        st.markdown(f"### {rep.athlete.name} — {rep.event.date} — {rep.event.title}")
        st.caption(f"Allenatore: {rep.coach.name} — {rep.created_at}")
        st.write(rep.content or "_Nessun testo_")
        st.markdown("---")
