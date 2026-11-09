import os
import random
import uuid
from datetime import datetime, timezone
from typing import Generator

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
    select,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


# -----------------------------------------------------------------------------
# Database
# -----------------------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mathquest.db")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()


# -----------------------------------------------------------------------------
# Models
# -----------------------------------------------------------------------------

class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(80), default="MathQuest Student")
    grade: Mapped[int] = mapped_column(Integer, default=4)
    archetype: Mapped[str] = mapped_column(String(30), default="Knight")
    variant: Mapped[str] = mapped_column(String(20), default="boy")
    level: Mapped[int] = mapped_column(Integer, default=1)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    coins: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class BattleSession(Base):
    __tablename__ = "battle_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    student_id: Mapped[str] = mapped_column(
        ForeignKey("student_profiles.id"), index=True
    )
    grade: Mapped[int] = mapped_column(Integer)
    archetype: Mapped[str] = mapped_column(String(30))
    variant: Mapped[str] = mapped_column(String(20))
    skill: Mapped[str] = mapped_column(String(50), default="mixed")
    prompt: Mapped[str] = mapped_column(String(255), default="")
    expected_answer: Mapped[float] = mapped_column(Float, default=0.0)
    hint: Mapped[str] = mapped_column(String(255), default="")
    player_hp: Mapped[int] = mapped_column(Integer, default=100)
    player_max_hp: Mapped[int] = mapped_column(Integer, default=100)
    enemy_hp: Mapped[int] = mapped_column(Integer, default=100)
    streak: Mapped[int] = mapped_column(Integer, default=0)
    ability_used: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class SkillMastery(Base):
    __tablename__ = "skill_mastery"
    __table_args__ = (
        UniqueConstraint("student_id", "skill", name="uq_student_skill"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(
        ForeignKey("student_profiles.id"), index=True
    )
    skill: Mapped[str] = mapped_column(String(50), index=True)
    mastery: Mapped[float] = mapped_column(Float, default=50.0)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0)
    incorrect_answers: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class BattleAnswer(Base):
    __tablename__ = "battle_answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    battle_id: Mapped[str] = mapped_column(
        ForeignKey("battle_sessions.id"), index=True
    )
    student_id: Mapped[str] = mapped_column(
        ForeignKey("student_profiles.id"), index=True
    )
    skill: Mapped[str] = mapped_column(String(50))
    prompt: Mapped[str] = mapped_column(String(255))
    submitted_answer: Mapped[float] = mapped_column(Float)
    expected_answer: Mapped[float] = mapped_column(Float)
    correct: Mapped[bool] = mapped_column(Boolean)
    response_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class Reward(Base):
    __tablename__ = "rewards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(
        ForeignKey("student_profiles.id"), index=True
    )
    reward_type: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(80))
    details: Mapped[str] = mapped_column(String(255))
    earned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


Base.metadata.create_all(bind=engine)


# -----------------------------------------------------------------------------
# Game configuration
# -----------------------------------------------------------------------------

CHARACTERS = {
    "Knight": {"hp": 125, "power": 12, "ability": "Fortify"},
    "Wizard": {"hp": 95, "power": 14, "ability": "Insight"},
    "Engineer": {"hp": 105, "power": 11, "ability": "Optimize"},
    "Ranger": {"hp": 105, "power": 12, "ability": "Precision"},
    "Ninja": {"hp": 95, "power": 12, "ability": "Quick Think"},
    "Paladin": {"hp": 130, "power": 10, "ability": "Encourage"},
    "Fairy": {"hp": 90, "power": 9, "ability": "Spark of Insight"},
    "Jester": {"hp": 100, "power": 11, "ability": "Wildcard"},
    "Warlock": {"hp": 105, "power": 15, "ability": "Arcane Equation"},
}


class StartRequest(BaseModel):
    grade: int = Field(ge=3, le=12)
    archetype: str
    variant: str = Field(pattern="^(boy|girl)$")
    display_name: str = Field(default="MathQuest Student", min_length=2, max_length=80)


class AnswerRequest(BaseModel):
    session_id: str
    answer: float
    seconds: float = Field(default=10.0, ge=0, le=300)


class AbilityRequest(BaseModel):
    session_id: str


app = FastAPI(title="MathQuest Persistent Learning Battles", version="3.0")
app.mount("/static", StaticFiles(directory="static"), name="static")


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def get_or_create_profile(
    request: Request,
    response: Response,
    database: Session,
    start_request: StartRequest,
) -> StudentProfile:
    profile_id = request.cookies.get("mathquest_profile_id")
    profile = database.get(StudentProfile, profile_id) if profile_id else None

    if profile is None:
        profile_id = str(uuid.uuid4())
        profile = StudentProfile(
            id=profile_id,
            display_name=start_request.display_name,
            grade=start_request.grade,
            archetype=start_request.archetype,
            variant=start_request.variant,
        )
        database.add(profile)
        
        # Insert the parent profile before creating records that
        # reference profile.id through a foreign key.
        database.flush()
        response.set_cookie(
            key="mathquest_profile_id",
            value=profile_id,
            max_age=60 * 60 * 24 * 365,
            httponly=True,
            samesite="lax",
            secure=bool(os.getenv("RENDER")),
        )
    else:
        profile.display_name = start_request.display_name
        profile.grade = start_request.grade
        profile.archetype = start_request.archetype
        profile.variant = start_request.variant

    return profile


def mastery_dictionary(database: Session, student_id: str) -> dict[str, float]:
    records = database.scalars(
        select(SkillMastery).where(SkillMastery.student_id == student_id)
    ).all()
    return {record.skill: round(record.mastery, 1) for record in records}


def allowed_skills_for_grade(grade: int) -> list[str]:
    if grade == 3:
        return [
            "multiplication",
            "division",
            "place_value",
            "fractions",
            "measurement",
            "area_perimeter",
            "two_step",
            "patterns",
            "geometry",
        ]

    if grade <= 5:
        return [
            "multiplication",
            "division",
            "fractions",
        ]

    if grade <= 8:
        return [
            "equations",
            "percent",
            "integers",
        ]

    return [
        "algebra",
        "functions",
        "geometry",
    ]


def weakest_skill(database: Session, student_id: str, grade: int) -> str | None:
    allowed = allowed_skills_for_grade(grade)
    records = database.scalars(
        select(SkillMastery)
        .where(
            SkillMastery.student_id == student_id,
            SkillMastery.skill.in_(allowed),
        )
        .order_by(SkillMastery.mastery.asc())
    ).all()
    existing = {record.skill for record in records}
    for skill in allowed:
        if skill not in existing:
            return skill
    return records[0].skill if records else None


def generate_problem(
    grade: int,
    preferred_skill: str | None = None,
    easier: bool = False,
) -> tuple[str, float, str, str]:

    # Arcane Equation creates an easier problem that remains appropriate
    # for the student's grade.
    if easier:
        if grade == 3:
            left = random.randint(2, 5)
            right = random.randint(2, 5)

            return (
                f"{left} × {right} = ?",
                float(left * right),
                "multiplication",
                "Think of equal groups or repeated addition.",
            )

        left = random.randint(2, 9)
        right = random.randint(2, 9)

        return (
            f"{left} × {right} = ?",
            float(left * right),
            "review",
            "Use a multiplication fact you already know.",
        )

    available = allowed_skills_for_grade(grade)

    skill = (
        preferred_skill
        if preferred_skill in available
        else random.choice(available)
    )

    # ------------------------------------------------------------------
    # Grade 3-specific problems
    # ------------------------------------------------------------------

    if grade == 3:
        if skill == "multiplication":
            left = random.randint(2, 10)
            right = random.randint(2, 10)

            return (
                f"{left} × {right} = ?",
                float(left * right),
                skill,
                f"Think of {left} groups with {right} in each group.",
            )

        if skill == "division":
            divisor = random.randint(2, 10)
            quotient = random.randint(2, 10)
            dividend = divisor * quotient

            return (
                f"{dividend} ÷ {divisor} = ?",
                float(quotient),
                skill,
                f"How many groups of {divisor} are in {dividend}?",
            )

        if skill == "place_value":
            hundreds = random.randint(1, 8)
            tens = random.randint(1, 9)
            ones = random.randint(1, 9)

            number = hundreds * 100 + tens * 10 + ones

            return (
                f"What is the value of the digit {tens} in {number}?",
                float(tens * 10),
                skill,
                "The middle digit is in the tens place.",
            )

        if skill == "fractions":
            denominator = random.choice([2, 3, 4, 6, 8])
            numerator = random.randint(1, denominator - 1)

            return (
                f"A shape has {denominator} equal parts. "
                f"{numerator} parts are shaded. "
                f"What is the numerator?",
                float(numerator),
                skill,
                "The numerator tells how many equal parts are selected.",
            )

        if skill == "measurement":
            first_length = random.randint(5, 25)
            second_length = random.randint(2, first_length)
            total_length = first_length + second_length

            return (
                f"A ribbon is {first_length} centimeters long. "
                f"Another ribbon is {second_length} centimeters long. "
                f"What is their total length?",
                float(total_length),
                skill,
                "Add the two lengths and keep the unit centimeters.",
            )

        if skill == "area_perimeter":
            width = random.randint(2, 10)
            height = random.randint(2, 10)

            if random.choice([True, False]):
                return (
                    f"A rectangle is {width} units wide and "
                    f"{height} units long. What is its area?",
                    float(width * height),
                    skill,
                    "Area equals length multiplied by width.",
                )

            return (
                f"A rectangle is {width} units wide and "
                f"{height} units long. What is its perimeter?",
                float(2 * (width + height)),
                skill,
                "Add all four sides, or double the sum of length and width.",
            (
                )

    if grade == 3 and skill == "two_step":
    starting = random.randint(20, 60)
    added = random.randint(5, 20)
    removed = random.randint(2, min(added + 5, 20))
    expected = starting + added - removed

    return (
        f"A player had {starting} coins, earned {added} more, "
        f"and spent {removed}. How many coins remain?",
        float(expcted),
        skill,
        "First add the earned coins, then subtract the spent coins.",
           )

        if skill == "patterns":
            start = random.randint(1, 10)
            step = random.randint(2, 10)

            first = start
            second = start + step
            third = start + step * 2
            fourth = start + step * 3

            return (
                f"What number comes next? "
                f"{first}, {second}, {third}, {fourth}, ?",
                float(start + step * 4),
                skill,
                f"Each number increases by {step}.",
            )

        # Grade 3 geometry
        sides = random.choice([3, 4, 5, 6])

        shape_names = {
            3: "triangle",
            4: "quadrilateral",
            5: "pentagon",
            6: "hexagon",
        }

        return (
            f"How many sides does a {shape_names[sides]} have?",
            float(sides),
            "geometry",
            "Count the straight sides of the shape.",
        )

    # ------------------------------------------------------------------
    # Grades 4–5
    # ------------------------------------------------------------------

    if skill == "multiplication":
        left = random.randint(2, 12)
        right = random.randint(2, 12)

        return (
            f"{left} × {right} = ?",
            float(left * right),
            skill,
            f"Break {left} × {right} into smaller facts.",
        )

    if skill == "division":
        divisor = random.randint(2, 12)
        answer = random.randint(2, 12)
        dividend = divisor * answer

        return (
            f"{dividend} ÷ {divisor} = ?",
            float(answer),
            skill,
            "Find the number that multiplied by the divisor equals the dividend.",
        )

    if skill == "fractions":
        denominator = random.choice([2, 4, 5, 10])
        numerator = random.randint(1, denominator - 1)

        return (
            f"Write {numerator}/{denominator} as a decimal.",
            float(numerator / denominator),
            skill,
            f"Divide {numerator} by {denominator}.",
        )

    # ------------------------------------------------------------------
    # Grades 6–8
    # ------------------------------------------------------------------

    if skill == "equations":
        answer = random.randint(2, 14)
        coefficient = random.randint(2, 8)
        constant = random.randint(1, 18)
        result = coefficient * answer + constant

        return (
            f"Solve: {coefficient}x + {constant} = {result}",
            float(answer),
            skill,
            f"Subtract {constant}, then divide by {coefficient}.",
        )

    if skill == "percent":
        percent = random.choice([10, 20, 25, 50, 75])
        base_number = random.choice([20, 40, 60, 80, 100, 120])

        return (
            f"What is {percent}% of {base_number}?",
            float(percent * base_number / 100),
            skill,
            "Convert the percent to a decimal, then multiply.",
        )

    if skill == "integers":
        left = random.randint(-15, 15)
        right = random.randint(-15, 15)

        return (
            f"{left} + ({right}) = ?",
            float(left + right),
            skill,
            "Use a number line and pay attention to the signs.",
        )

    # ------------------------------------------------------------------
    # Grades 9–12
    # ------------------------------------------------------------------

    if skill == "algebra":
        value = random.randint(-6, 8)
        result = value * value + 3 * value + 2

        return (
            f"Evaluate x² + 3x + 2 when x = {value}",
            float(result),
            skill,
            "Substitute the value for x; use parentheses for a negative value.",
        )

    if skill == "functions":
        value = random.randint(-5, 8)

        return (
            f"If f(x) = 2x − 5, find f({value}).",
            float(2 * value - 5),
            skill,
            "Replace x with the given input value.",
        )

    width = random.randint(3, 15)
    height = random.randint(3, 15)

    return (
        f"A rectangle is {width} units by {height} units. What is its area?",
        float(width * height),
        "geometry",
        "Area equals length multiplied by width.",
    )


def update_mastery(
    database: Session,
    student_id: str,
    skill: str,
    correct: bool,
) -> SkillMastery:
    record = database.scalar(
        select(SkillMastery).where(
            SkillMastery.student_id == student_id,
            SkillMastery.skill == skill,
        )
    )

    if record is None:
        record = SkillMastery(
            student_id=student_id,
            skill=skill,
            mastery=50.0,
            correct_answers=0,
            incorrect_answers=0,
        )

        database.add(record)

    # Defensive handling for older rows that might contain NULL.
    if record.correct_answers is None:
        record.correct_answers = 0

    if record.incorrect_answers is None:
        record.incorrect_answers = 0

    if record.mastery is None:
        record.mastery = 50.0

    if correct:
        record.correct_answers += 1
        record.mastery = min(
            100.0,
            record.mastery + 5.0,
        )
    else:
        record.incorrect_answers += 1
        record.mastery = max(
            0.0,
            record.mastery - 3.0,
        )

    return record

def add_reward(
    database: Session,
    student_id: str,
    reward_type: str,
    title: str,
    details: str,
) -> Reward:
    reward = Reward(
        student_id=student_id,
        reward_type=reward_type,
        title=title,
        details=details,
    )
    database.add(reward)
    return reward


def apply_level_ups(database: Session, profile: StudentProfile) -> list[str]:
    unlocked_rewards: list[str] = []

    while profile.xp >= profile.level * 100:
        profile.xp -= profile.level * 100
        profile.level += 1
        profile.coins += 50

        details_by_level = {
            2: "Fairy character unlocked and 50 coins awarded.",
            3: "Jester character unlocked and title badge awarded.",
            4: "Warlock character unlocked and Arcane effect awarded.",
            5: "Golden outfit colors unlocked.",
            6: "Crystal weapon skin unlocked.",
        }
        details = details_by_level.get(
            profile.level, "Level reached and 50 coins awarded."
        )
        add_reward(
            database,
            profile.id,
            "level_up",
            f"Level {profile.level}",
            details,
        )
        unlocked_rewards.append(details)

    return unlocked_rewards


def build_game_response(
    database: Session,
    profile: StudentProfile,
    battle: BattleSession,
    event: str,
    message: str,
) -> dict:
    rewards = database.scalars(
        select(Reward)
        .where(Reward.student_id == profile.id)
        .order_by(Reward.earned_at.desc())
        .limit(10)
    ).all()
    return {
        "session_id": battle.id,
        "profile_id": profile.id,
        "event": event,
        "message": message,
        "character": {
            "archetype": profile.archetype,
            "variant": profile.variant,
            "level": profile.level,
            "xp": profile.xp,
            "coins": profile.coins,
            "wins": profile.wins,
            "ability": CHARACTERS[profile.archetype]["ability"],
        },
        "battle": {
            "hp": battle.player_hp,
            "max_hp": battle.player_max_hp,
            "enemy_hp": battle.enemy_hp,
            "prompt": battle.prompt if battle.status == "active" else None,
            "skill": battle.skill,
            "streak": battle.streak,
            "status": battle.status,
            "ability_used": battle.ability_used,
        },
        "mastery": mastery_dictionary(database, profile.id),
        "rewards": [
            {"title": reward.title, "type": reward.reward_type, "details": reward.details}
            for reward in rewards
        ],
    }


def load_active_battle(database: Session, session_id: str) -> BattleSession:
    battle = database.scalar(
        select(BattleSession)
        .where(BattleSession.id == session_id)
        .with_for_update()
    )
    if battle is None:
        raise HTTPException(status_code=404, detail="Battle session not found.")
    if battle.status != "active":
        raise HTTPException(status_code=409, detail="This battle has already ended.")
    return battle


def load_profile_for_update(database: Session, student_id: str) -> StudentProfile:
    profile = database.scalar(
        select(StudentProfile)
        .where(StudentProfile.id == student_id)
        .with_for_update()
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    return profile


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------

@app.get("/")
def home() -> FileResponse:
    return FileResponse("static/index.html")


@app.get("/health")
def health(database: Session = Depends(get_db)) -> dict:
    database.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}


@app.post("/api/start")
def start_battle(
    start_request: StartRequest,
    request: Request,
    response: Response,
    database: Session = Depends(get_db),
) -> dict:
    if start_request.archetype not in CHARACTERS:
        raise HTTPException(status_code=422, detail="Unknown character archetype.")

    profile = get_or_create_profile(request, response, database, start_request)
    preferred = weakest_skill(database, profile.id, start_request.grade)
    prompt, expected, skill, hint = generate_problem(start_request.grade, preferred)
    stats = CHARACTERS[start_request.archetype]

    battle = BattleSession(
        id=str(uuid.uuid4()),
        student_id=profile.id,
        grade=start_request.grade,
        archetype=start_request.archetype,
        variant=start_request.variant,
        skill=skill,
        prompt=prompt,
        expected_answer=expected,
        hint=hint,
        player_hp=stats["hp"],
        player_max_hp=stats["hp"],
        enemy_hp=100,
    )
    database.add(battle)
    database.commit()
    database.refresh(profile)
    database.refresh(battle)

    return build_game_response(
        database,
        profile,
        battle,
        "battle_start",
        f"{start_request.variant.title()} {start_request.archetype} entered the arena!",
    )


@app.post("/api/answer")
def submit_answer(
    answer_request: AnswerRequest,
    database: Session = Depends(get_db),
) -> dict:
    battle = load_active_battle(database, answer_request.session_id)
    profile = load_profile_for_update(database, battle.student_id)
    correct = abs(answer_request.answer - battle.expected_answer) < 0.001

    database.add(
        BattleAnswer(
            battle_id=battle.id,
            student_id=profile.id,
            skill=battle.skill,
            prompt=battle.prompt,
            submitted_answer=answer_request.answer,
            expected_answer=battle.expected_answer,
            correct=correct,
            response_seconds=answer_request.seconds,
        )
    )
    update_mastery(database, profile.id, battle.skill, correct)

    event = "miss"
    message = f"The Number Guardian counterattacks. Hint: {battle.hint}"

    if correct:
        speed_bonus = max(0, 10 - int(answer_request.seconds))
        damage = 15 + CHARACTERS[profile.archetype]["power"] + speed_bonus + battle.streak * 2
        battle.enemy_hp = max(0, battle.enemy_hp - damage)
        battle.streak += 1
        xp_gain = 20 + min(10, battle.streak * 2)
        profile.xp += xp_gain
        profile.coins += 5
        event = "hit"
        message = f"Correct! {damage} damage dealt. +{xp_gain} XP and +5 coins."
    else:
        battle.player_hp = max(0, battle.player_hp - 15)
        battle.streak = 0

    level_rewards = apply_level_ups(database, profile)

    if battle.enemy_hp <= 0:
        battle.status = "victory"
        battle.completed_at = datetime.now(timezone.utc)
        profile.wins += 1
        profile.coins += 25
        add_reward(
            database,
            profile.id,
            "victory",
            "Victory Chest",
            "The Number Guardian was defeated. 25 coins awarded.",
        )
        event = "victory"
        message = "Victory! The Number Guardian was defeated. +25 coins."
    elif battle.player_hp <= 0:
        battle.status = "defeat"
        battle.completed_at = datetime.now(timezone.utc)
        event = "defeat"
        message = "The Number Guardian won this round. Mastery will guide the next lesson."
    else:
        preferred = weakest_skill(database, profile.id, profile.grade)
        prompt, expected, skill, hint = generate_problem(profile.grade, preferred)
        battle.prompt = prompt
        battle.expected_answer = expected
        battle.skill = skill
        battle.hint = hint

    if level_rewards:
        message += " " + " ".join(level_rewards)

    database.commit()
    database.refresh(profile)
    database.refresh(battle)
    return build_game_response(database, profile, battle, event, message)


@app.post("/api/ability")
def use_ability(
    ability_request: AbilityRequest,
    database: Session = Depends(get_db),
) -> dict:
    battle = load_active_battle(database, ability_request.session_id)
    profile = load_profile_for_update(database, battle.student_id)

    if battle.ability_used:
        raise HTTPException(
            status_code=409,
            detail="The character ability has already been used in this battle.",
        )

    battle.ability_used = True
    ability = CHARACTERS[profile.archetype]["ability"]

    if ability == "Fortify":
        battle.player_hp = min(battle.player_max_hp, battle.player_hp + 15)
        message = "Fortify restored 15 HP."
    elif ability == "Insight":
        message = f"Insight: {battle.hint}"
    elif ability == "Optimize":
        rounded = int(round(battle.expected_answer))
        message = f"Optimize: the nearest whole-number answer is {'even' if rounded % 2 == 0 else 'odd'}."
    elif ability == "Precision":
        battle.enemy_hp = max(0, battle.enemy_hp - 20)
        message = "Precision dealt 20 strategic damage."
    elif ability == "Quick Think":
        profile.xp += 10
        message = "Quick Think awarded 10 bonus XP."
    elif ability == "Encourage":
        battle.player_hp = min(battle.player_max_hp, battle.player_hp + 25)
        message = "Encourage restored 25 HP."
    elif ability == "Spark of Insight":
        battle.player_hp = min(battle.player_max_hp, battle.player_hp + 10)
        message = f"Spark of Insight restored 10 HP. Hint: {battle.hint}"
    elif ability == "Wildcard":
        effect = random.choice(["heal", "damage", "coins"])
        if effect == "heal":
            battle.player_hp = min(battle.player_max_hp, battle.player_hp + 20)
            message = "Wildcard restored 20 HP."
        elif effect == "damage":
            battle.enemy_hp = max(0, battle.enemy_hp - 30)
            message = "Wildcard dealt 30 damage."
        else:
            profile.coins += 15
            message = "Wildcard awarded 15 coins."
    else:
        prompt, expected, skill, hint = generate_problem(profile.grade, easier=True)
        battle.prompt = prompt
        battle.expected_answer = expected
        battle.skill = skill
        battle.hint = hint
        message = "Arcane Equation changed the problem into an easier review challenge."

    if battle.enemy_hp <= 0:
        battle.status = "victory"
        battle.completed_at = datetime.now(timezone.utc)
        profile.wins += 1
        profile.coins += 25
        add_reward(
            database,
            profile.id,
            "victory",
            "Ability Victory Chest",
            "A character ability defeated the Number Guardian. 25 coins awarded.",
        )
        message += " Victory Chest opened: +25 coins."

    level_rewards = apply_level_ups(database, profile)
    if level_rewards:
        message += " " + " ".join(level_rewards)

    database.commit()
    database.refresh(profile)
    database.refresh(battle)
    return build_game_response(database, profile, battle, "ability", message)


@app.get("/api/profile")
def get_profile(
    request: Request,
    database: Session = Depends(get_db),
) -> dict:
    profile_id = request.cookies.get("mathquest_profile_id")
    if not profile_id:
        raise HTTPException(status_code=404, detail="No MathQuest profile was found.")

    profile = database.get(StudentProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Student profile was not found.")

    rewards = database.scalars(
        select(Reward)
        .where(Reward.student_id == profile.id)
        .order_by(Reward.earned_at.desc())
        .limit(20)
    ).all()

    return {
        "profile": {
            "id": profile.id,
            "display_name": profile.display_name,
            "grade": profile.grade,
            "archetype": profile.archetype,
            "variant": profile.variant,
            "level": profile.level,
            "xp": profile.xp,
            "coins": profile.coins,
            "wins": profile.wins,
        },
        "mastery": mastery_dictionary(database, profile.id),
        "rewards": [
            {
                "title": reward.title,
                "type": reward.reward_type,
                "details": reward.details,
                "earned_at": reward.earned_at,
            }
            for reward in rewards
        ],
    }
