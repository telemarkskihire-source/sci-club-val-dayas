# core/ui_parent.py
from datetime import date, datetime

import streamlit as st
from sqlalchemy.orm import Session

from .models import Category, Athlete, ParentAthlete, Event, EventAttendance, User


def render_parent_dashboard(db: Session, user: User) -> None:
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

    status_label_map = {
        "undecided": "Da confermare",
        "present": "Presente",
        "absent": "Assente",
    }
    reverse_status_map = {v: k for k, v in status_label_map.items()}

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
