# Mandatory Documentation Synchronization

## Proactive Docs Updates (Strict)

Every time the project structure, architecture, command list, or codebase components change, all corresponding documentation **MUST** be updated immediately in the same task/commit.

## Documentation Targets

- **`README.md`:**
  - Keep entry points, features, requirements, command tables, settings, and documentation links strictly up to date.
- **`docs/project_structure.md`:**
  - Maintain the complete ASCII file structure and file descriptions whenever files or folders are added, removed, renamed, or repurposed.
- **`docs/architecture.md`:**
  - Keep Mermaid C4/Flowchart and Sequence diagrams synchronized with actual subsystems, data flows, and controller/integration logic.
- **`docs/config_spec.md`:**
  - Update whenever settings, schema, or configuration options change.
- **`.agents/rules/` (and Agent instructions):**
  - Must be updated whenever new project architectural patterns, conventions, tools, or dependencies are introduced.
