# streamlit_app.py
# Sci Club Val d'Ayas · MVP v1
#
# - Inizializza il database
# - Crea dati di esempio (utenti, categorie, atleti, eventi)
# - Permette di scegliere un utente (admin / coach / genitore)
# - Mostra una dashboard base diversa per ruolo

from __future__ import annotations

from datetime import date, datetime, timedelta

import streamlit as st
from sqlalchemy.orm import Session

from core.db import Base, engine, SessionLocal
from core.models import (
    User,
    Category,
    Athlete,
    ParentAthlete,
    CoachCategory,
    Event,
    EventAttendance,
)


# ---------- UTILS DB ----------

def get_db() -> Session:
    return SessionLocal()


def init_db_and_seed():
    """Crea le tabelle e inserisce dati di esempio se il DB è vuoto."""
    Base.metadata.create_all(bind=engine)

    db = get_db()
    try:
        if db.query(User).count() > 0:
            return

        # --- Utenti ---
        admin = User(name="Admin Sci Club", email="admin@club.test", role="admin")
        coach1 = User(name="Luca Coach", email="luca@club.test", role="coach")
        coach2 = User(name="Sara Coach", email="sara@club.test", role="coach")
        parent1 = User(name="Genitore Noah", email="noah@club.test", role="parent")
        parent2 = User(name="Genitore Juno", email="juno@club.test", role="parent")

        db.add_all([admin, coach1, coach2, parent1, parent2])
        db.flush()

        # --- Categorie ---
        cat_cuccioli = Category(name="U10 – Cuccioli", description="Atleti U10")
        cat_ragazzi = Category(name="U14 – Ragazzi", description="Atleti U14")
        db.add_all([cat_cuccioli, cat_ragazzi])
        db.flush()

        # --- Collegamento coaches <-> categorie ---
        db.add_all([
            CoachCategory(coach_id=coach1.id, category_id=cat_cuccioli.id),
            CoachCategory(coach_id=coach2.id, category_id=cat_ragazzi.id),
        ])

        # --- Atleti ---
        athlete_noah = Athlete(name="Noah Favre", birth_year=2014, category_id=cat_cuccioli.id)
        athlete_juno = Athlete(name="Juno Favre", birth_year=2020, category_id=cat_cuccioli.id)
        athlete_seth = Athlete(name="Seth Favre", birth_year=2014, category_id=cat_ragazzi.id)
        db.add_all([athlete_noah, athlete_juno, athlete_seth])
        db.flush()

        # --- Relazione genitori <-> atleti ---
        db.add_all([
            ParentAthlete(parent_id=parent1.id, athlete_id=athlete_noah.id),
            ParentAthlete(parent_id=parent1.id, athlete_id=athlete_seth.id),
            ParentAthlete(parent_id=parent2.id, athlete_id=athlete_juno.id),
        ])

        # --- Eventi ---
        today = date.today()
        ev1 = Event(
            type="training",
            category_id=cat_cuccioli.id,
            title="Allenamento GS Antagnod",
            description="Lavoro su curva media.",
            location="Antagnod – Boudin",
            date=today + timedelta(days=1),
        )
        ev2 = Event(
            type="training",
            category_id=cat_cuccioli.id,
            title="Allenamento SL Champoluc",
            description="Pali corti.",
            location="Champoluc – Crest",
            date=today + timedelta(days=3),
        )
        ev3 = Event(
            type="race",
            category_id=cat_ragazzi.id,
            title="Gara Regionale SL",
            description="Selezione U14.",
            location="Gressoney – Weissmatten",
            date=today + timedelta(days=5),
        )
        db.add_all([ev1, ev2, ev3])
        db.flush()

        # --- Presenze iniziali ---
        events = [ev1, ev2, ev3]
        athletes = [athlete_noah, athlete_juno, athlete_seth]

        for ev in events:
            for ath in athletes:
                if ath.category_id != ev.category_id:
                    continue
                db.add(EventAttendance(event_id=ev.id, athlete_id=ath.id, status="undecided"))

        db.commit()

    finally:
        db.close()


# ---------- UI HELPERS ----------

def get_role_label(role: str) -> str:
    return {
        "admin": "Admin",
        "coach": "Allenatore",
        "parent": "Genitore"
    }.get(role, role)


# ---------- DASHBOARD ADMIN ----------

def render_admin_dashboard(db: Session, user: User):
    st.header("Pannello Admin")
    st.write("Dashboard riassuntiva del club")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Utenti", db.query(User).count())
    col2.metric("Categorie", db.query(Category).count())
    col3.metric("Atleti", db.query(Athlete).count())
    col4.metric("Eventi", db.query(Event).count())

    today = date.today()
    events = db.query(Event).filter(Event.date >= today).order_by(Event.date.asc()).all()

    st.subheader("Prossimi eventi")
    for ev in events:
        st.markdown(f"**{ev.date} — {ev.title}**")
        st.caption(ev.description or "")
        st.divider()


# ---------- DASHBOARD COACH ----------

def render_coach_dashboard(db: Session, user: User):
    st.header("Pannello Allenatore")

    coach_cats = db.query(CoachCategory).filter(CoachCategory.coach_id == user.id).all()
    if not coach_cats:
        st.info("Non sei assegnato a nessuna categoria.")
        return

    cat_ids = [c.category_id for c in coach_cats]
    categories = db.query(Category).filter(Category.id.in_(cat_ids)).all()

    st.subheader("Categorie seguite:")
    st.write(", ".join(c.name for c in categories))

    today = date.today()
    events = db.query(Event).filter(Event.category_id.in_(cat_ids), Event.date >= today).order_by(Event.date.asc()).all()

    st.subheader("Prossimi eventi")
    for ev in events:
        st.markdown(f"### {ev.date} — {ev.title}")
        st.caption(ev.description or "")
        st.divider()


# ---------- DASHBOARD GENITORE ----------

def render_parent_dashboard(db: Session, user: User):
    st.header("Pannello Genitore")

    links = db.query(ParentAthlete).filter(ParentAthlete.parent_id == user.id).all()
    if not links:
        st.info("Nessun atleta collegato.")
        return

    athlete_ids = [l.athlete_id for l in links]
    athletes = db.query(Athlete).filter(Athlete.id.in_(athlete_ids)).all()

    st.subheader("I tuoi atleti:")
    st.write(", ".join(a.name for a in athletes))

    cat_ids = list({a.category_id for a in athletes})
    today = date.today()
    events = db.query(Event).filter(Event.category_id.in_(cat_ids), Event.date >= today).order_by(Event.date.asc()).all()

    st.subheader("Prossimi eventi")
    for ev in events:
        st.markdown(f"### {ev.date} — {ev.title}")
        st.caption(ev.description or "")
        st.divider()


# ---------- MAIN APP ----------

def main():
    st.set_page_config(
        page_title="Sci Club Val d'Ayas",
        page_icon="🎿",
        layout="wide"
    )

    init_db_and_seed()
    db = get_db()

    with st.sidebar:
        st.title("Sci Club Val d'Ayas")
        st.write("Seleziona utente:")

        users = db.query(User).order_by(User.role, User.name).all()

        options = {
            f"{u.name} ({get_role_label(u.role)})": u.id
            for u in users
        }

        selected = st.selectbox("Utente", list(options.keys()))
        current_user = db.query(User).get(options[selected])

    st.caption(f"Accesso come **{current_user.name}** — Ruolo: **{get_role_label(current_user.role)}**")

    if current_user.role == "admin":
        render_admin_dashboard(db, current_user)
    elif current_user.role == "coach":
        render_coach_dashboard(db, current_user)
    elif current_user.role == "parent":
        render_parent_dashboard(db, current_user)
    else:
        st.error("Ruolo sconosciuto.")

    db.close()


if __name__ == "__main__":
    main()
