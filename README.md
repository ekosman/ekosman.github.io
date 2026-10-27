# Eitan Kosman · Blue theme

A complete personal research website, ready for GitHub Pages.

The site includes 12 public research works, 11 distinct patent records, employment and education, talks, technical writing, and academic service. It uses plain HTML, CSS, and JavaScript. Viewing and publishing require no installation, build service, API key, database, or paid hosting.

## Start here

1. Extract the ZIP completely.
2. Open `index.html` in your browser to view the website.
3. Follow `PUBLISHING.md` to publish it on GitHub Pages.

The separate `Eitan_Kosman_Blue_Preview.html` file is a portable preview with embedded fonts, graphics, styles, and scripts. For publishing and ongoing edits, use the files in this ZIP.

## Features

* Responsive layout with mobile navigation.
* Interactive diffusion randomly reveals one of six photos each cycle, with noise stages, a reveal slider, pause and a New image button.
* Publication search by title, author, venue, and year.
* Topic filters and a full downloadable BibTeX bibliography.
* Citation dialogs with copy and individual download actions.
* Patent archive with published applications distinguished from the featured granted patent.
* Complete career progression and earlier teaching roles.
* Keyboard controls, skip navigation, visible focus states, and reduced motion support.
* Core content and links available without JavaScript.
* Local fonts and vector graphics. No analytics, trackers, external scripts, or third party font requests.
* Social sharing image, page metadata, structured data, sitemap, robots.txt, and a custom 404 page.

## File map

| File | Purpose |
| --- | --- |
| `index.html` | Complete website, ready to host |
| `assets/style.css` | Layout, colors, typography, responsive and print styles |
| `assets/main.js` | Interactions and conceptual canvas illustration |
| `assets/fonts.css` and `assets/fonts/` | Local fonts and their licenses |
| `assets/*.svg` | Editable original vector graphics |
| `assets/social.png` | Social sharing image |
| `assets/publications.bib` | Downloadable bibliography |
| `source/content/publications.json` | Publication metadata |
| `source/content/patents.json` | Patent metadata |
| `source/scripts/template.html` | Editable page template |
| `source/scripts/build.py` | Optional generator using only Python's standard library |
| `SOURCE_NOTES.md` | Sources and editorial choices |
| `PUBLISHING.md` | Publishing and maintenance instructions |

## Updating the content

Edit the files under `source/`, then run this from the extracted website directory:

```bash
python3 source/scripts/build.py
```

This regenerates `index.html` and `assets/publications.bib`. Publication and patent counts update automatically. Upload or commit the regenerated files together with the edited sources.

For a quick one time change, you may edit `index.html` directly. Also make that change in `source/scripts/template.html` if you intend to use the generator later, otherwise regeneration will overwrite it.

The generator does not run on GitHub. All website files are already generated. Do not configure a framework or install Node packages.

## Local preview

Opening `index.html` directly works. For a local HTTP preview:

```bash
python3 -m http.server 8000
```

Open `http://localhost:8000/`. Clipboard permissions vary by browser when using a local file; the citation dialog selects the text for manual copying when clipboard access is unavailable. Bibliography downloads remain available.

## Design notes

This alternate theme takes inspiration from Booking.com's strong blue navigation, yellow search frame and white content cards. All branding and content identify Eitan Kosman. The discovery bar filters the publication archive by keyword and research area. One of six user supplied photos emerges from noise each cycle. Photos are chosen randomly without immediate repeats, with pause, a New image button, clickable stages and a slider. Reduced motion preferences show the clear portrait without autoplay. This version is saved separately from the earlier midnight theme.

Prepared 26 October 2026. See `SOURCE_NOTES.md` for content scope and provenance.

## Impact metrics

`source/content/impact.json` holds the dated Google Scholar snapshot, per paper citation counts and public repository snapshot. Update these fields and run the generator to refresh the saved figures. Citation counts are from Google Scholar on 26 October 2026. The website refreshes GitHub stars and forks on each visit using GitHub's public API, excluding repositories forked from other owners. If the API is unavailable or rate limited, dated saved figures remain visible. Google Scholar counts use the saved snapshot and link directly to the citation record. No API key is required.
