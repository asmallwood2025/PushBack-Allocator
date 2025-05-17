import streamlit as st
import pandas as pd
import sqlite3
import random
import string
from io import StringIO

# Inject custom CSS for red theme and circular buttons
st.markdown("""
    <style>
        body {
            background-color: white;
            color: #000000;
        }
        .stButton>button {
            background-color: #d32f2f;
            color: white;
            border-radius: 50%;
            font-size: 20px;
            height: 50px;
            width: 50px;
            margin: 5px;
        }
        .stButton>button:hover {
            background-color: #b71c1c;
        }
        .stTextInput>div>input {
            border: 1px solid #d32f2f;
        }
        .stTextInput>div>label {
            color: #d32f2f;
        }
        .stSelectbox>div>label {
            color: #d32f2f;
        }
        .stSelectbox>div>div>div>div {
            background-color: #ffffff;
            border: 1px solid #d32f2f;
        }
        .stAlert {
            background-color: #d32f2f;
            color: white;
        }
    </style>
    """, unsafe_allow_html=True)

# Helper functions
def create_db():
    conn = sqlite3.connect('task_allocation.db')
    c = conn.cursor()
    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, passcode INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS flights (flight_id INTEGER PRIMARY KEY, flight_number TEXT, status TEXT, assigned_user_id INTEGER)''')
    conn.commit()
    conn.close()

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

def generate_passcode():
    return ''.join(random.choices(string.digits, k=4))

# Streamlit Interface
st.title('Flight Task Allocation System')

# Sidebar for master/admin
option = st.sidebar.selectbox('Select Option', ['Admin', 'User'])

if option == 'Admin':
    st.subheader('Admin Interface')
    
    # Upload flight file
    uploaded_file = st.file_uploader("Upload Flight File", type=["csv", "xlsx"])
    
    if uploaded_file is not None:
        # Process the uploaded file
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        # Assume the first column contains flight numbers
        for flight_number in df.iloc[:, 0]:
            add_flight(flight_number)
        
        st.success('Flights have been uploaded and added to the database.')

    # View and Allocate Flights
    flights = get_flights()
    flight_to_allocate = st.selectbox('Select Flight to Allocate', [f"{flight[1]} (ID: {flight[0]})" for flight in flights if flight[3] is None])
    
    if flight_to_allocate:
        flight_id = int(flight_to_allocate.split(" (ID: ")[1].split(")")[0])
        users = get_users()
        user_name = st.selectbox('Select User to Allocate Flight', [user[1] for user in users])
        if st.button('Allocate Flight'):
            user_id = next(user[0] for user in users if user[1] == user_name)
            allocate_flight(flight_id, user_id)
            st.success(f"Flight {flight_id} has been allocated to {user_name}.")
            st.experimental_rerun()  # Trigger live update

    # Update Flight Status
    flight_to_update = st.selectbox('Select Flight to Update Status', [f"{flight[1]} (ID: {flight[0]})" for flight in flights])
    status_options = ['unallocated', 'allocated', 'completed', 'delayed']
    new_status = st.selectbox('Select New Status', status_options)
    
    if st.button('Update Flight Status'):
        flight_id = int(flight_to_update.split(" (ID: ")[1].split(")")[0])
        update_flight_status(flight_id, new_status)
        st.success(f"Flight {flight_id} status has been updated to {new_status}.")
        st.experimental_rerun()  # Trigger live update

elif option == 'User':
    st.subheader('User Interface')
    
    # Passcode Authentication - Circular Button Input (1-9 Keypad)
    passcode = ""
    def handle_button_click(number):
        nonlocal passcode
        passcode += str(number)
        if len(passcode) == 4:
            st.session_state.passcode_entered = passcode
            st.experimental_rerun()

    col1, col2, col3 = st.columns([1, 1, 1])

    # 1-9 Circular Keypad Buttons
    with col1:
        for i in range(1, 4):
            if st.button(str(i), key=f"btn_{i}"):
                handle_button_click(i)

    with col2:
        for i in range(4, 7):
            if st.button(str(i), key=f"btn_{i}"):
                handle_button_click(i)

    with col3:
        for i in range(7, 10):
            if st.button(str(i), key=f"btn_{i}"):
                handle_button_click(i)

    if 'passcode_entered' in st.session_state:
        passcode = st.session_state.passcode_entered
        st.text_input("Passcode", value=passcode, disabled=True)
    
    if passcode:
        user = get_user_by_passcode(passcode)
        if user:
            user_id, user_name, _ = user
            st.write(f"Welcome {user_name}!")
            flights = get_flights()
            allocated_flights = [flight for flight in flights if flight[3] == user_id]
            
            if allocated_flights:
                st.write("Your allocated flights:")
                for flight in allocated_flights:
                    st.write(f"- {flight[1]} (Status: {flight[2]})")
            else:
                st.write("No flights allocated yet.")
        else:
            st.error("Invalid passcode.")
