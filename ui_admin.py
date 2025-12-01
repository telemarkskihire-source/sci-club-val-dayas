# ui_admin.py
from datetime import date, datetime
import io
import csv

import streamlit as st
from sqlalchemy.orm import Session

from core.models import (
    User,
    Category,
    Athlete,
    ParentAthlete,
    CoachCategory,
    Event,
    EventAttendance,
)


# ------------------ ENTRYPOINT ------------------ #


def render_admin_dashboard(db: Session, user: User) -> None:
    st.header("Pannello Admin")

    tab_overview, tab_users, tab_categories, tab_athletes, tab_events = st.tabs(
        [
            "Panoramica",
            "Utenti & ruoli",
            "Categorie & allenatori",
            "Atleti & genitori",
            "Eventi",
        ]
    )

    with tab_overview:
        _overview_tab(db)

    with tab_users:
        _users_tab(db)

    with tab_categories:
        _categories_tab(db)

    with tab_athletes:
        _athletes_tab(db)

    with tab_events:
        _events_tab(db)


# ------------------ PANORAMICA ------------------ #


def _overview_tab(db: Session) -> None:
    st.subheader("Sintesi club")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Utenti totali", db.query(User).count())
    col2.metric("Categorie", db.query(Category).count())
    col3.metric("Atleti", db.query(Athlete).count())
    col4.metric("Eventi", db.query(Event).count())

    today = date.today()
    events = (
        db.query(Event)
        .filter(Event.date >= today)
        .order_by(Event.date.asc())
        .limit(10)
        .all()
    )

    st.markdown("### Prossimi eventi")
    if not events:
        st.info("Nessun evento futuro.")
        return

    for ev in events:
        cat = db.query(Category).get(ev.category_id)
        st.markdown(f"**{ev.date} — {ev.title}**")
        st.caption(
            f"{'Gara' if ev.type == 'race' else 'Allenamento'} · "
            f"Categoria: {cat.name if cat else '-'} · "
            f"{ev.location or ''}"
        )
        if ev.description:
            st.write(ev.description)
        st.markdown("---")


# ------------------ UTENTI & RUOLI ------------------ #


def _users_tab(db: Session) -> None:
    st.subheader("Gestione utenti")

    users = db.query(User).order_by(User.role, User.name).all()
    if users:
        st.markdown("### Elenco utenti")
        for u in users:
            st.write(f"- **{u.name}** · {u.email or '—'} · ruolo: `{u.role}`")

    st.markdown("### Crea nuovo utente")

    with st.form("create_user"):
        name = st.text_input("Nome e cognome")
        email = st.text_input("Email (opzionale)")
        role = st.selectbox(
            "Ruolo",
            options=["admin", "coach", "parent"],
            format_func=lambda r: {"admin": "Admin", "coach": "Allenatore", "parent": "Genitore"}[r],
        )
        submitted = st.form_submit_button("Crea utente")

    if submitted:
        if not name.strip():
            st.error("Il nome è obbligatorio.")
            return

        if email:
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                st.error("Esiste già un utente con questa email.")
                return

        user = User(name=name.strip(), email=email or None, role=role)
        db.add(user)
        db.commit()
        st.success("Utente creato.")


# ------------------ CATEGORIE & ALLENATORI ------------------ #


def _categories_tab(db: Session) -> None:
    st.subheader("Categorie e assegnazione allenatori")

    categories = db.query(Category).order_by(Category.name).all()
    coaches = db.query(User).filter(User.role == "coach").order_by(User.name).all()

    # elenco categorie
    if categories:
        st.markdown("### Categorie esistenti")
        for c in categories:
            coach_links = (
                db.query(CoachCategory)
                .filter(CoachCategory.category_id == c.id)
                .all()
            )
            coach_names = [
                db.query(User).get(link.coach_id).name for link in coach_links
            ]
            st.write(
                f"- **{c.name}** – {c.description or ''} "
                f"(allenatori: {', '.join(coach_names) if coach_names else 'nessuno'})"
            )
    else:
        st.info("Nessuna categoria ancora definita.")

    st.markdown("---")
    st.markdown("### Crea nuova categoria")

    with st.form("create_category"):
        name = st.text_input("Nome categoria (es. U10 – Cuccioli)")
        desc = st.text_area("Descrizione (opzionale)", height=80)
        submitted = st.form_submit_button("Crea categoria")

    if submitted:
        if not name.strip():
            st.error("Il nome categoria è obbligatorio.")
            return
        existing = db.query(Category).filter(Category.name == name.strip()).first()
        if existing:
            st.error("Esiste già una categoria con questo nome.")
            return

        cat = Category(name=name.strip(), description=desc or None)
        db.add(cat)
        db.commit()
        st.success("Categoria creata.")

    st.markdown("---")
    st.markdown("### Assegna allenatore a categoria")

    if not categories or not coaches:
        st.info("Servono almeno una categoria e un allenatore per fare l'assegnazione.")
        return

    cat_label_map = {c.name: c.id for c in categories}
    coach_label_map = {c.name: c.id for c in coaches}

    with st.form("assign_coach"):
        cat_label = st.selectbox("Categoria", list(cat_label_map.keys()))
        coach_label = st.selectbox("Allenatore", list(coach_label_map.keys()))
        submitted2 = st.form_submit_button("Assegna")

    if submitted2:
        cat_id = cat_label_map[cat_label]
        coach_id = coach_label_map[coach_label]

        exists = (
            db.query(CoachCategory)
            .filter(
                CoachCategory.category_id == cat_id,
                CoachCategory.coach_id == coach_id,
            )
            .first()
        )
        if exists:
            st.warning("Questo allenatore è già assegnato a questa categoria.")
        else:
            link = CoachCategory(category_id=cat_id, coach_id=coach_id)
            db.add(link)
            db.commit()
            st.success("Allenatore assegnato alla categoria.")


# ------------------ ATLETI & GENITORI ------------------ #


def _athletes_tab(db: Session) -> None:
    st.subheader("Atleti e collegamento genitori")

    categories = db.query(Category).order_by(Category.name).all()
    parents = db.query(User).filter(User.role == "parent").order_by(User.name).all()
    athletes = db.query(Athlete).order_by(Athlete.name).all()

    # elenco atleti
    if athletes:
        st.markdown("### Elenco atleti")
        cat_map = {c.id: c for c in categories}
        for a in athletes:
            cat = cat_map.get(a.category_id)
            links = (
                db.query(ParentAthlete)
                .filter(ParentAthlete.athlete_id == a.id)
                .all()
            )
            parent_names = [
                db.query(User).get(link.parent_id).name for link in links
            ]
            st.write(
                f"- **{a.name}** "
                f"(anno {a.birth_year or '?'} · categoria: {cat.name if cat else '-'}) "
                f"— genitori: {', '.join(parent_names) if parent_names else 'nessuno'}"
            )
    else:
        st.info("Nessun atleta ancora inserito.")

    st.markdown("---")
    st.markdown("### Crea nuovo atleta")

    if not categories:
        st.info("Prima crea almeno una categoria nella scheda Categorie.")
    else:
        cat_label_map = {c.name: c.id for c in categories}

        with st.form("create_athlete"):
            name = st.text_input("Nome atleta")
            birth_year = st.number_input(
                "Anno di nascita",
                min_value=2000,
                max_value=date.today().year,
                value=2014,
                step=1,
            )
            cat_label = st.selectbox("Categoria", list(cat_label_map.keys()))
            submitted = st.form_submit_button("Crea atleta")

        if submitted:
            if not name.strip():
                st.error("Il nome atleta è obbligatorio.")
            else:
                ath = Athlete(
                    name=name.strip(),
                    birth_year=int(birth_year),
                    category_id=cat_label_map[cat_label],
                )
                db.add(ath)
                db.commit()
                st.success("Atleta creato.")

    st.markdown("---")
    st.markdown("### Collega genitore ↔ atleta")

    if not parents or not athletes:
        st.info("Servono almeno un genitore e un atleta per creare il collegamento.")
        return

    parent_label_map = {p.name: p.id for p in parents}
    athlete_label_map = {a.name: a.id for a in athletes}

    with st.form("link_parent_athlete"):
        parent_label = st.selectbox("Genitore", list(parent_label_map.keys()))
        athlete_label = st.selectbox("Atleta", list(athlete_label_map.keys()))
        submitted2 = st.form_submit_button("Collega")

    if submitted2:
        parent_id = parent_label_map[parent_label]
        athlete_id = athlete_label_map[athlete_label]

        exists = (
            db.query(ParentAthlete)
            .filter(
                ParentAthlete.parent_id == parent_id,
                ParentAthlete.athlete_id == athlete_id,
            )
            .first()
        )
        if exists:
            st.warning("Questo genitore è già collegato a questo atleta.")
        else:
            link = ParentAthlete(parent_id=parent_id, athlete_id=athlete_id)
            db.add(link)
            db.commit()
            st.success("Collegamento creato.")


# ------------------ EVENTI (+ EXPORT CSV) ------------------ #


def _events_tab(db: Session) -> None:
    st.subheader("Gestione eventi")

    categories = db.query(Category).order_by(Category.name).all()
    if not categories:
        st.info("Prima crea almeno una categoria.")
        return

    events = db.query(Event).order_by(Event.date.desc()).all()
    cat_map = {c.id: c for c in categories}

    if events:
        st.markdown("### Eventi esistenti")

        for ev in events:
            cat = cat_map.get(ev.category_id)

            with st.expander(
                f"{ev.date} · {ev.title} "
                f"({ 'Gara' if ev.type == 'race' else 'Allenamento' } · "
                f"{cat.name if cat else '-'})",
                expanded=False,
            ):
                if ev.description:
                    st.write(ev.description)
                if ev.location:
                    st.caption(f"Località: {ev.location}")

                # riepilogo presenze
                rows = (
                    db.query(EventAttendance, Athlete)
                    .join(Athlete, EventAttendance.athlete_id == Athlete.id)
                    .filter(EventAttendance.event_id == ev.id)
                    .order_by(Athlete.name.asc())
                    .all()
                )

                if rows:
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

                    # bottone download CSV
                    csv_bytes = _build_event_csv(ev, rows)
                    st.download_button(
                        label="Scarica presenze (CSV)",
                        data=csv_bytes,
                        file_name=f"presenze_{ev.id}_{ev.date}.csv",
                        mime="text/csv",
                        key=f"dl_csv_{ev.id}",
                    )
                else:
                    st.info("Nessuna presenza ancora registrata.")

    else:
        st.info("Nessun evento presente.")

    st.markdown("---")
    st.markdown("### Crea nuovo evento")

    cat_label_map = {c.name: c.id for c in categories}

    with st.form("create_event"):
        ev_type_label = st.selectbox(
            "Tipo evento",
            options=["Allenamento", "Gara"],
        )
        ev_type = "training" if ev_type_label == "Allenamento" else "race"

        cat_label = st.selectbox("Categoria", list(cat_label_map.keys()))
        title = st.text_input("Titolo")
        location = st.text_input("Località (opzionale)")
        date_val = st.date_input("Data", value=date.today())
        description = st.text_area("Descrizione (opzionale)", height=80)
        submitted = st.form_submit_button("Crea evento")

    if submitted:
        if not title.strip():
            st.error("Il titolo è obbligatorio.")
            return

        cat_id = cat_label_map[cat_label]
        ev = Event(
            type=ev_type,
            category_id=cat_id,
            title=title.strip(),
            description=description or None,
            location=location or None,
            date=date_val,
        )
        db.add(ev)
        db.flush()  # otteniamo ev.id

        # crea automaticamente le presenze "undecided" per tutti gli atleti della categoria
        athletes = (
            db.query(Athlete)
            .filter(Athlete.category_id == cat_id)
            .all()
        )
        for ath in athletes:
            db.add(
                EventAttendance(
                    event_id=ev.id,
                    athlete_id=ath.id,
                    status="undecided",
                    updated_at=datetime.utcnow(),
                )
            )

        db.commit()
        st.success("Evento creato e presenze iniziali generate.")


def _build_event_csv(ev: Event, rows) -> bytes:
    """Crea CSV (in memoria) con elenco presenze di un evento."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")

    # header
    writer.writerow(
        [
            "Evento ID",
            "Data",
            "Titolo",
            "Tipo",
            "Atleta",
            "Stato",
            "Sci in ski-room",
            "Automunito",
            "Posti auto",
        ]
    )

    for att, athlete in rows:
        status = att.status
        skis = "SI" if att.skis_in_skiroom else "NO"
        car = "SI" if att.car_available else "NO"
        seats = att.car_seats or 0

        writer.writerow(
            [
                ev.id,
                ev.date.isoformat(),
                ev.title,
                ev.type,
                athlete.name,
                status,
                skis,
                car,
                seats,
            ]
        )

    return buffer.getvalue().encode("utf-8")
