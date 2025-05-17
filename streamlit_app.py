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

# Helper functions
def get_users():
    with sqlite3.connect('task_allocation.db') as conn:
        return conn.execute("SELECT id, name, passcode, active FROM users").fetchall()

def get_flights():
    with sqlite3.connect('task_allocation.db') as conn:
        return conn.execute("SELECT * FROM flights").fetchall()

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

# Login Page
if st.session_state.user_type is None:
    st.title("🔐 Login")
    st.write("Enter 4-digit passcode:")

    keypad = [["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"], ["Clear", "0", "⌫"]]
    cols = st.columns(3)
    for i, row in enumerate(keypad):
        for j, key in enumerate(row):
            if cols[j].button(key, key=f"{key}_{i}_{j}"):
                if key == "Clear":
                    st.session_state.passcode_entered = ""
                elif key == "⌫":
                    st.session_state.passcode_entered = st.session_state.passcode_entered[:-1]
                else:
                    if len(st.session_state.passcode_entered) < 4:
                        st.session_state.passcode_entered += key

    st.write(f"Entered: {'*' * len(st.session_state.passcode_entered)}")

    if len(st.session_state.passcode_entered) == 4:
        code = st.session_state.passcode_entered
        if code == "3320":
            st.session_state.user_type = "admin"
            st.rerun()
        else:
            user = authenticate_user(code)
            if user:
                st.session_state.user_type = "user"
                st.session_state.username = user[0]
                st.rerun()
            else:
                st.error("Invalid passcode")
                st.session_state.passcode_entered = ""

# Admin Dashboard
elif st.session_state.user_type == "admin":
    st.title("🛠 Admin Dashboard")

    tab1, tab2, tab3 = st.tabs(["Users", "Flights", "Logout"])

    with tab1:
        st.header("👥 Manage Users")
        users = get_users()
        for user in users:
            with st.expander(f"User: {user[1]}"):
                new_name = st.text_input("Edit Name", value=user[1], key=f"name_{user[0]}")
                new_code = st.text_input("Edit Passcode", value=str(user[2]), key=f"code_{user[0]}")
                col1, col2, col3 = st.columns(3)
                if col1.button("Update", key=f"update_{user[0]}"):
                    update_user(user[0], new_name, int(new_code))
                    st.success("User updated")
                    st.rerun()
                if col2.button("Toggle Active", key=f"toggle_{user[0]}"):
                    toggle_user_active(user[0], user[3])
                    st.success("User status updated")
                    st.rerun()
                if col3.button("Delete", key=f"delete_{user[0]}"):
                    delete_user(user[0])
                    st.success("User deleted")
                    st.rerun()

        st.subheader("➕ Add New User")
        name = st.text_input("New Username")
        passcode = st.text_input("New Passcode")
        if st.button("Add User"):
            if name and passcode.isdigit():
                add_user(name, int(passcode))
                st.success("User added")
                st.rerun()
            else:
                st.error("Enter valid name and numeric passcode")

    with tab2:
        st.header("📋 Manage Flights")

        uploaded_file = st.file_uploader("Upload Flight Schedule (.xlsx)", type="xlsx")
        if uploaded_file:
            df_dom = pd.read_excel(uploaded_file, sheet_name="DOM")
            df_int = pd.read_excel(uploaded_file, sheet_name="INT")
            combined_df = pd.concat([df_dom, df_int])
            for _, row in combined_df.iterrows():
                flight = str(row.iloc[8])
                aircraft = str(row.iloc[9])
                std = pd.to_datetime(row.iloc[10], errors='coerce')
                if pd.notna(std):
                    add_flight(flight, aircraft, std.isoformat())

        flights = get_flights()
        if flights:
            df = pd.DataFrame(flights, columns=["ID", "Flight", "A/C", "STD", "Status", "Assigned To"])
            df["STD"] = pd.to_datetime(df["STD"], errors='coerce')
            df = df.sort_values(by="STD")
            st.dataframe(df)

        st.subheader("✈️ Allocate Flight Tasks")
        for flight in [f for f in flights if f[4] == "unallocated"]:
            with st.expander(f"{flight[1]} — STD: {flight[3]} — A/C: {flight[2]}"):
                user_list = [u[1] for u in get_users() if u[3] == 1]
                selected_user = st.selectbox("Assign to", user_list, key=f"assign_{flight[0]}")
                if st.button("Assign", key=f"assign_btn_{flight[0]}"):
                    allocate_flight(flight[0], selected_user)
                    st.success(f"Assigned to {selected_user}")
                    st.rerun()

    with tab3:
        if st.button("Logout"):
            st.session_state.user_type = None
            st.session_state.passcode_entered = ""
            st.session_state.username = ""
            st.rerun()

# User Dashboard
elif st.session_state.user_type == "user":
    st.title(f"👤 {st.session_state.username}'s Dashboard")
    flights = get_flights()
    my_flights = [f for f in flights if f[5] == st.session_state.username]
    my_flights_df = pd.DataFrame(my_flights, columns=["ID", "Flight", "A/C", "STD", "Status", "Assigned To"])
    my_flights_df["STD"] = pd.to_datetime(my_flights_df["STD"], errors='coerce')
    my_flights_df = my_flights_df.sort_values(by="STD")
    st.dataframe(my_flights_df)

    st.subheader("🟢 Your Tasks")
    for flight in my_flights:
        with st.expander(f"{flight[1]} — STD: {flight[3]} — Status: {flight[4]}"):
            if flight[4] == "allocated":
                if st.button("Mark as Complete", key=f"complete_{flight[0]}"):
                    mark_complete(flight[0])
                    st.success("Task marked complete")
                    st.rerun()
            elif flight[4] == "completed":
                if st.button("Mark as Incomplete", key=f"incomplete_{flight[0]}"):
                    mark_incomplete(flight[0])
                    st.success("Task marked incomplete")
                    st.rerun()

    if st.button("Logout"):
        st.session_state.user_type = None
        st.session_state.username = ""
        st.session_state.passcode_entered = ""
        st.rerun()
