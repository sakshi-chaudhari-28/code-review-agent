import os
import json
from groq import Groq
from tools.github_tool import GitHubTool
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
github = GitHubTool()

SYSTEM_PROMPT = """You are a conservative QA engineer.

STRICT RULES:
- If the PR contains ONLY source code files (no test files) return []
- If functions already validate inputs with if/raise — they are tested enough
- Do NOT post one comment per function — maximum 1 comment per PR
- Only flag missing tests if the code has dangerous operations with NO validation

Return [] for most PRs that only add well-written source code.
Return [] if the code already handles edge cases.

Reply ONLY with JSON array, no markdown, no explanation.
Default response: []

Format only if critical test missing:
[{"file": "x.py", "line": 1, "severity": "low", "function": "name", "message": "what test"}]"""


def parse_findings(response_text: str) -> list:
    """Safely parse JSON findings from model response."""
    text = response_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        text = "\n".join(lines).strip()
    start = text.find("[")
    end   = text.rfind("]") + 1
    if start == -1 or end == 0:
        return []
    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError:
        return []


async def run(pr_data: dict, diff_text: str) -> list:
    """
    Evaluate test coverage in PR diff.
    Posts inline comments on GitHub for missing tests.
    """
    owner     = pr_data.get("base", {}).get("repo", {}).get("owner", {}).get("login")
    repo      = pr_data.get("base", {}).get("repo", {}).get("name")
    pr_number = pr_data.get("number")
    head_sha  = pr_data.get("head", {}).get("sha")

    print("[TEST EVALUATOR] Starting evaluation...")

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"Evaluate test coverage for this PR diff:\n\n{diff_text}"}
        ],
        temperature=0.1,
        max_tokens=1000,
    )

    findings = parse_findings(response.choices[0].message.content)
    print(f"[TEST EVALUATOR] Found {len(findings)} missing test(s)")

    # Post inline comment for each finding
    for f in findings:
        try:
            severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(f.get("severity", "medium"), "🟡")
            body = (
                f"{severity_emoji} **Missing Test Coverage**\n\n"
                f"**Function:** `{f.get('function', 'unknown')}`\n\n"
                f"{f.get('message', '')}\n\n"
                f"*— 🧪 Test Evaluator Agent*"
            )
            github.post_review_comment(
                owner, repo, pr_number,
                body=body,
                path=f.get("file", ""),
                line=int(f.get("line", 1)),
                commit_sha=head_sha
            )
            print(f"[TEST EVALUATOR] Posted comment on {f.get('file')} line {f.get('line')}")
        except Exception as e:
            print(f"[TEST EVALUATOR] Could not post comment: {e}")

    return findings