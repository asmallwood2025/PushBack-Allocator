import streamlit as st
import sqlite3
import pandas as pd
import datetime
import time
from io import BytesIO

# ✅ Must be the first Streamlit command
st.set_page_config(page_title="Flight Task Manager", layout="centered")

# Fixed Users
STATIC_USERS = {
    "Adam": "0001",
    "Samuel C": "0002",
    "Darren": "0003",
    "Isaac": "0004",
    "Faith": "0005",
    "Bailey": "0006",
    "Bastien": "0007",
    "Janith": "0008",
    "Ringo": "0009",
    "Jolly": "0010",
    "Sam R": "0011",
    "Sal": "0012",
    "Albert": "3314",
    "Mitch": "0013",
    "Tadj": "0014",
    "John": "0015",
    "Du Bao": "0016",
    "Kam": "0017",
    "Ernie": "0018",
    "Huss": "0019",
    "Mo": "0020",
    "Ronan": "0021",
    "Caruso": "0022",
    "Tunj": "0023",
    "Mark": "0024",
    "Shawn": "0025",
    "David": "0026",
    "D-mac": "0027",
    "Costa": "0028"
}

# DB Setup
conn = sqlite3.connect('flight_tasks.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS pins (username TEXT PRIMARY KEY, pin TEXT)''')
c.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        flight TEXT,
        aircraft TEXT,
        aircraft_type TEXT,
        destination TEXT,
        std TEXT,
        etd TEXT,
        assigned_to TEXT,
        complete INTEGER DEFAULT 0,
        notes TEXT,
        completed_at TEXT
    )
''')
conn.commit()

# Initialize PINs table with static users
for user, pin in STATIC_USERS.items():
    c.execute("INSERT OR IGNORE INTO pins (username, pin) VALUES (?, ?)", (user, pin))
conn.commit()

# Auth Functions
def verify_pin(pin):
    if pin == "3320":
        return "admin"
    c.execute("SELECT username FROM pins WHERE pin = ?", (pin,))
    row = c.fetchone()
    return row[0] if row else None

# UI Functions
def admin_dashboard():
    st.title("👨‍✈️ Admin Dashboard")
    tabs = st.tabs(["Users", "Flights", "History"])

    with tabs[0]:
        st.header("👥 Manage Users")
        for user in STATIC_USERS.keys():
            current_pin = c.execute("SELECT pin FROM pins WHERE username = ?", (user,)).fetchone()[0]
            col1, col2, col3 = st.columns([2, 2, 1])
            col1.write(user)
            new_pin = col2.text_input("Edit PIN", value=current_pin, max_chars=4, key=f"pin_{user}")
            if col3.button("Update", key=f"update_{user}"):
                if len(new_pin) == 4 and new_pin.isdigit():
                    c.execute("UPDATE pins SET pin = ? WHERE username = ?", (new_pin, user))
                    conn.commit()
                    st.success(f"Updated PIN for {user}")
                else:
                    st.warning("PIN must be 4 digits")

    with tabs[1]:
        st.header("📄 Manage Flights")
        uploaded_file = st.file_uploader("Upload Flight Schedule (.xlsx)", type=["xlsx"])

        if uploaded_file:
            try:
                df = pd.read_excel(uploaded_file, sheet_name='Push Back', header=None)
                created = 0

                for i, row in df.iterrows():
                    try:
                        flight = str(row[3]).strip()
                        aircraft = str(row[0]).strip()
                        aircraft_type = str(row[1]).strip()
                        destination = str(row[4]).strip()
                        std_raw = row[5]
                        etd_raw = row[6]

                        # Validate flight format (e.g., QF600, JQ810, VA231)
                        if not flight or not any(char.isdigit() for char in flight):
                            continue

                        def parse_time(val):
                            if pd.isna(val):
                                return None
                            try:
                                val = int(val)
                                hours = val // 100
                                minutes = val % 100
                                return f"{hours:02d}:{minutes:02d}"
                            except:
                                try:
                                    parsed = pd.to_datetime(str(val), format="%H%M", errors='coerce')
                                    if pd.isna(parsed):
                                        return None
                                    return parsed.strftime("%H:%M")
                                except:
                                    return None

                        std = parse_time(std_raw)
                        etd = parse_time(etd_raw)

                        if not std:
                            raise ValueError("Invalid STD format")

                        # Check for duplicates
                        c.execute("SELECT COUNT(*) FROM tasks WHERE flight = ? AND std = ?", (flight, std))
                        if c.fetchone()[0] == 0:
                            c.execute('''
                                INSERT INTO tasks (flight, aircraft, aircraft_type, destination, std, etd)
                                VALUES (?, ?, ?, ?, ?, ?)
                            ''', (flight, aircraft, aircraft_type, destination, std, etd))
                            created += 1

                    except Exception as e:
                        st.warning(f"⚠️ Row {i+1} skipped: {e}")

                conn.commit()
                st.success(f"✅ {created} flight tasks created")
            except Exception as e:
                st.error(f"❌ Failed to process file: {e}")


        st.subheader("🛫 Flight Tasks")
        if st.button("❌ Delete All Tasks"):
            c.execute("DELETE FROM tasks WHERE complete = 0")
            conn.commit()
            st.rerun()

        tasks = c.execute("SELECT id, flight, aircraft, std, assigned_to FROM tasks WHERE complete = 0 ORDER BY std").fetchall()
        users = list(STATIC_USERS.keys())

        for t in tasks:
            st.markdown(f"**{t[1]}** Aircraft: {t[2]} STD: {t[3]}")
            cols = st.columns([2, 1, 1])
            assigned = cols[0].selectbox("Assign to", users, key=f"assign_{t[0]}", index=users.index(t[4]) if t[4] in users else 0)
            if cols[1].button("Push Complete", key=f"complete_{t[0]}"):
                completed_at = datetime.datetime.now().isoformat()
                c.execute("UPDATE tasks SET complete = 1, completed_at = ? WHERE id = ?", (completed_at, t[0]))
                conn.commit()
                st.rerun()
            if cols[2].button("Delete", key=f"delete_{t[0]}"):
                c.execute("DELETE FROM tasks WHERE id = ?", (t[0],))
                conn.commit()
                st.rerun()
            c.execute("UPDATE tasks SET assigned_to = ? WHERE id = ?", (assigned, t[0]))
        conn.commit()

    with tabs[2]:
        st.header("📦 History")
        completed = c.execute("SELECT id, flight, aircraft, std, completed_at FROM tasks WHERE complete = 1 ORDER BY completed_at DESC").fetchall()
        for t in completed:
            col1, col2 = st.columns([4, 1])
            date_str = pd.to_datetime(t[4]).strftime('%Y-%m-%d %H:%M') if t[4] else 'N/A'
            col1.markdown(f"**{t[1]}** Aircraft: {t[2]} STD: {t[3]} Completed: {date_str}")
            if col2.button("Mark Incomplete", key=f"undo_{t[0]}"):
                c.execute("UPDATE tasks SET complete = 0, completed_at = NULL WHERE id = ?", (t[0],))
                conn.commit()
                st.rerun()

def user_dashboard(username):
    from datetime import datetime

    st.experimental_set_query_params(refresh=str(time.time()))
    time.sleep(5)

    st.title(f"👋 Welcome {username}")
    tabs = st.tabs(["Tasks", "History"])

    def get_status_color(std_time_str):
        now = datetime.now()
        try:
            std_today = datetime.combine(now.date(), datetime.strptime(std_time_str, "%H:%M").time())
        except:
            return "#cccccc"
        diff = (std_today - now).total_seconds() / 60
        if diff <= 10:
            return "#ff5252"
        elif diff <= 15:
            return "#ff9800"
        elif diff <= 25:
            return "#4caf50"
        else:
            return "#cccccc"

    with tabs[0]:
        st.header("🛠️ Your Tasks")

        tasks = c.execute(
            "SELECT id, flight, aircraft, std FROM tasks WHERE assigned_to = ? AND complete = 0 ORDER BY std",
            (username,)
        ).fetchall()

        if tasks:
            current = tasks[0]
            color = get_status_color(current[3])
            st.markdown("### 🟢 **Current Task**")
            with st.container():
                st.markdown(
                    f"""
                    <div style='padding: 20px; background-color: {color}; border-radius: 12px; color: white;'>
                        <h2 style='margin-bottom: 10px;'>✈️ {current[1]}</h2>
                        <p><strong>Aircraft:</strong> {current[2]}</p>
                        <p><strong>STD:</strong> {current[3]}</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                if st.button("✅ Complete Current", key=f"complete_{current[0]}"):
                    completed_at = datetime.now().isoformat()
                    c.execute("UPDATE tasks SET complete = 1, completed_at = ? WHERE id = ?", (completed_at, current[0]))
                    conn.commit()
                    st.rerun()

            if len(tasks) > 1:
                next_task = tasks[1]
                color = get_status_color(next_task[3])
                st.markdown("### 🟡 **Next Task**")
                with st.container():
                    st.markdown(
                        f"""
                        <div style='padding: 20px; background-color: {color}; border-radius: 12px; color: white;'>
                            <h3 style='margin-bottom: 10px;'>✈️ {next_task[1]}</h3>
                            <p><strong>Aircraft:</strong> {next_task[2]}</p>
                            <p><strong>STD:</strong> {next_task[3]}</p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
        else:
            st.info("You currently have no assigned tasks.")

        if len(tasks) > 2:
            with st.expander("📋 View Future Tasks"):
                for t in tasks[2:]:
                    col1, col2 = st.columns([4, 1])
                    col1.markdown(f"**{t[1]}** | Aircraft: {t[2]} | STD: {t[3]}")
                    if col2.button("Complete", key=f"user_complete_future_{t[0]}"):
                        completed_at = datetime.now().isoformat()
                        c.execute("UPDATE tasks SET complete = 1, completed_at = ? WHERE id = ?", (completed_at, t[0]))
                        conn.commit()
                        st.rerun()

    with tabs[1]:
        st.header("📦 Completed Tasks")
        completed = c.execute(
            "SELECT id, flight, aircraft, std, completed_at FROM tasks WHERE assigned_to = ? AND complete = 1 ORDER BY completed_at DESC",
            (username,)
        ).fetchall()
        for t in completed:
            col1, col2 = st.columns([4, 1])
            date_str = pd.to_datetime(t[4]).strftime('%Y-%m-%d %H:%M') if t[4] else 'N/A'
            col1.markdown(f"**{t[1]}** | Aircraft: {t[2]} | STD: {t[3]} | Completed: {date_str}")
            if col2.button("🔁 Reactivate", key=f"reactivate_{t[0]}"):
                c.execute("UPDATE tasks SET complete = 0, completed_at = NULL WHERE id = ?", (t[0],))
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
        else:
            st.error("Invalid PIN")

if "user" in st.session_state:
    if st.session_state.user == "admin":
        admin_dashboard()
    else:
        user_dashboard(st.session_state.user)
