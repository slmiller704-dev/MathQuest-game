from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), index=True)
    grade: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )


class Classroom(Base):
    __tablename__ = "classrooms"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    join_code: Mapped[str] = mapped_column(
        String(12),
        unique=True,
        index=True,
    )
    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
    )


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint(
            "classroom_id",
            "student_id",
            name="uq_classroom_student",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    classroom_id: Mapped[int] = mapped_column(
        ForeignKey("classrooms.id"),
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
    )


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        unique=True,
    )
    name: Mapped[str] = mapped_column(String(40))
    archetype: Mapped[str] = mapped_column(String(30))
    variant: Mapped[str] = mapped_column(String(20))

    level: Mapped[int] = mapped_column(default=1)
    xp: Mapped[int] = mapped_column(default=0)
    coins: Mapped[int] = mapped_column(default=0)
    wins: Mapped[int] = mapped_column(default=0)

    max_hp: Mapped[int] = mapped_column(default=100)
    power: Mapped[int] = mapped_column(default=10)
    focus: Mapped[int] = mapped_column(default=10)
    speed: Mapped[int] = mapped_column(default=10)


class SkillMastery(Base):
    __tablename__ = "skill_mastery"
    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "skill",
            name="uq_student_skill",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )
    skill: Mapped[str] = mapped_column(String(50), index=True)
    mastery: Mapped[float] = mapped_column(Float, default=50.0)
    correct_answers: Mapped[int] = mapped_column(default=0)
    incorrect_answers: Mapped[int] = mapped_column(default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class BattleSession(Base):
    __tablename__ = "battle_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )
    skill: Mapped[str] = mapped_column(String(50))
    prompt: Mapped[str] = mapped_column(String(255))
    expected_answer: Mapped[str] = mapped_column(String(80))

    player_hp: Mapped[int] = mapped_column(default=100)
    enemy_hp: Mapped[int] = mapped_column(default=100)
    streak: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )


class BattleAnswer(Base):
    __tablename__ = "battle_answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    battle_id: Mapped[int] = mapped_column(
        ForeignKey("battle_sessions.id"),
        index=True,
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )
    skill: Mapped[str] = mapped_column(String(50))
    prompt: Mapped[str] = mapped_column(String(255))
    submitted_answer: Mapped[str] = mapped_column(String(80))
    correct: Mapped[int] = mapped_column()
    response_seconds: Mapped[float] = mapped_column(Float)
    answered_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )


class Reward(Base):
    __tablename__ = "rewards"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )
    reward_type: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(80))
    details: Mapped[str] = mapped_column(String(255))
    earned_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )
