## FastAPI webhook skill

When building webhook handlers:
- Always validate HMAC-SHA256 signatures before processing payloads
- Return HTTP 200 immediately, process async in background
- Use Pydantic models for all request/response shapes
- Log every incoming event with structured fields: event_type, repo, pr_number