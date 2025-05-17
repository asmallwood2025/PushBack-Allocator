# Full combined code for the updated Streamlit flight allocation app

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# ---------- DATABASE SETUP ----------
def create_db():
    conn = sqlite3.connect('task_allocation.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, passcode INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS flights (
                    flight_id INTEGER PRIMARY KEY,
                    flight_number TEXT,
                    aircraft TEXT,
                    std TEXT,
                    status TEXT,
                    assigned_user_id TEXT
                )''')
    conn.commit()
    conn.close()

create_db()

# ---------- DATABASE HELPERS ----------
def get_users():
    conn = sqlite3.connect('task_allocation.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    conn.close()
    return users

def add_user(name, passcode):
    conn = sqlite3.connect('task_allocation.db')
    c = conn.cursor()
    c.execute("INSERT INTO users (name, passcode) VALUES (?, ?)", (name, passcode))
    conn.commit()
    conn.close()

def add_flight(flight_number, aircraft, std):
    conn = sqlite3.connect('task_allocation.db')
    c = conn.cursor()
    c.execute("INSERT INTO flights (flight_number, aircraft, std, status) VALUES (?, ?, ?, 'unallocated')", 
              (flight_number, aircraft, std))
    conn.commit()
    conn.close()

def allocate_flight(flight_id, user_name):
    conn = sqlite3.connect('task_allocation.db')
    c = conn.cursor()
    c.execute("UPDATE flights SET status='allocated', assigned_user_id=? WHERE flight_id=?", (user_name, flight_id))
    conn.commit()
    conn.close()

def update_flight_status(flight_id, status):
    conn = sqlite3.connect('task_allocation.db')
    c = conn.cursor()
    c.execute("UPDATE flights SET status=? WHERE flight_id=?", (status, flight_id))
    conn.commit()
    conn.close()

def mark_flight_complete(flight_id):
    update_flight_status(flight_id, 'completed')

def mark_flight_incomplete(flight_id):
    update_flight_status(flight_id, 'allocated')

def get_flights():
    conn = sqlite3.connect('task_allocation.db')
    c = conn.cursor()
    c.execute("SELECT * FROM flights")
    flights = c.fetchall()
    conn.close()
    return flights

# ---------- STREAMLIT UI ----------
st.set_page_config(page_title="Flight Allocator", layout="centered")

# Custom CSS
st.markdown(
    """
    <style>
    .stButton > button {
        border-radius: 50%;
        width: 80px;
        height: 80px;
        font-size: 30px;
        background-color: red !important;
        color: white !important;
        margin: 10px;
    }
    .stTextInput > div > input {
        font-size: 24px;
        text-align: center;
    }
    .stTextInput {
        text-align: center;
        font-size: 20px;
    }
    .landing-container {
        display: flex;
        justify-content: center;
        align-items: flex-start;
        height: 100vh;
        text-align: center;
        margin-top: 10%;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------- LOGIN STATE ----------
if 'passcode_entered' not in st.session_state:
    st.session_state.passcode_entered = ""

predefined_users = {
    "3320": "Admin",
    "0001": "Adam",
    "0002": "Tadj",
    "0003": "Darren",
}

def handle_button_click(num):
    if len(st.session_state.passcode_entered) < 4:
        st.session_state.passcode_entered += str(num)
        if len(st.session_state.passcode_entered) == 4:
            st.rerun()

def logout():
    for key in ['passcode_entered', 'user_type', 'username']:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

# ---------- LOGIN PAGE ----------
if 'user_type' not in st.session_state:
    st.markdown('<div class="landing-container">', unsafe_allow_html=True)
    keypad_layout = [[1, 2, 3], [4, 5, 6], [7, 8, 9], [0]]
    cols = st.columns(3)
    for i, row in enumerate(keypad_layout):
        with cols[i % 3]:
            for num in row:
                st.button(str(num), key=f"btn{num}", on_click=handle_button_click, args=(num,))
    st.text_input("Entered Passcode", value=st.session_state.passcode_entered, disabled=True)

    if len(st.session_state.passcode_entered) == 4:
        user_passcode = st.session_state.passcode_entered
        user = predefined_users.get(user_passcode)
        if user_passcode == "3320":
            st.session_state.user_type = "admin"
            st.session_state.username = "Admin"
            st.rerun()
        elif user:
            st.session_state.user_type = "user"
            st.session_state.username = user
            st.rerun()
        else:
            st.session_state.passcode_entered = ""
            st.error("❌ Invalid passcode. Please try again.")
    st.markdown('</div>', unsafe_allow_html=True)

# ---------- ADMIN DASHBOARD ----------
elif st.session_state.get('user_type') == 'admin':
    st.title('Admin Dashboard')

    st.subheader("📂 Import Flight Data")
    uploaded_file = st.file_uploader("Upload Flight XLSX", type=["xlsx"])
    if uploaded_file:
        try:
            xl = pd.ExcelFile(uploaded_file)
            df_int = xl.parse('INT')
            df_dom = xl.parse('DOM')
            combined_df = pd.concat([df_int, df_dom])
            combined_df = combined_df[['I', 'J', 'K']]
            combined_df.columns = ['Flight Number', 'A/C', 'STD']
            combined_df = combined_df.dropna(subset=['Flight Number'])
            for _, row in combined_df.iterrows():
                add_flight(str(row['Flight Number']), str(row['A/C']), str(row['STD']))
            st.success("✅ Flights imported.")
        except Exception as e:
            st.error(f"❌ Failed to import: {e}")

    st.subheader("👥 Add New User")
    new_user_name = st.text_input("Name")
    new_user_passcode = st.text_input("Passcode", type="password")
    if st.button("Add User"):
        add_user(new_user_name, new_user_passcode)
        st.success(f"User {new_user_name} added.")

    st.subheader("✈️ Allocate Flights")
    flights_unallocated = [f for f in get_flights() if f[4] == 'unallocated']
    users = get_users()
    if flights_unallocated and users:
        flight_options = {f"{f[1]} | STD: {f[3]}": f[0] for f in flights_unallocated}
        user_options = {f"{u[1]} (PIN: {u[2]})": u[1] for u in users}
        selected_flight = st.selectbox("Flight", list(flight_options.keys()))
        selected_user = st.selectbox("User", list(user_options.keys()))
        if st.button("Allocate Flight"):
            allocate_flight(flight_options[selected_flight], user_options[selected_user])
            st.success("Flight allocated.")
            st.rerun()

    st.subheader("📋 All Flights")
    flights = sorted(get_flights(), key=lambda x: x[3] or "")
    for f in flights:
        st.write(f"🛫 {f[1]} | A/C: {f[2]} | STD: {f[3]} | Status: {f[4]} | Assigned: {f[5]}")

    if st.button("Log out"):
        logout()

# ---------- USER DASHBOARD ----------
elif st.session_state.get('user_type') == 'user':
    st.title(f"👨‍✈️ Welcome, {st.session_state.username}")
    flights = get_flights()
    active = [f for f in flights if f[5] == st.session_state.username and f[4] == 'allocated']
    completed = [f for f in flights if f[5] == st.session_state.username and f[4] == 'completed']

    st.subheader("🛠 Active Flights")
    if active:
        for f in active:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"✈️ {f[1]} | A/C: {f[2]} | STD: {f[3]}")
            with col2:
                if st.button("✅ Push Complete", key=f"comp_{f[0]}"):
                    mark_flight_complete(f[0])
                    st.rerun()
    else:
        st.info("No active flights.")

    st.subheader("📜 Flight History")
    if completed:
        for f in completed:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"✔️ {f[1]} | A/C: {f[2]} | STD: {f[3]}")
            with col2:
                if st.button("↩️ Mark Incomplete", key=f"inc_{f[0]}"):
                    mark_flight_incomplete(f[0])
                    st.rerun()
    else:
        st.info("No completed flights.")

    if st.button("Log out"):
        logout()
