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
             username TEXT UNIQUE)''')

conn.commit()

# Helper functions
def insert_flight_tasks(flights):
    for flight in flights:
        c.execute("""INSERT INTO flight_tasks (flight_number, ac_type, std)
                     VALUES (?, ?, ?)""", (flight['flight_number'], flight['ac_type'], flight['std']))
    conn.commit()

def get_all_tasks():
    return pd.read_sql_query("SELECT * FROM flight_tasks ORDER BY std", conn)

def update_task_status(task_id, status):
    c.execute("UPDATE flight_tasks SET status = ? WHERE id = ?", (status, task_id))
    conn.commit()

def assign_task(task_id, username):
    c.execute("UPDATE flight_tasks SET assigned_to = ? WHERE id = ?", (username, task_id))
    conn.commit()

def get_users():
    return pd.read_sql_query("SELECT * FROM users", conn)

def add_user(username):
    try:
        c.execute("INSERT INTO users (username) VALUES (?)", (username,))
        conn.commit()
    except sqlite3.IntegrityError:
        st.warning("Username already exists!")

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
st.title("Flight Task Management Dashboard")

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
    new_user = st.text_input("Add a new user")
    if st.button("Add User"):
        if new_user:
            add_user(new_user)
            st.success(f"User '{new_user}' added.")
        else:
            st.warning("Please enter a username")

    st.subheader("Existing Users")
    users_df = get_users()
    st.dataframe(users_df)
