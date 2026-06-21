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

---

## Execution Steps

### 1. Identify Changed Components
Review the files you have created, modified, or deleted during your session.

### 2. Determine Which Post-Docs Require Updates
Determine which files in `docs/` correspond to your changes:

* **[architecture.md](file:///Users/aly/repos/kompass/docs/architecture.md)**
  * *Update when:* Modifying backend routes/endpoints, adding/changing domain models, creating ports or adapters, updating SQLite schemas, integrating new external APIs (MCP, CopilotKit, Google Maps), or changing third-party frameworks.
* **[design.md](file:///Users/aly/repos/kompass/docs/design.md)**
  * *Update when:* Changing the active visual theme, CSS properties/styling, layout systems, component markup structure, font styles, animations, or interactive behaviors.
* **[product.md](file:///Users/aly/repos/kompass/docs/product.md)**
  * *Update when:* Implementing, testing, or modifying high-level features. Ensure the feature status checklist is kept up to date.
* **[user-stories.md](file:///Users/aly/repos/kompass/docs/user-stories.md)**
  * *Update when:* Developing code that fulfills the acceptance criteria of any user stories. Mark stories as:
    * `[x]` Completed (when fully functional and verified)
    * `[/]` In Progress (when currently being worked on)
    * `[ ]` Not Started (backlog)

### 3. Read Existing Post-Docs
Always read the current content of the target post-doc file using `view_file` to ensure you understand its current structure and do not overwrite or duplicate sections.

### 4. Apply Updates
Use code replacement tools (`replace_file_content` or `multi_replace_file_content`) to apply edits to the files. Ensure all file references in the documentation are formatted as absolute paths (e.g., `[main.py](file:///Users/aly/repos/kompass/backend/app/main.py)`).

---

## Formatting Guidelines
* **Read-Only Pre-Docs:** Never modify files under `pre-docs/`. They are historical blueprints. Only edit files under `docs/`.
* **Be Precise and Direct:** Document actual names of classes, functions, routes, tables, and variables.
* **Maintain Absolute Links:** Always write file references as absolute links, e.g. `[db_sqlite.py](file:///Users/aly/repos/kompass/backend/app/adapters/db_sqlite.py)`.
