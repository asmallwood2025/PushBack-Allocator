import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# Database setup
conn = sqlite3.connect('task_allocation.db')
c = conn.cursor()

# Create necessary tables
c.execute("""CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY, 
                name TEXT, 
                passcode INTEGER,
                active INTEGER DEFAULT 1)""")

c.execute("""CREATE TABLE IF NOT EXISTS flights (
                id INTEGER PRIMARY KEY, 
                flight_number TEXT, 
                aircraft TEXT, 
                std TEXT, 
                status TEXT DEFAULT 'unallocated', 
                assigned_to TEXT)""")
conn.commit()

# Ensure 'active' column exists in 'users' table
try:
    c.execute("ALTER TABLE users ADD COLUMN active INTEGER DEFAULT 1")
    conn.commit()
except sqlite3.OperationalError:
    pass  # Column already exists

# Helper functions
def get_users():
    with sqlite3.connect('task_allocation.db') as conn:
        return conn.execute("SELECT id, name, passcode, active FROM users").fetchall()

def get_flights():
    with sqlite3.connect('task_allocation.db') as conn:
        return conn.execute("SELECT * FROM flights ORDER BY std").fetchall()

def flight_exists(flight_number, std):
    with sqlite3.connect('task_allocation.db') as conn:
        result = conn.execute("SELECT 1 FROM flights WHERE flight_number=? AND std=?", (flight_number, std)).fetchone()
        return result is not None

def add_user(name, passcode):
    with sqlite3.connect('task_allocation.db') as conn:
        conn.execute("INSERT INTO users (name, passcode, active) VALUES (?, ?, 1)", (name, passcode))
        conn.commit()

def update_user(user_id, name, passcode):
    with sqlite3.connect('task_allocation.db') as conn:
        conn.execute("UPDATE users SET name=?, passcode=? WHERE id=?", (name, passcode, user_id))
        conn.commit()

def toggle_user_active(user_id, current_status):
    with sqlite3.connect('task_allocation.db') as conn:
        conn.execute("UPDATE users SET active=? WHERE id=?", (0 if current_status else 1, user_id))
        conn.commit()

def delete_user(user_id):
    with sqlite3.connect('task_allocation.db') as conn:
        conn.execute("DELETE FROM users WHERE id=?", (user_id,))
        conn.commit()

def add_flight(flight_number, aircraft, std):
    with sqlite3.connect('task_allocation.db') as conn:
        conn.execute("INSERT INTO flights (flight_number, aircraft, std, status) VALUES (?, ?, ?, 'unallocated')",
                     (flight_number, aircraft, std))
        conn.commit()

def allocate_flight(flight_id, user):
    with sqlite3.connect('task_allocation.db') as conn:
        conn.execute("UPDATE flights SET assigned_to=?, status='allocated' WHERE id=?", (user, flight_id))
        conn.commit()

def mark_complete(flight_id):
    with sqlite3.connect('task_allocation.db') as conn:
        conn.execute("UPDATE flights SET status='completed' WHERE id=?", (flight_id,))
        conn.commit()

def mark_incomplete(flight_id):
    with sqlite3.connect('task_allocation.db') as conn:
        conn.execute("UPDATE flights SET status='allocated' WHERE id=?", (flight_id,))
        conn.commit()

def update_std(flight_id, new_std):
    with sqlite3.connect('task_allocation.db') as conn:
        conn.execute("UPDATE flights SET std=? WHERE id=?", (new_std, flight_id))
        conn.commit()

def authenticate_user(passcode):
    with sqlite3.connect('task_allocation.db') as conn:
        result = conn.execute("SELECT name FROM users WHERE passcode=? AND active=1", (passcode,)).fetchone()
    return result

# Session state initialization
if "user_type" not in st.session_state:
    st.session_state.user_type = None
if "username" not in st.session_state:
    st.session_state.username = ""
if "passcode_entered" not in st.session_state:
    st.session_state.passcode_entered = ""

# The rest of the app logic continues unchanged...
# (Not repeating full interface code here for brevity)
# Let me know if you'd like this full logic reincluded after the fix.
