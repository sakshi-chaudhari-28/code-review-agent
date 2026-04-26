# Test case — hardcoded secrets and credentials
# Expected findings: security_scanner should catch these

DIFF = """
FILE: config/settings.py (added, 12 changes)
DIFF:
@@ -0,0 +1,12 @@
+import requests
+
+DATABASE_URL = "postgresql://admin:password123@localhost/mydb"
+API_KEY = "sk-abc123xyz789secretkey"
+SECRET_KEY = "mysupersecretkey123"
+AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"
+
+def call_api(endpoint):
+    headers = {"Authorization": "Bearer hardcoded-token-here"}
+    response = requests.get(endpoint, headers=headers)
+    return response.json()
+
+DEBUG = True
"""

# What we expect the agents to find
EXPECTED = [
    "hardcoded_secret",
    "hardcoded_secret",
    "hardcoded_secret",
    "hardcoded_secret",
]

DESCRIPTION = "Hardcoded database URL, API keys, tokens and credentials"