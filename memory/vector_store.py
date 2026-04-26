import os
import json
from dotenv import load_dotenv

load_dotenv()

# ── Simple JSON file storage ─────────────────────────
# No ChromaDB, no embeddings, no model downloads
# Just stores findings in a JSON file — lightweight and fast

MEMORY_FILE = "./memory/findings.json"


def _load() -> dict:
    """Load memory from JSON file."""
    if not os.path.exists(MEMORY_FILE):
        return {"files": {}, "findings": []}
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"files": {}, "findings": []}


def _save(data: dict) -> None:
    """Save memory to JSON file."""
    try:
        os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
        with open(MEMORY_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[MEMORY] Could not save: {e}")


print("[MEMORY] JSON memory store ready ✓")


def index_file(file_path: str, content: str) -> None:
    """Index a single file into memory."""
    if not content or not content.strip():
        return
    data = _load()
    data["files"][file_path] = content[:2000]
    _save(data)


def index_pr_files(files: list) -> None:
    """Index all changed files from a PR."""
    print(f"[MEMORY] Indexing {len(files)} file(s)...")
    indexed = 0
    for f in files:
        patch = f.get("patch", "")
        if patch:
            index_file(f["filename"], patch)
            indexed += 1
    print(f"[MEMORY] Indexed {indexed} file(s) ✓")


def store_finding(finding: dict, pr_number: int) -> None:
    """Store a finding from an agent."""
    data = _load()
    data["findings"].append({
        "pr_number": str(pr_number),
        "file":      finding.get("file", ""),
        "line":      str(finding.get("line", 0)),
        "severity":  finding.get("severity", "low"),
        "type":      finding.get("type", "unknown"),
        "message":   finding.get("message", ""),
    })
    _save(data)


def store_all_findings(findings: list, pr_number: int) -> None:
    """Store all findings from a review."""
    for finding in findings:
        store_finding(finding, pr_number)
    print(f"[MEMORY] Stored {len(findings)} finding(s) ✓")


def get_similar_code(query: str, n_results: int = 3) -> list:
    """Get stored files from memory."""
    data = _load()
    files = data.get("files", {})
    results = []
    for path, content in list(files.items())[:n_results]:
        results.append({"content": content, "path": path})
    return results


def get_similar_findings(query: str, n_results: int = 3) -> list:
    """Get recent findings from memory."""
    data = _load()
    findings = data.get("findings", [])
    return findings[-n_results:] if findings else []


def build_context_block(diff_text: str) -> str:
    """Build context string to inject into agent prompts."""
    context_parts = []

    similar_findings = get_similar_findings(diff_text)
    if similar_findings:
        context_parts.append("=== SIMILAR PAST FINDINGS ===")
        for item in similar_findings:
            context_parts.append(
                f"[{item['severity'].upper()}] {item['type']} in "
                f"{item['file']} (PR #{item['pr_number']}): {item['message']}"
            )
        context_parts.append("")

    return "\n".join(context_parts) if context_parts else ""


def get_memory_stats() -> dict:
    """Return how many items are stored in memory."""
    data = _load()
    return {
        "indexed_files":   len(data.get("files", {})),
        "stored_findings": len(data.get("findings", [])),
    }


def clear_memory() -> None:
    """Clear all memory."""
    _save({"files": {}, "findings": []})
    print("[MEMORY] Memory cleared ✓")