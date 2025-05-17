import streamlit as st
import sqlite3
import pandas as pd
import datetime
from io import BytesIO

# Set page config FIRST
st.set_page_config(page_title="Flight Task Manager", layout="centered")

# DB Setup
conn = sqlite3.connect('flight_tasks.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, active INTEGER DEFAULT 1, pin TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, flight TEXT, aircraft TEXT, std TEXT, assigned_to TEXT, complete INTEGER DEFAULT 0)''')
conn.commit()

# Auth Functions
def verify_pin(pin):
    if pin == "3320":
        return "admin"
    c.execute("SELECT username FROM users WHERE pin = ? AND active = 1", (pin,))
    row = c.fetchone()
    return row[0] if row else None

# Admin Dashboard
def admin_dashboard():
    st.title("👨‍✈️ Admin Dashboard")
    if st.button("Logout"):
        del st.session_state["user"]
        st.rerun()

    tabs = st.tabs(["Users", "Flights", "History"])

    with tabs[0]:
        st.header("👥 Manage Users")
        new_user = st.text_input("New Username")
        new_pin = st.text_input("4-digit PIN", type="password", max_chars=4)
        if st.button("Add User"):
            if len(new_pin) == 4 and new_user:
                try:
                    c.execute("INSERT INTO users (username, pin) VALUES (?, ?)", (new_user, new_pin))
                    conn.commit()
                    st.success("User added")
                except:
                    st.error("Username already exists")
            else:
                st.warning("Enter valid username and 4-digit PIN")

        for row in c.execute("SELECT username, active FROM users"):
            col1, col2, col3 = st.columns([2, 1, 1])
            col1.write(row[0])
            col2.write("✅ Active" if row[1] else "❌ Inactive")
            if col3.button("Toggle", key=f"toggle_{row[0]}"):
                c.execute("UPDATE users SET active = 1 - active WHERE username = ?", (row[0],))
                conn.commit()
                st.rerun()

    with tabs[1]:
        st.header("📄 Manage Flights")
        uploaded_file = st.file_uploader("Upload Flight Schedule (.xlsx)", type=["xlsx"])

        if uploaded_file:
            df_int = pd.read_excel(uploaded_file, sheet_name='INT', header=None)
            df_dom = pd.read_excel(uploaded_file, sheet_name='DOM', header=None)
            combined_df = pd.concat([df_int, df_dom], ignore_index=True)
            created = 0
            for i, row in combined_df.iterrows():
                try:
                    flight = str(row[8]).strip()  # Column I = index 8
                    aircraft = str(row[1]).strip()  # Column B = index 1
                    std_raw = str(row[10]).strip()  # Column K = index 10

                    if not flight or not std_raw:
                        raise ValueError("Missing flight or STD")

                    try:
                        std = pd.to_datetime(std_raw, errors='coerce')
                        if pd.isna(std):
                            std = pd.to_datetime(std_raw, format="%H%M", errors='coerce')
                        if pd.isna(std):
                            raise ValueError(f"Unrecognized time format: {std_raw}")
                        std = std.strftime("%H:%M")  # Only time
                    except Exception as inner_e:
                        raise ValueError(f"Failed to parse STD: {std_raw} ({inner_e})")

                    c.execute("SELECT COUNT(*) FROM tasks WHERE flight = ? AND aircraft = ? AND std = ?", (flight, aircraft, std))
                    if c.fetchone()[0] == 0:
                        c.execute("INSERT INTO tasks (flight, aircraft, std) VALUES (?, ?, ?)", (flight, aircraft, std))
                        created += 1
                except Exception as e:
                    st.warning(f"⚠️ Row {i+1} skipped due to error: {e}")
            conn.commit()
            st.success(f"✅ {created} flight tasks created")

        st.subheader("🛫 Flight Tasks")
        if st.button("❌ Delete All Tasks"):
            c.execute("DELETE FROM tasks WHERE complete = 0")
            conn.commit()
            st.rerun()

        tasks = c.execute("SELECT id, flight, aircraft, std, assigned_to FROM tasks WHERE complete = 0 ORDER BY std").fetchall()
        users = [row[0] for row in c.execute("SELECT username FROM users WHERE active = 1").fetchall()]

        for t in tasks:
            st.markdown(f"**{t[1]}** | Aircraft: {t[2]} | STD: {t[3]}")
            cols = st.columns([2, 1, 1, 1])
            assigned = cols[0].selectbox("Assign to", users, key=f"assign_{t[0]}", index=users.index(t[4]) if t[4] in users else 0)
            new_time = cols[1].time_input("Reschedule", value=datetime.datetime.strptime(t[3], "%H:%M").time(), key=f"time_{t[0]}")
            if cols[2].button("Push Complete", key=f"complete_{t[0]}"):
                c.execute("UPDATE tasks SET complete = 1 WHERE id = ?", (t[0],))
                conn.commit()
                st.rerun()
            if cols[3].button("Delete", key=f"delete_{t[0]}"):
                c.execute("DELETE FROM tasks WHERE id = ?", (t[0],))
                conn.commit()
                st.rerun()
            c.execute("UPDATE tasks SET assigned_to = ?, std = ? WHERE id = ?", (assigned, new_time.strftime("%H:%M"), t[0]))
        conn.commit()

    with tabs[2]:
        st.header("📦 History")
        completed = c.execute("SELECT id, flight, aircraft, std FROM tasks WHERE complete = 1").fetchall()
        for t in completed:
            col1, col2 = st.columns([4, 1])
            col1.markdown(f"**{t[1]}** Aircraft: {t[2]} STD: {t[3]}")
            if col2.button("Mark Incomplete", key=f"undo_{t[0]}"):
                c.execute("UPDATE tasks SET complete = 0 WHERE id = ?", (t[0],))
                conn.commit()
                st.rerun()

# User Dashboard
def user_dashboard(username):
    st.experimental_set_query_params(refresh=str(datetime.datetime.now().timestamp()))
    st.title(f"👋 Welcome {username}")
    if st.button("Logout"):
        del st.session_state["user"]
        st.rerun()

    tabs = st.tabs(["Tasks", "Future Tasks", "History"])

    with tabs[0]:
        st.header("🛠️ Current Tasks")
        tasks = c.execute("SELECT id, flight, aircraft, std FROM tasks WHERE assigned_to = ? AND complete = 0 ORDER BY std", (username,)).fetchall()

        # Show current and next task only
        for i, t in enumerate(tasks[:2]):
            st.markdown(f"### 🛫 Task {i+1}")
            st.markdown(f"**Flight:** {t[1]}  \n**Aircraft:** {t[2]}  \n**STD:** {t[3]}")
            if st.button("Complete", key=f"user_complete_{t[0]}"):
                c.execute("UPDATE tasks SET complete = 1 WHERE id = ?", (t[0],))
                conn.commit()
                st.rerun()

    with tabs[1]:
        st.header("📋 Future Tasks")
        future_tasks = tasks[2:]  # Skip first two
        for t in future_tasks:
            col1, col2 = st.columns([4, 1])
            col1.markdown(f"**{t[1]}** Aircraft: {t[2]} STD: {t[3]}")
            if col2.button("Complete", key=f"user_future_complete_{t[0]}"):
                c.execute("UPDATE tasks SET complete = 1 WHERE id = ?", (t[0],))
                conn.commit()
                st.rerun()

    with tabs[2]:
        st.header("📦 Completed Tasks")
        completed = c.execute("SELECT id, flight, aircraft, std FROM tasks WHERE assigned_to = ? AND complete = 1 ORDER BY std", (username,)).fetchall()
        for t in completed:
            col1, col2 = st.columns([4, 1])
            col1.markdown(f"**{t[1]}** Aircraft: {t[2]} STD: {t[3]}")
            if col2.button("Reactivate", key=f"user_reactivate_{t[0]}"):
                c.execute("UPDATE tasks SET complete = 0 WHERE id = ?", (t[0],))
                conn.commit()
                st.rerun()

# App Entry
with st.sidebar:
    st.markdown("## 🔐 Sign In")
    pin = st.text_input("Enter 4-digit PIN", type="password", max_chars=4)
    if st.button("Login") and pin:
        user = verify_pin(pin)
        if user:
            st.session_state["user"] = user
            st.rerun()
        else:
            st.error("Invalid PIN")

if "user" in st.session_state:
    if st.session_state.user == "admin":
        admin_dashboard()
    else:
        st_autorefresh = st.experimental_rerun if "last_refresh" not in st.session_state or (datetime.datetime.now() - st.session_state.last_refresh).seconds >= 5 else None
        st.session_state.last_refresh = datetime.datetime.now()
        user_dashboard(st.session_state.user)
