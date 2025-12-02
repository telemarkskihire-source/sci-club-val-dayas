# core/models.py
# Modelli SQLAlchemy per Sci Club Val d'Ayas

from datetime import datetime, date

from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import relationship

from .db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    email = Column(String(200), nullable=True, unique=True)
    role = Column(String(50), nullable=False)  # "admin", "coach", "parent"

    # relazioni
    coached_categories = relationship("CoachCategory", back_populates="coach")
    parent_links = relationship("ParentAthlete", back_populates="parent")
    sent_messages = relationship("Message", back_populates="sender")
    team_reports = relationship("TeamReport", back_populates="coach")
    athlete_reports = relationship("AthleteReport", back_populates="coach")
    device_tokens = relationship("DeviceToken", back_populates="user")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    athletes = relationship("Athlete", back_populates="category")
    events = relationship("Event", back_populates="category")


class Athlete(Base):
    __tablename__ = "athletes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    birth_year = Column(Integer, nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)

    category = relationship("Category", back_populates="athletes")
    parents = relationship("ParentAthlete", back_populates="athlete")
    attendances = relationship("EventAttendance", back_populates="athlete")
    personal_reports = relationship("AthleteReport", back_populates="athlete")


class ParentAthlete(Base):
    __tablename__ = "parent_athlete"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=False)

    parent = relationship("User", back_populates="parent_links")
    athlete = relationship("Athlete", back_populates="parents")


class CoachCategory(Base):
    __tablename__ = "coach_category"

    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)

    coach = relationship("User", back_populates="coached_categories")
    category = relationship("Category")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)

    # "training" / "race"
    type = Column(String(50), nullable=False)

    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(200), nullable=True)
    date = Column(Date, nullable=False)

    # richieste logistiche decise dal coach
    ask_skiroom = Column(Boolean, default=False)   # chiedo sci in ski-room?
    ask_carpool = Column(Boolean, default=False)   # chiedo auto (solo gare)?

    category = relationship("Category", back_populates="events")
    attendances = relationship("EventAttendance", back_populates="event")
    team_reports = relationship("TeamReport", back_populates="event")
    athlete_reports = relationship("AthleteReport", back_populates="event")


class EventAttendance(Base):
    __tablename__ = "event_attendance"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=False)

    # "undecided" / "present" / "absent"
    status = Column(String(20), nullable=False, default="undecided")

    # logistica legata alla richiesta del coach
    skis_in_skiroom = Column(Boolean, default=False)
    car_available = Column(Boolean, default=False)
    car_seats = Column(Integer, nullable=True)

    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    event = relationship("Event", back_populates="attendances")
    athlete = relationship("Athlete", back_populates="attendances")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # broadcast per categoria o personale per atleta
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=True)

    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    sender = relationship("User", back_populates="sent_messages")
    category = relationship("Category")
    athlete = relationship("Athlete")


class TeamReport(Base):
    __tablename__ = "team_reports"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    coach_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    content = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    event = relationship("Event", back_populates="team_reports")
    coach = relationship("User", back_populates="team_reports")


class AthleteReport(Base):
    __tablename__ = "athlete_reports"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=False)
    coach_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    content = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    event = relationship("Event", back_populates="athlete_reports")
    athlete = relationship("Athlete", back_populates="personal_reports")
    coach = relationship("User", back_populates="athlete_reports")


class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    platform = Column(String(50), nullable=False, default="web")  # es. "web", "android"
    token = Column(String(512), nullable=False, unique=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="device_tokens")
