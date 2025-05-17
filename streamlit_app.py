import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os

# --- DB Setup ---
conn = sqlite3.connect("flight_app.db", check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    active INTEGER DEFAULT 1
)''')

c.execute('''CREATE TABLE IF NOT EXISTS flights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flight_number TEXT,
    aircraft_type TEXT,
    std TEXT,
    assigned_to TEXT,
    complete INTEGER DEFAULT 0
)''')
conn.commit()

# --- Utility Functions ---
def get_users():
    return c.execute("SELECT username FROM users WHERE active=1").fetchall()

def get_all_users():
    return c.execute("SELECT username, active FROM users").fetchall()

def add_user(username):
    c.execute("INSERT OR IGNORE INTO users (username) VALUES (?)", (username,))
    conn.commit()

def toggle_user(username):
    current = c.execute("SELECT active FROM users WHERE username=?", (username,)).fetchone()[0]
    c.execute("UPDATE users SET active=? WHERE username=?", (0 if current else 1, username))
    conn.commit()

def insert_flight(flight_number, aircraft_type, std):
    c.execute("INSERT INTO flights (flight_number, aircraft_type, std) VALUES (?, ?, ?)",
              (flight_number, aircraft_type, std))
    conn.commit()

def get_flights(active_only=True):
    query = "SELECT * FROM flights"
    if active_only:
        query += " WHERE complete=0"
    query += " ORDER BY std"
    return c.execute(query).fetchall()

def assign_flight(flight_id, username):
    c.execute("UPDATE flights SET assigned_to=? WHERE id=?", (username, flight_id))
    conn.commit()

def mark_complete(flight_id):
    c.execute("UPDATE flights SET complete=1 WHERE id=?", (flight_id,))
    conn.commit()

def mark_incomplete(flight_id):
    c.execute("UPDATE flights SET complete=0 WHERE id=?", (flight_id,))
    conn.commit()

def delete_flight(flight_id):
    c.execute("DELETE FROM flights WHERE id=?", (flight_id,))
    conn.commit()

def delete_all_flights():
    c.execute("DELETE FROM flights")
    conn.commit()

# --- UI ---
st.set_page_config(page_title="Flight Allocation App", layout="centered")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Enter Access Code")
    pin = st.text_input("PIN", type="password")
    if pin == "3320":
        st.session_state.logged_in = True
        st.experimental_rerun()
    else:
        st.stop()

menu = st.sidebar.radio("", ["Users", "Flights", "History", "Logout"])

if menu == "Logout":
    st.session_state.logged_in = False
    st.experimental_rerun()

elif menu == "Users":
    st.header("👫 Manage Users")
    new_user = st.text_input("New Username")
    if st.button("Add User"):
        if new_user:
            add_user(new_user.strip().lower())
    st.markdown("---")
    for user, active in get_all_users():
        cols = st.columns([2, 1, 1])
        with cols[0]:
            st.markdown(f"**{user}**")
        with cols[1]:
            st.markdown("✅ Active" if active else "❌ Inactive")
        with cols[2]:
            if st.button("Toggle", key=f"toggle_{user}"):
                toggle_user(user)

elif menu == "Flights":
    st.header("🛫 Flight Tasks")
    uploaded_file = st.file_uploader("Upload Flight Schedule (.xlsx)", type=["xlsx"])

    if uploaded_file:
        df_int = pd.read_excel(uploaded_file, sheet_name="INT")
        df_dom = pd.read_excel(uploaded_file, sheet_name="DOM")

        for df in [df_int, df_dom]:
            for i, row in df.iterrows():
                try:
                    flight_number = str(row['I'])
                    aircraft = str(row['B'])
                    std = pd.to_datetime(row['K']).isoformat()
                    if flight_number and aircraft and std:
                        insert_flight(flight_number, aircraft, std)
                except Exception:
                    continue

        st.success("✅ Flights imported!")

    if st.button("❌ Delete All Flight Tasks"):
        delete_all_flights()
        st.experimental_rerun()

    flights = get_flights()
    users = [u[0] for u in get_users()]

    for flight in flights:
        fid, number, aircraft, std, assigned, complete = flight
        cols = st.columns([3, 2, 2, 2])
        with cols[0]:
            st.markdown(f"**{number}** Aircraft: {aircraft} STD: {std[:16]}")
        with cols[1]:
            user = st.selectbox("Assign to", users, index=users.index(assigned) if assigned in users else 0, key=f"assign_{fid}")
        with cols[2]:
            if st.button("Push Complete", key=f"complete_{fid}"):
                assign_flight(fid, user)
                mark_complete(fid)
                st.experimental_rerun()
        with cols[3]:
            if st.button("Delete", key=f"delete_{fid}"):
                delete_flight(fid)
                st.experimental_rerun()

elif menu == "History":
    st.header("📜 Completed Flight History")
    completed_flights = get_flights(active_only=False)
    for flight in completed_flights:
        fid, number, aircraft, std, assigned, complete = flight
        if complete:
            cols = st.columns([3, 2, 2])
            with cols[0]:
                st.markdown(f"**{number}** Aircraft: {aircraft} STD: {std[:16]} → {assigned}")
            with cols[1]:
                if st.button("Mark as Incomplete", key=f"undo_{fid}"):
                    mark_incomplete(fid)
                    st.experimental_rerun()
            with cols[2]:
                if st.button("Delete", key=f"hist_delete_{fid}"):
                    delete_flight(fid)
                    st.experimental_rerun()
