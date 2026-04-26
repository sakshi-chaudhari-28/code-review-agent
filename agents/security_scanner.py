import os
import json
from groq import Groq
from tools.github_tool import GitHubTool
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
github = GitHubTool()

SYSTEM_PROMPT = """You are a security expert. Only flag DEFINITE vulnerabilities.

ONLY flag these specific patterns:
- SQL string concatenation: "WHERE x = '" + variable + "'"
- Hardcoded passwords: PASSWORD = "abc123"
- Hardcoded API keys: API_KEY = "sk-abc123"
- Hardcoded tokens: TOKEN = "hardcoded-value"
- eval() or exec() on user input
- subprocess with shell=True and user input

DO NOT flag:
- Parameterized queries — these are safe
- Environment variables — these are safe
- Hashed passwords — these are safe
- Any code that does NOT have the above patterns

Return [] for clean code with no hardcoded secrets or injection risks.

Reply ONLY with JSON array, no markdown, no explanation.
Default response: []

Format only if real vulnerability found:
[{"file": "x.py", "line": 1, "severity": "high", "type": "sql_injection", "owasp": "A03:2021", "message": "exact issue"}]"""


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
    Scan PR diff for security vulnerabilities.
    Posts inline comments on GitHub for each finding.
    """
    owner     = pr_data.get("base", {}).get("repo", {}).get("owner", {}).get("login")
    repo      = pr_data.get("base", {}).get("repo", {}).get("name")
    pr_number = pr_data.get("number")
    head_sha  = pr_data.get("head", {}).get("sha")

    print("[SECURITY SCANNER] Starting scan...")

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"Scan this PR diff for security issues:\n\n{diff_text}"}
        ],
        temperature=0.1,
        max_tokens=1000,
    )

    findings = parse_findings(response.choices[0].message.content)
    print(f"[SECURITY SCANNER] Found {len(findings)} vulnerability(s)")

    # Post inline comment for each finding
    for f in findings:
        try:
            body = (
                f"🔒 **Security Vulnerability [CRITICAL]**\n\n"
                f"**Type:** {f.get('type', 'unknown')}\n\n"
                f"**OWASP:** {f.get('owasp', 'N/A')}\n\n"
                f"{f.get('message', '')}\n\n"
                f"*— 🔒 Security Scanner Agent*"
            )
            github.post_review_comment(
                owner, repo, pr_number,
                body=body,
                path=f.get("file", ""),
                line=int(f.get("line", 1)),
                commit_sha=head_sha
            )
            print(f"[SECURITY SCANNER] Posted comment on {f.get('file')} line {f.get('line')}")
        except Exception as e:
            print(f"[SECURITY SCANNER] Could not post comment: {e}")

    return findings