# Code Quality & Implementation Rules

## Anti-Legacy Rules & Standards

1. **PEP 8 & PEP 257 Documentation Standards:**
   - **Comments:** Meaningful inline and block comments (`# ...`) are allowed and encouraged where necessary to explain non-obvious logic, complex algorithms, or Win32/hardware nuances. Technical directives (`# noqa`, `# type: ignore`) are fully permitted.
   - **Docstrings:** Public modules and classes must provide clear, concise docstrings following PEP 257 standards.
   - **Self-documenting code:** Rely primarily on clean code structure, expressive naming (functions, variables, classes), and strict type annotations, using docstrings and comments to enrich context.

2. **No Artificial Backward Compatibility:**
   - **Do not write wrapper adapters or legacy bridges:** Never re-introduce adapters (such as `FunctionalCommand`, alias functions, fake parameters, or `*args/**kwargs` unpackers) purely to support hypothetical old signatures.
   - **No deprecated alias methods or redundant properties:** When refactoring a class or module, migrate the callers directly instead of leaving obsolete functions/properties with comments like `# Для обратной совместимости`.
   - **Strict type signatures:** New and refactored functions must use strict, explicit keyword/positional parameters with complete type annotations.
   - **Clean dependency contracts & standard libraries:** Standard libraries and established ecosystem packages (e.g. `pydantic`, `psutil`, `rapidfuzz`, `httpx`, `fake-useragent`, `cyrtranslit`, `yt-dlp`) are canonical. Do not implement manual string parsing, hand-rolled typo matching, browser registry crawlers, custom subprocess scrapers, or huge reinvented wheels where vetted PyPI libraries or standard ecosystem solutions can solve the problem cleanly and reliably. Feel free to adopt and install external libraries for integrations and complex OS/system tasks instead of writing brittle custom workarounds.
