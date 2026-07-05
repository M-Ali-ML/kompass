---
name: post-docs-updater
description: Update post-building documentation in the docs/ directory (the markdown docs, their HTML twins, and the published index.html flow visualization — all one connected site). Run this skill whenever you make structural, architectural, database, or UI/styling changes, or finish a feature to keep the living documentation in sync with the codebase.
---

# Skill: Maintaining Post-Building Documentation (Post-Docs)

## Purpose
This skill defines how coding agents must maintain the post-building documentation in the `docs/` directory. While `pre-docs/` contains static blueprints, requirements, and design specifications created *before* construction, `docs/` represents the living, single source of truth for what has *actually* been built. Any agent changing the codebase must ensure `docs/` is updated accordingly.

`docs/` is served as a static site via **GitHub Pages** (`https://m-ali-ml.github.io/kompass/`), so every file placed there is publicly reachable — there is no separate docs site elsewhere in the repo. It contains two parallel forms of the same content, kept consistent with each other:
* **Markdown** — `architecture.md`, `design.md`, `product.md`, `user-stories.md`, `evals.md`: the prose source of truth, easiest to diff and edit.
* **HTML** — `index.html` (the interactive flow demo / homepage), `architecture.html`, `design.html`, `product.html`, `user-stories.html`, `evals.html`: visual pages sharing one theme (`docs/assets/style.css`, the "Candy" palette also used by the app itself) and one consistent nav bar (Overview · Flow Demo · Architecture · Product · Design · User Stories · Evals) so every page is cross-linked and reachable from every other page.

---

## When to Execute this Skill
You **MUST** invoke this skill and update the relevant documents in `docs/` whenever you make any of the following changes:
1. **Structural/Architectural Changes:** Modifying folder layout, adding packages/modules, changing API endpoints, adding database tables, or changing communication protocols (e.g., AGUI, CopilotKit, MCP).
2. **UI/Design Changes:** Modifying global styles (`globals.css`), component styling, theme colors, typography, layout definitions, or interactive animation patterns.
3. **Feature Implementation:** Completing any feature or sub-feature described in the PRD or user stories.
4. **Dependency/Tooling Updates:** Adding, upgrading, or removing backend packages (`pyproject.toml`) or frontend packages (`package.json`).

After updating the Markdown docs, **always check whether the published flow visualization ([docs/index.html](../../../docs/index.html)) also needs to be updated** to reflect the same change (see its entry below).

---

## Execution Steps

### 1. Identify Changed Components
Review the files you have created, modified, or deleted during your session.

### 2. Determine Which Post-Docs Require Updates
Determine which files in `docs/` correspond to your changes:

* **[architecture.md](../../../docs/architecture.md)** + its HTML twin **[architecture.html](../../../docs/architecture.html)**
  * *Update when:* Modifying backend routes/endpoints, adding/changing domain models, creating ports or adapters, updating SQLite schemas, integrating new external APIs (MCP, CopilotKit, Google Maps), or changing third-party frameworks.
  * Update both files together: the markdown is the prose reference, the HTML page renders the same facts as a system map, a ports/adapters table, and an agent-tools table. Don't let them disagree.
* **[design.md](../../../docs/design.md)** + its HTML twin **[design.html](../../../docs/design.html)**
  * *Update when:* Changing the active visual theme, CSS properties/styling, layout systems, component markup structure, font styles, animations, or interactive behaviors.
  * If the actual theme tokens change (colors, radii, shadows), update them in **three** places so the docs stay honest about their own look: `design.md`, the live swatches/demos in `design.html`, and — since all doc pages share it — `docs/assets/style.css`.
* **[product.md](../../../docs/product.md)** + its HTML twin **[product.html](../../../docs/product.html)**
  * *Update when:* Implementing, testing, or modifying high-level features. Ensure the feature status checklist (and the matching status pills in `product.html`) are kept up to date.
* **[user-stories.md](../../../docs/user-stories.md)** + its HTML twin **[user-stories.html](../../../docs/user-stories.html)**
  * *Update when:* Developing code that fulfills the acceptance criteria of any user stories. Mark stories as:
    * `[x]` Completed (when fully functional and verified)
    * `[/]` In Progress (when currently being worked on)
    * `[ ]` Not Started (backlog)
  * Mirror the same status in `user-stories.html`'s status pills.
* **[evals.md](../../../docs/evals.md)** — the technical reference for the agent-behavior eval suite (`backend/evals/`: schema, fixtures, harness, judge, evaluators, cases, runner, dashboard).
  * *Update when:* Changing the eval suite's architecture (new evaluator, fixture, case category, CLI flag, or file). Keep the file map, evaluator table, and case-category table honest about actual file/class names.
  * Its HTML twin **[evals.html](../../../docs/evals.html)** is different in kind from the other twins: it's a **chronological findings log** (regressions caught, root causes, before/after numbers), appended to whenever an eval run teaches something new — never rewritten after the fact. Append a new timeline entry there when a run surfaces a real finding; only touch `evals.md` for structural/architectural changes to the suite itself.
* **[index.html](../../../docs/index.html)** — the public homepage: the interactive, click-through flow visualization, served directly via **GitHub Pages** (`https://m-ali-ml.github.io/kompass/`). `docs/index.html` is the single source of truth — edit it directly (there is no separate source copy to keep in sync).
  * *Always check whether this needs updating* whenever the changes above touch anything the visualization depicts: the architecture/layers, the request flow (the step-by-step lifecycle), the agent tools (the toolbelt), data sources (MCP servers, grounding, persistence), the generative-UI tool cards, the hexagonal ports/adapters, or the tech stack.
  * *How to update:* edit [docs/index.html](../../../docs/index.html) directly. Keep its content consistent with `architecture.md`/`.html`, `product.md`/`.html`, and `design.md`/`.html`.

### 3. Read Existing Post-Docs
Always read the current content of the target post-doc file using `view_file` to ensure you understand its current structure and do not overwrite or duplicate sections.

### 4. Apply Updates
Use code replacement tools (`replace_file_content` or `multi_replace_file_content`) to apply edits to the files. Ensure all file references in the documentation are formatted as **repo-relative links** (e.g., from `docs/`, `[main.py](../backend/app/main.py)`). Never use machine-absolute `file:///Users/...` paths — they leak local usernames and break for other clones and on GitHub.

---

## Formatting Guidelines
* **Read-Only Pre-Docs:** Never modify files under `pre-docs/`. They are historical blueprints. Only edit files under `docs/`.
* **Be Precise and Direct:** Document actual names of classes, functions, routes, tables, and variables.
* **Maintain Relative Links:** Always write file references as repo-relative links from the doc's location, e.g. from `docs/`: `[db_sqlite.py](../backend/app/adapters/db_sqlite.py)`. Never use `file:///Users/...` absolute paths.
