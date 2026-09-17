# Swiss CV and cover-letter layout (German-speaking Switzerland)

Date: 2026-09-17

**Question.** How do Swiss CVs and cover letters *look* — page structure, photo, dates, personal block, headings, colour, density — as opposed to what they contain (that is in `swiss-cv-and-cover-letter-conventions.md`).

**Method.** A first pass with a text-only fetch tool could not read layout out of PDFs. The template PDFs it located were then downloaded and rendered to images with `pdftoppm`, and each page was inspected visually on 2026-09-17: the HSG "CV – DACH Region" template, the ETH Career Center sample CV and sample letter (Application Guide 2025, pp. 100 and 114), the BIZ Bern adult leaflet's CV and letter templates (M051, pp. 10 and 13), and the three SDBB/berufsberatung.ch sample CVs. The SDBB samples address apprenticeship seekers and are read as a sign of the range, not as guidance for a graduate. Not opened: the jobs.ch template downloads (behind a form) and the UZH sample PDFs (budget).

## 1. What each template looks like

| Source | Audience | Page | Photo | Dates | Personal block | Headings | Colour |
|---|---|---|---|---|---|---|---|
| HSG DACH template [HSG-tpl] | BSc/MSc students | one column, 2 pages, dense | rectangular portrait top right, ≈ 3.5 × 4.5 cm | right-aligned on the entry's first line, `09/2023 – heute` | labelled inline: `Geboren: 05.03.2001 \| Nationalität: Schweiz`, then address, phone \| e-mail, LinkedIn | white caps on a dark teal bar (`PROFIL`, `AUSBILDUNG`, `BERUFSERFAHRUNG`) | one accent (teal) |
| ETH sample CV [ETH-CV] | BSc/MSc students | one column | portrait top right, ≈ 3 × 4 cm | left column, `10.2022 – 09.2023` | bare values: name large, address / phone / e-mail small; `07.05.2000` and `Swiss/Italian` beside the photo, no labels | small heading with a thin rule (`Education`, `Practical experience`) | monochrome |
| BIZ Bern CV template [BIZ-CV] | adults | one column | `(FOTO)` top right | left column, `Seit MM.JJJJ`, `MM.JJJJ – MM.JJJJ` | one contact line `Strasse • PLZ Ort • Telefon • Mail • Profil`, optional Slogan/Kurzprofil line, then bare `TT.MM.JJJJ`, `Nationalität, Ausweis`, `Zivilstand, Kinder` — the leaflet says explicitly no labels are needed | bold text, no rule | monochrome |
| SDBB sample 1 "Aurora" [SDBB-1] | apprentices | one column | portrait top right | left column | labelled two-column table (`Name`, `Adresse`, `Telefon`, …) | green heading text | one accent (green) |
| SDBB sample 2 "Elias" [SDBB-2] | apprentices | **two columns** (left: Persönliche Daten, Stärken, Hobbys, Sprachen; right: Schule, Schnuppern, Referenzen) | round photo top right | inline | labelled, bold keys | caps with a green dot | one accent (green) |
| SDBB sample 3 "Victoria" [SDBB-3] | apprentices | one column | photo **left**, inside a green arrow band | left column | labelled table | green heading text | one accent (green) |

## 2. Common ground

- **One column** for the page in every template aimed at students or adults (HSG, ETH, BIZ Bern). The only two-column layout is an apprenticeship sample.
- **Photo top right of page 1**, portrait format, roughly passport size (3–3.5 cm wide, ETH and HSG). Five of six templates; the exception puts it left.
- **Dates in a left column** or right-aligned on the entry's first line, always month-precise (`MM.YYYY`, `MM/YYYY`), never day-precise, `heute`/`ongoing` for the current entry.
- **Entry shape**: institution or employer bold, degree or role on the next line, then two to four bullets. HSG and ETH both do this; BIZ Bern's template does the same with `Funktion / Stellenbezeichnung` bold.
- **Name large at top left**, contact data in small type directly under it (ETH, BIZ Bern) or as a line with `|` separators (HSG).
- **Kurzprofil optional and first**: HSG's `PROFIL` paragraph, BIZ Bern's `Slogan, Checkliste, Kurzprofil` line. ETH's sample has none.
- **Sans-serif throughout**, body text around 9–10 pt (HSG's floor: "not smaller than 9 pts or 10 pts"), headings barely larger than the body.
- **Sections** in this order everywhere: Ausbildung before Berufserfahrung for students, then Sprachen / IT / Interessen.

## 3. Where they differ

- **Labelled vs bare personal data.** ETH and BIZ Bern show bare values (`07.05.2000`, `Swiss/Italian`) and BIZ Bern's prose says labels like «Geburtsdatum» are unnecessary; HSG labels inline (`Geboren:`, `Nationalität:`); the SDBB samples use full key/value tables. Both conventions are current; bare values are the more Swiss-specific one.
- **Colour.** ETH and BIZ Bern are black on white; HSG uses one accent colour for heading bars; every SDBB sample uses one accent (green). Nobody uses more than one colour.
- **Heading treatment.** Thin rule under small text (ETH), coloured bar with white caps (HSG), plain bold (BIZ Bern).
- **Where dates sit.** Left column (ETH, BIZ Bern, SDBB 1 and 3) vs right-aligned on the first line (HSG).

## 4. Cover letter layout

Both samples ([ETH-letter], [BIZ-letter]) are the classic single-column business letter, monochrome:

- Sender block top left: name, street, PLZ Ort, phone, e-mail. BIZ Bern: it may move into the Kopfzeile, and in an e-mail or online application the company address may be dropped entirely.
- Company block below: company, `Frau/Herr Name Ansprechperson`, street, PLZ Ort.
- `Ort, Datum` on its own line.
- Subject in bold: ETH `Application for the position of consultant, Ref. 42810CH`; BIZ Bern `Funktion oder Jobtitel`. No word "Betreff".
- Salutation, then three blocks (BIZ Bern: Einleitung – Motivation, Hauptteil – Qualifikation, Abschluss – Passion; ETH: YOU – ME – WE), one page.
- Sign-off `Freundliche Grüsse`, signature space, typed name. BIZ Bern: `Optional: Beilagen erwähnen`; ETH: "The term 'Enclosed' is outdated and no longer used."

## 5. Implications for the default template

Our `cv.html` / `style.css` already matches the graduate templates in structure: one column, name large, photo right, dates in a 38 mm left column, thin-rule headings, sans-serif, monochrome. Points of difference and the choice each one leaves:

1. **Photo width 40 mm is on the large side.** ETH and HSG show ≈ 30–35 mm. Suggest 35 mm. [ETH-CV, HSG-tpl]
2. **Labelled personal block** (`Geburtsdatum`, `Nationalität`, …) matches HSG but not ETH or BIZ Bern; BIZ Bern says labels are unnecessary. Either keep (HSG) or switch to bare values grouped on one or two lines under the name. A defensible default is to keep labels for `permit` and `marital_status`, whose bare values are ambiguous, and drop them for birth date and nationality. [BIZ-CV, ETH-CV, HSG-tpl]
3. **Sender in the letter.** Ours is a one-line `topline` (name | street | phone | e-mail) rather than a stacked block; BIZ Bern allows exactly that ("in der Kopfzeile"). No change needed. [BIZ-letter]
4. **No Beilagen list** is confirmed visually: ETH's sample letter has none and its annotation calls the term outdated; BIZ Bern lists it as optional. Consistent with ADR 0003. [ETH-letter, BIZ-letter]
5. **One accent colour is acceptable, not expected.** If a second Template variant is ever offered, an HSG-style coloured heading bar is the only kind of "design" the graduate sources show; two-column or sidebar layouts appear only in the apprenticeship samples. This bounds the pending CV-template choice: variants differ in heading treatment and colour, not in page structure. [HSG-tpl, SDBB-2]

## 6. Sources

| id | Title | URL | Opened |
|---|---|---|---|
| HSG-tpl | CV – DACH Region, template (PDF, 2 pages) | https://hsgcareer.ch/media/4049/curriculum-vitae_template_de.pdf | yes, rendered |
| ETH-CV | Application Guide 2025 EN, p. 100 "Sample CV – MSc and BSc" | https://ethz.ch/content/dam/ethz/associates/students/karriere/berufskarriere/files/Bewerbungsratgeber%202025%20EN%20v1.pdf | yes, rendered |
| ETH-letter | Application Guide 2025 EN, p. 114 "Sample cover letter – structure" | same file | yes, rendered |
| BIZ-CV | Stellensuche: Tipps für das Bewerbungsdossier (Erwachsene), M051, p. 10 "Elemente eines Lebenslaufs" | https://www.biz.bkd.be.ch/content/dam/biz_bkd/dokumente/de/angebote/informationsangebote/biz-publikationen/infoblaetter-und-broschueren/stellensuche-berufseinstieg-praktikum/m051-bewerbungsdossier-erwachsene.pdf | yes, rendered |
| BIZ-letter | same leaflet, p. 13 "Vorlage Bewerbungsbrief: Formatierung und Aufbau" | same file | yes, rendered |
| SDBB-1 | Vorlage Lebenslauf 1 Aurora (SDBB / Laufbahnzentrum Stadt Zürich, 2026) | https://media.sdbb.ch/asset/640e985c-7582-4945-ab8d-a5fea80279b5/Vorlage-Lebenslauf-1-Aurora.pdf | yes, rendered |
| SDBB-2 | Vorlage Lebenslauf 2 Elias | https://media.sdbb.ch/asset/bb5499ad-fe4c-43d6-bbf5-24c4ab477a67/Vorlage-Lebenslauf-2-Elias.pdf | yes, rendered |
| SDBB-3 | Vorlage Lebenslauf 3 Victoria | https://media.sdbb.ch/asset/c2d83607-f5b7-4c3d-906b-a83e2c8e1ee6/Vorlage-Lebenslauf-3-Victoria.pdf | yes, rendered |
| jobs-Vorlagen | jobs.ch Job Coach, Lebenslauf-Vorlagen | https://www.jobs.ch/de/job-coach/lebenslauf-vorlagen-gratis-downloaden/ | prose only; downloads not opened |
| UZH-CV | UZH Career Services, Lebenslauf / CV | https://www.careerservices.uzh.ch/de/ratgeber/bewerbung/bewerbungsdossier/Lebenslauf.html | prose only; sample PDFs not opened |

All accessed 2026-09-17. Rendered pages were inspected at 45–130 dpi; measurements are approximate, read against the A4 page.
