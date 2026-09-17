Copy any of the bundled templates here to override them:

- cv.html
- cover-letter.html
- style.css

A Style is one CSS file that changes the look without touching the HTML: put your own under `styles/<name>.css` here and set `"style": "<name>"` (or `"letter_style"`) in `config.json` or an application's `application.json`. The bundled Styles are classic, bar, bare and accent; `var(--accent)` is the colour from `config.json`. Scope rules to `.cv` or `.letter` when a look should apply to one document only; the bundled Styles change the letter only through `.letter .subject`.

The bundled originals live in the installed package under `jobapply/templates/` and `jobapply/templates/styles/`.
