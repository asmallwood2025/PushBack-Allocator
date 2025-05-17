import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- Database setup ---
conn = sqlite3.connect('flight_tasks.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    active INTEGER
)''')

c.execute('''CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flight_number TEXT,
    aircraft TEXT,
    std TEXT,
    user_id INTEGER,
    completed INTEGER DEFAULT 0
)''')
conn.commit()

# --- Helper functions ---
def load_schedule(file):
    xls = pd.ExcelFile(file)
    flights = []
    for sheet in ['DOM', 'INT']:
        if sheet in xls.sheet_names:
            df = xls.parse(sheet)
            for _, row in df.iterrows():
                try:
                    flight = row['I']
                    ac = row['A/C']
                    std = pd.to_datetime(row['STD']).strftime('%Y-%m-%d %H:%M')
                    flights.append((flight, ac, std))
                except:
                    continue
    return flights

def add_tasks(flights):
    for flight, ac, std in flights:
        c.execute("INSERT INTO tasks (flight_number, aircraft, std) VALUES (?, ?, ?)", (flight, ac, std))
    conn.commit()

def get_tasks():
    c.execute("SELECT * FROM tasks ORDER BY std")
    return c.fetchall()

def get_users():
    c.execute("SELECT * FROM users")
    return c.fetchall()

# --- Login Page ---
def login_page():
    st.title("Enter Passcode")
    pin = st.session_state.get('pin', '')

    def handle_digit(d):
        st.session_state.pin = st.session_state.get('pin', '') + d

    def clear_pin():
        st.session_state.pin = ''

    st.write("Your passcode is required to enable Face ID")
    st.text(" ".join(["●" if i < len(pin) else "○" for i in range(4)]))

    cols = st.columns(3)
    for i in range(1, 10):
        if cols[(i - 1) % 3].button(str(i)):
            handle_digit(str(i))
    if cols[0].button("Clear"):
        clear_pin()
    if cols[1].button("0"):
        handle_digit("0")

    if len(pin) == 4:
        if pin == '3320':
            st.session_state.logged_in = True
        else:
            st.error("Incorrect PIN. Try again.")
            clear_pin()

# --- Admin Dashboard ---
def admin_dashboard():
    st.title("Admin Dashboard")
    tabs = st.tabs(["Users", "Flights"])

    with tabs[0]:
        st.subheader("User Management")
        name = st.text_input("User Name")
        if st.button("Add User"):
            c.execute("INSERT INTO users (name, active) VALUES (?, 1)", (name,))
            conn.commit()
        for user in get_users():
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                new_name = st.text_input(f"Edit {user[1]}", user[1], key=f"name_{user[0]}")
            with col2:
                if st.button("Update", key=f"update_{user[0]}"):
                    c.execute("UPDATE users SET name=? WHERE id=?", (new_name, user[0]))
                    conn.commit()
            with col3:
                if st.button("Delete", key=f"delete_{user[0]}"):
                    c.execute("DELETE FROM users WHERE id=?", (user[0],))
                    conn.commit()
            st.toggle("Active", value=bool(user[2]), key=f"toggle_{user[0]}", on_change=lambda uid=user[0]: c.execute("UPDATE users SET active=? WHERE id=?", (int(not user[2]), uid)) or conn.commit())

    with tabs[1]:
        st.subheader("Flight Task Management")
        uploaded = st.file_uploader("Upload Flight Schedule (XLSX)", type='xlsx')
        if uploaded:
            tasks = load_schedule(uploaded)
            add_tasks(tasks)
            st.success("Tasks Imported Successfully")

        st.subheader("Scheduled Tasks")
        for task in get_tasks():
            col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
            col1.text(task[1])  # flight number
            col2.text(task[2])  # aircraft
            std = col3.text_input("STD", task[3], key=f"std_{task[0]}")
            user_list = [(str(u[0]), u[1]) for u in get_users() if u[2] == 1]
            selected_user = col4.selectbox("Assign to", ["None"] + [u[1] for u in user_list], key=f"assign_{task[0]}")
            if st.button("Update Task", key=f"update_task_{task[0]}"):
                new_user_id = None
                for uid, uname in user_list:
                    if uname == selected_user:
                        new_user_id = uid
                c.execute("UPDATE tasks SET std=?, user_id=? WHERE id=?", (std, new_user_id, task[0]))
                conn.commit()

# --- User Dashboard ---
def user_dashboard(user_id):
    st.title("My Tasks")
    c.execute("SELECT * FROM tasks WHERE user_id=? AND completed=0 ORDER BY std", (user_id,))
    tasks = c.fetchall()
    for task in tasks:
        if st.button(f"Mark Complete: {task[1]}", key=f"done_{task[0]}"):
            c.execute("UPDATE tasks SET completed=1 WHERE id=?", (task[0],))
            conn.commit()
    st.subheader("Completed Tasks")
    c.execute("SELECT * FROM tasks WHERE user_id=? AND completed=1 ORDER BY std DESC", (user_id,))
    completed = c.fetchall()
    for task in completed:
        if st.button(f"Mark Incomplete: {task[1]}", key=f"undo_{task[0]}"):
            c.execute("UPDATE tasks SET completed=0 WHERE id=?", (task[0],))
            conn.commit()

# --- Main App ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login_page()
else:
    admin_dashboard()
