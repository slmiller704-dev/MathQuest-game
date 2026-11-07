# MathQuest Live Learning Battles
Animated FastAPI game prototype with adaptive mastery.

## Features
- Animated character and guardian battle states
- Grade-banded questions for grades 4-12
- Adaptive question selection based on weakest mastery skill
- Nine character classes and two selectable variants
- Character abilities, HP, damage, streaks, XP, levels, coins, and rewards
- Render Blueprint deployment

## Run
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000.

## Deploy
Place all files at the GitHub repository root and sync the included Render Blueprint.

## MVP note
Sessions are held in server memory. For classroom production, move sessions, profiles, mastery, and rewards to PostgreSQL; add authentication, teacher-managed rosters, privacy controls, migrations, tests, and multi-instance shared state.
