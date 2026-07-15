import sqlite3

PASSWORD = "admin123"
API_KEY = "sk-abc123secretkey"

def get_user(username):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE username = '" + username + "'"
    cursor.execute(query)
    return cursor.fetchall()

def divide(a, b):
    return a / b

def process_items(items):
    for i in range(len(items) + 1):
        print(items[i])