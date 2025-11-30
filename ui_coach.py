# core/ui_coach.py
from datetime import date

import streamlit as st
from sqlalchemy.orm import Session

from .models import Category, Athlete, CoachCategory, Event, EventAttendance, User


def render_coach_dashboard(db: Session, user: User) -> None:
    st.header("Pannello Allenatore")

    coach_cats = (
        db.query(CoachCategory)
        .filter(CoachCategory.coach_id == user.id)
        .all()
    )
    if not coach_cats:
        st.info("Non sei assegnato a nessuna categoria.")
        return

    cat_ids = [c.category_id for c in coach_cats]
    categories = db.query(Category).filter(Category.id.in_(cat_ids)).all()
    cat_map = {c.id: c for c in categories}

    st.subheader("Categorie seguite")
    st.write(", ".join(c.name for c in categories))

    today = date.today()
    events = (
        db.query(Event)
        .filter(Event.category_id.in_(cat_ids), Event.date >= today)
        .order_by(Event.date.asc())
        .all()
    )

    st.subheader("Prossimi eventi delle tue categorie")
    if not events:
        st.info("Nessun evento futuro per le tue categorie.")
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

            rows = (
                db.query(EventAttendance, Athlete)
                .join(Athlete, EventAttendance.athlete_id == Athlete.id)
                .filter(EventAttendance.event_id == ev.id)
                .order_by(Athlete.name.asc())
                .all()
            )

            if not rows:
                st.info("Nessun atleta collegato a questo evento.")
            else:
                present = sum(1 for a, _ in rows if a.status == "present")
                absent = sum(1 for a, _ in rows if a.status == "absent")
                undecided = sum(1 for a, _ in rows if a.status == "undecided")

                skis_count = sum(1 for a, _ in rows if a.skis_in_skiroom)
                car_drivers = sum(1 for a, _ in rows if a.car_available)
                total_car_seats = sum((a.car_seats or 0) for a, _ in rows)

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Presenze previste", present)
                col2.metric("Assenti", absent)
                col3.metric("Da confermare", undecided)
                col4.metric("Sci in ski-room", skis_count)

                col5, col6 = st.columns(2)
                col5.metric("Automuniti", car_drivers)
                col6.metric("Posti auto totali", total_car_seats)

                st.markdown("----")
                st.markdown("**Dettaglio atleti:**")

                table_data = []
                for att, athlete in rows:
                    status_icon = {
                        "present": "✅ Presente",
                        "absent": "❌ Assente",
                        "undecided": "❓ Da confermare",
                    }.get(att.status, att.status)

                    skis_label = "🎿 Sì" if att.skis_in_skiroom else "—"
                    if att.car_available and is_race:
                        car_label = f"🚗 Sì ({att.car_seats or 0} posti)"
                    elif is_race:
                        car_label = "—"
                    else:
                        car_label = "N/A"

                    table_data.append(
                        {
                            "Atleta": athlete.name,
                            "Stato": status_icon,
                            "Sci in ski-room": skis_label,
                            "Auto": car_label,
                        }
                    )

                st.table(table_data)
                st.markdown(
                    "_Nota: in questa versione l'allenatore vede ma non modifica; le modifiche vengono dal genitore._"
                )
