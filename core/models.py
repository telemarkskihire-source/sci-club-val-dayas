import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Boolean, Integer, ForeignKey,
    Date, Time, Text, DateTime, CheckConstraint,
    UniqueConstraint
)
from sqlalchemy.orm import relationship
from .db import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())

# ---------- USERS ----------

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    role = Column(String, nullable=False)  # 'admin', 'coach', 'parent'
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(role.in_(["admin", "coach", "parent"]), name="ck_users_role"),
    )

    parent_links = relationship("ParentAthlete", back_populates="parent")
    coached_categories = relationship("CoachCategory", back_populates="coach")
    sent_messages = relationship("Message", back_populates="sender")
    athlete_reports = relationship("AthleteReport", back_populates="coach")
    team_reports = relationship("TeamReport", back_populates="coach")


# ---------- CATEGORIES ----------

class Category(Base):
    __tablename__ = "categories"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    athletes = relationship("Athlete", back_populates="category")
    coaches = relationship("CoachCategory", back_populates="category")
    events = relationship("Event", back_populates="category")
    team_reports = relationship("TeamReport", back_populates="category")


# ---------- ATHLETES ----------

class Athlete(Base):
    __tablename__ = "athletes"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    birth_year = Column(Integer, nullable=True)
    category_id = Column(String, ForeignKey("categories.id", ondelete="SET NULL"))
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    category = relationship("Category", back_populates="athletes")
    parent_links = relationship("ParentAthlete", back_populates="athlete")
    attendances = relationship("EventAttendance", back_populates="athlete")
    reports = relationship("AthleteReport", back_populates="athlete")


# ---------- PARENT_ATHLETE ----------

class ParentAthlete(Base):
    __tablename__ = "parent_athlete"

    parent_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    athlete_id = Column(String, ForeignKey("athletes.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    parent = relationship("User", back_populates="parent_links")
    athlete = relationship("Athlete", back_populates="parent_links")


# ---------- COACH_CATEGORIES ----------

class CoachCategory(Base):
    __tablename__ = "coaches_categories"

    coach_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    category_id = Column(String, ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    coach = relationship("User", back_populates="coached_categories")
    category = relationship("Category", back_populates="coaches")


# ---------- EVENTS ----------

class Event(Base):
    __tablename__ = "events"

    id = Column(String, primary_key=True, default=gen_uuid)
    type = Column(String, nullable=False)  # 'training' / 'race'
    category_id = Column(String, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String, nullable=True)
    date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    created_by = Column(String, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(type.in_(["training", "race"]), name="ck_events_type"),
    )

    category = relationship("Category", back_populates="events")
    attendances = relationship("EventAttendance", back_populates="event")


# ---------- EVENT_ATTENDANCE ----------

class EventAttendance(Base):
    __tablename__ = "event_attendance"

    id = Column(String, primary_key=True, default=gen_uuid)
    event_id = Column(String, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    athlete_id = Column(String, ForeignKey("athletes.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, nullable=False, default="undecided")
    skis_in_skiroom = Column(Boolean, nullable=False, default=False)
    car_available = Column(Boolean, nullable=False, default=False)
    car_seats = Column(Integer, default=0)
    updated_by = Column(String, ForeignKey("users.id", ondelete="SET NULL"))
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("event_id", "athlete_id", name="uq_event_athlete"),
        CheckConstraint(status.in_(["present", "absent", "undecided"]), name="ck_event_attendance_status"),
    )

    event = relationship("Event", back_populates="attendances")
    athlete = relationship("Athlete", back_populates="attendances")


# ---------- MESSAGES ----------

class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=gen_uuid)
    sender_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(String, ForeignKey("categories.id", ondelete="CASCADE"))
    athlete_id = Column(String, ForeignKey("athletes.id", ondelete="CASCADE"))
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    sender = relationship("User", back_populates="sent_messages")
    category = relationship("Category")
    athlete = relationship("Athlete")


# ---------- ATHLETE_REPORTS ----------

class AthleteReport(Base):
    __tablename__ = "athlete_reports"

    id = Column(String, primary_key=True, default=gen_uuid)
    athlete_id = Column(String, ForeignKey("athletes.id", ondelete="CASCADE"), nullable=False)
    coach_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    date = Column(Date, nullable=False, default=date.today)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    athlete = relationship("Athlete", back_populates="reports")
    coach = relationship("User", back_populates="athlete_reports")


# ---------- TEAM_REPORTS ----------

class TeamReport(Base):
    __tablename__ = "team_reports"

    id = Column(String, primary_key=True, default=gen_uuid)
    category_id = Column(String, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    coach_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    date = Column(Date, nullable=False, default=date.today)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    category = relationship("Category", back_populates="team_reports")
    coach = relationship("User", back_populates="team_reports")
