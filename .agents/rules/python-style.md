---
trigger: always_on
---

# Project rules

- Always use Python 3.11+
- Use type hints on all function signatures
- Use async/await for all route handlers
- Never hardcode secrets — always read from environment variables using python-dotenv
- Use structured logging (structlog), never print()
- All functions must have docstrings