
import streamlit as st
import pandas as pd
import sqlite3
import datetime

# ---------- DATABASE SETUP ----------
def create_db():
    conn = sqlite3.connect('task_allocation.db')
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY, 
                    name TEXT, 
                    passcode INTEGER)""")
    c.execute("""CREATE TABLE IF NOT EXISTS flights (
                    flight_id INTEGER PRIMARY KEY, 
                    flight_number TEXT, 
                    aircraft TEXT,
                    std TEXT,
                    status TEXT, 
                    assigned_user TEXT)""")
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
    c.execute("INSERT INTO flights (flight_number, aircraft, std, status, assigned_user) VALUES (?, ?, ?, 'unallocated', NULL)", 
              (flight_number, aircraft, std))
    conn.commit()
    conn.close()

def allocate_flight(flight_id, user_name):
    conn = sqlite3.connect('task_allocation.db')
    c = conn.cursor()
    c.execute("UPDATE flights SET status='allocated', assigned_user=? WHERE flight_id=?", (user_name, flight_id))
    conn.commit()
    conn.close()

def update_flight_status(flight_id, status):
    conn = sqlite3.connect('task_allocation.db')
    c = conn.cursor()
    c.execute("UPDATE flights SET status=? WHERE flight_id=?", (status, flight_id))
    conn.commit()
    conn.close()

def get_flights():
    conn = sqlite3.connect('task_allocation.db')
    c = conn.cursor()
    c.execute("SELECT * FROM flights")
    flights = c.fetchall()
    conn.close()
    return flights

# ---------- STYLING ----------
st.markdown("""
<style>
.stButton > button {
    font-size: 24px;
    height: 60px;
    width: 100%;
    border-radius: 8px;
}
.pin-container {
    display: flex;
    justify-content: center;
    flex-direction: column;
    align-items: center;
}
.keypad-row {
    display: flex;
    justify-content: center;
    margin: 5px;
}
.keypad-row button {
    margin: 5px;
    background-color: #e74c3c !important;
    color: white !important;
    width: 80px;
    height: 80px;
    font-size: 24px !important;
    border-radius: 10px !important;
}
input[type="text"] {
    font-size: 36px !important;
    text-align: center !important;
}
</style>
""", unsafe_allow_html=True)

# ---------- LANDING PAGE ----------
if 'passcode_entered' not in st.session_state:
    st.session_state.passcode_entered = ""
if 'user_type' not in st.session_state:
    st.session_state.user_type = None
if 'username' not in st.session_state:
    st.session_state.username = None

predefined_users = {
    "3320": "Admin",
    "0001": "Adam",
    "0002": "Tadj",
    "0003": "Darren",
}

def logout():
    st.session_state.passcode_entered = ""
    st.session_state.user_type = None
    st.session_state.username = None
    st.rerun()

def handle_keypress(value):
    if value == "CLR":
        st.session_state.passcode_entered = ""
    elif value == "DEL":
        st.session_state.passcode_entered = st.session_state.passcode_entered[:-1]
    else:
        if len(st.session_state.passcode_entered) < 4:
            st.session_state.passcode_entered += str(value)

if st.session_state.user_type is None:
    st.markdown('<div class="pin-container"><h2>Enter PIN Number</h2>', unsafe_allow_html=True)
    st.text_input("", value=st.session_state.passcode_entered, disabled=True, label_visibility="collapsed")

    keypad = [
        [7, 8, 9],
        [4, 5, 6],
        [1, 2, 3],
        ["CLR", 0, "DEL"]
    ]

    for row in keypad:
        cols = st.columns(3)
        for i, val in enumerate(row):
            with cols[i]:
                st.button(str(val), key=str(val), on_click=handle_keypress, args=(val,))

    if len(st.session_state.passcode_entered) == 4:
        code = st.session_state.passcode_entered
        user = predefined_users.get(code)
        if code == "3320":
            st.session_state.user_type = "admin"
            st.rerun()
        elif user:
            st.session_state.user_type = "user"
            st.session_state.username = user
            st.rerun()
        else:
            st.error("Invalid passcode")
            st.session_state.passcode_entered = ""
    st.markdown("</div>", unsafe_allow_html=True)
    st.button("Log Out", on_click=logout)

# ---------- ADMIN DASHBOARD ----------
elif st.session_state.user_type == "admin":
    st.title("🛠️ Admin Dashboard")

    tab1, tab2 = st.tabs(["Flights", "Users"])

    with tab1:
        st.subheader("📥 Import Flights from Excel")

        uploaded_file = st.file_uploader("Upload Movement Sheet", type=["xlsx"])
        if uploaded_file:
            try:
                excel_file = pd.ExcelFile(uploaded_file)
                all_data = []
                for sheet in ["INT", "DOM"]:
                    if sheet in excel_file.sheet_names:
                        df = excel_file.parse(sheet)
                        df = df.iloc[:, :11]
                        df = df[df.iloc[:, 8].notna()]
                        for _, row in df.iterrows():
                            flight_number = str(row.iloc[8])
                            aircraft = str(row.iloc[9]) if not pd.isna(row.iloc[9]) else "N/A"
                            std = str(row.iloc[10]) if not pd.isna(row.iloc[10]) else "N/A"
                            all_data.append((flight_number, aircraft, std))
                all_data.sort(key=lambda x: x[2])
                for flight_number, aircraft, std in all_data:
                    add_flight(flight_number, aircraft, std)
                st.success("Flights imported and sorted by STD.")
            except Exception as e:
                st.error(f"Failed to import: {e}")

        st.subheader("🛫 Flight Tasks")
        flights = get_flights()
        df = pd.DataFrame(flights, columns=["ID", "Flight", "A/C", "STD", "Status", "Assigned To"])
        st.dataframe(df.sort_values(by="STD"))

    with tab2:
        st.subheader("👤 Add User")
        name = st.text_input("Name")
        passcode = st.text_input("Passcode", type="password")
        if st.button("Add"):
            add_user(name, passcode)
            st.success("User added.")

    if st.button("Log Out"):
        logout()

# ---------- USER DASHBOARD ----------
elif st.session_state.user_type == "user":
    st.title(f"👋 Welcome, {st.session_state.username}")
    flights = get_flights()
    user_flights = [f for f in flights if f[5] == st.session_state.username]

    ongoing = [f for f in user_flights if f[4] != "completed"]
    history = [f for f in user_flights if f[4] == "completed"]

    tab1, tab2 = st.tabs(["🟢 Ongoing Tasks", "📜 History"])

    with tab1:
        for f in ongoing:
            with st.expander(f"{f[1]} — STD: {f[3]} — A/C: {f[2]}"):
                if st.button("✅ Push Complete", key=f"complete_{f[0]}"):
                    update_flight_status(f[0], "completed")
                    st.rerun()

    with tab2:
        for f in history:
            with st.expander(f"{f[1]} — STD: {f[3]} — A/C: {f[2]}"):
                if st.button("↩️ Mark as Incomplete", key=f"incomplete_{f[0]}"):
                    update_flight_status(f[0], "allocated")
                    st.rerun()

    if st.button("Log Out"):
        logout()
