---
trigger: manual
description: Enforce Test-Driven Development (TDD) workflow with red-green-refactor cycles.
---

# Test-Driven Development (TDD) Rule

You must strictly follow a Test-Driven Development (TDD) workflow for all feature implementations, bug fixes, and code modifications in this codebase.

## 1. Philosophy: Test Behaviors, Not Implementations
* **Public Interfaces Only**: Tests must verify behavior through public APIs and interfaces, never internal implementation details, private methods, or internal variables.
* **Resilient to Refactoring**: Tests should act as specifications. If you rename an internal function or refactor class internals, the tests must still pass without modification if the external behavior hasn't changed.
* **Avoid Over-Mocking**: Prefer integration-style tests that run actual code paths. Only mock external network calls or expensive/unstable third-party services. Do not mock internal collaborators.

## 2. Strict Red-Green-Refactor Loop (Vertical Slices)
Do **NOT** write all tests first and then all implementation (avoid "horizontal slicing"). Instead, implement feature behavior incrementally using "vertical slices":
1. **RED**: Write a single failing test for one specific behavior. Run the test suite and verify it fails for the expected reason.
2. **GREEN**: Write the minimal amount of code necessary to make that specific test pass. Do not write speculative code or anticipate future requirements.
3. **REFACTOR**: Clean up, de-duplicate, and structure the code (applying SOLID principles) while maintaining a passing suite. **Never refactor while in a RED state.**
4. **Repeat**: Move to the next behavior and repeat the loop.

## 3. Checklist per Cycle
Before completing a cycle, ensure:
* [ ] The test describes a user-facing or system behavior, not an implementation detail.
* [ ] The test exercises the public interface only.
* [ ] The test would survive a complete internal refactoring.
* [ ] Code is minimal for this test.
* [ ] No speculative features or unused arguments were introduced.