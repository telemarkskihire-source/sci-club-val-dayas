# ui_coach.py
from datetime import date, datetime

import streamlit as st
from sqlalchemy.orm import Session

from core.models import (
    Category,
    Athlete,
    CoachCategory,
    Event,
    EventAttendance,
    Message,
    TeamReport,
    AthleteReport,
    User,
)


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

    tab_eventi, tab_messaggi, tab_report = st.tabs(
        ["Eventi", "Comunicazioni", "Report"]
    )

    with tab_eventi:
        _render_events_view(db, events, cat_map)

    with tab_messaggi:
        _render_messages_view(db, user, categories, cat_ids)

    with tab_report:
        _render_reports_view(db, user, categories, cat_ids)


# ---------- EVENTI ----------


def _render_events_view(db: Session, events, cat_map):
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

            # --- Impostazioni logistiche decise dal coach ---
            st.markdown("**Richieste logistiche**")
            ask_skiroom = st.checkbox(
                "Chiedi di lasciare gli sci in ski-room",
                value=ev.ask_skiroom,
                key=f"ask_ski_{ev.id}",
            )

            ask_carpool = ev.ask_carpool
            if is_race:
                ask_carpool = st.checkbox(
                    "Chiedi disponibilità auto (carpool per la gara)",
                    value=ev.ask_carpool,
                    key=f"ask_car_{ev.id}",
                )

            if st.button("Salva richieste", key=f"save_req_{ev.id}"):
                ev.ask_skiroom = ask_skiroom
                if is_race:
                    ev.ask_carpool = ask_carpool
                else:
                    ev.ask_carpool = False
                db.commit()
                st.success("Impostazioni logistiche aggiornate.")

            st.markdown("---")

            # --- Presenze & riepilogo ---
            rows = (
                db.query(EventAttendance, Athlete)
                .join(Athlete, EventAttendance.athlete_id == Athlete.id)
                .filter(EventAttendance.event_id == ev.id)
                .order_by(Athlete.name.asc())
                .all()
            )

            if not rows:
                st.info("Nessun atleta collegato a questo evento.")
                continue

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
            if ev.ask_skiroom:
                col4.metric("Sci in ski-room", skis_count)
            else:
                col4.metric("Sci in ski-room", "-")

            if is_race and ev.ask_carpool:
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
                if is_race and ev.ask_carpool:
                    if att.car_available:
                        car_label = f"🚗 Sì ({att.car_seats or 0} posti)"
                    else:
                        car_label = "—"
                else:
                    car_label = "N/A"

                table_data.append(
                    {
                        "Atleta": athlete.name,
                        "Stato": status_icon,
                        "Sci in ski-room": skis_label if ev.ask_skiroom else "N/A",
                        "Auto": car_label,
                    }
                )

            st.table(table_data)
            st.markdown(
                "_Nota: in questa versione l'allenatore vede ma non modifica le presenze; le modifiche vengono dal genitore._"
            )



# ---------- MESSAGGI ----------

def _render_messages_view(
    db: Session,
    user: User,
    categories: list[Category],
    cat_ids: list[int],
) -> None:
    st.subheader("Comunicazioni con i genitori")

    tab_nuovo, tab_storico = st.tabs(["Nuovo messaggio", "Storico inviati"])

    with tab_nuovo:
        _render_new_message_form(db, user, categories, cat_ids)

    with tab_storico:
        msgs = (
            db.query(Message)
            .filter(Message.sender_id == user.id)
            .order_by(Message.created_at.desc())
            .limit(50)
            .all()
        )
        if not msgs:
            st.info("Non hai ancora inviato messaggi.")
        else:
            for msg in msgs:
                target = "Tutto il club"
                if msg.athlete_id:
                    target = f"Personale (atleta id {msg.athlete_id})"
                elif msg.category_id:
                    cat = next((c for c in categories if c.id == msg.category_id), None)
                    target = f"Categoria: {cat.name if cat else msg.category_id}"

                st.markdown(f"**{msg.title}**")
                st.caption(
                    f"Destinatari: {target} · Inviato il {msg.created_at.strftime('%d/%m/%Y %H:%M')}"
                )
                st.write(msg.content)
                st.markdown("---")


def _render_new_message_form(
    db: Session,
    user: User,
    categories: list[Category],
    cat_ids: list[int],
) -> None:
    st.markdown("Invia una comunicazione ai genitori.")

    athletes = (
        db.query(Athlete)
        .filter(Athlete.category_id.in_(cat_ids))
        .order_by(Athlete.name.asc())
        .all()
    )

    audience_type = st.radio(
        "Destinatari",
        options=["Tutto il club", "Categoria", "Genitore di atleta"],
        horizontal=False,
    )

    selected_category_id = None
    selected_athlete_id = None

    if audience_type == "Categoria":
        if not categories:
            st.warning("Non hai categorie associate.")
            return
        cat_label_map = {c.name: c.id for c in categories}
        label = st.selectbox("Categoria", list(cat_label_map.keys()))
        selected_category_id = cat_label_map[label]

    elif audience_type == "Genitore di atleta":
        if not athletes:
            st.warning("Nessun atleta collegato alle tue categorie.")
            return
        ath_label_map = {f"{a.name} ({a.id})": a.id for a in athletes}
        label = st.selectbox("Atleta", list(ath_label_map.keys()))
        selected_athlete_id = ath_label_map[label]

    with st.form("new_message"):
        title = st.text_input("Titolo", "")
        content = st.text_area("Contenuto", "", height=150)
        submitted = st.form_submit_button("Invia messaggio")

    if submitted:
        if not title.strip() or not content.strip():
            st.error("Titolo e contenuto sono obbligatori.")
            return

        msg = Message(
            sender_id=user.id,
            category_id=selected_category_id,
            athlete_id=selected_athlete_id,
            title=title.strip(),
            content=content.strip(),
        )
        db.add(msg)
        db.commit()
        st.success("Messaggio inviato.")


# ---------- REPORT ----------

def _render_reports_view(
    db: Session,
    user: User,
    categories: list[Category],
    cat_ids: list[int],
) -> None:
    st.subheader("Report allenamenti / gare")

    # Eventi di tutte le categorie del coach, passati e futuri
    events = (
        db.query(Event)
        .filter(Event.category_id.in_(cat_ids))
        .order_by(Event.date.desc())
        .all()
    )
    if not events:
        st.info("Nessun evento disponibile per i report.")
        return

    cat_map = {c.id: c for c in categories}
    options = {
        f"{ev.date} · {ev.title} ({cat_map.get(ev.category_id).name})": ev.id
        for ev in events
    }
    label = st.selectbox("Evento", list(options.keys()))
    event_id = options[label]
    event = next(e for e in events if e.id == event_id)

    st.markdown(f"### {event.date} · {event.title}")

    # ----- REPORT GENERALE SQUADRA -----
    team_rep = (
        db.query(TeamReport)
        .filter(
            TeamReport.event_id == event.id,
            TeamReport.coach_id == user.id,
        )
        .first()
    )

    default_content = team_rep.content if team_rep else ""
    content = st.text_area(
        "Report generale (visibile a tutti i genitori della categoria)",
        value=default_content,
        height=150,
        key=f"teamrep_{event.id}",
    )

    if st.button("Salva report generale", key=f"save_teamrep_{event.id}"):
        if team_rep is None:
            team_rep = TeamReport(
                event_id=event.id,
                coach_id=user.id,
                content=content.strip(),
            )
            db.add(team_rep)
        else:
            team_rep.content = content.strip()
            team_rep.created_at = datetime.utcnow()
        db.commit()
        st.success("Report generale salvato.")

    st.markdown("---")
    st.markdown("### Report personali per atleta")

    rows = (
        db.query(EventAttendance, Athlete)
        .join(Athlete, EventAttendance.athlete_id == Athlete.id)
        .filter(EventAttendance.event_id == event.id)
        .order_by(Athlete.name.asc())
        .all()
    )

    if not rows:
        st.info("Nessun atleta per questo evento.")
        return

    for att, athlete in rows:
        st.markdown(f"**{athlete.name}**")

        a_rep = (
            db.query(AthleteReport)
            .filter(
                AthleteReport.event_id == event.id,
                AthleteReport.athlete_id == athlete.id,
                AthleteReport.coach_id == user.id,
            )
            .first()
        )

        default_note = a_rep.content if a_rep else ""
        note = st.text_area(
            "Nota personale (visibile solo al genitore di questo atleta)",
            value=default_note,
            height=80,
            key=f"arep_{event.id}_{athlete.id}",
        )

        if st.button("Salva nota", key=f"save_arep_{event.id}_{athlete.id}"):
            if a_rep is None:
                a_rep = AthleteReport(
                    event_id=event.id,
                    athlete_id=athlete.id,
                    coach_id=user.id,
                    content=note.strip(),
                )
                db.add(a_rep)
            else:
                a_rep.content = note.strip()
                a_rep.created_at = datetime.utcnow()
            db.commit()
            st.success(f"Nota salvata per {athlete.name}.")

        st.markdown("---")
