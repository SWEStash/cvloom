# Changelog

All notable changes to cvloom are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Fixed

- **The last entry on every page had its date emitted after its own bullets, welded to the
  next entry's title.** Reported from a real CV: `"…and front-end frameworks. 2002-06 -
  2008-12Customer Facing Engineer"`. Right-aligning a date makes it a text column, and poppler
  flushes a column when the **page** ends, not when the entry does — so one date per page was
  corrupted, in the engine most parsing pipelines are built on. Six constructs were measured
  (float, clearfix, flow-root, absolute, CSS table, flex) and every one of them fails this way;
  only a date in the same continuous run as the title survives. Leader dots technically qualify
  and are disqualified anyway, since filling the gap requires near-invisible text — the thing
  ATS vendors flag as keyword stuffing.

  **Dates are now inline for every template**, next to the title rather than at the right
  margin. The right-hand scan column is genuinely lost. It was not real: it did not survive
  being read.

  This reverses a claim made earlier in the same development cycle, on the strength of a
  synthetic corpus that never put a short entry at the foot of a page.

- **Kerning put spaces inside words.** WeasyPrint emits a kerned pair as two positioned runs
  and extractors read a large enough jump as a word break, so `PAYPAL` extracted as `P AYP AL`,
  `AVATAR` as `A V ATAR`, `WAVE` as `WA VE`. The page is perfect and the word a recruiter
  searches for does not exist in the document. Any employer or skill containing a hard kern
  pair — PA, AV, AW, Ta, Wa, Vo — was exposed. `font-kerning: none` is now set on `body`.

- **The candidate's name was welded to the headline** with no line break between them —
  in every template under pypdf, which infers line breaks from the vertical delta between text
  runs and saw only 2px. The gap under the name is now `0.4em`, expressed relative to the
  heading so it scales with each template's size rather than clearing the threshold at 18pt
  and missing it at 24pt.

- **A CSS escape swallowed its own separator.** `content: " \00b7 "` terminates the escape on
  the following space, so the design templates rendered `Engineer ·2010-01` with the date
  welded to the middot. Now `" \00b7\0020"`.

### Added

- **`cvloom build --extract-text`** writes the PDF's text layer beside it, once per available
  engine (`out.poppler.txt`, `out.pypdf.txt`, `out.pdfminer.txt`). This is the only honest way
  to see what an ATS reads: every defect above was invisible in the rendered page and in the
  HTML, and showed up only by selecting the text. One file per engine on purpose — a single
  `.txt` invites the conclusion that there is one right answer, and the engines disagree.

  `poppler` needs the system `pdftotext`; `pypdf` and `pdfminer` come with `uv sync --extra
  extract`.

- **`tests/test_extraction_fidelity.py`** builds real PDFs and reads them back with every
  installed engine — 5 templates x 3 engines x 6 invariants. Unit tests over the HTML could
  not have caught any of this, because the HTML was never wrong.

### Previously in this cycle

- **Every template fused its job title into its date under one of two PDF extractors.**
  Ratings up to now were measured with `pdftotext` alone, which rebuilds columns from glyph
  geometry. Checked against `pypdf`, which follows the content stream instead, the standard
  `overflow: hidden` + `float: right` date construct came back with the title and date run
  together as one unsplittable token — `TTL00` and `2012-01 – 2013-02` fused. Nothing looked
  wrong on the page, and nothing was wrong in the extractor we happened to have tried.

  Entry headers are now a table row: two cells state "these are one line" outright, where a
  float only implies it. The gutter also needed a real character — padding puts nothing in
  the text stream and a CSS `::before` does not survive — so every right-aligned date is
  preceded by a literal ASCII space, preserved with `white-space: pre`.

- **A full-width skills label fused with its first value.** Same root cause on the aligned
  skills column: `CloudOpsAWS`, one token, unmatchable by any keyword search. Every category
  label now ends in a colon, which guarantees a separator whatever the label's width.

- **`skill_level_bar` rendered its markup as visible text.** It returned `str` rather than
  `Markup`, so Jinja's autoescape printed `<span class="skill-level ...></span>` on the page.
  No packaged template called the filter, so the bug sat unnoticed until one did.

- **`cv/sidebar-compact` was over-padded in the HTML build.** The sidebar carried 14mm of
  left padding — the inset the band needs to clear a *page* edge, not what its text needs.
  On screen the negative margin already pulls the band flush, so that 14mm landed on the
  text. The PDF was unaffected, which is why it survived: print overrides that padding.

### Changed

- **`cv/ats-single` is renamed `cv/ats-clean`.** BREAKING for any profile naming it. "Single"
  meant single-*column* and read as a promise about page count, which the template never made
  — it paginates to two or three pages like the rest.

- **`cv/modern-single`, `cv/timeline-clean`, and `cv/executive-dark` are now rated `safe`.**
  Not by relaxing the bar: the two constructs that had them at `caution` were found to be
  real defects, fixed, and re-measured. Audited over a tagged corpus — 8 work entries with
  0–4 bullets, 15 skill categories with labels from 3 to 28 characters, titles both short
  and long enough to fill the row, across page breaks — every token checked for presence,
  ownership, and order, under both extractors. Five of six templates are now safe; only the
  two-column `cv/sidebar-compact` is not, and no styling fixes that.

  `ATS_CAUTION` now has no members. It is kept because the distinction is real.

- **Extraction ratings are measured with two extractors, not one.** `pdftotext` and `pypdf`
  disagree, and the disagreement is where the defects were hiding. Only what survives both
  is rated safe.

- **`cv/sidebar-compact` renders skill proficiency bars** for `{name, level}` skill items.
  The bar carries its level in a CSS class and so puts no text in the PDF — which rules it
  out of the five templates that have to survive extraction, and costs this one nothing,
  since it is already unsafe for a reason no styling fixes.

### Added

- **`cvloom init` scaffolds `section_titles`** as a commented example on the generated
  `profiles/general.yaml`, with the full list of valid keys.

- **`cvloom build --all`** builds every profile in `profiles/` in one run. A failing profile
  stops the batch rather than being skipped: these are artefacts for a live application, and a
  run that reports success while one CV silently did not rebuild is worse than one that stops
  and names the profile.

- **`section_titles` in a profile renames any section heading.** Text only — styling stays in
  the template.

  ```yaml
  section_titles:
    work: "Professional Experience"
    skills: "Technical Toolkit"
    summary: "Profile"
    professional_development: "Continuing Education"
  ```

  A key left out keeps whatever the chosen template supplies, so `cv/executive-dark` still heads
  skills "Core Competencies" and `cv/academic` still says "Positions Held" — the feature adds an
  override, it does not flatten six designs into one voice. The schema enumerates the valid keys,
  so a typo fails validation with the list rather than silently doing nothing. `certifications`
  renders as two headed groups and takes two keys (`certifications`, `professional_development`);
  `summary` and `contact` are renameable too.

  Implemented as a Jinja global reading `section_titles` off the render context, so
  `render_template` callers that never heard of headings — tests, the MCP server — keep working.

- **`cvloom list-templates`** — every packaged template with its column count, PDF
  text-extraction rating (`safe` / `caution` / `unsafe`), whether it fetches fonts over the
  network, and the caveat for anything not rated safe. Backed by `cvloom/templates_meta.py`.

- **Build- and check-time layout warnings.** Whether a layout survives extraction is a property
  of the template, not of anything the user wrote, so `cvloom check` — which grades content —
  could never surface it. It is now printed by `build` and `check` alike for any template not
  rated safe. This has to fire on the command the user actually runs: the failure is invisible
  from the artefact in front of them, because the PDF renders correctly and it is the copy the
  ATS makes of it that is scrambled.

- **Right-aligned dates now apply to `ats-clean` and `academic` too.** The previous pass gave
  them up on those two as a precaution and inlined every date. Re-measuring showed the
  precaution was unnecessary for entries that carry a bullet list: 0 mismatched dates over 12
  real entries across 2 pages, and over 86 generated entries spanning 0–8 bullets and 1–11 word
  titles. All six templates now right-align on work, education, and projects, and run the date
  inline on publications, certifications, and awards. Right-alignment is the more readable form
  and it is now used everywhere it measured safe.

- **Right-aligned dates are kept, and now land correctly.** The earlier sweep gave them up as
  unsafe; measuring rather than assuming showed the rule is narrower than that. A right-aligned
  date is its own geometric column, and an extractor flushes that column when the text beside it
  ends — so on `work`, `education`, and `projects`, whose entries end in a bullet list, the date
  lands beside its own entry every time. On `publications`, `certifications`, and `awards` —
  short entries, some with a trailing summary paragraph — the column stayed open past the entry
  and the date surfaced late, in the worst case after the last section of the document. Those
  three now run the date inline on the meta line; the rest keep the right-hand scan column
  recruiters actually use. Audited across all three design templates: zero orphaned dates,
  down from three.

- **`cv/sidebar-compact` is styled in the PDF, not only in the preview.** Its `@media print`
  block repainted the sidebar `#f3f4f6` with black text, so the teal band existed only in the
  HTML and every PDF — the artefact anyone actually receives — came out grey. The band now
  survives into print. Pages two and three also get their padding back via
  `box-decoration-break: clone`; a fragmented box otherwise draws padding only at its very start
  and very end, leaving continuation pages with text flush against the band.

- **Sidebar skills stack as comma lists instead of one bordered chip per skill.** In a 190px
  column a chip grid wraps after two or three items, so a fifteen-category list ran for pages,
  and the borders drew a box around each individual word. The same content is now roughly a
  third of the height.

### Changed

- **Documentation reconciled against this release.** The template tables in `README.md`,
  `docs/user/user-guide.md`, and `docs/user/getting-started.md` all described fonts, colours,
  and layouts that no longer existed — `cv/timeline-clean` was listed as "two-column grid"
  when it is single-column, `cv/modern-single` as having "skill level bars" it never had.
  Those tables are now generated from `cvloom/templates_meta.py`, so they carry the same
  ratings the CLI prints. Also documented: `cert_groups` and the `section_title` global in
  `docs/dev/custom-templates.md` (neither had any coverage), the measured layout rules a
  custom template has to respect, and a warning on `skill_level_bar` that it renders no text
  and so is invisible to any parser.

- **Page ceiling raised from 2 to 3.** `build`'s warning, the `wl-011` lint rule, and
  `trim --target-pages` all used to push toward one or two pages. ResumeGo's 482-recruiter
  simulation (7,712 resume choices) found two-page resumes preferred 2.3x over one-page
  overall and 2.9x at managerial level, so the old ceiling was arguing against the evidence.

- **Fonts.** `modern-single` and `sidebar-compact` now use Lato and `executive-dark` uses
  Source Sans 3, replacing Inter and Roboto — all three appear on recruiter-facing "best
  resume font" lists where the originals do not. `ats-clean` and `academic` stay on system
  fonts and fetch nothing.

- **`executive-dark` repalettes to carbon and steel.** Amber-on-near-black is the single most
  reproduced "executive template" palette on the resume-builder sites, and at `#b45309` it sat
  at roughly 4.5:1 on white — fine on screen, muddy off an office laser printer. The template
  now carries two accents, because one cannot serve both grounds: a steel `#3f5a68` that reads
  on white at ~6.5:1, and a lighter `#8fb3c7` for the carbon band.

- **`modern-single` drops the tag chips and the violet.** The rounded coloured contact pills
  were the one element a recruiter recognises on sight as drag-and-drop builder output; the
  contact line is now plain and pipe-separated. Accent moves from violet `#7c3aed` to indigo
  `#4338ca` for the same print-contrast reason as above.

- **Default section order leads with work, not skills.** Skills opened every CV, which put a
  keyword block exactly where the reader's first fixation lands; the Ladders eye-tracking work
  found recruiters fixate on job titles before anything else in the ~7s initial scan.

- **`modern-single` accent is now slate `#4a5568`** — violet to indigo to slate over two passes.
  Slate reads as ink with a temperature rather than as a colour, which is the point: hierarchy
  should come from weight and rules, not from hue competing with the text.

- **Skills render as an aligned label column** in the three design-led templates. Each label
  used to be its own width, so the values restarted at a different x on every row — and in
  `timeline-clean`, across two columns at once, which read as scatter rather than as a list.
  `ats-clean` deliberately does not align: alignment and single-line extraction are mutually
  exclusive, and that template takes the guarantee. Research on skills formatting is consistent
  that a labelled comma-separated list parses more reliably than tables, chips, or cards, so
  the underlying pattern was already right; only the alignment needed fixing.

### Fixed

- **`cv/sidebar-compact` no longer appears to hang on a long CV.** WeasyPrint's CSS Grid
  fragmentation is superlinear in page count: a 60-entry CV took 69s against ~6s for the
  single-column templates, and it kept getting worse with length. The same two columns as a
  CSS table build in 6.8s — a 10x improvement that puts it back in line with the rest.
  `min-height: 100vh` went with it; it was not what made the sidebar full-height, and vh units
  in paged media pin a minimum height onto every fragment.

- **Page two now looks deliberate.** `base.html.j2` carries `break-after: avoid` on headings,
  `break-inside: avoid` on entries and list items, and `orphans`/`widows` of 2. Verified across
  four templates at 17 pages each: no heading stranded at the foot of a page, no job split from
  its own bullets.

- **Contact line no longer opens with a dangling `|`.** The separator was emitted as a literal
  span before each field, which assumes the fields before it rendered — under `--public`, where
  email, phone, and location are dropped entirely, the line began with a separator and nothing
  to its left. It now comes from an adjacent-sibling CSS rule, which can only match a span that
  actually has one before it.

### Fixed

- **Section headings no longer extract as loose letters from the rendered PDF.** WeasyPrint
  writes CSS `letter-spacing` as real inter-glyph advance, and PDF text extractors reinsert a
  word break wherever that advance crosses their threshold. Measured against WeasyPrint output
  at heading sizes, `.08em` still extracts as one word and `.10em` does not. Five of the six CV
  templates tracked their uppercase section headings above that cliff, so `EDUCATION` came out
  of `pdftotext` as `E D U C AT I O N` (`timeline-clean`, at `.15em`) and `EXECUTIVE SUMMARY` as
  `E XEC U TI V E SU M M ARY` (`executive-dark`). Section headings are what an ATS segments a
  document on, so each mangled heading cost its whole section a label. All heading tracking is
  now `.06em`, which keeps the tracked-uppercase look with margin under the cliff, and a
  regression test fails the build above `.08em`.

- **`cv/ats-clean` entries now extract as one contiguous block.** Dates were right-aligned with
  `float: right`, which puts them in their own geometric column; extractors reconstruct columns
  independently of the body text, so the date landed wherever that column fell in the reading
  order — before the project name, spliced between the education bullets, or orphaned at the end
  of the document. Dates now run inline on a `Company | Location | Dates` meta line under a
  job title that gets its own bold line. The right-hand date scan column is a real loss for a
  human skimming, and the five design-led templates keep it; the ATS-first template trades it for
  an entry that always parses.

### Removed

- **BREAKING: `include_tags` and `include_entries` are replaced by `select`; entry tags are no longer rendered.**

  `include_tags` was *global* — one tag set applied to all seven entry sections at once — so narrowing one section silently gutted the others, and `include_entries` existed purely to claw back what the global filter over-removed. A patch on a patch. Skills, meanwhile, were selected by a different key in a different block (`overlays.skills.include_categories`).

  ```yaml
  # before — global, plus an escape hatch for its own over-reach
  include_tags: [python, aws]
  include_entries:
    work:
      - match: {company: "Acme Corp"}
  overlays:
    skills:
      include_categories: [Languages, Cloud]

  # after — per-section and opt-in; a section not named keeps every entry
  select:
    work:
      tags: [python, aws]
    skills:
      categories: [Languages, Cloud]
  ```

  **Untagged entries no longer survive an include list.** An include list is a query, and untagged content answers no query — the same way filtering issues by label does not surface unlabelled ones. This is now uniform: `strict_tags` is deleted from the section registry, so projects' behaviour became the rule rather than a per-section exception. Per-section, opt-in selection is what makes that safe — the old lenient rule existed only to stop the *global* filter wiping out sections you never meant to touch. cvloom warns when a selector drops untagged entries, because the failure mode is a newly added, untagged role vanishing from the CV you are about to send.

  **Entry `tags` are no longer rendered.** Tags are a filing vocabulary, and rendering them published the filing system: a leadership CV showed chips reading `early-career`, `freelance`, `support`, and former employers' names next to roles. Those keywords already counted toward `cvloom match` coverage without being rendered, and duplicated `skills`. Three of six CV templates printed work tags and all six printed project tags; none do now, and a parametrised render test holds the line.

  Tags work best as a **one-dimensional classification** — one axis, such as practice area. That is why `select` has no `exclude_tags`: on a single axis, an allow-list expresses everything. Skill *categories* do get `exclude_categories`, because they are a closed enumerable set where excluding three of fifteen is both equally expressive and far shorter than listing the other twelve.

- **BREAKING: `linkedin`, `github`, and `website` are gone from `private/contact.yaml`, and `basics.public_links` is now `basics.links`.** The same profile link could previously be written two ways — a handle field in the gitignored contact file, or a labelled URL in committed `basics.yaml` — and both rendered. The header reconciled them at render time by substring-matching the handle against the URL, which silently failed whenever the two disagreed, printing LinkedIn and GitHub twice. It also broke on `www.` prefixes, trailing slashes, and case. The split was along the wrong axis: `--public` strips only `email` and `phone`, so links in `contact.yaml` were never actually being hidden, while a public build with no `private/` directory lost them entirely — the same profile rendering differently depending on whether a gitignored file happened to exist.

  Profile links now live only in `data/basics.yaml`, which every build reads:

  ```yaml
  # private/contact.yaml — identity and reachability only
  name: "Jane Smith"
  email: "jane@example.com"
  phone: "+44 7700 900000"
  location: "London, UK"

  # data/basics.yaml — links are public by definition
  links:
    - label: LinkedIn
      url: https://linkedin.com/in/janesmith
    - label: GitHub
      url: https://github.com/janesmith
  ```

  With one source there is nothing left to reconcile, so the dedupe guard is gone rather than repaired. Existing projects must move their links by hand; a build with the old keys fails schema validation naming the offending key. Handles are no longer accepted — write the full URL, and cvloom recognises LinkedIn and GitHub by host.

### Added

- **`cvloom/select.py`** — one home for all content selection, replacing filtering that was spread across `loader`, `builder`, and `overlays`. Returns warnings for a selector that matches nothing, one naming an unknown section or category, and one that drops untagged entries.
- `cvloom list-profiles` gained a **Narrows** column showing which sections each profile selects.

- **Header links are now real anchors.** Every CV template and the standard cover letter render `basics.links` through a new `link_anchor` filter, which emits `<a href="…">` with the URL as its *visible* text (scheme and `www.` trimmed). ATS parsers split on whether they read visible text or the `href`; anchor text that hides the URL leaves the text-reading half nothing usable, so both halves now get a complete address. WeasyPrint turns each `href` into a real PDF link annotation, so the human reviewer gets a clickable link from the same markup. Previously nothing in the header was a link at all.
- **`cv/modern-single`, `cv/executive-dark`, `cv/timeline-clean`, and `cv/sidebar-compact` render profile links.** Only `cv/ats-clean` and `cv/academic` ever read `public_links`; on the other four, links set in `basics.yaml` were silently dropped. A parametrised render test now asserts every CV template emits each link exactly once.
- **`public_name` works.** `loader._apply_public_mode` has always implemented it — replacing `name` in `--public` builds only, so you can publish under a pen name — but `contact.json` sets `additionalProperties: false` and never declared the key, so setting it failed validation. It is now in the schema and documented.
- **Lint rule `wl-022` (duplicate-links, structure):** flags two `links` entries resolving to the same destination, comparing after normalising away scheme, `www.`, host case, and trailing slash.
- **`wl-021` (unfilled-placeholders) now scans link URLs.** A scaffolded `https://github.com/[handle]` reaching a PDF is exactly what the rule exists to catch, and it was not looking there.
- **`cvloom/links.py`** — the shared profile-link vocabulary (`network_of`, `link_username`, `normalize_url`) used by export, import, and the linter, so host recognition and URL comparison are defined once.

- **Four new lint rules.** `wl-019` (chronological-order) flags any dated section not ordered newest-first — cvloom renders entries in load order and never sorts, so ordering is entirely the author's, and nothing previously checked it. `wl-020` (date-sanity) catches an `end_date` before its `start_date`, dates in the future, and expired credentials via `expiry_date`; the first two can make a parser compute a negative tenure and drop or mis-assign an entry, and the third is a credibility risk (AWS certifications, for instance, lapse after three years). `wl-021` (unfilled-placeholders) catches scaffold text like `[Company Name]` or `[X]%` surviving into the rendered PDF — `cvloom init` ships placeholders by design and nothing else in the pipeline stops one reaching an application, since schema validation only checks types and every other rule reads placeholder text as ordinary prose; Markdown links are exempt. The section registry gained `sort_date_keys`, `range_keys` and `expiry_key` so all three derive their date knowledge from one table rather than three copies of a field list.
- **`type` on certification entries, separating credentials from coursework.** A single "Certifications" heading over a list that mixes an exam-backed AWS credential with a Udemy course overclaims the courses, and there was no way to say so. Entries now take an optional `type` — `certification`, `license`, `course`, or `micro-credential` — following [Open Badges 3.0](https://www.imsglobal.org/spec/ob/v3p0)'s `achievementType` vocabulary. Credentials render under **Certifications**, completion records under **Professional Development**, credentials first, empty groups omitted; omitting `type` means `certification`, so existing files render unchanged. A type discriminator was chosen over a separate top-level `courses` section deliberately: JSON Resume has no such section (its `courses` lives *inside* an education entry, meaning subjects within a degree), so a new section would export to a private extension nothing else reads — whereas `type` maps directly onto the two profile sections LinkedIn actually has, which is what the planned LinkedIn export needs.
- **Per-template parse-safety guidance.** The user guide's template table now records which templates are single-column and which use CSS grid columns. Multi-column layout is the one formatting choice with a well-supported effect on parsing — parsers walk source order, not visual order — so `timeline-clean` and `sidebar-compact` are flagged as worth checking. It is a risk flag, not a prohibition.

- **`awards` and `languages` sections.** Two more optional data files — `data/awards.yaml` (`title` required, plus `awarder`, `date`, `summary`, `tags`) and `data/languages.yaml` (`language` required, plus `fluency`, `tags`). Both map field-for-field to JSON Resume's native `awards` and `languages` arrays. Languages render as a single inline run (`Spanish (Native speaker) · English (C1)`) rather than a stack of entry blocks, since two short fields per language don't warrant the vertical space. These were the first sections added since the registry landed: adding each to the pipeline was one `sections.SECTIONS` entry — loading, tag filtering, validation, visibility, ordering and the CLI summary all followed automatically.
- **First-class `certifications` section.** A new optional `data/certifications.yaml` for certifications, licences, and short courses — `name` (required) plus `issuer`, `date`, `expiry_date`, `identifier`, `url`, `tags`. All six CV templates render it **compactly** — a title row plus one meta line, with no bullet list — rather than giving it the full entry treatment education gets. That is the point: a CV with 2 degrees and 21 vendor certs previously rendered all 23 with equal weight and no way to differentiate them. Exports to JSON Resume's native `certificates` array (see the export fix above for how `expiry_date` and `identifier` are carried).
- **`tags` on education entries**, with tag filtering in the loader. Education was the only array section that could not be tag-filtered. The user guide already documented `tags` as an education field, so this was a documented-but-unimplemented feature: adding `tags:` to an education entry previously failed schema validation with `Additional properties are not allowed`. Filtering follows `work`'s lenient semantics — an untagged entry is always included — rather than `projects`' strict semantics, where `tags` is a required field. The education `grade` field is now documented too.
- **Lint rule `wl-018` (education-size, structure):** warns when the education section exceeds 6 entries and points at `certifications.yaml`.
- **First-class `publications` section.** A new optional `data/publications.yaml` holds papers, articles, and talks — `name` (required) plus `publisher`, `release_date`, `identifier` (ISBN/DOI/arXiv), `url`, `summary`, and `tags`. All six CV templates render it; `cv/academic` places it directly after education. Profiles control it like any other section (`sections: { publications: false }`, `section_order`, `include_tags` — with `work`'s forgiving semantics, where untagged entries are always included). Export maps it to JSON Resume's native `publications` array (`identifier` is folded into `summary`, since JSON Resume has no field for it) and `import` maps it back; Markdown and DOCX export gained the section too. Omitting the file entirely is the normal case and produces no warning.
- `docs/user/user-guide.md` documented the section, and its **stale claim that `cv/academic` already "supports research and publications sections"** — which was never true; the template had the same four sections as every other one — is corrected to describe what that template actually does.

### Changed

- **`cv/ats-clean` and `cv/academic` join fields with ASCII separators** — `|` in the contact line, `,` between a role and its organisation (`Senior Engineer, Acme Corp`, which reads as apposition). The four design-led templates keep the middot. This is not an extraction fix: every separator tested — middot, pipe, comma, em dash, en dash, bullet — survives WeasyPrint PDF text extraction intact, and the claim that an ATS "cannot read" a middot is folklore. The reason is narrower: `·` is U+00B7, so it depends on the embedded font subset carrying that glyph, while ASCII has no such failure mode. Worth the trade only on the two templates whose purpose is conservatism. Date ranges follow the same split: `date_range` gained a `sep` argument (default en dash) and the two ASCII-first templates pass `sep="-"`, so their extracted text is pure ASCII apart from the bullet glyph WeasyPrint renders for list markers. Date ranges are one of the few things an ATS genuinely tries to parse. The design-led templates keep the en dash, which is correct typography for a range.
- **Templates no longer use literal em dashes.** Page titles and the `ats-clean` role/company separator used them; both now follow the convention above.
- **`loader.load_data` no longer filters.** It is I/O and merge only; selection is a separate pipeline step in `resolve()`, applied before normalisation so overlays only ever see what survives.
- **`overlays.skills` keeps only `category_overrides`.** Choosing which categories appear is selection, not patching. The `include_categories`/`exclude_categories` mutual-exclusion warning is gone with the keys.

- **Export and import follow the single source.** `to_json_resume` builds `basics.profiles` from `links` alone, recovering `username` from the URL path for LinkedIn and GitHub and deduplicating on the normalised URL; Markdown and DOCX headers list `links` instead of contact handles. `from_json_resume` writes *every* profile to `data/basics.yaml`, including LinkedIn and GitHub, with JSON Resume's `basics.url` importing as a `Website` link — nothing PII-adjacent, so nothing belongs in `private/`. The round trip stays closed.
- **`wl-010` (profile-links) checks `basics.links`** and recognises networks by host rather than by handle substring, so `linkedin.com/in/jane`, `https://www.linkedin.com/in/jane/`, and subdomains all satisfy it.
- **The scaffold no longer hardcodes `SWEStash`.** `cvloom init` wrote `github: "SWEStash"` into every user's contact file and placeholder — one project's org name in generic sample data. Scaffolded links now use `[handle]`, which `wl-021` flags if left unedited.

- **`wl-002` (missing-quantification) now reports once per entry instead of once per bullet.** It fired on every bullet without a digit — eleven findings on a single role — which buried every other rule on exactly the CVs that needed them most. The underlying claim does not survive scrutiny either: recruiter-preference evidence supports *a role showing measurable impact*, not a number in every bullet. One quantified highlight now satisfies the entry.
- **The default PDF filename carries a `_<profile>` suffix.** The default was contact-derived only (`Jane_Doe_Resume.pdf`) and therefore identical for every profile, so building several profiles produced several HTML files but a **single** PDF — whichever profile built last silently overwrote the rest, with no warning. `pdf_filename_format` also accepts a new `{profile}` token for placing it elsewhere in the name.

- **The pre-commit PII hook no longer cries wolf.** It scanned whole staged files, so any commit touching a file that has always contained a placeholder (`your.email@example.com` in `loader.py`, `+1 (555) 000-0000` in the test fixtures) was blocked — training the reflex of passing `--no-verify`, which is exactly how real PII eventually slips through. The hook now scans only the **added lines** of a diff, and allows values reserved for documentation: RFC 2606 / 6761 domains (`example.com`, `.example`, `.test`, `.invalid`, `.localhost`) and the fictional phone ranges (NANP `555`, UK Ofcom `7700 900xxx`). It also prints the offending value instead of just the filename, so the warning can be judged without re-grepping. Existing projects pick this up via `cvloom sync`.

- Internal slop-audit cleanup, phase 3: made the pipeline's `resolve()` a **pure function** as documented — it no longer prints Rich output or raises `SystemExit` from the library layer. It raises a typed `builder.ResolveError(errors)` instead; the CLI catches it, renders the errors, and exits, while the MCP server returns them as structured `details`. `schema.validate_all` and `overlays` lost their terminal I/O too (no more module-level `Console`), overlay non-match warnings are reported once (via `validate_overlays`, returned on `ResolvedProfile.warnings`) instead of twice, and the overlay exclude path drops its `None`-sentinel `type: ignore`. Behavior change is confined to the error/warning path; new tests assert `resolve()` writes nothing to stderr and that MCP errors carry real `details`.
- Internal slop-audit cleanup, phase 2 (no behavior change): killed the two biggest sources of structural duplication. Added `builder.resolve_project`/`build_project` wrappers over the fixed `data/`+`private/`+`profiles/` project layout and migrated all 23 call sites in the CLI and MCP server, so the 5-argument wiring block exists once. Added `cvloom/projects.py` (a shared profile/project-listing data layer behind both the CLI table and the MCP JSON) and `cvloom/sections.py` (single home for the CV data walk: `highlight_text`, `skill_name`, `entry_label`, `iter_entry_text`/`count_words`, and one NFKD-normalizing `slugify`). The `~18` copies of the `str | {text}` highlight guard, the three hand-copied word-count walks, the section→label maps, and the two divergent slugifiers now resolve to those shared helpers
- Internal slop-audit cleanup, phase 1 (no behavior change): removed a meaningless, never-surfaced `frequency_cv` field from `match`; factored the four AI orchestrators' identical LLM call-and-parse block into a shared `ai.provider.complete_json` helper; unified the four AI MCP tool responses on `dataclasses.asdict`; corrected `filters.register_filters` to a real `jinja2.Environment` type (dropping three `type: ignore`s); tightened several tests (real assertions for the unmatched-overlay warning, the `init --force` overwrite, and the `_suggest_section` "work" branch) and removed a dead fixture, a subsumed test, and dead code (a no-op contact `pop`, unused `_init_*` `force` params, a stale renderer comment). The `dev` extra now pulls `cvloom[docx]` instead of re-pinning `python-docx`

### Changed (internal)

- **Section registry (`sections.SECTIONS`), no behavior change.** Adding a section previously meant editing ~16 sites across 13 files — `_ENTRY_SCHEMAS`, file loading, tag filtering, `validate_all`, three `sections.py` constants, `section_defaults`, `default_order`, `_section_summary`, export headings, and more — where forgetting one failed *silently*. The entry-list sections are now frozen `Section` records carrying `schema`, `label_key`, `heading`, `summary_label`, `from_directory` and `warn_if_missing`; loader, schema validation, builder, CLI, export and `select` all derive from them. `skills` and `basics` stay out deliberately — their shapes genuinely differ, and forcing them in would buy uniformity at the price of exceptions everywhere. `tests/test_sections_registry.py` guards what the registry cannot derive: `profile.json`'s `sections`/`section_order` enum, and each section's entry schema existing.
- `export.py`'s five near-identical `_map_*` functions — each a hand-rolled block of conditional field assignments — collapsed into one table-driven `_map_entry` over `_Field(src, dest, kind)` tuples. Adding the namespaced extensions above was then a table edit rather than a sixth copy of the same block. `tests/conftest.py`'s `make_resolved` factory had drifted behind the data model; it now derives its section defaults from the registry itself, so it cannot drift again.

- Slop-audit cleanup, phase 5 (SLOP-024, no behavior change): decomposed the `cli.py` God-file. The project-scaffolding logic (`init`/`sync` file operations and the managed-file registry) moved into a new `cvloom.scaffold` package, and the ~100 lines of embedded sample-YAML string constants became real files under `cvloom/scaffold/samples/`, loaded at runtime. `cli.py` dropped from ~1,190 to ~940 lines and no longer mixes command definitions with scaffold internals and inline data. Verified: a fresh `cvloom init` scaffolds and builds identically.
- Slop-audit cleanup, phase 4: added `tests/conftest.py` with shared `make_resolved` and `make_project` factories. The six per-file `_make_resolved` copies now delegate to one `ResolvedProfile` builder (defaults no longer drift), and the duplicated on-disk project scaffolds for the builder and MCP suites are single-sourced through `make_project`. (Bespoke fixtures whose content is load-bearing for their own assertions — loader, match, CLI-list — keep their tailored data.)

### Fixed

- **The MCP `uvx` client config was unrunnable.** It passed `["--extra", "mcp", "cvloom-mcp"]`, but `uvx` has no `--extra` flag — it exits with `unexpected argument '--extra' found` before starting anything. The extra belongs in `--from`: `uvx --from "cvloom[mcp]" cvloom-mcp`. The MCP guide also gained a **"Which project the server operates on"** section: `project_root` falls back to the server's own cwd, which is fine for Claude Code launched inside a project and wrong for Claude Desktop, where the fix is `uvx --directory`. `get_section`'s documented section list was stale at six values against the eleven it accepts (missing `publications`, `certifications`, `awards`, `languages`), and `uv tool install cvloom[mcp]` is now quoted so it survives shell globbing.
- **Documentation drift sweep.** The lint-rule count was stated as 18 (README, architecture, `CLAUDE.md`) or 17 (user guide) against 21 actual rules. The user guide still carried an **"ATS Scoring"** section documenting a `100 - (warnings × 5) - (suggestions × 2)` formula and `--strict N` as a *score* threshold — both removed with the score itself, and directly contradicting [the ATS-readiness model](docs/reference/ats-readiness.md); it is now "Lint Integration" and describes `--strict N` as what it is, a findings budget. The non-existent `--private` build flag reappeared in the PII-safety and overlays guides (private is the default; only `--public` exists). `pdf_filename_format`'s documented default was missing the `_{profile}` suffix and the `{name}`/`{profile}` tokens. The architecture repo tree was missing `projects.py`, `hooks/` and `scaffold/`. Formatting: a broken `basics.yaml` table-of-contents anchor, thirteen lists that followed a paragraph with no blank line between (they render as paragraph text in strict CommonMark), and an `[Unreleased]` changelog block with `Added`/`Changed`/`Fixed` each repeated three or four times instead of once.
- **`wl-013` no longer reads present-tense verbs ending in `-ed` as past tense.** The heuristic treated any `-ed` opener as past, so "Embed governance practice…" in a current role was flagged — as would "Exceed", "Proceed", "Succeed", "Feed", "Need" and a dozen others. Those are now excluded by name; genuinely past openers still flag.
- **`wl-007` no longer reads roman numerals as the pronoun "I".** "Taught Algorithms I and II" tripped the first-person rule, as would "Phase I" or "Type I". A bare `I` now counts as a pronoun only when it opens a clause or follows a lowercase word — a roman numeral follows a capitalised noun. `I` is also matched case-sensitively now: lowercase `i` is never the pronoun, and matching it case-insensitively flagged stray initials.
- **`wl-019` checks certification groups independently.** Certifications render as two blocks (credentials, then coursework), but the rule compared the flat list — so a correctly ordered file, with each group newest-first, reported the first course as out of order against the last credential. Ordering is now checked within each rendered block.
- **A date range with identical endpoints renders as one date.** `date_range` unconditionally joined its two arguments, so an entry recorded only by the year it completed — the normal case for a degree, where people rarely list a start year — rendered "2017 – 2017".
- **A schema-declared `default` is now honoured when filling optional fields.** `entry_defaults()` filled every optional property with its *typed empty* value, which is fine for a free-text string but wrong for a constrained one: `""` is not a member of an `enum`, so normalising an entry that omitted such a field produced data the validator then rejected. Any property declaring a `default` gets that value instead. Surfaced immediately by the new certification `type` field, and it would have hit every future enum the same way.
- **Markdown never actually rendered.** `md_to_html` returned a plain `str` while the Jinja environment runs with `autoescape` on, so every tag it generated was escaped straight back into the page: `**bold**` reached the PDF as `&lt;strong&gt;bold&lt;/strong&gt;`. Links and multi-paragraph fields broke the same way, and the shipped `cover-letter` profile rendered its `job_context.notes` as visible HTML source. It went unnoticed because plain-text bullets — nearly all of them — hit the single-`<p>` unwrap and had nothing left to escape, so the common case looked correct. The filter now returns `Markup`, and markdown-it is explicitly configured with `html=False` so raw HTML in CV data is escaped rather than passed through: without that, marking the output safe would have turned imported JSON Resume content into an injection vector on published GitHub Pages builds.
- **`cvloom match` now counts every section toward keyword coverage.** It extracted CV keywords from `work`, `education`, `projects` and `skills` only, so a job description asking for Kubernetes was reported as a **gap** even when the CV carried a Kubernetes certification — and asking for Spanish was a gap against a CV listing Spanish. Every section added since made the false negatives worse. Extraction now walks `sections.ARRAY_SECTIONS` via the shared `iter_entry_text` helper instead of a local copy of the field list, so publications, certifications, awards and languages all count (and a section hidden for the profile still correctly does not).
- **The post-build section summary was never displayed.** `cvloom build` computed `work×2  edu×1  …` and printed it inside literal square brackets, which Rich parsed as a markup tag and silently dropped — so the line has been invisible for its whole existence. That is also why nobody noticed it had stopped listing sections: the bracket is now escaped, the iteration derives from the section registry rather than a hardcoded list (it was missing `awards` and `languages`), and a CLI test asserts the counts actually reach stdout.
- **JSON Resume export now actually conforms to JSON Resume.** It never had. Validated against the official schema, the shipped demo project produced two violations: `basics.email: ""` (a `--public` build strips email, and the empty string fails the schema's `email` format) and `endDate: "Present"` (JSON Resume has no such sentinel — a current role omits `endDate`). Empty fields are now omitted rather than exported as `""`, and dates that aren't ISO 8601 are omitted rather than emitted invalid. A new suite (`tests/test_export_jsonresume_conformance.py`) validates every export — full, public, sparse, and all three demo profiles — against a vendored copy of the official schema, so this is a checked promise rather than an aspiration.
- **`basics.links` are now exported.** They were dropped entirely; they map to JSON Resume's `basics.profiles` with the link label standing in for `network`. Import already read them back, so the round-trip now closes. (Landed in this cycle as `public_links`, renamed before release — see Removed.)
- **An `export` → `import` round-trip no longer silently strips your tags.** `tags` survived only for projects (which map to the spec's `keywords`); on work, education, publications, and certifications they were dropped outright — meaning a round-trip returned your content but quietly destroyed the tag taxonomy that every profile's `include_tags` filtering depends on. Fields JSON Resume has no home for are now carried under an `x-cvloom-*` namespace the schema permits and other tools ignore: `x-cvloom-tags`, plus certifications' `expiry_date`/`identifier` and per-item skill `level` (previously rendered by `skill_level_bar` but lost on export). Education bullets now map to the spec's `courses` field instead of a non-standard `highlights` key, and import accepts either.

- **Omitting an optional field no longer crashes the build.** Templates render under Jinja2's `StrictUndefined`, where reading a dict key that is simply *absent* raises `UndefinedError` rather than evaluating falsy — so `{% if edu.field %}` blew up on any `work`/`education`/`project` entry that left out a field the schema and docs both call optional (`field`, `location`, `highlights`, `url`, `start_date`, `description`, `tags`, …). Every built-in template was affected, and the only workaround was to write out `field: ""`, `highlights: []` by hand. `resolve()` now fills each entry's schema-declared optional keys with typed empties (`""`/`[]`) via the new `schema.entry_defaults()`, so "optional" means optional for current and future templates alike. The same fix covers partially-specified `job_context` in cover-letter profiles. `contact` is deliberately excluded — its templates guard with `is defined` so that `--public` redaction keeps email/phone invisible rather than blank — and the three templates that instead tested contact keys for truthiness (`cover-letter/brief`, `cover-letter/standard`, `project-summary/card`, which crashed on any public build) now check presence first. Regression test renders all 9 templates against a project carrying only schema-required fields.
- MCP tools now surface **real validation errors**. Previously every pipeline failure collapsed to the unactionable string `"exit code 1"`; the tools now return `{"error": "resolve failed", "details": [...]}` with the actual schema/profile messages an agent needs. The four AI tools also resolve inside their `try` block (a resolve failure no longer escapes uncaught) and catch specific error types instead of a blanket `except Exception`.

---

## [0.6.0] — 2026-07-18

First public release on PyPI. Install with `pip install cvloom` or `uv tool install cvloom`.
This is a pre-1.0 release: the CV/profile schema and CLI are still free to change on MINOR
version bumps. Note the **breaking changes** below if migrating from a pre-release checkout.

### Added
- `SECURITY.md` — private vulnerability disclosure process (GitHub Security Advisories) and a note that any real-contact-data leak (tracked file, `--public` build, Pages artifact, or MCP response) is treated as a security issue
- `cvloom sync` — refresh cvloom-managed scaffold files (the pre-commit hook and the Pages publish workflow) to the installed package's versions after `uv tool upgrade cvloom`. Reports `up to date` / `out of date` / `missing` by default and writes nothing; `--force` applies. `init` and `sync` now share one managed-file registry. New guide: [keeping your instance updated](docs/user/keeping-updated.md)
- Reusable **GitHub Pages publish workflow**: `cvloom init` now scaffolds `.github/workflows/publish-cv.yml`, which builds your CV in public mode (email/phone stripped) and deploys to Pages — gated behind a `DEPLOY_PAGES=true` repo variable so nothing publishes until you opt in. An optional `CONTACT_YAML` secret adds your real name/links. The tool's own repo uses the same pattern to publish `examples/`
- `cvloom import --format json-resume <file>` — import a [JSON Resume](https://jsonresume.org/) document into cvloom's layout (the inverse of `export`), with a PII-aware split that routes contact details to `private/contact.yaml` and everything else to `data/`. Supports `--dry-run` and `--force`; imported data is schema-validated before any file is written
- `docs/reference/ats-readiness.md` — explains the three honest, measurable axes of ATS-readiness (writing quality, JD keyword coverage, parseability) and why a single "ATS score 0–100" is not honestly achievable
- Lint findings now carry a `category` (`writing` / `structure` / `ats-parse`), surfaced in `cvloom check`, `build --check`, and the `check_cv` MCP tool
- MCP agent-safety hardening: documented and tested guarantees that mutating tools reject malformed writes with a structured `{"error", "details"}` (no partial write), and that read/analysis tools never surface contact email/phone. The `export_json_resume` MCP tool now defaults to `public=true` (PII fenced); pass `public=false` to opt into real contact details
- MIT `LICENSE` file (the license was previously declared but not shipped)
- Fake-client tests for all four AI orchestrators (`review`, `generate_cover`, `suggest`, `align`) and all four AI MCP tools, including malformed-response cases — AI orchestration modules now at 100% coverage
- CI quality gates: `ruff check`, `ruff format --check`, and strict `mypy` now run in the test job, across Python 3.11, 3.12, and 3.13

### Changed
- **Documentation sweep** for gaps/drift: refreshed a stale `CLAUDE.md` (pre-rename `simple_cv` paths, "ATS linter with 5 rules", a non-existent `--private` flag, missing `import`/`sync`); normalized end-user docs to `cvloom` (from `uv run cvloom`); replaced the old "re-run `init` to refresh the hook" upgrade step with `cvloom sync`. All internal doc links verified
- `LICENSE` copyright holder set to **SWEStash**
- **README repositioned** to lead with the differentiators — declarative per-job overlays (one dataset → N tailored, diffable CVs), the agent-safe MCP data layer, and PII compartmentalisation — with the AI commands demoted to a supporting section
- **Repo restructure:** the sample CV data moved from root `data/`/`profiles/` into [`examples/`](examples/); the repository root is now unambiguously the tool. The README hero commands are now real and runnable against `examples/` (added a sample `examples/stripe-infra-jd.txt` for `match`). Contributors and the CI Pages demo build from `examples/` (`cd examples && cvloom build`); end users scaffold their own project with `cvloom init`. The removed stale `simple_cv/` leftover directory is gone
- **Breaking:** lint rule IDs renamed from `ats-NNN` to `wl-NNN` (writing-lint), reflecting that most rules measure writing quality, not ATS parsing. Update any scripts or overlays that filter by rule ID
- **Breaking:** dropped the single "ATS score 0–100" from `build --check`; it now prints a per-axis findings breakdown. `--strict N` now fails when there are *more than N findings* (a lint budget) instead of when a score is below N
- `__version__` is now read from package metadata (`pyproject.toml` is the single source of truth)
- Codebase formatted with `ruff format`; formatting is now enforced in CI
- Root `CONTRIBUTING.md` is the canonical contributing guide; `docs/dev/contributing.md` now points to it

### Fixed
- All outstanding `ruff` and `mypy` errors on `main`
- README MCP tool table now lists all 16 tools (`trim_report` and `diff_profiles` were missing)

---

## [0.5.0] — 2026-04-29

### Added
- `cvloom ai align` — qualitative AI analysis of CV-to-JD alignment: narrative summary, repositioning actions, tone gaps, and strengths; combines rules-based keyword analysis with AI qualitative insight
- `ai_align_to_jd` MCP tool for LLM-driven CV-to-JD alignment analysis
- `cvloom ai suggest` — AI-generated improvement ideas (new bullets, skill additions, rewordings) for a target role; `--role` option or falls back to `job_context.role` from the profile
- `ai_suggest_improvements` MCP tool for LLM-driven CV improvement suggestions
- `cvloom ai cover` — AI-generated cover letter from CV + job description file (`--jd FILE`), with optional `--output FILE` to write to disk
- `ai_generate_cover` MCP tool for LLM-driven cover letter generation
- `cvloom ai review` — AI-powered section scoring (1–10) with strengths, weaknesses, and improvement suggestions per section plus top-3 priorities across the whole CV
- `ai_review_cv` MCP tool for LLM-driven CV scoring
- `docs/ai-features.md` — installation, configuration, and backend quickstart guide for AI features (Ollama, LiteLLM, OpenAI)

---

## [0.4.0] — 2026-04-25

### Added
- Linter rule ats-016: Readability — flags highlights with Flesch-Kincaid grade level >12 (too complex) or <6 (too simple); suggestion severity.
- Linter rule ats-017: Tech mentions in work — flags work entries whose highlights contain no skill item name; suggestion severity.
- `MatchReport.reorder_hints`: when `match --jd` is used, suggests moving the most JD-relevant work entry to the top; shown in `cvloom match` output.
- Linter rule ats-006: Bullet count per role — warns if a work entry has fewer than 3 or more than 8 highlights.
- Linter rule ats-007: First-person pronouns — flags `I/my/me/mine/myself` in highlights and summary.
- Linter rule ats-008: Vague buzzwords — detects terms like "motivated", "proactive", "passionate", etc.
- Linter rule ats-009: Skill count — warns if total skills listed is below 8 or above 25.
- Linter rule ats-010: Profile links presence — warns if no LinkedIn or GitHub link is found in contact or public_links.
- Linter rule ats-011: Page count estimate — warns if estimated page count exceeds 2 (skipped for academic templates).
- Linter rule ats-012: Date format consistency — flags mixed YYYY-MM / YYYY within a section.
- Linter rule ats-013: Tense consistency — past tense for past roles, present for current.
- Linter rule ats-014: Summary length — warns if summary is <20 or >80 words.
- Linter rule ats-015: Action→result — flags highlights with a metric but no result framing (suggestion severity).
- `MatchReport.suggestions`: for each gap keyword, recommends the section to add it to; shown in `cvloom match` output.
- Smart PDF filename: defaults to `FirstName_LastName_Resume.pdf` derived from `contact.name`; customisable via `pdf_filename_format` in profile YAML.
- PDF metadata: `<meta name="author">` added to base template; `<title>` updated to `{name} — Resume`.
- Skill-level bar CSS: `.skill-level-1` through `.skill-level-4` styles added to `base.html.j2` (the `skill_level_bar` filter now renders visually).
- `cvloom build --check`: runs ATS linter post-build and prints a 0–100 score.
- `cvloom build --strict N`: exits non-zero if ATS score is below N (implies `--check`).
- Grayscale print safety: `sidebar-compact` forces light sidebar background + dark text in `@media print`; `executive-dark` forces dark heading colours for B&W printing.
- `cvloom export --format markdown`: exports CV as a Markdown file (`dist/<profile>.resume.md`).
- `cvloom export --format linkedin`: exports CV as LinkedIn-pasteable plain text (`dist/<profile>.linkedin.txt`); warns when About section exceeds LinkedIn's 2600-character limit.
- `cvloom export --format docx`: exports CV as a `.docx` file via `python-docx` (optional dependency: `uv pip install python-docx` or `uv sync --extra docx`).

### Changed
- **Typography (Phase 4):** Added `{% block fonts %}` to `base.html.j2`; `timeline-clean`, `modern-single`, `executive-dark`, and `sidebar-compact` now load Google Fonts (Inter or Roboto) via HTTPS `<link>` tags. `ats-clean` and `academic` remain system-fonts-only by design.
- `h2` base font size increased `11pt` → `12pt` for improved section heading legibility.
- Body `line-height` tightened `1.45` → `1.35` to improve print density while preserving readability.
- `modern-single`, `executive-dark`, and `sidebar-compact` font stacks updated to lead with their respective web font (Inter / Roboto).

---

## [0.3.0] — Phase 3 — 2026-03-26

### Added
- `cvloom match --jd <file> [--profile]` — keyword gap analysis comparing CV
  content against a plain-text job description. Reports coverage percentage,
  matched/missing keywords by section, and top JD keywords.
- MCP server parity: 4 new tools (`check_cv`, `trim_report`, `diff_profiles`,
  `match_jd`) bringing the total from 8 to 12 tools.
- `validate_overlays()` now checks for: unmatched overlay entries, nonexistent
  highlight IDs in pick/exclude/replace, unknown match field names, and
  non-existent skill categories.
- `renderer.template_exists()` and `renderer.list_templates()` helper functions.
- Template existence pre-check in `builder.resolve()` with available templates
  listed in the error message.
- `cvloom-template-*` naming convention for third-party templates.

### Fixed
- MCP `upsert_project` slug generation now handles accents, special characters,
  consecutive spaces, and empty names via `_slugify()`.
- ATS linter passive voice rule (ats-001) no longer flags adjectives ending in
  -nt, -lt, etc. (e.g. "is present", "was efficient").
- Overlay warnings now surface during `builder.resolve()` instead of being
  silently discarded.

---

## [0.2.0] — Phase 2 — 2026-03-24

### Added
- `cvloom check [--profile]` — ATS linter with 5 built-in rules: passive
  voice, missing quantification, noise skills, weak action verbs, highlight
  length. Per-bullet feedback with fix hints.
- `cvloom trim [--profile] [--target-pages]` — per-section word breakdown
  with cut recommendations to reach target page count.
- `cvloom diff <profile-a> <profile-b>` — compare two profiles: sections,
  entries, word counts, and highlight counts side by side.
- `cvloom export --format json-resume [--profile]` — export CV data to
  JSON Resume schema for interoperability with the JSON Resume ecosystem.
- `cvloom-mcp` — MCP server exposing 8 tools (list_profiles, list_projects,
  get_section, build_cv, create_profile, upsert_project, validate_data,
  export_json_resume) for LLM-accessible CV management. Data stays local.
- `templates/cover-letter/brief.html.j2` — compact cover letter template.
- `templates/project-summary/card.html.j2` — single-page project summary card.
- `builder.resolve()` — pure function returning `ResolvedProfile` for
  programmatic access to the build pipeline without rendering or file I/O.
- `builder.build()` now returns `BuildResult` with structured data (words,
  pages, section word counts, file paths).
- Per-section word counts in build output via `_word_count_by_section()`.
- `schema.validate_all()` accepts `raise_on_error=False` for programmatic use.
- Profile YAML is now validated against the profile schema during build.

### Fixed
- `_estimate_pages()` now strips `<style>` blocks before word counting,
  preventing CSS tokens from inflating word counts.
- `pytest-cov` moved from runtime to dev dependencies.
- Removed dead `_apply_include_entries()` placeholder in overlays.py.

---

## [0.1.0] — Phase 0 + Phase 1 — 2026-03-20

### Added
- `cvloom list-projects [--tag TAG]` — list projects from `data/projects/`,
  optionally filtered by one or more tags.
- `cvloom list-profiles` — tabular listing of all profiles in `profiles/`
  with their template, output filename, tag filters, and job context.
- `templates/cover-letter/standard.html.j2` — professional cover letter
  template driven by `job_context` in the build profile. Renders date, sender,
  recipient, salutation, and body from profile data.
- `templates/cv/academic.html.j2` — academic CV template: education-first
  layout, serif body font, positions/research/projects sections.
- Build output now shows per-section item counts alongside word count and page
  estimate (e.g. `450 words · ~1 page  [work×3  edu×1  skills×4  projects×2]`).
- `today` variable available in all templates (formatted as `Month DD, YYYY`).
- `profiles/cover-letter.yaml` scaffold created by `cvloom init`.
- Profile overlays: per-job data patches with match-and-patch, highlight
  pick/exclude/replace for tailoring CV content per application.
- `section_order` profile key for reordering template sections.
- `include_entries` for force-including tag-filtered entries back into a build.

---

### Added (Phase 0)
- `cvloom build [--profile] [--template] [--public] [--skip-pdf]` — full
  build pipeline: YAML → JSON Schema validation → Jinja2 HTML → WeasyPrint PDF.
- `cvloom init` — scaffold project structure, install pre-commit PII scanner
  hook, verify `.gitignore` contains `private/`.
- JSON Schema validation for all data types: basics, contact, work, education,
  skills, project, profile.
- Two built-in templates: `cv/ats-clean` (ATS-optimised single column) and
  `cv/modern-single` (visual hierarchy with skill tags).
- PII separation: contact data lives in gitignored `private/contact.yaml`;
  `--public` mode substitutes placeholder data.
- Per-project YAML files under `data/projects/*.yaml` with tag-based filtering.
- Named build profiles (`profiles/*.yaml`) with section visibility control,
  `include_tags`, and `job_context`.
- GitHub Actions workflow: test → build (public mode) → deploy to GitHub Pages.
- Pre-commit hook that scans staged files for contact data patterns.
- Word count and page estimate after each build.
