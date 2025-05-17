import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os

st.set_page_config(page_title="Flight Task Manager", layout="centered")

# Database setup
conn = sqlite3.connect("flight_tasks.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    active INTEGER DEFAULT 1
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flight_number TEXT,
    aircraft_type TEXT,
    std TEXT,
    assigned_to TEXT,
    complete INTEGER DEFAULT 0
)
""")
conn.commit()

# PIN-based login
st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("is_admin", False)

if not st.session_state.logged_in:
    st.title("🔐 Login")
    pin = st.text_input("Enter PIN:", type="password")
    if st.button("Login"):
        if pin == "3320":
            st.session_state.logged_in = True
            st.session_state.is_admin = True
        else:
            cursor.execute("SELECT * FROM users WHERE name = ? AND active = 1", (pin,))
            user = cursor.fetchone()
            if user:
                st.session_state.logged_in = True
                st.session_state.username = pin
            else:
                st.error("Invalid PIN or inactive user.")
    st.stop()

# Admin Interface
if st.session_state.get("is_admin"):
    st.sidebar.markdown("### Admin Menu")
    menu = st.sidebar.radio("", ["Users", "Flights", "Logout"])

    if menu == "Users":
        st.subheader("👥 Manage Users")

        with st.form("add_user_form"):
            new_user = st.text_input("New Username")
            submit = st.form_submit_button("Add User")
            if submit and new_user:
                try:
                    cursor.execute("INSERT INTO users (name) VALUES (?)", (new_user,))
                    conn.commit()
                    st.success(f"✅ User {new_user} added.")
                except:
                    st.error("⚠️ User already exists.")

        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()

        st.write("### 👥 Existing Users:")
        for uid, name, active in users:
            status = "✅ Active" if active else "❌ Inactive"
            st.write(f"{name} — {status}")
            if st.button(f"Toggle {name}", key=f"toggle_{uid}"):
                cursor.execute("UPDATE users SET active = ? WHERE id = ?", (1 - active, uid))
                conn.commit()
                st.rerun()

    elif menu == "Flights":
        st.subheader("🛫 Manage Flights")

        uploaded_file = st.file_uploader("Upload Flight Schedule (.xlsx)", type="xlsx")
        if uploaded_file:
            df_int = pd.read_excel(uploaded_file, sheet_name="INT", header=None)
            df_dom = pd.read_excel(uploaded_file, sheet_name="DOM", header=None)
            combined = pd.concat([df_int, df_dom], ignore_index=True)

            skipped = 0
            for idx, row in combined.iterrows():
                try:
                    flight_number = str(row[8]).strip()
                    aircraft_type = str(row[1]).strip()
                    std_raw = row[10]
                    if pd.isna(flight_number) or flight_number.lower() == "nan":
                        raise ValueError("Missing flight number")
                    std = pd.to_datetime(std_raw).strftime("%Y-%m-%d %H:%M")
                    cursor.execute("""
                        INSERT INTO tasks (flight_number, aircraft_type, std)
                        VALUES (?, ?, ?)
                    """, (flight_number, aircraft_type, std))
                except Exception as e:
                    st.warning(f"⚠️ Row {idx + 2} skipped due to error: {e}")
                    skipped += 1
            conn.commit()
            if skipped == 0:
                st.success("✅ All tasks imported successfully.")

        # Show and allocate tasks
        cursor.execute("SELECT * FROM tasks ORDER BY std")
        tasks = cursor.fetchall()
        st.write("### ✈️ Flight Tasks")
        for task in tasks:
            tid, fn, ac, std, assigned, complete = task
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
            col1.markdown(f"**{fn}**  \
                          Aircraft: {ac}  \
                          STD: {std}")
            cursor.execute("SELECT name FROM users WHERE active = 1")
            user_list = [u[0] for u in cursor.fetchall()]
            selected_user = col2.selectbox("Assign to", user_list, index=user_list.index(assigned) if assigned in user_list else 0, key=f"assign_{tid}")
            if selected_user != assigned:
                cursor.execute("UPDATE tasks SET assigned_to = ? WHERE id = ?", (selected_user, tid))
                conn.commit()
            if complete:
                col3.success("✅ Complete")
                if col4.button("Undo", key=f"undo_{tid}"):
                    cursor.execute("UPDATE tasks SET complete = 0 WHERE id = ?", (tid,))
                    conn.commit()
                    st.rerun()
            else:
                if col3.button("Push Complete", key=f"complete_{tid}"):
                    cursor.execute("UPDATE tasks SET complete = 1 WHERE id = ?", (tid,))
                    conn.commit()
                    st.rerun()

    elif menu == "Logout":
        st.session_state.logged_in = False
        st.session_state.is_admin = False
        st.rerun()

# User Dashboard
else:
    st.title(f"👋 Welcome, {st.session_state.username}")
    st.subheader("Your Assigned Tasks")

    cursor.execute("SELECT * FROM tasks WHERE assigned_to = ? ORDER BY std", (st.session_state.username,))
    tasks = cursor.fetchall()
    for task in tasks:
        tid, fn, ac, std, assigned, complete = task
        st.markdown(f"**Flight:** {fn}  \
                     Aircraft: {ac}  \
                     STD: {std}")
        if complete:
            st.success("✅ Complete")
            if st.button("Mark as Incomplete", key=f"incomplete_{tid}"):
                cursor.execute("UPDATE tasks SET complete = 0 WHERE id = ?", (tid,))
                conn.commit()
                st.rerun()
        else:
            if st.button("Mark Complete", key=f"usercomplete_{tid}"):
                cursor.execute("UPDATE tasks SET complete = 1 WHERE id = ?", (tid,))
                conn.commit()
                st.rerun()

    if st.button("Logout"):
        st.session_state.logged_in = False
        del st.session_state.username
        st.rerun()
