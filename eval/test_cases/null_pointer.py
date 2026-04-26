# Test case — null pointer / missing error handling
# Expected findings: code_analyzer should catch these

DIFF = """
FILE: utils/processor.py (added, 20 changes)
DIFF:
@@ -0,0 +1,20 @@
+def process_order(order):
+    total = order["items"] * order["price"]
+    return total
+
+def get_username(user):
+    return user["profile"]["name"].upper()
+
+def divide_scores(a, b):
+    return a / b
+
+def read_config():
+    with open("config.json") as f:
+        data = f.read()
+    return data
+
+def process_list(items):
+    for i in range(len(items) + 1):
+        print(items[i])
"""

# What we expect the agents to find
EXPECTED = [
    "bug",
    "bug",
    "bug",
    "error_handling",
]

DESCRIPTION = "Missing null checks, zero division, off-by-one error"