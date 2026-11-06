# MathQuest Render Deployment
Push this folder to GitHub, GitLab, or Bitbucket. In Render, create a Blueprint from the repository. The included render.yaml installs dependencies and launches the FastAPI service.

## Added playable archetypes
- Fairy: 85 HP, 9 Power, 15 Focus, 14 Speed. Ability: Spark of Insight.
- Jester: 95 HP, 10 Power, 12 Focus, 15 Speed. Ability: Wildcard.
- Warlock: 100 HP, 15 Power, 14 Focus, 8 Speed. Ability: Arcane Equation.

## Gameplay update
- Added younger and high-school Fairy, Jester, and Warlock artwork in `static/assets/new_character_roster.png`.
- All nine abilities now change battle state or rewards.
- Fairy unlocks at level 2, Jester at level 3, and Warlock at level 4.
- Additional level rewards include coins, title badges, outfit colors, and weapon skins.
- MVP progress is stored in browser localStorage. Move progression to authenticated server-side storage before classroom use.

## Full character variants
The character selector now includes a Boy/Girl version selector for all nine classes: Knight, Wizard, Engineer, Ranger, Ninja, Paladin, Fairy, Jester, and Warlock. The selection is saved with local MVP progress. The integrated roster artwork includes younger (grades 4-8) and high-school (grades 9-12) versions.
