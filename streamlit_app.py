import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import base64
import io

# Constants
ADMIN_PIN = "3320"

# Database setup
conn = sqlite3.connect('flight_tasks.db', check_same_thread=False)
c = conn.cursor()

# Create tables
c.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                pin TEXT,
                active INTEGER DEFAULT 1
            )''')

c.execute('''CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                flight_number TEXT,
                aircraft TEXT,
                std TEXT,
                status TEXT DEFAULT 'incomplete',
                assigned_to TEXT
            )''')

conn.commit()

# Helper Functions
def add_user(name, pin):
    c.execute("INSERT INTO users (name, pin) VALUES (?, ?)", (name, pin))
    conn.commit()

def get_users():
    c.execute("SELECT * FROM users")
    return c.fetchall()

def delete_user(user_id):
    c.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()

def toggle_user_status(user_id, active):
    c.execute("UPDATE users SET active = ? WHERE id = ?", (active, user_id))
    conn.commit()

def import_tasks_from_excel(file):
    df_dom = pd.read_excel(file, sheet_name="DOM")
    df_int = pd.read_excel(file, sheet_name="INT")

    def extract_tasks(df):
        df = df.iloc[1:]  # Skip header row
        tasks = []
        for _, row in df.iterrows():
            flight = str(row[8]).strip() if not pd.isna(row[8]) else ""
            aircraft = str(row[9]).strip() if not pd.isna(row[9]) else ""
            std = row[11] if not pd.isna(row[11]) else None
            if flight and aircraft and std:
                try:
                    std_time = pd.to_datetime(std)
                    tasks.append((flight, aircraft, std_time.strftime("%Y-%m-%d %H:%M:%S")))
                except:
                    continue
        return tasks

    tasks = extract_tasks(df_dom) + extract_tasks(df_int)
    for flight, aircraft, std in tasks:
        c.execute("INSERT INTO tasks (flight_number, aircraft, std) VALUES (?, ?, ?)", (flight, aircraft, std))
    conn.commit()

def get_all_tasks():
    c.execute("SELECT * FROM tasks WHERE status = 'incomplete' ORDER BY std")
    return c.fetchall()

def get_task_history():
    c.execute("SELECT * FROM tasks WHERE status = 'complete' ORDER BY std DESC")
    return c.fetchall()

def assign_task(task_id, user):
    c.execute("UPDATE tasks SET assigned_to = ? WHERE id = ?", (user, task_id))
    conn.commit()

def complete_task(task_id):
    c.execute("UPDATE tasks SET status = 'complete' WHERE id = ?", (task_id,))
    conn.commit()

def undo_task(task_id):
    c.execute("UPDATE tasks SET status = 'incomplete' WHERE id = ?", (task_id,))
    conn.commit()

def delete_task(task_id):
    c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()

def delete_all_tasks():
    c.execute("DELETE FROM tasks")
    conn.commit()

def get_user_tasks(name):
    c.execute("SELECT * FROM tasks WHERE assigned_to = ? AND status = 'incomplete' ORDER BY std", (name,))
    return c.fetchall()

def get_user_task_history(name):
    c.execute("SELECT * FROM tasks WHERE assigned_to = ? AND status = 'complete' ORDER BY std DESC", (name,))
    return c.fetchall()

# UI
st.set_page_config(layout="wide")
st.title("Flight Task Allocator")

# PIN Login
pin_input = st.text_input("Enter 4-digit PIN", type="password")

if pin_input == ADMIN_PIN:
    tab1, tab2, tab3, tab4 = st.tabs(["Users", "Flights", "Assign", "History"])

    with tab1:
        st.header("User Management")
        name = st.text_input("Name")
        pin = st.text_input("4-digit PIN", max_chars=4)
        if st.button("Add User"):
            if name and pin:
                add_user(name, pin)
                st.success("User added!")
        users = get_users()
        for user in users:
            col1, col2, col3, col4 = st.columns(4)
            col1.write(user[1])
            col2.write("Active" if user[3] else "Inactive")
            if col3.button("Toggle Active", key=f"toggle_{user[0]}"):
                toggle_user_status(user[0], 0 if user[3] else 1)
            if col4.button("Delete", key=f"delete_{user[0]}"):
                delete_user(user[0])
                st.experimental_rerun()

    with tab2:
        st.header("Import Flight Tasks")
        uploaded_file = st.file_uploader("Upload Flight Schedule (XLSX)", type="xlsx")
        if uploaded_file:
            import_tasks_from_excel(uploaded_file)
            st.success("Tasks imported!")

        st.subheader("All Tasks")
        tasks = get_all_tasks()
        for task in tasks:
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            col1.write(task[1])  # Flight Number
            col2.write(task[2])  # A/C
            col3.write(task[3])  # STD
            col4.write(task[5] if task[5] else "Unassigned")
            if col5.button("Complete", key=f"complete_{task[0]}"):
                complete_task(task[0])
                st.experimental_rerun()
            if col6.button("Delete", key=f"delete_{task[0]}"):
                delete_task(task[0])
                st.experimental_rerun()

        if st.button("Delete All Tasks"):
            delete_all_tasks()
            st.experimental_rerun()

    with tab3:
        st.header("Assign Tasks")
        tasks = get_all_tasks()
        users = [user[1] for user in get_users() if user[3] == 1]
        for task in tasks:
            col1, col2 = st.columns([2, 1])
            col1.write(f"{task[1]} - {task[2]} - {task[3]}")
            selected_user = col2.selectbox("Assign to", users, index=users.index(task[5]) if task[5] in users else 0, key=f"assign_{task[0]}")
            if selected_user != task[5]:
                assign_task(task[0], selected_user)

    with tab4:
        st.header("Completed Tasks History")
        history = get_task_history()
        for task in history:
            col1, col2, col3, col4 = st.columns(4)
            col1.write(task[1])  # Flight Number
            col2.write(task[2])  # A/C
            col3.write(task[3])  # STD
            if col4.button("Mark as Incomplete", key=f"undo_{task[0]}"):
                undo_task(task[0])
                st.experimental_rerun()

elif pin_input:
    # Check if user exists
    users = get_users()
    user_dict = {user[2]: user[1] for user in users if user[3] == 1}
    if pin_input in user_dict:
        name = user_dict[pin_input]
        st.header(f"Welcome {name}")

        tab1, tab2, tab3 = st.tabs(["Tasks", "Future Tasks", "History"])

        with tab1:
            st.subheader("Current and Next Task")
            tasks = get_user_tasks(name)
            for task in tasks[:2]:
                st.markdown(f"### {task[1]} - {task[2]} - {task[3]}")
                if st.button("Mark as Complete", key=f"user_complete_{task[0]}"):
                    complete_task(task[0])
                    st.experimental_rerun()

        with tab2:
            st.subheader("Future Tasks")
            tasks = get_user_tasks(name)
            for task in tasks[2:]:
                st.write(f"{task[1]} - {task[2]} - {task[3]}")

        with tab3:
            st.subheader("Completed Tasks")
            history = get_user_task_history(name)
            for task in history:
                st.write(f"{task[1]} - {task[2]} - {task[3]}")
                if st.button("Undo Complete", key=f"user_undo_{task[0]}"):
                    undo_task(task[0])
                    st.experimental_rerun()
    else:
        st.error("Invalid PIN or inactive user.")
