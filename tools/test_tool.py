# tools/test_tool.py
from github_tool import GitHubTool

tool = GitHubTool()

# Replace with your actual values
OWNER  = "sakshi-chaudhari-28"
REPO   = "code-review-agent"
PR_NUM = 1           # the test PR you opened in Step 1

# Test 1 — get PR details
print("=== PR DETAILS ===")
details = tool.get_pr_details(OWNER, REPO, PR_NUM)
print(details)

# Test 2 — get changed files
print("\n=== CHANGED FILES ===")
files = tool.get_pr_files(OWNER, REPO, PR_NUM)
for f in files:
    print(f"  {f['status']} — {f['filename']} ({f['changes']} changes)")
    if f['patch']:
        print(f"  diff preview: {f['patch'][:100]}...")