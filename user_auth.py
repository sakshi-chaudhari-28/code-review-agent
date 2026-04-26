import sqlite3
import hashlib

# Hardcoded credentials
DB_PASSWORD = "admin123"
SECRET_KEY = "mysecretkey456"

def login(username, password):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    # SQL injection vulnerability
    query = "SELECT * FROM users WHERE username='" + username + "' AND password='" + password + "'"
    cursor.execute(query)
    result = cursor.fetchone()
    return result

def get_user_data(user_id):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    # Another SQL injection
    cursor.execute("SELECT * FROM users WHERE id=" + str(user_id))
    return cursor.fetchall()
    # connection never closed

def calculate_discount(price, discount):
    # no zero/negative check
    return price / discount

def process_users(users):
    # off-by-one error
    for i in range(len(users) + 1):
        print(users[i])

def read_user_file(filename):
    # no error handling
    f = open(filename)
    data = f.read()
    return data