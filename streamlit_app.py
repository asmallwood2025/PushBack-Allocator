import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# Connect to SQLite DB
conn = sqlite3.connect("flight_tasks.db", check_same_thread=False)
cursor = conn.cursor()

# Create tables if not exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS flights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        flight_number TEXT,
        aircraft TEXT,
        std TEXT,
        allocated_to TEXT,
        status TEXT DEFAULT 'Incomplete'
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        active INTEGER DEFAULT 1
    )
''')
conn.commit()

# ============ Admin Portal ============

def upload_flight_schedule():
    st.subheader("📄 Manage Flights")
    uploaded_file = st.file_uploader("Upload Flight Schedule (.xlsx)", type=["xlsx"])
    
    if uploaded_file:
        st.success(f"✅ Uploaded: {uploaded_file.name}")
        try:
            dom_df = pd.read_excel(uploaded_file, sheet_name="DOM", header=None)
            int_df = pd.read_excel(uploaded_file, sheet_name="INT", header=None)

            combined_df = pd.concat([dom_df, int_df], ignore_index=True)

            st.write("📋 Preview of combined sheet:")
            st.dataframe(combined_df.head())

            new_flights = []
            for i, row in combined_df.iterrows():
                try:
                    flight_number = str(row.iloc[8]).strip().upper()  # Column I
                    aircraft = str(row.iloc[1]).strip()               # Column B
                    std_raw = row.iloc[10]                            # Column K

                    # Convert STD to string time
                    std = pd.to_datetime(std_raw).strftime('%Y-%m-%d %H:%M:%S')

                    cursor.execute('''
                        INSERT INTO flights (flight_number, aircraft, std)
                        VALUES (?, ?, ?)
                    ''', (flight_number, aircraft, std))
                    new_flights.append(flight_number)
                except Exception as e:
                    st.warning(f"⚠️ Row {i+1} skipped due to error: {e}")
            conn.commit()

            st.success(f"✅ Added {len(new_flights)} new flights.")
        except Exception as e:
            st.error(f"❌ Failed to process file: {e}")

    # Display all flights sorted by STD
    st.markdown("### ✈️ Current Flights")
    cursor.execute("SELECT * FROM flights ORDER BY std ASC")
    flights = cursor.fetchall()

    if flights:
        for flight in flights:
            fid, flight_number, aircraft, std, allocated_to, status = flight
            with st.expander(f"{flight_number} ({aircraft}) – {std}"):
                st.write(f"**Aircraft:** {aircraft}")
                st.write(f"**STD:** {std}")
                st.write(f"**Allocated To:** {allocated_to or 'Unassigned'}")
                st.write(f"**Status:** {status}")

                # Allocation dropdown
                cursor.execute("SELECT name FROM users WHERE active = 1")
                active_users = [u[0] for u in cursor.fetchall()]
                selected_user = st.selectbox(f"Assign to user:", active_users, key=f"user_{fid}")
                if st.button("Allocate", key=f"alloc_{fid}"):
                    cursor.execute("UPDATE flights SET allocated_to = ? WHERE id = ?", (selected_user, fid))
                    conn.commit()
                    st.success(f"✅ Allocated to {selected_user}")

                # Task completion
                if status == 'Incomplete':
                    if st.button("✔️ Mark as Complete", key=f"complete_{fid}"):
                        cursor.execute("UPDATE flights SET status = 'Complete' WHERE id = ?", (fid,))
                        conn.commit()
                        st.success("✅ Task marked as complete")
                else:
                    if st.button("↩️ Mark as Incomplete", key=f"incomplete_{fid}"):
                        cursor.execute("UPDATE flights SET status = 'Incomplete' WHERE id = ?", (fid,))
                        conn.commit()
                        st.info("🔄 Task reverted to incomplete")

# ============ User Portal ============

def user_dashboard(username):
    st.subheader(f"👤 Welcome, {username}")
    cursor.execute("SELECT * FROM flights WHERE allocated_to = ? ORDER BY std ASC", (username,))
    tasks = cursor.fetchall()

    if tasks:
        for task in tasks:
            fid, flight_number, aircraft, std, _, status = task
            with st.expander(f"{flight_number} – {std}"):
                st.write(f"**Aircraft:** {aircraft}")
                st.write(f"**STD:** {std}")
                st.write(f"**Status:** {status}")

                if status == 'Incomplete':
                    if st.button("✔️ Complete Task", key=f"user_complete_{fid}"):
                        cursor.execute("UPDATE flights SET status = 'Complete' WHERE id = ?", (fid,))
                        conn.commit()
                        st.success("✅ Task completed")
                else:
                    if st.button("↩️ Undo Completion", key=f"user_incomplete_{fid}"):
                        cursor.execute("UPDATE flights SET status = 'Incomplete' WHERE id = ?", (fid,))
                        conn.commit()
                        st.info("🔄 Task reverted")

    else:
        st.info("📭 No tasks assigned yet.")

# ============ Login Page ============

def login():
    st.title("🔐 Flight Task Allocation")
    pin = st.text_input("Enter Access PIN", type="password")

    if st.button("Login"):
        if pin == "3320":
            st.session_state.role = "admin"
        else:
            cursor.execute("SELECT name FROM users WHERE name = ?", (pin,))
            result = cursor.fetchone()
            if result:
                st.session_state.role = "user"
                st.session_state.username = result[0]
            else:
                st.error("❌ Invalid PIN or User not found")

# ============ Main App ============

def main():
    if "role" not in st.session_state:
        login()
    else:
        if st.session_state.role == "admin":
            menu = st.sidebar.radio("Admin Menu", ["Users", "Flights", "Logout"])
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
                for uid, name, active in users:
                    col1, col2, col3 = st.columns(3)
                    col1.write(name)
                    col2.write("✅ Active" if active else "❌ Inactive")
                    if col3.button("Toggle", key=f"toggle_{uid}"):
                        cursor.execute("UPDATE users SET active = ? WHERE id = ?", (1 - active, uid))
                        conn.commit()
                        st.rerun()

            elif menu == "Flights":
                upload_flight_schedule()
            elif menu == "Logout":
                st.session_state.clear()
                st.rerun()

        elif st.session_state.role == "user":
            user_dashboard(st.session_state.username)
            if st.button("Logout"):
                st.session_state.clear()
                st.rerun()

if __name__ == "__main__":
    main()

