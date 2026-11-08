# MathQuest character asset patch

New asset convention:
`/static/characters/{younger|highschool}/{boy|girl}/{class}.png`

The included transition JavaScript switches the preview whenever grade, version, or class changes and preloads the new image before fading it in.

This package contains nine newly separated younger-boy assets from the generated roster. The remaining younger-girl and high-school boy/girl unique sheets still need their individual art generated before their corresponding folders can be populated with final assets.

HTML preview element expected by the patch:
`<div class="character-preview-frame"><img id="characterPreview" class="character-preview" alt="Selected MathQuest character"></div>`

Include `/static/character-transition.css` and `/static/character-transition.js` after copying them into your static folder.
