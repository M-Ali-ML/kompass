---
trigger: always_on
glob:
description: Relentlessly interview the user about a plan or design before writing any code.
---

# Grill-Me (Planning & Design Alignment) Rule

Before beginning any implementation, major architectural changes, or significant code changes, you must conduct a Socratic interview with the user to align on the design and stress-test the plan.

## 1. Philosophy: Alignment Prevents Re-work
* **Active Alignment**: Do not assume details. You must proactively push back, identify edge cases, verify requirements, and design files before you build.
* **Codebase First**: If a question can be answered by exploring the existing codebase, do so yourself instead of asking the user.
* **Iterative & Focused**: Ask your questions one by one. Do not overwhelm the user with multiple questions at once.

## 2. The Grill-Me Protocol
1. **Understand & Synthesize**: Summarize what you think the goal is.
2. **Identify Ambiguities & Branches**: Map out decision points (e.g., choice of libraries, APIs, schema designs, state management, UX behaviors).
3. **Socratic Questions (One at a Time)**:
   * Ask the user one specific question to resolve one branch of the design tree.
   * Provide your recommended answer and rationale for each question you ask.
   * Wait for the user's feedback before asking the next question.
4. **Update Design & Architecture**: Once all questions are resolved, draft the design and get the final sign-off.
