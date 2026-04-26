import os
import json
from groq import Groq
from tools.github_tool import GitHubTool
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
github = GitHubTool()

SYSTEM_PROMPT = """You are a senior developer generating code fixes for PR issues.

You will be given a PR diff and a list of findings from other agents.
For each HIGH severity finding, generate a concrete code fix.

Reply ONLY with a valid JSON array. No explanation, no markdown, no code fences.
If no fixes needed return an empty array: []

Format:
[
  {
    "file": "path/to/file.py",
    "line": 10,
    "original": "the problematic code snippet",
    "fixed": "the corrected code snippet",
    "explanation": "Why this fix resolves the issue"
  }
]

Rules:
- Only fix HIGH severity issues
- Keep fixes minimal — change only what is needed
- Preserve existing code style
- If you cannot determine exact line number use line 1."""


def parse_fixes(response_text: str) -> list:
    """Safely parse JSON fixes from model response."""
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


async def run(pr_data: dict, diff_text: str, findings: list) -> list:
    """
    Generate fixes for high severity findings.
    Posts fix suggestions as inline comments on GitHub.
    """
    owner     = pr_data.get("base", {}).get("repo", {}).get("owner", {}).get("login")
    repo      = pr_data.get("base", {}).get("repo", {}).get("name")
    pr_number = pr_data.get("number")
    head_sha  = pr_data.get("head", {}).get("sha")

    # Only run if there are high severity findings
    high_findings = [f for f in findings if f.get("severity") == "high"]
    if not high_findings:
        print("[FIX GENERATOR] No high severity findings — skipping")
        return []

    print(f"[FIX GENERATOR] Generating fixes for {len(high_findings)} high severity issue(s)...")

    findings_text = json.dumps(high_findings, indent=2)

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"PR diff:\n{diff_text}\n\nHigh severity findings:\n{findings_text}"}
        ],
        temperature=0.1,
        max_tokens=1500,
    )

    fixes = parse_fixes(response.choices[0].message.content)
    print(f"[FIX GENERATOR] Generated {len(fixes)} fix(es)")

    # Post each fix as an inline comment
    for fix in fixes:
        try:
            body = (
                f"🔧 **Suggested Fix**\n\n"
                f"**Issue on this line:**\n"
                f"```\n{fix.get('original', '')}\n```\n\n"
                f"**Suggested fix:**\n"
                f"```\n{fix.get('fixed', '')}\n```\n\n"
                f"**Why:** {fix.get('explanation', '')}\n\n"
                f"*— 🔧 Fix Generator Agent*"
            )
            github.post_review_comment(
                owner, repo, pr_number,
                body=body,
                path=fix.get("file", ""),
                line=int(fix.get("line", 1)),
                commit_sha=head_sha
            )
            print(f"[FIX GENERATOR] Posted fix on {fix.get('file')} line {fix.get('line')}")
        except Exception as e:
            print(f"[FIX GENERATOR] Could not post fix: {e}")

    return fixes