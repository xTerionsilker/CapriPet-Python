# Code Quality & Implementation Rules

## Anti-Legacy Rules & Standards

1. **No Code Comments or Docstrings (Strict):**
   - **Do not write comments:** Do not add inline or block comments (`# ...`) in code under any circumstances (except mandatory shebangs `#!/usr/bin/env ...` when applicable).
   - **Do not write docstrings:** Do not add triple-quoted docstrings (`"""..."""` or `'''...'''`) to modules, classes, or functions.
   - **Self-documenting code:** Rely entirely on clean code structure, expressive naming (functions, variables, classes), and strict type annotations to make logic self-evident.

2. **No Artificial Backward Compatibility:**
   - **Do not write wrapper adapters or legacy bridges:** Never re-introduce adapters (such as `FunctionalCommand`, alias functions, fake parameters, or `*args/**kwargs` unpackers) purely to support hypothetical old signatures.
   - **No deprecated alias methods or redundant properties:** When refactoring a class or module, migrate the callers directly instead of leaving obsolete functions/properties with comments like `# Для обратной совместимости`.
   - **Strict type signatures:** New and refactored functions must use strict, explicit keyword/positional parameters with complete type annotations.
   - **Clean dependency contracts & standard libraries:** Standard libraries and established ecosystem packages (e.g. `pydantic`, `psutil`, `rapidfuzz`, `httpx`, `fake-useragent`, `cyrtranslit`, `yt-dlp`) are canonical. Do not implement manual string parsing, hand-rolled typo matching, browser registry crawlers, custom subprocess scrapers, or huge reinvented wheels where vetted PyPI libraries or standard ecosystem solutions can solve the problem cleanly and reliably. Feel free to adopt and install external libraries for integrations and complex OS/system tasks instead of writing brittle custom workarounds.
