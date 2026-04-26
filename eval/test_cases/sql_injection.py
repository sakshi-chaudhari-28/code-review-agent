# Test case — SQL injection vulnerability
# Expected findings: security_scanner should catch this

DIFF = """
FILE: users/db.py (added, 15 changes)
DIFF:
@@ -0,0 +1,15 @@
+import sqlite3
+
+def get_user(username):
+    conn = sqlite3.connect("users.db")
+    cursor = conn.cursor()
+    query = "SELECT * FROM users WHERE username = '" + username + "'"
+    cursor.execute(query)
+    return cursor.fetchall()
+
+def delete_user(user_id):
+    conn = sqlite3.connect("users.db")
+    cursor = conn.cursor()
+    query = "DELETE FROM users WHERE id = " + str(user_id)
+    cursor.execute(query)
+    conn.commit()
"""

# What we expect the agents to find
EXPECTED = [
    "sql_injection",
    "sql_injection",
]

DESCRIPTION = "SQL injection in raw string query concatenation"