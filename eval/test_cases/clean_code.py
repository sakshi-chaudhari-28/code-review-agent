# Test case — clean well-written code
# Expected findings: empty — no issues should be found
# This tests that agents don't produce false positives

DIFF = """
FILE: utils/calculator.py (added, 20 changes)
DIFF:
@@ -0,0 +1,20 @@
+from typing import Optional
+
+def add(a: float, b: float) -> float:
+    return a + b
+
+def divide(a: float, b: float) -> Optional[float]:
+    if b == 0:
+        raise ValueError("Cannot divide by zero")
+    return a / b
+
+def get_username(user: dict) -> str:
+    if not user:
+        raise ValueError("User cannot be None")
+    profile = user.get("profile", {})
+    return profile.get("name", "unknown").upper()
+
+def process_items(items: list) -> list:
+    if not items:
+        return []
+    return [item for item in items if item is not None]
"""

# Expected: no issues — clean code
EXPECTED = []

DESCRIPTION = "Clean code with proper error handling and type hints"