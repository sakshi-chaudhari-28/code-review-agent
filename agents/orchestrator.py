import os
import sys
import json
from groq import Groq
from tools.github_tool import GitHubTool
from memory.vector_store import (
    index_pr_files,
    store_all_findings,
    build_context_block,
    get_memory_stats
)
from dotenv import load_dotenv

load_dotenv()

# ── Groq client ──────────────────────────────────────
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
github = GitHubTool()

# ── System prompt ────────────────────────────────────
SYSTEM_PROMPT = """You are a senior engineering lead reviewing a Pull Request.

You will be given a list of changed files and their diffs.
Your job is to decide which specialist agents to call.

Reply ONLY with a valid JSON array — no explanation, no markdown, no code fences.
Example format:
[
  {"agent": "code_analyzer", "reason": "Review new functions for bugs", "priority": "high"},
  {"agent": "security_scanner", "reason": "User input handling detected", "priority": "high"}
]

Available agents:
- code_analyzer   — ALWAYS include this for every PR
- security_scanner — include if you see: DB queries, user input, auth, tokens, passwords, HTTP requests
- test_evaluator  — include if you see: new functions, new classes, new endpoints
- fix_generator   — include only if there are likely HIGH severity issues

Priority must be one of: high, medium, low
Return ONLY the JSON array. Nothing else."""


def format_diff_for_prompt(files: list) -> str:
    """Format PR files into a clean string for the model."""
    output = []
    for f in files:
        output.append(f"FILE: {f['filename']} ({f['status']}, {f['changes']} changes)")
        if f['patch']:
            output.append(f"DIFF:\n{f['patch']}")
        output.append("---")
    return "\n".join(output)


def parse_agents(response_text: str) -> list:
    """Safely parse the JSON response."""
    text = response_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        text = "\n".join(lines).strip()
    start = text.find("[")
    end   = text.rfind("]") + 1
    if start == -1 or end == 0:
        return [{"agent": "code_analyzer", "reason": "Default review", "priority": "medium"}]
    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError:
        return [{"agent": "code_analyzer", "reason": "Default review", "priority": "medium"}]


async def run(pr_data: dict) -> dict:
    """
    Main orchestrator — fetches diff, uses memory for context,
    plans agents, runs each specialist, stores findings.
    """
    # ── Extract PR metadata ──────────────────────────
    owner     = pr_data.get("base", {}).get("repo", {}).get("owner", {}).get("login")
    repo      = pr_data.get("base", {}).get("repo", {}).get("name")
    pr_number = pr_data.get("number")
    pr_title  = pr_data.get("title")

    print(f"\n{'='*50}")
    print(f"[ORCHESTRATOR] PR #{pr_number}: {pr_title}")
    print(f"[ORCHESTRATOR] Repo: {owner}/{repo}")
    print(f"{'='*50}\n")

    # ── Step 1: Fetch the PR diff ────────────────────
    print("[ORCHESTRATOR] Fetching PR diff...")
    files     = github.get_pr_files(owner, repo, pr_number)
    diff_text = format_diff_for_prompt(files)

    print(f"[ORCHESTRATOR] {len(files)} changed file(s):")
    for f in files:
        print(f"  → {f['filename']} ({f['status']})")

    # ── Step 2: Index files into memory ─────────────
    index_pr_files(files)
    stats = get_memory_stats()
    print(f"[MEMORY] Stats: {stats['indexed_files']} files, "
          f"{stats['stored_findings']} past findings")

    # ── Step 3: Build context from memory ───────────
    print("[MEMORY] Retrieving relevant context...")
    context = build_context_block(diff_text)
    if context:
        print("[MEMORY] Context retrieved ✓")
    else:
        print("[MEMORY] No prior context yet (first review)")

    # ── Step 4: Ask Groq to plan the review ─────────
    print("\n[ORCHESTRATOR] Planning review with Groq...")
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"PR Title: {pr_title}\n\nChanged files:\n{diff_text}"}
        ],
        temperature=0.1,
        max_tokens=500,
    )
    dispatched = parse_agents(response.choices[0].message.content)

    print(f"[ORCHESTRATOR] Dispatching {len(dispatched)} agent(s):")
    for d in dispatched:
        print(f"  → {d['agent'].upper()} ({d['priority']}) — {d['reason']}")

    # ── Step 5: Post initial summary comment ─────────
    summary = build_summary_comment(pr_title, dispatched, files)
    github.post_pr_summary(owner, repo, pr_number, summary)
    print("\n[ORCHESTRATOR] Initial summary posted to GitHub ✓")

    # ── Step 6: Run each specialist agent ────────────
    # Pass context from memory into each agent's diff
    diff_with_context = (
        f"{diff_text}\n\n{context}" if context else diff_text
    )

    all_findings = []
    agent_names  = [d["agent"] for d in dispatched]

    if "code_analyzer" in agent_names:
        from agents.code_analyzer import run as run_code_analyzer
        findings = await run_code_analyzer(pr_data, diff_with_context)
        all_findings.extend(findings)

    if "security_scanner" in agent_names:
        from agents.security_scanner import run as run_security_scanner
        findings = await run_security_scanner(pr_data, diff_with_context)
        all_findings.extend(findings)

    if "test_evaluator" in agent_names:
        from agents.test_evaluator import run as run_test_evaluator
        findings = await run_test_evaluator(pr_data, diff_with_context)
        all_findings.extend(findings)

    if "fix_generator" in agent_names:
        from agents.fix_generator import run as run_fix_generator
        await run_fix_generator(pr_data, diff_with_context, all_findings)

    # ── Step 7: Store findings in memory ────────────
    if all_findings:
        store_all_findings(all_findings, pr_number)
        print(f"[MEMORY] Stored {len(all_findings)} finding(s) for future reviews ✓")

    # ── Step 8: Post final results summary ───────────
    high   = len([f for f in all_findings if f.get("severity") == "high"])
    medium = len([f for f in all_findings if f.get("severity") == "medium"])
    low    = len([f for f in all_findings if f.get("severity") == "low"])

    final_comment = (
        f"## ✅ Code Review Complete\n\n"
        f"**Total issues found: {len(all_findings)}**\n\n"
        f"| Severity | Count |\n"
        f"|----------|-------|\n"
        f"| 🔴 High   | {high} |\n"
        f"| 🟡 Medium | {medium} |\n"
        f"| 🟢 Low    | {low} |\n\n"
        f"*Check inline comments above for details on each issue.*\n\n"
        f"---\n"
        f"*Powered by Groq LLaMA 3.3 70B · Autonomous Code Review Agent*"
    )
    github.post_pr_summary(owner, repo, pr_number, final_comment)
    print(f"\n[ORCHESTRATOR] Final summary posted ✓")
    print(f"[ORCHESTRATOR] Total: {len(all_findings)} findings "
          f"(🔴 {high} high, 🟡 {medium} medium, 🟢 {low} low)")

    return {
        "dispatched":     dispatched,
        "files_reviewed": len(files),
        "total_findings": len(all_findings),
        "high":   high,
        "medium": medium,
        "low":    low
    }


def build_summary_comment(pr_title: str, dispatched: list, files: list) -> str:
    """Build the opening summary comment posted on the GitHub PR."""
    agent_labels = {
        "code_analyzer":    "🔍 Code Analyzer",
        "security_scanner": "🔒 Security Scanner",
        "test_evaluator":   "🧪 Test Evaluator",
        "fix_generator":    "🔧 Fix Generator"
    }
    priority_labels = {
        "high":   "🔴 High",
        "medium": "🟡 Medium",
        "low":    "🟢 Low"
    }
    rows = "\n".join([
        f"| {agent_labels.get(d['agent'], d['agent'])} "
        f"| {priority_labels.get(d['priority'], d['priority'])} "
        f"| {d['reason']} |"
        for d in dispatched
    ])
    return (
        f"## 🤖 Autonomous Code Review — Analysis Started\n\n"
        f"**PR:** {pr_title}  \n"
        f"**Files changed:** {len(files)}\n\n"
        f"| Agent | Priority | Focus |\n"
        f"|-------|----------|-------|\n"
        f"{rows}\n\n"
        f"*Inline comments will appear on specific lines shortly...*\n\n"
        f"---\n"
        f"*Powered by Groq LLaMA 3.3 70B · Autonomous Code Review Agent*"
    )