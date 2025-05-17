import streamlit as st
import pandas as pd
import random
import string
import json
import os

# File paths
USERS_FILE = 'users.json'
FLIGHTS_FILE = 'flights.json'

# Helper functions
def load_data(filename):
    """Load data from a JSON file."""
    if os.path.exists(filename):
        with open(filename, 'r') as file:
            return json.load(file)
    return {}

def save_data(filename, data):
    """Save data to a JSON file."""
    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)

def get_users():
    """Get the list of users from the users file."""
    users_data = load_data(USERS_FILE)
    return users_data.get('users', [])

def add_user(name, passcode):
    """Add a new user to the users file."""
    users_data = load_data(USERS_FILE)
    users = users_data.get('users', [])
    users.append({'name': name, 'passcode': passcode})
    users_data['users'] = users
    save_data(USERS_FILE, users_data)

def get_flights():
    """Get the list of flights from the flights file."""
    flights_data = load_data(FLIGHTS_FILE)
    return flights_data.get('flights', [])

def add_flight(flight_number):
    """Add a new flight to the flights file."""
    flights_data = load_data(FLIGHTS_FILE)
    flights = flights_data.get('flights', [])
    flights.append({'flight_number': flight_number, 'status': 'unallocated', 'assigned_user': None})
    flights_data['flights'] = flights
    save_data(FLIGHTS_FILE, flights_data)

def allocate_flight(flight_number, user_name):
    """Allocate a flight to a user."""
    flights_data = load_data(FLIGHTS_FILE)
    flights = flights_data.get('flights', [])
    for flight in flights:
        if flight['flight_number'] == flight_number and flight['status'] == 'unallocated':
            flight['status'] = 'allocated'
            flight['assigned_user'] = user_name
            save_data(FLIGHTS_FILE, flights_data)
            return True
    return False

def update_flight_status(flight_number, status):
    """Update the status of a flight."""
    flights_data = load_data(FLIGHTS_FILE)
    flights = flights_data.get('flights', [])
    for flight in flights:
        if flight['flight_number'] == flight_number:
            flight['status'] = status
            save_data(FLIGHTS_FILE, flights_data)
            return True
    return False

def get_user_by_passcode(passcode):
    """Get a user by their passcode."""
    users = get_users()
    for user in users:
        if user['passcode'] == passcode:
            return user
    return None

def generate_passcode():
    """Generate a random 4-digit passcode."""
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
    flight_to_allocate = st.selectbox('Select Flight to Allocate', [f"{flight['flight_number']} (Status: {flight['status']})" for flight in flights if flight['status'] == 'unallocated'])
    
    if flight_to_allocate:
        flight_number = flight_to_allocate.split(" (")[0]
        users = get_users()
        user_name = st.selectbox('Select User to Allocate Flight', [user['name'] for user in users])
        if st.button('Allocate Flight'):
            if allocate_flight(flight_number, user_name):
                st.success(f"Flight {flight_number} has been allocated to {user_name}.")
                st.experimental_rerun()  # Trigger live update

    # Update Flight Status
    flight_to_update = st.selectbox('Select Flight to Update Status', [f"{flight['flight_number']} (Status: {flight['status']})" for flight in flights])
    status_options = ['unallocated', 'allocated', 'completed', 'delayed']
    new_status = st.selectbox('Select New Status', status_options)
    
    if st.button('Update Flight Status'):
        flight_number = flight_to_update.split(" (")[0]
        if update_flight_status(flight_number, new_status):
            st.success(f"Flight {flight_number} status has been updated to {new_status}.")
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
            user_name = user['name']
            st.write(f"Welcome {user_name}!")
            flights = get_flights()
            allocated_flights = [flight for flight in flights if flight['assigned_user'] == user_name]
            
            if allocated_flights:
                st.write("Your allocated flights:")
                for flight in allocated_flights:
                    st.write(f"- {flight['flight_number']} (Status: {flight['status']})")
            else:
                st.write("No flights allocated yet.")
        else:
            st.error("Invalid passcode.")
