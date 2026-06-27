---
name: session-logging
description: Maintain daily session logs and context handoffs in the sessions/ directory. Run this skill at the end of every session/turn, after completing major implementation steps, or when resolving bugs to document completed tasks, active bugs, and next steps for the next agent.
---

# Skill: Daily Session Logging & Context Handoff

## Purpose
This skill defines how coding agents must maintain daily session logs in the `sessions/` directory. These logs ensure that when a new conversation is started, the next agent can immediately resume with full context of completed tasks, active bugs, gotchas, user preferences, and next steps.

---

## Core Development Philosophies (Always Follow)
* **Start Very Simple**: Do not attempt to build a complex agent or fully-featured application immediately. Start with a minimal, working prototype/baseline and build up incrementally.
* **Test-Driven Development (TDD)**: Do not engage in "pure vibe coding" of a full application without verifying correctness. Write tests first and fully implement TDD per [tdd.md](../../../.agents/rules/tdd.md) to ensure each vertical slice of behavior is verified before expanding.

---

## When to Execute this Skill
You **MUST** invoke this skill and update the current daily session log:
1. **At the end of a session/turn:** Before wrapping up your response, ensure the log reflects everything done.
2. **After completing a major implementation step:** When a feature, test suite, or page is implemented.
3. **When a bug/issue is resolved:** Especially if it involved troubleshooting or finding a workaround.
4. **When architectural decisions change:** Documenting a change in direction, technology, or patterns.
5. **When a user preference is discovered:** Such as coding styles, visual styles, library version preferences, etc.

---

## Execution Steps

### 1. Identify the Current Date
* Check the current local date provided by system metadata.
* Target session log file path: `sessions/YYYY-MM-DD.md` (e.g., `sessions/2026-06-21.md`).

### 2. Check for an Existing Log
* Check if `sessions/YYYY-MM-DD.md` already exists.
* If it **does not exist**, create it using the **Template** below.
* If it **does exist**, read it first using `view_file` to understand the day's existing log and avoid duplicates.

### 3. Apply the Updates
* Make updates to the corresponding sections:
  * **Current Objectives**: What is the overall goal of the current work stream.
  * **Today's Progress**: Bulleted list of implemented features, refactorings, or changes. Include repo-relative file links (from `sessions/`, e.g. `[main.py](../backend/app/main.py)`) for edited files.
  * **Gotchas & Troubleshooting**: Any unexpected behaviors, dependency conflicts, APIs quirks, or issues you had to debug and how they were resolved.
  * **Preferences & Architectural Decisions**: Design/backend architecture choices, configuration settings, or constraints.
  * **Next Steps**: What the next agent needs to pick up immediately.
* Use atomic file edits (`replace_file_content` or `multi_replace_file_content`) to modify the log.

---

## Session Log Template (`sessions/YYYY-MM-DD.md`)

```markdown
# Session Log: YYYY-MM-DD

## 🎯 Current Objectives
- [ ] Brief summary of what we are building or researching in this work stream.

## 🚀 Today's Progress
- **Feature/Component**:
  - Detailed bullet points of what was done.
  - Link files changed: `[filename](../path/to/file)`

## ⚠️ Gotchas & Troubleshooting
- **Issue Description**: Explain what failed or acted unexpectedly.
- **Resolution/Workaround**: Explain how it was resolved, so future agents don't re-encounter it.

## 🧠 Preferences & Architectural Decisions
- **Decision**: Details on why a certain architectural pattern, folder structure, library, or design style was chosen.
- **User Preference**: Specific requests or habits the user preferred (e.g., "likes very descriptive logs", "prefers Next.js App Router over Pages").

## 📋 Next Steps
- [ ] Checklist of immediate next actions for the next conversation session.
```

---

## Formatting Guidelines
* Keep summaries concise but technical. Specify file paths, function/class names, and library names.
* Use repo-relative Markdown links for all files (from `sessions/`, e.g., `[architecture.md](../docs/architecture.md)`). Never use machine-absolute `file:///Users/...` paths.
* Do not delete history from the current day's log; append or update the checklists as tasks progress.
