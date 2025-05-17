import streamlit as st
import pandas as pd
import sqlite3

# ---------- DATABASE SETUP ----------
def create_db():
    conn = sqlite3.connect('task_allocation.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, passcode INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS flights (flight_id INTEGER PRIMARY KEY, flight_number TEXT, status TEXT, assigned_user_id INTEGER)''')
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

def add_flight(flight_number):
    conn = sqlite3.connect('task_allocation.db')
    c = conn.cursor()
    c.execute("INSERT INTO flights (flight_number, status) VALUES (?, 'unallocated')", (flight_number,))
    conn.commit()
    conn.close()

def allocate_flight(flight_id, user_id):
    conn = sqlite3.connect('task_allocation.db')
    c = conn.cursor()
    c.execute("UPDATE flights SET status='allocated', assigned_user_id=? WHERE flight_id=?", (user_id, flight_id))
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

def get_user_by_passcode(passcode):
    conn = sqlite3.connect('task_allocation.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE passcode=?", (passcode,))
    user = c.fetchone()
    conn.close()
    return user

# ---------- STREAMLIT INTERFACE ----------
st.set_page_config(page_title="Flight Allocator", layout="centered")

# Add the missing triple-quote closure
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
    .stSelectbox {
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
    .pin-container {
        display: flex;
        justify-content: center;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------- USER REGISTRATION FOR THE FIRST TIME ----------
# Predefined Users for Admin
predefined_users = {
    "3320": "Admin",
    "0001": "Adam",
    "0002": "Tadj",
    "0003": "Darren",
}

# ---------- LANDING PAGE - PASSCODE ENTRY ----------
if 'passcode_entered' not in st.session_state:
    st.session_state.passcode_entered = ""

def handle_button_click(num):
    if len(st.session_state.passcode_entered) < 4:
        st.session_state.passcode_entered += str(num)
        if len(st.session_state.passcode_entered) == 4:
            st.experimental_rerun()

def logout():
    st.session_state.passcode_entered = ""
    st.session_state.user_type = None
    st.session_state.username = None
    st.experimental_rerun()

# Center the login page and keypad
with st.container():
    st.markdown('<div class="landing-container">', unsafe_allow_html=True)
    
    # Display passcode input with grid layout for numbers 0-9
    keypad_layout = [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
        [0]
    ]
    
    cols = st.columns(3)
    for i, row in enumerate(keypad_layout):
        with cols[i % 3]:  # Wrap each row with columns
            for num in row:
                st.button(str(num), key=f"btn{num}", on_click=handle_button_click, args=(num,))
    
    st.text_input("Entered Passcode", value=st.session_state.passcode_entered, disabled=True)
    
    if len(st.session_state.passcode_entered) == 4:
        user_passcode = st.session_state.passcode_entered
        user = predefined_users.get(user_passcode)
        
        if user_passcode == "3320":
            st.session_state.user_type = "admin"
            st.experimental_rerun()
        elif user:
            st.session_state.user_type = "user"
            st.session_state.username = user
            st.experimental_rerun()
        else:
            st.session_state.passcode_entered = ""
            st.error("❌ Invalid passcode. Please try again.")
    
    st.markdown('</div>', unsafe_allow_html=True)

# ---------- ADMIN INTERFACE ----------
if st.session_state.get('user_type') == 'admin':
    st.title('Admin Dashboard')
    st.subheader('👨‍✈️ Admin Interface')

    uploaded_file = st.file_uploader("Upload Flight File (CSV or Excel)", type=["csv", "xlsx"])

    if uploaded_file is not None:
        try:
            st.write("Debug: File uploaded.")
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)

            st.write("Debug: File loaded successfully:")
            st.write(df.head())  # Show the first few rows for debugging

            for flight_number in df.iloc[:, 0]:  # Assuming flight numbers are in the first column
                add_flight(str(flight_number))
            st.success("✅ Flights uploaded successfully.")

        except Exception as e:
            st.error(f"Error processing file: {e}")
            st.write(f"Debug: Error - {e}")

    # Add new user form
    st.markdown("### Add New User")
    new_user_name = st.text_input("User Name")
    new_user_passcode = st.text_input("User Passcode", type="password")
    
    if new_user_name and new_user_passcode:
        if st.button("Add User"):
            try:
                add_user(new_user_name, new_user_passcode)
                st.success(f"✅ User {new_user_name} added successfully.")
            except Exception as e:
                st.error(f"❌ Error adding user: {e}")
    
    st.markdown("### Allocate Flights")
    flights = get_flights()
    unallocated = [f for f in flights if f[3] is None]

    if unallocated:
        flight_selection = st.selectbox('Select flight to allocate:', [f"{f[1]} (ID: {f[0]})" for f in unallocated])
        users = get_users()
        user_selection = st.selectbox('Select user to assign:', [f"{u[1]} (Passcode: {u[2]})" for u in users])
        
        if st.button("Allocate Flight"):
            flight_id = int(flight_selection.split("ID: ")[1].replace(")", ""))
            user_id = int(user_selection.split(" (")[0])
            allocate_flight(flight_id, user_id)
            st.success("✅ Flight allocated.")
            st.experimental_rerun()

    st.markdown("### Update Flight Status")
    all_flights = get_flights()

    if all_flights:
        flight_update = st.selectbox("Choose a flight", [f"{f[1]} (ID: {f[0]}, Status: {f[2]})" for f in all_flights])
        new_status = st.selectbox("New status", ['unallocated', 'allocated', 'completed', 'delayed'])
        if st.button("Update Status"):
            flight_id = int(flight_update.split("ID: ")[1].split(",")[0])
            update_flight_status(flight_id, new_status)
            st.success("✅ Flight status updated.")
            st.experimental_rerun()
    else:
        st.info("No flights found.")
    
    # Log out button
    if st.button('Log out'):
        logout()

# ---------- USER INTERFACE ----------
elif st.session_state.get('user_type') == 'user':
    st.title(f"Welcome {st.session_state.username}")
    st.subheader(f"Hello, {st.session_state.username}, here are your allocated flights.")

    flights = get_flights()
    user_flights = [f for f in flights if f[3] == st.session_state.username]

    if user_flights:
        st.markdown("### ✈️ Your Allocated Flights")
        for f in user_flights:
            st.write(f"- {f[1]} — Status: {f[2]}")
    else:
        st.info("No allocated flights.")
    
    # Log out button
    if st.button('Log out'):
        logout()
