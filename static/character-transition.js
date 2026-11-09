const CHARACTER_CLASSES = ['Knight','Wizard','Engineer','Ranger','Ninja','Paladin','Fairy','Jester','Warlock'];

function characterBand(grade) {
  return Number(grade) <= 8 ? 'younger' : 'highschool';
}

function characterImagePath(grade, variant, archetype) {
  const band = characterBand(grade);
  const type = String(variant).toLowerCase();
  const hero = String(archetype).toLowerCase();
  return `/static/characters/${band}/${type}/${hero}.png`;
}

function updateCharacterPreview({ grade, variant, archetype }) {
  const img = document.querySelector('#characterPreview');
  if (!img) return;
  img.classList.add('is-switching');
  const next = new Image();
  next.onload = () => {
    img.src = next.src;
    img.alt = `${variant} ${archetype}, grade ${grade} MathQuest character`;
    requestAnimationFrame(() => img.classList.remove('is-switching'));
  };
  next.onerror = () => {
    console.warn(
        "Character image not found:",
        characterImagePath(
            grade,
            variant,
            archetype
        )
    );

    img.alt =
        `${variant} ${archetype} artwork ` +
        `has not been added yet`;

    img.removeAttribute("src");

    img.classList.remove(
        "is-switching"
    );
};
  next.src = characterImagePath(grade, variant, archetype);
}

function wireCharacterSelectors() {
  const grade = document.querySelector('#grade');
  const variant = document.querySelector('#variant');
  const archetype = document.querySelector('#char');
  if (!grade || !variant || !archetype) return;
  const refresh = () => updateCharacterPreview({
    grade: grade.value,
    variant: variant.value,
    archetype: archetype.value
  });
  grade.addEventListener('change', refresh);
  variant.addEventListener('change', refresh);
  archetype.addEventListener('change', refresh);
  refresh();
}

document.addEventListener('DOMContentLoaded', wireCharacterSelectors);
