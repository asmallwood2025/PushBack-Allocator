
import streamlit as st
import pandas as pd
import sqlite3
import datetime

# -------------------- DATABASE SETUP --------------------

DB_FILE = "flight_allocation.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    pin TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS flights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    flight_number TEXT,
                    ac TEXT,
                    std TEXT,
                    assigned_user_id INTEGER,
                    status TEXT DEFAULT 'unallocated',
                    FOREIGN KEY (assigned_user_id) REFERENCES users (id)
                )''')
    conn.commit()
    conn.close()

def get_users():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    conn.close()
    return users

def add_user(name, pin):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO users (name, pin) VALUES (?, ?)", (name, pin))
    conn.commit()
    conn.close()

def update_user(user_id, name, pin):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET name = ?, pin = ? WHERE id = ?", (name, pin, user_id))
    conn.commit()
    conn.close()

def delete_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def toggle_user_active(user_id, is_active):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET is_active = ? WHERE id = ?", (is_active, user_id))
    conn.commit()
    conn.close()

def ensure_default_user():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE name = 'Adam'")
    if not c.fetchone():
        c.execute("INSERT INTO users (name, pin) VALUES ('Adam', '0001')")
        conn.commit()
    conn.close()

def import_flights_from_excel(file):
    df_int = pd.read_excel(file, sheet_name='INT', usecols="I:K")
    df_dom = pd.read_excel(file, sheet_name='DOM', usecols="I:K")
    df = pd.concat([df_int, df_dom])
    df.columns = ['flight_number', 'ac', 'std']
    df.dropna(subset=['flight_number', 'ac', 'std'], inplace=True)
    df['std'] = pd.to_datetime(df['std'])
    df.sort_values(by='std', inplace=True)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    for _, row in df.iterrows():
        c.execute("INSERT INTO flights (flight_number, ac, std) VALUES (?, ?, ?)", 
                  (row['flight_number'], row['ac'], row['std'].strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()

def get_flights(assigned_user_id=None, completed=False):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if assigned_user_id is not None:
        if completed:
            c.execute("SELECT * FROM flights WHERE assigned_user_id=? AND status='completed'", (assigned_user_id,))
        else:
            c.execute("SELECT * FROM flights WHERE assigned_user_id=? AND status!='completed'", (assigned_user_id,))
    else:
        c.execute("SELECT * FROM flights")
    flights = c.fetchall()
    conn.close()
    return flights

def allocate_flight(flight_id, user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE flights SET assigned_user_id=?, status='allocated' WHERE id=?", (user_id, flight_id))
    conn.commit()
    conn.close()

def update_flight_status(flight_id, status):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE flights SET status=? WHERE id=?", (status, flight_id))
    conn.commit()
    conn.close()

def get_user_by_pin(pin):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE pin=? AND is_active=1", (pin,))
    user = c.fetchone()
    conn.close()
    return user

# -------------------- STREAMLIT UI --------------------

st.set_page_config(page_title="Flight Allocation", layout="wide")
init_db()
ensure_default_user()

if 'passcode_entered' not in st.session_state:
    st.session_state.passcode_entered = ""
if 'user_info' not in st.session_state:
    st.session_state.user_info = None

def logout():
    st.session_state.passcode_entered = ""
    st.session_state.user_info = None
    st.rerun()

def keypad_login():
    st.markdown("<h2 style='text-align: center;'>Enter PIN</h2>", unsafe_allow_html=True)
    keypad = [[1,2,3],[4,5,6],[7,8,9],[0]]
    for row in keypad:
        cols = st.columns(3)
        for i, num in enumerate(row):
            with cols[i % 3]:
                if st.button(str(num), key=f"btn_{num}"):
                    if len(st.session_state.passcode_entered) < 4:
                        st.session_state.passcode_entered += str(num)
                        if len(st.session_state.passcode_entered) == 4:
                            user = get_user_by_pin(st.session_state.passcode_entered)
                            if user:
                                st.session_state.user_info = user
                            else:
                                st.session_state.passcode_entered = ""
                                st.error("Invalid PIN")
                            st.rerun()
    st.text_input("Entered", value=st.session_state.passcode_entered, disabled=True)

if not st.session_state.user_info:
    keypad_login()
else:
    user = st.session_state.user_info
    if user[1] == "Admin":
        tabs = st.tabs(["Flights", "Users"])
        with tabs[0]:
            st.header("📋 Flight Task Management")
            file = st.file_uploader("Upload Movement Sheet", type=["xlsx"])
            if file:
                try:
                    import_flights_from_excel(file)
                    st.success("Flights imported.")
                except Exception as e:
                    st.error(f"Failed to import: {e}")
            flights = get_flights()
            for f in flights:
                st.write(f"{f[1]} | A/C: {f[2]} | STD: {f[3]} | Status: {f[5]}")

        with tabs[1]:
            st.header("👥 User Management")
            new_name = st.text_input("New User Name")
            new_pin = st.text_input("New PIN", type="password")
            if st.button("Add User"):
                if new_name and new_pin:
                    add_user(new_name, new_pin)
                    st.success("User added.")
                    st.rerun()
            users = get_users()
            for u in users:
                with st.expander(f"{u[1]}"):
                    name = st.text_input("Name", value=u[1], key=f"name_{u[0]}")
                    pin = st.text_input("PIN", value=u[2], key=f"pin_{u[0]}", type="password")
                    active = st.checkbox("Active", value=bool(u[3]), key=f"active_{u[0]}")
                    if st.button("Update", key=f"update_{u[0]}"):
                        update_user(u[0], name, pin)
                        toggle_user_active(u[0], int(active))
                        st.success("Updated")
                        st.rerun()
                    if st.button("Delete", key=f"delete_{u[0]}"):
                        delete_user(u[0])
                        st.warning("Deleted")
                        st.rerun()
    else:
        st.header(f"Welcome, {user[1]}")
        st.subheader("Your Assigned Flights")
        flights = get_flights(assigned_user_id=user[0])
        for f in flights:
            st.markdown(f"✈️ {f[1]} | A/C: {f[2]} | STD: {f[3]} | Status: {f[5]}")
            if f[5] != "completed":
                if st.button("✅ Push Complete", key=f"done_{f[0]}"):
                    update_flight_status(f[0], "completed")
                    st.success("Marked complete.")
                    st.rerun()

        st.subheader("🕘 History")
        history = get_flights(assigned_user_id=user[0], completed=True)
        for h in history:
            st.markdown(f"✅ {h[1]} | A/C: {h[2]} | STD: {h[3]}")
            if st.button("↩️ Mark as Incomplete", key=f"incomplete_{h[0]}"):
                update_flight_status(h[0], "allocated")
                st.rerun()

    if st.button("Logout"):
        logout()
