# ui_coach.py
# Pannello Allenatore – Sci Club Val d'Ayas

from datetime import date
from typing import List, Set

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
    DeviceToken,
)
from core.notifications import send_push_to_tokens


# --------- UTILS ----------


def _get_coach_categories(db: Session, user: User):
    links = db.query(Category).join(
        "events", isouter=True
    )  # solo per tenerle "vive"
    # ma in realtà abbiamo già la relazione in CoachCategory, quindi:
    coach_links = [c for c in user.coached_categories]
    cat_ids = [cl.category_id for cl in coach_links]
    if not cat_ids:
        return [], []

    categories = db.query(Category).filter(Category.id.in_(cat_ids)).all()
    cat_map = {c.id: c for c in categories}
    return categories, cat_ids, cat_map


def _load_future_events_for_cats(db: Session, cat_ids: List[int]):
    today = date.today()
    return (
        db.query(Event)
        .filter(Event.category_id.in_(cat_ids), Event.date >= today)
        .order_by(Event.date.asc())
        .all()
    )


def _collect_parent_ids_for_category(db: Session, category_id: int) -> Set[int]:
    athletes = db.query(Athlete).filter(Athlete.category_id == category_id).all()
    if not athletes:
        return set()

    ath_ids = [a.id for a in athletes]
    links = (
        db.query(ParentAthlete)
        .filter(ParentAthlete.athlete_id.in_(ath_ids))
        .all()
    )
    return {l.parent_id for l in links}


def _collect_parent_ids_for_athlete(db: Session, athlete_id: int) -> Set[int]:
    links = (
        db.query(ParentAthlete)
        .filter(ParentAthlete.athlete_id == athlete_id)
        .all()
    )
    return {l.parent_id for l in links}


def _get_tokens_for_users(db: Session, user_ids: List[int]) -> List[str]:
    if not user_ids:
        return []
    tokens = (
        db.query(DeviceToken)
        .filter(DeviceToken.user_id.in_(user_ids))
        .all()
    )
    return [t.token for t in tokens]


# --------- TAB EVENTI ----------


def _render_events_tab(db: Session, user: User):
    categories, cat_ids, cat_map = _get_coach_categories(db, user)

    if not categories:
        st.info("Non sei assegnato a nessuna categoria.")
        return

    st.subheader("Categorie seguite")
    st.write(", ".join(c.name for c in categories))

    events = _load_future_events_for_cats(db, cat_ids)

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
                if att.car_available:
                    car_label = f"🚗 Sì ({att.car_seats or 0} posti)"
                else:
                    car_label = "—"

                table_data.append(
                    {
                        "Atleta": athlete.name,
                        "Stato": status_icon,
                        "Sci in ski-room": skis_label,
                        "Auto": car_label if is_race else "N/A" if not is_race else car_label,
                    }
                )

            st.table(table_data)

            st.markdown(
                "_Nota: in questa versione l'allenatore vede ma non modifica; le modifiche vengono dal genitore._"
            )


# --------- TAB COMUNICAZIONI ----------


def _render_comunicazioni_tab(db: Session, user: User):
    st.subheader("Nuova comunicazione ai genitori")

    mode = st.radio(
        "Destinatari",
        options=["Tutti i genitori delle mie categorie", "Solo una categoria", "Per atleta"],
        horizontal=False,
    )

    categories, cat_ids, _ = _get_coach_categories(db, user)

    target_category_id = None
    target_athlete_id = None

    if mode == "Solo una categoria":
        cat_names = {c.name: c.id for c in categories}
        selected = st.selectbox("Categoria", list(cat_names.keys()))
        target_category_id = cat_names[selected]

    elif mode == "Per atleta":
        # elenco atleti delle categorie del coach
        athletes = (
            db.query(Athlete)
            .filter(Athlete.category_id.in_(cat_ids))
            .order_by(Athlete.name.asc())
            .all()
        )
        if not athletes:
            st.info("Nessun atleta collegato alle tue categorie.")
            return
        ath_labels = {a.name: a.id for a in athletes}
        selected = st.selectbox("Atleta", list(ath_labels.keys()))
        target_athlete_id = ath_labels[selected]

    title = st.text_input("Titolo", value="")
    content = st.text_area("Contenuto", height=150)

    if st.button("Invia comunicazione"):
        if not title or not content:
            st.warning("Inserisci titolo e contenuto.")
            return

        parent_ids: Set[int] = set()

        if mode == "Tutti i genitori delle mie categorie":
            for c in categories:
                parent_ids |= _collect_parent_ids_for_category(db, c.id)
            msg = Message(
                sender_id=user.id,
                title=title,
                content=content,
                category_id=None,
                athlete_id=None,
            )
        elif mode == "Solo una categoria" and target_category_id:
            parent_ids |= _collect_parent_ids_for_category(db, target_category_id)
            msg = Message(
                sender_id=user.id,
                title=title,
                content=content,
                category_id=target_category_id,
                athlete_id=None,
            )
        elif mode == "Per atleta" and target_athlete_id:
            parent_ids |= _collect_parent_ids_for_athlete(db, target_athlete_id)
            msg = Message(
                sender_id=user.id,
                title=title,
                content=content,
                category_id=None,
                athlete_id=target_athlete_id,
            )
        else:
            st.warning("Seleziona correttamente i destinatari.")
            return

        db.add(msg)
        db.commit()

        tokens = _get_tokens_for_users(db, list(parent_ids))
        result = send_push_to_tokens(tokens, title=title, body=content)

        if result.get("ok"):
            st.success(f"Messaggio salvato e notifiche inviate a {len(tokens)} dispositivi.")
        else:
            st.warning(
                f"Messaggio salvato ma problema nell'invio notifiche: {result.get('reason')}"
            )
            st.json(result.get("response", {}))


def _render_reports_tab(db: Session, user: User):
    st.subheader("Report di squadra")
    st.info("In questa versione demo i report sono ancora in sola lettura / placeholder.")


# --------- ENTRY POINT ----------


def render_coach_dashboard(db: Session, user: User):
    st.header("Pannello Allenatore")

    tab_eventi, tab_comunicazioni, tab_report = st.tabs(
        ["Eventi", "Comunicazioni", "Report"]
    )

    with tab_eventi:
        _render_events_tab(db, user)

    with tab_comunicazioni:
        _render_comunicazioni_tab(db, user)

    with tab_report:
        _render_reports_tab(db, user)
