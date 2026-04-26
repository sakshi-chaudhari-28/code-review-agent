import os
import json
from groq import Groq
from tools.github_tool import GitHubTool
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
github = GitHubTool()

SYSTEM_PROMPT = """You are a conservative code reviewer.

You ONLY flag code that has a DEFINITE bug that will cause a crash or wrong result.

ONLY flag these specific patterns:
- Division like "a / b" with NO if b == 0 check anywhere
- Array access like "items[i]" where i can equal len(items)
- String SQL concatenation like "WHERE x = '" + var + "'"
- Opening a file with open() but never calling .close()
- Using a variable that was never assigned

DO NOT flag ANY of these:
- Functions that have if/raise statements — they are already safe
- Type hints like "a: float" — this is good code
- Docstrings — this is good code
- Custom exception classes — this is good code
- Logging — this is good code
- Return statements — this is good code
- Functions that check inputs before using them
- Any code in payment.py, calculator.py, or clean files

MOST IMPORTANT RULE:
If a function has ANY validation (if not x, if x <= 0, if x == 0) 
it is SAFE — do NOT flag it.

Return [] for clean well-written code.
Return [] if you are not 100% certain there is a real bug.

Reply ONLY with JSON array, no markdown, no explanation.
Empty result: []

Format only if real bug found:
[{"file": "x.py", "line": 1, "severity": "high", "type": "bug", "message": "exact bug"}]"""


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
    Analyze PR diff for code quality issues.
    Posts inline comments on GitHub for each finding.
    """
    owner     = pr_data.get("base", {}).get("repo", {}).get("owner", {}).get("login")
    repo      = pr_data.get("base", {}).get("repo", {}).get("name")
    pr_number = pr_data.get("number")
    head_sha  = pr_data.get("head", {}).get("sha")

    print("[CODE ANALYZER] Starting analysis...")

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"Analyze this PR diff:\n\n{diff_text}"}
        ],
        temperature=0.1,
        max_tokens=1000,
    )

    findings = parse_findings(response.choices[0].message.content)
    print(f"[CODE ANALYZER] Found {len(findings)} issue(s)")

    # Post inline comment for each finding
    for f in findings:
        try:
            severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(f.get("severity", "low"), "🟢")
            body = (
                f"{severity_emoji} **Code Issue [{f.get('severity', 'low').upper()}]**\n\n"
                f"**Type:** {f.get('type', 'unknown')}\n\n"
                f"{f.get('message', '')}\n\n"
                f"*— 🔍 Code Analyzer Agent*"
            )
            github.post_review_comment(
                owner, repo, pr_number,
                body=body,
                path=f.get("file", ""),
                line=int(f.get("line", 1)),
                commit_sha=head_sha
            )
            print(f"[CODE ANALYZER] Posted comment on {f.get('file')} line {f.get('line')}")
        except Exception as e:
            print(f"[CODE ANALYZER] Could not post comment: {e}")

    return findings