import os
import sys
import json
import asyncio

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ── Import test cases ────────────────────────────────
from eval.test_cases.sql_injection    import DIFF as SQL_DIFF,    EXPECTED as SQL_EXPECTED,    DESCRIPTION as SQL_DESC
from eval.test_cases.null_pointer     import DIFF as NULL_DIFF,   EXPECTED as NULL_EXPECTED,   DESCRIPTION as NULL_DESC
from eval.test_cases.hardcoded_secret import DIFF as SECRET_DIFF, EXPECTED as SECRET_EXPECTED, DESCRIPTION as SECRET_DESC
from eval.test_cases.clean_code       import DIFF as CLEAN_DIFF,  EXPECTED as CLEAN_EXPECTED,  DESCRIPTION as CLEAN_DESC

# ── Test suite ───────────────────────────────────────
TEST_CASES = [
    {
        "name":        "SQL Injection",
        "description": SQL_DESC,
        "diff":        SQL_DIFF,
        "expected":    SQL_EXPECTED,
        "agent":       "security_scanner",
    },
    {
        "name":        "Null Pointer / Error Handling",
        "description": NULL_DESC,
        "diff":        NULL_DIFF,
        "expected":    NULL_EXPECTED,
        "agent":       "code_analyzer",
    },
    {
        "name":        "Hardcoded Secrets",
        "description": SECRET_DESC,
        "diff":        SECRET_DIFF,
        "expected":    SECRET_EXPECTED,
        "agent":       "security_scanner",
    },
    {
        "name":        "Clean Code (false positive test)",
        "description": CLEAN_DESC,
        "diff":        CLEAN_DIFF,
        "expected":    CLEAN_EXPECTED,
        "agent":       "code_analyzer",
    },
]

# ── Agent system prompts ─────────────────────────────
CODE_ANALYZER_PROMPT = """You are an expert code reviewer.
Analyze the diff for bugs, code smells, and error handling issues.

IMPORTANT RULES:
- Only flag REAL issues — do not flag good practices as issues
- If code has proper null checks, type hints, and error handling — it is clean
- Do NOT flag code that already handles edge cases correctly
- Do NOT flag code just because it could theoretically be improved
- A function with proper validation and error handling is GOOD code

Reply ONLY with a valid JSON array. No explanation, no markdown.
If no issues return exactly: []
Format: [{"type": "bug", "message": "description", "line": 1}]
type must be one of: bug, smell, performance, style, error_handling"""

SECURITY_SCANNER_PROMPT = """You are an application security expert.
Analyze the diff for security vulnerabilities only.
Reply ONLY with a valid JSON array. No explanation, no markdown.
If no issues return [].
Format: [{"type": "sql_injection", "message": "description", "line": 1}]
type must be one of: sql_injection, hardcoded_secret, xss, path_traversal, broken_auth, insecure_deserialization"""


def run_agent(diff: str, agent: str) -> list:
    """Run a single agent on a diff and return findings."""
    prompt = (
        CODE_ANALYZER_PROMPT
        if agent == "code_analyzer"
        else SECURITY_SCANNER_PROMPT
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user",   "content": f"Analyze this diff:\n{diff}"}
        ],
        temperature=0.1,
        max_tokens=1000,
    )

    text = response.choices[0].message.content.strip()

    # Strip markdown fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        text  = "\n".join(lines).strip()

    # Extract JSON array
    start = text.find("[")
    end   = text.rfind("]") + 1
    if start == -1 or end == 0:
        return []

    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError:
        return []


def calculate_metrics(predicted_types: list, expected_types: list) -> dict:
    """
    Calculate precision, recall and F1 score.

    Precision = TP / (TP + FP)  — how many flagged issues were real
    Recall    = TP / (TP + FN)  — how many real issues were found
    F1        = 2 * P * R / (P + R) — balance of both
    """
    predicted = set(predicted_types)
    expected  = set(expected_types)

    tp = len(predicted & expected)   # correctly found
    fp = len(predicted - expected)   # wrongly flagged
    fn = len(expected - predicted)   # missed issues

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1        = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0 else 0.0
    )

    return {
        "tp":        tp,
        "fp":        fp,
        "fn":        fn,
        "precision": round(precision, 3),
        "recall":    round(recall, 3),
        "f1":        round(f1, 3),
    }


def print_separator(char="─", width=55):
    print(char * width)


def run_evaluation():
    """Run all test cases and print a full evaluation report."""

    print("\n")
    print_separator("═")
    print("  AUTONOMOUS CODE REVIEW AGENT — EVALUATION REPORT")
    print_separator("═")
    print(f"  Test cases : {len(TEST_CASES)}")
    print(f"  Model      : llama-3.3-70b-versatile (Groq)")
    print_separator("═")

    all_results     = []
    total_precision = []
    total_recall    = []
    total_f1        = []

    for i, case in enumerate(TEST_CASES, 1):
        print(f"\n[{i}/{len(TEST_CASES)}] {case['name']}")
        print_separator()
        print(f"  Description : {case['description']}")
        print(f"  Agent       : {case['agent']}")
        print(f"  Expected    : {case['expected'] or ['none (clean code)']}")

        # Run the agent
        print(f"  Running agent...")
        findings = run_agent(case["diff"], case["agent"])

        # Extract predicted issue types
        predicted_types = [f.get("type", "unknown") for f in findings]
        expected_types  = case["expected"]

        print(f"  Predicted   : {predicted_types or ['none']}")

        # Calculate metrics
        metrics = calculate_metrics(predicted_types, expected_types)

        # Print results
        status = "✅ PASS" if metrics["f1"] >= 0.5 else "❌ FAIL"
        print(f"  Result      : {status}")
        print(f"  Precision   : {metrics['precision']:.1%}")
        print(f"  Recall      : {metrics['recall']:.1%}")
        print(f"  F1 Score    : {metrics['f1']:.1%}")
        print(f"  TP:{metrics['tp']}  FP:{metrics['fp']}  FN:{metrics['fn']}")

        # Store for summary
        all_results.append({
            "name":      case["name"],
            "status":    status,
            "metrics":   metrics,
            "findings":  len(findings),
            "expected":  len(expected_types),
        })
        total_precision.append(metrics["precision"])
        total_recall.append(metrics["recall"])
        total_f1.append(metrics["f1"])

    # ── Overall Summary ──────────────────────────────
    avg_precision = sum(total_precision) / len(total_precision)
    avg_recall    = sum(total_recall)    / len(total_recall)
    avg_f1        = sum(total_f1)        / len(total_f1)
    passed        = sum(1 for r in all_results if "PASS" in r["status"])

    print("\n")
    print_separator("═")
    print("  OVERALL RESULTS")
    print_separator("═")
    print(f"  Tests passed  : {passed} / {len(TEST_CASES)}")
    print(f"  Avg Precision : {avg_precision:.1%}")
    print(f"  Avg Recall    : {avg_recall:.1%}")
    print(f"  Avg F1 Score  : {avg_f1:.1%}")
    print_separator("═")

    # ── Per-test summary table ───────────────────────
    print("\n  SUMMARY TABLE")
    print_separator()
    print(f"  {'Test Case':<35} {'Status':<8} {'F1':>6}")
    print_separator()
    for r in all_results:
        print(f"  {r['name']:<35} {r['status']:<8} {r['metrics']['f1']:.1%}")
    print_separator()

    # ── Resume line ──────────────────────────────────
    print(f"\n  RESUME BULLET:")
    print(f"  \"Built an autonomous multi-agent code review system")
    print(f"   achieving {avg_precision:.0%} precision and {avg_recall:.0%} recall")
    print(f"   on a {len(TEST_CASES)}-case labelled evaluation suite.\"")
    print_separator("═")
    print()

    return {
        "passed":        passed,
        "total":         len(TEST_CASES),
        "avg_precision": avg_precision,
        "avg_recall":    avg_recall,
        "avg_f1":        avg_f1,
    }


if __name__ == "__main__":
    run_evaluation()