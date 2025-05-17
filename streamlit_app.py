import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from io import BytesIO

# Database connection
conn = sqlite3.connect("flights.db", check_same_thread=False)
c = conn.cursor()

# Create tables
c.execute('''CREATE TABLE IF NOT EXISTS flight_tasks (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             flight_number TEXT,
             ac_type TEXT,
             std TEXT,
             status TEXT DEFAULT 'Incomplete',
             assigned_to TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS users (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             username TEXT UNIQUE,
             pin TEXT UNIQUE)''')

# Ensure 'pin' column exists (migration logic)
try:
    c.execute("ALTER TABLE users ADD COLUMN pin TEXT UNIQUE")
    conn.commit()
except sqlite3.OperationalError:
    pass  # Column already exists

conn.commit()

# Helper functions
def insert_flight_tasks(flights):
    for flight in flights:
        c.execute("""INSERT INTO flight_tasks (flight_number, ac_type, std)
                     VALUES (?, ?, ?)""", (flight['flight_number'], flight['ac_type'], flight['std']))
    conn.commit()

def get_all_tasks():
    return pd.read_sql_query("SELECT * FROM flight_tasks ORDER BY std", conn)

def get_tasks_for_user(username):
    return pd.read_sql_query("SELECT * FROM flight_tasks WHERE assigned_to = ? ORDER BY std", conn, params=(username,))

def update_task_status(task_id, status):
    c.execute("UPDATE flight_tasks SET status = ? WHERE id = ?", (status, task_id))
    conn.commit()

def assign_task(task_id, username):
    c.execute("UPDATE flight_tasks SET assigned_to = ? WHERE id = ?", (username, task_id))
    conn.commit()

def get_users():
    return pd.read_sql_query("SELECT * FROM users", conn)

def add_user(username, pin):
    try:
        c.execute("INSERT INTO users (username, pin) VALUES (?, ?)", (username, pin))
        conn.commit()
    except sqlite3.IntegrityError:
        st.warning("Username or PIN already exists!")

def delete_user(username):
    c.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()

def read_flights_from_excel(uploaded_file):
    xls = pd.ExcelFile(uploaded_file)
    flights = []
    for sheet in ['INT', 'DOM']:
        df = pd.read_excel(xls, sheet_name=sheet)
        for _, row in df.iterrows():
            flight_number = row.get('I')  # Column I
            ac_type = row.get('A/C')      # Column A/C
            std = row.get('STD')          # Column STD
            if pd.notna(flight_number) and pd.notna(ac_type) and pd.notna(std):
                std_str = std if isinstance(std, str) else std.strftime("%Y-%m-%d %H:%M:%S")
                flights.append({
                    'flight_number': str(flight_number),
                    'ac_type': str(ac_type),
                    'std': std_str
                })
    return flights

# UI starts here
st.set_page_config(page_title="Flight Task Management", layout="centered")
st.title("Flight Task Management")

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.pin_code = ""

if not st.session_state.authenticated:
    st.subheader("Enter PIN Number")

    col_input = st.empty()
    col_input.text_input("", value=st.session_state.pin_code, disabled=True, label_visibility="collapsed")

    pin_layout = [
        ["7", "8", "9"],
        ["4", "5", "6"],
        ["1", "2", "3"],
        ["CLR", "0", "DEL"]
    ]

    for row in pin_layout:
        cols = st.columns(3)
        for i, key in enumerate(row):
            if cols[i].button(key, use_container_width=True):
                if key == "CLR":
                    st.session_state.pin_code = ""
                elif key == "DEL":
                    st.session_state.pin_code = st.session_state.pin_code[:-1]
                else:
                    st.session_state.pin_code += key

    if len(st.session_state.pin_code) >= 4:
        pin_code = st.session_state.pin_code
        if pin_code == "3320":
            st.session_state.authenticated = True
            st.session_state.username = "admin"
        else:
            try:
                user_df = pd.read_sql_query("SELECT username FROM users WHERE pin = ?", conn, params=(pin_code,))
                if not user_df.empty:
                    st.session_state.authenticated = True
                    st.session_state.username = user_df.iloc[0]['username']
                else:
                    st.warning("Invalid PIN. Please try again.")
                    st.session_state.pin_code = ""
            except Exception as e:
                st.error("Login error occurred. Please try again.")
                st.session_state.pin_code = ""

    st.stop()

if st.button("Log Out"):
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.pin_code = ""
    st.rerun()

if st.session_state.username == "admin":
    st.success("Admin access granted")
    tabs = st.tabs(["Flights", "Users"])
    tab_flights, tab_users = tabs

    with tab_flights:
        st.subheader("Import Flights from Excel")
        uploaded_file = st.file_uploader("Choose an XLSX file", type="xlsx")
        if uploaded_file:
            flights = read_flights_from_excel(uploaded_file)
            insert_flight_tasks(flights)
            st.success("Flights imported successfully!")

        st.subheader("🟢 Ongoing Tasks")
        tasks_df = get_all_tasks()
        ongoing_tasks = tasks_df[tasks_df['status'] == 'Incomplete']
        for _, row in ongoing_tasks.iterrows():
            with st.expander(f"{row['flight_number']} | {row['ac_type']} | {row['std']}"):
                st.write(f"Assigned to: {row['assigned_to'] if row['assigned_to'] else 'Unassigned'}")
                users = get_users()['username'].tolist()
                selected_user = st.selectbox("Assign to:", ["Unassigned"] + users, key=f"assign_{row['id']}")
                if selected_user != "Unassigned":
                    assign_task(row['id'], selected_user)
                if st.button("Push Complete", key=f"complete_{row['id']}"):
                    update_task_status(row['id'], "Complete")
                    st.success("Marked as complete")

        st.subheader("📜 History")
        completed_tasks = tasks_df[tasks_df['status'] == 'Complete']
        st.dataframe(completed_tasks)

    with tab_users:
        st.subheader("User Management")
        new_user = st.text_input("Username")
        new_pin = st.text_input("PIN Code", type="password")
        if st.button("Add User"):
            if new_user and new_pin:
                add_user(new_user, new_pin)
                st.success(f"User '{new_user}' added.")
            else:
                st.warning("Please enter both username and PIN")

        st.subheader("Existing Users")
        users_df = get_users()
        st.dataframe(users_df)
        user_to_delete = st.selectbox("Delete user:", users_df['username'].tolist())
        if st.button("Delete User"):
            delete_user(user_to_delete)
            st.success(f"User '{user_to_delete}' deleted.")
else:
    username = st.session_state.username
    st.success(f"Welcome, {username}!")
    st.subheader("Your Assigned Flights")
    tasks_df = get_tasks_for_user(username)

    for _, row in tasks_df.iterrows():
        with st.expander(f"{row['flight_number']} | {row['ac_type']} | {row['std']}"):
            st.write(f"Status: {row['status']}")
            if row['status'] == 'Incomplete':
                if st.button("Mark as Complete", key=f"user_complete_{row['id']}"):
                    update_task_status(row['id'], "Complete")
                    st.success("Task marked complete")
