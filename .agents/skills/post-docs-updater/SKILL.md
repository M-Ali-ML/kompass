---
name: post-docs-updater
description: Update post-building documentation in the docs/ directory (such as architecture, design, and product files, plus the published index.html flow visualization). Run this skill whenever you make structural, architectural, database, or UI/styling changes, or finish a feature to keep the living documentation in sync with the codebase.
---

# Skill: Maintaining Post-Building Documentation (Post-Docs)

## Purpose
This skill defines how coding agents must maintain the post-building documentation in the `docs/` directory. While `pre-docs/` contains static blueprints, requirements, and design specifications created *before* construction, `docs/` represents the living, single source of truth for what has *actually* been built. Any agent changing the codebase must ensure `docs/` is updated accordingly.

---

## When to Execute this Skill
You **MUST** invoke this skill and update the relevant documents in `docs/` whenever you make any of the following changes:
1. **Structural/Architectural Changes:** Modifying folder layout, adding packages/modules, changing API endpoints, adding database tables, or changing communication protocols (e.g., AGUI, CopilotKit, MCP).
2. **UI/Design Changes:** Modifying global styles (`globals.css`), component styling, theme colors, typography, layout definitions, or interactive animation patterns.
3. **Feature Implementation:** Completing any feature or sub-feature described in the PRD or user stories.
4. **Dependency/Tooling Updates:** Adding, upgrading, or removing backend packages (`pyproject.toml`) or frontend packages (`package.json`).

After updating the Markdown docs, **always check whether the published flow visualization ([docs/index.html](../../../docs/index.html), sourced from [artifacts/kompass-flow.html](../../../artifacts/kompass-flow.html)) also needs to be updated** to reflect the same change (see its entry below).

---

## Execution Steps

### 1. Identify Changed Components
Review the files you have created, modified, or deleted during your session.

### 2. Determine Which Post-Docs Require Updates
Determine which files in `docs/` correspond to your changes:

* **[architecture.md](../../../docs/architecture.md)**
  * *Update when:* Modifying backend routes/endpoints, adding/changing domain models, creating ports or adapters, updating SQLite schemas, integrating new external APIs (MCP, CopilotKit, Google Maps), or changing third-party frameworks.
* **[design.md](../../../docs/design.md)**
  * *Update when:* Changing the active visual theme, CSS properties/styling, layout systems, component markup structure, font styles, animations, or interactive behaviors.
* **[product.md](../../../docs/product.md)**
  * *Update when:* Implementing, testing, or modifying high-level features. Ensure the feature status checklist is kept up to date.
* **[user-stories.md](../../../docs/user-stories.md)**
  * *Update when:* Developing code that fulfills the acceptance criteria of any user stories. Mark stories as:
    * `[x]` Completed (when fully functional and verified)
    * `[/]` In Progress (when currently being worked on)
    * `[ ]` Not Started (backlog)
* **[index.html](../../../docs/index.html)** — the public, interactive flow visualization served via **GitHub Pages** (`https://m-ali-ml.github.io/kompass/`). Its editable source is [artifacts/kompass-flow.html](../../../artifacts/kompass-flow.html); `docs/index.html` is a published copy of it.
  * *Always check whether this needs updating* whenever the changes above touch anything the visualization depicts: the architecture/layers, the request flow (the step-by-step lifecycle), the agent tools (the toolbelt), data sources (MCP servers, grounding, persistence), the generative-UI tool cards, the hexagonal ports/adapters, or the tech stack.
  * *How to update:* edit the source [artifacts/kompass-flow.html](../../../artifacts/kompass-flow.html) first, then sync the published copy with `cp artifacts/kompass-flow.html docs/index.html` so the two stay identical. Keep its content consistent with `architecture.md`, `product.md`, and `design.md`.

### 3. Read Existing Post-Docs
Always read the current content of the target post-doc file using `view_file` to ensure you understand its current structure and do not overwrite or duplicate sections.

### 4. Apply Updates
Use code replacement tools (`replace_file_content` or `multi_replace_file_content`) to apply edits to the files. Ensure all file references in the documentation are formatted as **repo-relative links** (e.g., from `docs/`, `[main.py](../backend/app/main.py)`). Never use machine-absolute `file:///Users/...` paths — they leak local usernames and break for other clones and on GitHub.

---

## Formatting Guidelines
* **Read-Only Pre-Docs:** Never modify files under `pre-docs/`. They are historical blueprints. Only edit files under `docs/`.
* **Be Precise and Direct:** Document actual names of classes, functions, routes, tables, and variables.
* **Maintain Relative Links:** Always write file references as repo-relative links from the doc's location, e.g. from `docs/`: `[db_sqlite.py](../backend/app/adapters/db_sqlite.py)`. Never use `file:///Users/...` absolute paths.
