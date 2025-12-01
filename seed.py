# seed.py
from datetime import date, timedelta

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


def get_db() -> Session:
    """Crea una nuova sessione DB."""
    return SessionLocal()


def init_db_and_seed() -> None:
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
        db.add_all(
            [
                CoachCategory(coach_id=coach1.id, category_id=cat_cuccioli.id),
                CoachCategory(coach_id=coach2.id, category_id=cat_ragazzi.id),
            ]
        )

        # --- Atleti ---
        athlete_noah = Athlete(
            name="Noah Favre", birth_year=2014, category_id=cat_cuccioli.id
        )
        athlete_juno = Athlete(
            name="Juno Favre", birth_year=2020, category_id=cat_cuccioli.id
        )
        athlete_seth = Athlete(
            name="Seth Favre", birth_year=2014, category_id=cat_ragazzi.id
        )
        db.add_all([athlete_noah, athlete_juno, athlete_seth])
        db.flush()

        # --- Relazione genitori <-> atleti ---
        db.add_all(
            [
                ParentAthlete(parent_id=parent1.id, athlete_id=athlete_noah.id),
                ParentAthlete(parent_id=parent1.id, athlete_id=athlete_seth.id),
                ParentAthlete(parent_id=parent2.id, athlete_id=athlete_juno.id),
            ]
        )

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
                db.add(
                    EventAttendance(
                        event_id=ev.id,
                        athlete_id=ath.id,
                        status="undecided",
                    )
                )

        db.commit()

    finally:
        db.close()
