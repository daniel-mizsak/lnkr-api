# AGENTS.md

## Runtime and dependencies

- Requires Python 3.14.
- PEP 758's `except A, B:` syntax is intentional. Do not flag or rewrite it.
- Dependencies are managed with uv. Project dependencies and dependency groups use exact `==` pins.
  Add new dependencies with `uv add 'pkg==x.y.z'`.
  The `exclude-newer` setting in `pyproject.toml` is intentional.

## Implementation

- Use `extra="forbid"` on input schemas containing fields that may be omitted, so misspelled keys cannot silently fall back to defaults.
  Omit it for required-only input schemas. Misspelling a required key already causes a missing-field error when the correct key is absent.
- Add logs for failures or when useful for diagnosis or auditing.
  Include relevant actor/target identifiers.

## Migrations

- Generate or edit migration revisions only with explicit user approval.
- Generate new revisions with `just database-migration "message"`. Do not hand-write them.
- Review migrations for correctness, unintended changes, and risks to existing data.

## Testing

- Name tests `test_<operation>__<scenario_or_behavior>`, using existing terminology.
  Keep one scenario per test, but multiple actions are appropriate when testing a sequence.
- Order tests for each function to follow its control flow, including validation and early exits before later operations.
  Preserve the existing order when the relative flow order is unclear.
- Parametrize only cases sharing setup and assertions, without conditional logic or varying patch targets.
  Split cases when sharing assertions requires indirect logic.
- Set up endpoint tests through APIs.
  Write directly to the database only for otherwise unreachable states.
  Database reads may verify side effects.
- Use the fixed `now` fixture for ordinary time data.
  Use `@pytest.mark.usefixtures("frozen_now")` when the behavior or assertions depend on the current time.
  Use local `time_machine.travel(..., tick=False)` contexts for boundaries or time changes.
  Fixtures needing frozen setup must depend on `frozen_now`.
- Separate Arrange, Act, Assert with blank lines, without routine section comments.
  Store results before asserting, except with `pytest.raises`.
- For HTTP responses, separate these groups with blank lines, in order:
  response assertions (status, headers, content), body/error extraction, body assertions.
  Use dictionary equality for long JSON contracts.
  For short responses, assign `data = response.json()` before assertions or error extraction.
  A single body assertion for a successful response may immediately follow that assignment if no error is extracted.
- Keep assertions focused on the named scenario. Add supporting checks only when needed to prove its outcome or state transition.
- Avoid duplicating lower-level behavior unless needed to verify the current layer's contract.
  Preserve endpoint status, authorization, and response-contract checks.

## Validation

- Use `just test` with Docker running, as bare `uv run pytest` skips required environment setup.
- Before finishing, pass `just check-all` except for documentation-only changes.
  This runs lint, type checks, and tests with 100% coverage required for test code.
  Application coverage is reported without a minimum threshold.
