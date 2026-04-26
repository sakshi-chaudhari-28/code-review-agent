import os
import hmac
import hashlib
import asyncio
import sys
import structlog

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from dotenv import load_dotenv
from agents.orchestrator import run as orchestrator_run

load_dotenv()

# ── structlog JSON config ──────────────────────────
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.PrintLoggerFactory(sys.stdout),
    cache_logger_on_first_use=True,
)
# ───────────────────────────────────────────────────

log = structlog.get_logger()
app = FastAPI(title="Code Review Agent", version="0.1.0")

@app.delete("/memory/reset")
async def reset_memory():
    """Reset the vector store — removes all past findings."""
    import shutil
    try:
        shutil.rmtree("./memory/chroma_db", ignore_errors=True)
        os.makedirs("./memory/chroma_db", exist_ok=True)
        return {"status": "memory cleared"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.get("/memory/clear")
async def clear_memory_endpoint() -> dict[str, str]:
    """Clear all memory — GET request for easy browser access."""
    import shutil
    try:
        shutil.rmtree("./memory/chroma_db", ignore_errors=True)
        os.makedirs("./memory/chroma_db", exist_ok=True)
        return {"status": "memory cleared successfully"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")


def verify_signature(payload_body: bytes, signature_header: str) -> bool:
    """Validate GitHub HMAC-SHA256 webhook signature."""
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode("utf-8"),
        payload_body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


# Global lock — only one PR processed at a time
pr_lock = asyncio.Lock()

async def process_pr_event(pr_data: dict, action: str):
    """Background task — runs the full orchestrator pipeline."""
    async with pr_lock:
        log.info(
            "pr_event_received",
            action=action,
            pr_number=pr_data.get("number"),
            repo=pr_data.get("base", {}).get("repo", {}).get("full_name"),
            author=pr_data.get("user", {}).get("login"),
        )
        sys.stdout.flush()

        pr_number = pr_data.get("number")
        print(f"[WEBHOOK] PR #{pr_number} received — starting orchestrator...")
        sys.stdout.flush()

        try:
            result = await orchestrator_run(pr_data)
            print(f"[WEBHOOK] Orchestrator finished: {result}")
        except Exception as e:
            print(f"[WEBHOOK] Orchestrator error: {e}")

        sys.stdout.flush()


@app.post("/webhook")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """Receive and validate GitHub PR webhook events."""
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not verify_signature(body, signature):
        log.warning("invalid_webhook_signature")
        sys.stdout.flush()
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    event_type = request.headers.get("X-GitHub-Event", "unknown")

    if event_type == "pull_request":
        action = payload.get("action", "")
        if action in ["opened", "synchronize", "reopened"]:
            pr_data = payload["pull_request"]
            pr_number = pr_data.get("number")
            branch    = pr_data.get("head", {}).get("ref", "")

            # Skip old test branches — only process real PRs
            skip_branches = [
                "test/webhook-check",
                "test/real-review",
            ]

            if branch in skip_branches:
                print(f"[WEBHOOK] Skipping PR #{pr_number} on branch {branch}")
                return {"status": "skipped", "branch": branch}

            print(f"[WEBHOOK] Processing PR #{pr_number} on branch {branch}")
            background_tasks.add_task(process_pr_event, pr_data, action)

    return {"status": "accepted", "event": event_type}


@app.get("/")
async def root():
    """Root endpoint to welcome users and prevent 404 on base URL."""
    return {"message": "Code Review Agent Webhook Server is running. Visit /health to check status."}


@app.get("/health")
async def health_check():
    """Simple health check — confirm server is running."""
    return {"status": "ok", "service": "code-review-agent"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))


