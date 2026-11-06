# Git Commit Conventions & Standards

## Commit Style: Conventional Commits

All commit messages in the CapriPet repository must strictly follow the **Conventional Commits** specification.

### Commit Format

```text
<type>(<scope>): <short imperative description>
```
*Note: `(<scope>)` is optional when the change touches multiple subsystems or general tooling.*

### Allowed Types

- **`feat`**: A new feature, command, effect, integration, or capability.
- **`fix`**: A bug fix, regression repair, or error correction.
- **`docs`**: Documentation updates (e.g. `README.md`, `docs/*`, `.agents/rules/*`).
- **`style`**: Code formatting, syntax cleanup, typography or visual adjustments with no logic changes.
- **`refactor`**: Code refactoring that neither fixes a bug nor adds a feature.
- **`perf`**: Performance improvement, reduction of lag, memory optimization, or caching.
- **`test`**: Adding new tests or modifying existing tests.
- **`chore`**: Maintenance tasks, dependencies updates, tooling configurations.

### Scope Guidelines

Use clean, lowercase scopes representing the affected subsystem or domain:
- `audio`, `asr`, `voice`
- `ui`, `theme`, `speech`, `menu`
- `effects`, `glitch`, `teleport`
- `commands`, `input`
- `integrations`, `spotify`, `discord`, `system`
- `core`, `config`, `morphology`
- `rules`, `docs`
- `tests`

### Message Rules

1. **Imperative, present tense:** Use "add", "fix", "update", "refactor" rather than "added", "fixing", "updated".
2. **Concise & lowercase:** Keep the first line concise (max 72 characters) and start the description with a lowercase letter (e.g. `feat(discord): add spotify presence`).
3. **No trailing punctuation:** Do not end the commit message subject with a period (`.`).
4. **Atomic commits:** Group related changes into logical atomic commits rather than bundling unrelated work together.