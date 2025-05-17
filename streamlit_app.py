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
    with sqlite3.connect('task_allocation.db') as conn:
        return conn.execute("SELECT * FROM users").fetchall()

def add_user(name, passcode):
    with sqlite3.connect('task_allocation.db') as conn:
        conn.execute("INSERT INTO users (name, passcode) VALUES (?, ?)", (name, passcode))
        conn.commit()

def add_flight(flight_number):
    with sqlite3.connect('task_allocation.db') as conn:
        conn.execute("INSERT INTO flights (flight_number, status) VALUES (?, 'unallocated')", (flight_number,))
        conn.commit()

def allocate_flight(flight_id, user_id):
    with sqlite3.connect('task_allocation.db') as conn:
        conn.execute("UPDATE flights SET status='allocated', assigned_user_id=? WHERE flight_id=?", (user_id, flight_id))
        conn.commit()

def update_flight_status(flight_id, status):
    with sqlite3.connect('task_allocation.db') as conn:
        conn.execute("UPDATE flights SET status=? WHERE flight_id=?", (status, flight_id))
        conn.commit()

def get_flights():
    with sqlite3.connect('task_allocation.db') as conn:
        return conn.execute("SELECT * FROM flights").fetchall()

def get_user_by_passcode(passcode):
    with sqlite3.connect('task_allocation.db') as conn:
        return conn.execute("SELECT * FROM users WHERE passcode=?", (passcode,)).fetchone()

# ---------- STREAMLIT CONFIG ----------
st.set_page_config(page_title="Flight Allocator", layout="centered")

# ---------- SESSION SETUP ----------
if 'passcode_entered' not in st.session_state:
    st.session_state.passcode_entered = ""
if 'user_type' not in st.session_state:
    st.session_state.user_type = None
if 'username' not in st.session_state:
    st.session_state.username = None

# ---------- PREDEFINED USERS ----------
predefined_users = {
    "3320": "Admin",
    "0001": "Adam",
    "0002": "Tadj",
    "0003": "Darren",
}

# ---------- FUNCTIONS ----------
def handle_digit(d):
    if len(st.session_state.passcode_entered) < 4:
        st.session_state.passcode_entered += str(d)

def handle_clear():
    st.session_state.passcode_entered = ""

def handle_delete():
    st.session_state.passcode_entered = st.session_state.passcode_entered[:-1]

def logout():
    st.session_state.clear()
    st.rerun()

# ---------- LOGIN PAGE ----------
if st.session_state.user_type is None:
    st.markdown("<h2 style='text-align: center; color: #3366cc;'>Enter PIN Number</h2>", unsafe_allow_html=True)
    
    st.markdown(
        f"<div style='text-align: center; font-size: 36px; border: 2px solid black; padding: 10px; margin-bottom: 20px; background-color: white;'>{st.session_state.passcode_entered}</div>",
        unsafe_allow_html=True
    )

    # Keypad buttons layout
    buttons = [["7", "8", "9"],
               ["4", "5", "6"],
               ["1", "2", "3"],
               ["CLR", "0", "DEL"]]

    for row in buttons:
        cols = st.columns(3)
        for i, label in enumerate(row):
            if label == "CLR":
                cols[i].button("CLR", on_click=handle_clear, key=f"btn_{label}")
            elif label == "DEL":
                cols[i].button("DEL", on_click=handle_delete, key=f"btn_{label}")
            else:
                cols[i].button(label, on_click=handle_digit, args=(label,), key=f"btn_{label}")

    st.markdown("<div style='text-align: center; margin-top: 20px;'>", unsafe_allow_html=True)
    st.button("Log Out", on_click=logout)
    st.markdown("</div>", unsafe_allow_html=True)

    if len(st.session_state.passcode_entered) == 4:
        entered = st.session_state.passcode_entered
        user = predefined_users.get(entered)
        if entered == "3320":
            st.session_state.user_type = "admin"
            st.rerun()
        elif user:
            st.session_state.user_type = "user"
            st.session_state.username = user
            st.rerun()
        else:
            st.error("❌ Invalid passcode.")
            handle_clear()

# ---------- ADMIN INTERFACE ----------
elif st.session_state.user_type == "admin":
    st.title("Admin Dashboard")
    st.subheader("👨‍✈️ Admin Interface")

    uploaded_file = st.file_uploader("Upload Flight File (CSV or Excel)", type=["csv", "xlsx"])
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            for flight_number in df.iloc[:, 0]:
                add_flight(str(flight_number))
            st.success("✅ Flights uploaded successfully.")
        except Exception as e:
            st.error(f"Error processing file: {e}")

    st.markdown("### ➕ Add New User")
    name = st.text_input("Name")
    pin = st.text_input("Passcode", type="password")
    if name and pin and st.button("Add User"):
        add_user(name, pin)
        st.success("✅ User added.")

    st.markdown("### ✈️ Allocate Flights")
    flights = get_flights()
    unallocated = [f for f in flights if f[2] == 'unallocated']
    if unallocated:
        flight_opt = st.selectbox("Flight", [f"{f[1]} (ID: {f[0]})" for f in unallocated])
        users = get_users()
        user_opt = st.selectbox("User", [f"{u[1]} (ID: {u[0]})" for u in users])
        if st.button("Allocate"):
            fid = int(flight_opt.split("ID: ")[1].replace(")", ""))
            uid = int(user_opt.split("ID: ")[1].replace(")", ""))
            allocate_flight(fid, uid)
            st.success("✅ Allocated.")
            st.rerun()

    st.markdown("### 🔧 Update Flight Status")
    if flights:
        flight_stat = st.selectbox("Flight", [f"{f[1]} (ID: {f[0]}, Status: {f[2]})" for f in flights])
        new_stat = st.selectbox("New status", ["unallocated", "allocated", "completed", "delayed"])
        if st.button("Update Status"):
            fid = int(flight_stat.split("ID: ")[1].split(",")[0])
            update_flight_status(fid, new_stat)
            st.success("✅ Updated.")
            st.rerun()
    else:
        st.info("No flights found.")

    if st.button("Log Out"):
        logout()

# ---------- USER INTERFACE ----------
elif st.session_state.user_type == "user":
    st.title(f"Welcome {st.session_state.username}")
    st.subheader("✈️ Your Allocated Flights")

    flights = get_flights()
    user_obj = [u for u in get_users() if u[1] == st.session_state.username]
    user_id = user_obj[0][0] if user_obj else None

    if user_id is not None:
        allocated = [f for f in flights if f[3] == user_id and f[2] == "allocated"]
        completed = [f for f in flights if f[3] == user_id and f[2] == "completed"]

        if allocated:
            st.markdown("#### Active Tasks")
            for f in allocated:
                st.write(f"- {f[1]} — Status: {f[2]}")
                if st.button(f"✅ Push Complete — {f[1]}", key=f"complete_{f[0]}"):
                    update_flight_status(f[0], "completed")
                    st.rerun()
        else:
            st.info("No active flights.")

        st.markdown("---")
        st.markdown("#### 📚 Task History")
        for f in completed:
            st.write(f"- {f[1]} — Status: {f[2]}")
            if st.button(f"🔄 Mark as Incomplete — {f[1]}", key=f"incomplete_{f[0]}"):
                update_flight_status(f[0], "allocated")
                st.rerun()

    if st.button("Log Out"):
        logout()
