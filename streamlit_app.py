import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import time
from io import BytesIO
from streamlit_autorefresh import st_autorefresh







# ✅ Must be the first Streamlit command
st.set_page_config(page_title="Flight Task Manager", layout="centered")




if "refresh_key" not in st.session_state:
    st.session_state.refresh_key = 0



def refresh_data():
    st.session_state.refresh_key += 1

def get_current_task_for_user(username):
    result = c.execute(
        "SELECT id, flight, aircraft, std FROM tasks WHERE assigned_to = ? AND complete = 0 ORDER BY std LIMIT 1",
        (username,)
    ).fetchone()
    return result

def get_future_tasks_for_user(username):
    all_tasks = c.execute(
        "SELECT id, flight, aircraft, std FROM tasks WHERE assigned_to = ? AND complete = 0 ORDER BY std",
        (username,)
    ).fetchall()
    return all_tasks[1:]  # Skip the first task


def get_completed_tasks_for_user(username):
    result = c.execute(
        "SELECT id, flight, aircraft, std, completed_at FROM tasks WHERE assigned_to = ? AND complete = 1 ORDER BY completed_at DESC",
        (username,)
    ).fetchall()
    return result

def get_all_flights():
    return c.execute("SELECT * FROM tasks WHERE complete = 0 ORDER BY std").fetchall()


def display_flights(flights):
    for t in flights:
        st.markdown(
            f"**Flight:** {t[1]} | Aircraft: {t[2]} | Type: {t[3]} | Dest: {t[4]} | STD: {t[5]} | ETD: {t[6]} | Assigned To: {t[7]}"
        )



# Fixed Users
STATIC_USERS = {
    "a.elliott": "0001",
    "s.chianta": "0002",
    "d.jeffery": "0003",
    "i,faramio": "0004",
    "f.fepuleai": "0005",
    "b.close": "0006",
    "b.costello": "0007",
    "j.ferdinando": "0008",
    "c.mahoney": "0009",
    "j.oliver": "0010",
    "s.rheese": "0011",
    "s.randone": "0012",
    "a.smallwood": "3314",
    "m.leach": "0013",
    "j.voykovic": "0015",
    "du,tran": "0016",
    "k.pan": "0017",
    "e.lober": "0018",
    "mo.ismail": "0020",
    "r.hunt-cameron": "0021",
    "da.maskell": "0026",
    "d.mcshane": "0027",
    "ky.murray": "0029",
    "s.brooks": "0028"
}

# DB Setup
conn = sqlite3.connect('flight_tasks.db', check_same_thread=False)
c = conn.cursor()

# Ensure tables exist
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

c.execute('''
    CREATE TABLE IF NOT EXISTS shifts (
        username TEXT PRIMARY KEY,
        start TEXT,
        finish TEXT
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS pins (
        username TEXT PRIMARY KEY,
        pin TEXT
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

import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# UI Functions
def admin_dashboard():
    st.title("👨‍✈️ Admin Dashboard")
    tabs = st.tabs(["Users", "Shifts", "Flights", "History"])

    # USERS TAB
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

    # SHIFTS TAB
    with tabs[1]:
        st.header("📅 Shift Management")

        st.subheader("📥 Import Shifts from Excel")
        shift_file = st.file_uploader("Upload Shift Schedule (.xlsx)", type=["xlsx"], key="shift_upload")

        if shift_file:
            try:
                shift_df = pd.read_excel(shift_file, skiprows=1, usecols="A:C", names=["username", "start", "finish"])
                shift_df = shift_df.dropna(subset=["username", "start", "finish"])
                imported = 0

                for _, row in shift_df.iterrows():
                    username = str(row["username"]).strip().lower()
                    start = pd.to_datetime(row["start"]).strftime("%H:%M")
                    finish = pd.to_datetime(row["finish"]).strftime("%H:%M")

                    if username in STATIC_USERS:
                        c.execute(
                            "REPLACE INTO shifts (username, start, finish) VALUES (?, ?, ?)",
                            (username, start, finish)
                        )
                        imported += 1

                conn.commit()
                st.success(f"✅ Imported {imported} shifts.")
            except Exception as e:
                st.error(f"Failed to import: {e}")

        st.subheader("📝 Manually Edit Shifts")
        for user in STATIC_USERS:
            row = c.execute("SELECT start, finish FROM shifts WHERE username = ?", (user,)).fetchone()
            start_val = row[0] if row else ""
            finish_val = row[1] if row else ""

            col1, col2, col3 = st.columns([2, 2, 1])
            col1.markdown(f"**{user}**")
            start = col2.text_input("Start", value=start_val, key=f"start_{user}")
            finish = col3.text_input("Finish", value=finish_val, key=f"finish_{user}")

            if st.button("Update Shift", key=f"update_shift_{user}"):
                c.execute(
                    "REPLACE INTO shifts (username, start, finish) VALUES (?, ?, ?)",
                    (user, start, finish)
                )
                conn.commit()
                st.success(f"Updated shift for {user}")

        if st.button("🗑 Clear All Shifts"):
            c.execute("DELETE FROM shifts")
            conn.commit()
            st.success("✅ All shifts cleared.")

    # FLIGHTS TAB
    with tabs[2]:
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

        if st.button("❌ Delete All Tasks"):
            c.execute("DELETE FROM tasks WHERE complete = 0")
            conn.commit()
            st.success("✅ All tasks deleted.")
            st.session_state["task_refresh"] = time.time()

        users = list(STATIC_USERS.keys())
        tasks = c.execute("SELECT * FROM tasks WHERE complete = 0 ORDER BY std").fetchall()

        for t in tasks:
            st.markdown(f"**{t[1]}** Aircraft: {t[2]} STD: {t[5]}")
            cols = st.columns([2, 1, 1])
            assigned = cols[0].selectbox("Assign to", users, key=f"assign_{t[0]}", index=users.index(t[4]) if t[4] in users else 0)
            if cols[1].button("Push Complete", key=f"complete_{t[0]}"):
                completed_at = datetime.now().isoformat()
                c.execute("UPDATE tasks SET complete = 1, completed_at = ? WHERE id = ?", (completed_at, t[0]))
                conn.commit()
                st.rerun()
            if cols[2].button("Delete", key=f"delete_{t[0]}"):
                c.execute("DELETE FROM tasks WHERE id = ?", (t[0],))
                conn.commit()
                st.rerun()
            c.execute("UPDATE tasks SET assigned_to = ? WHERE id = ?", (assigned, t[0]))
        conn.commit()

        st.button("🔄 Refresh Flights", on_click=refresh_data)

        # Use refresh_key as a dummy dependency to re-fetch from DB
        _ = st.session_state.refresh_key
        flights = get_all_flights()
        display_flights(flights)

    # HISTORY TAB
    with tabs[3]:
        st.header("📦 History")
        completed = c.execute(
            "SELECT id, flight, aircraft, std, completed_at FROM tasks WHERE complete = 1 ORDER BY completed_at DESC"
        ).fetchall()

        for t in completed:
            col1, col2 = st.columns([4, 1])
            date_str = pd.to_datetime(t[4]).strftime('%Y-%m-%d %H:%M') if t[4] else 'N/A'
            col1.markdown(f"**{t[1]}** Aircraft: {t[2]} STD: {t[3]} Completed: {date_str}")
            if col2.button("Mark Incomplete", key=f"undo_{t[0]}"):
                c.execute("UPDATE tasks SET complete = 0, completed_at = NULL WHERE id = ?", (t[0],))
                conn.commit()
                st.rerun()

        st.button("🔄 Refresh History", on_click=refresh_data)

        if st.button("🗑️ Clear Flight History"):
            c.execute("DELETE FROM tasks WHERE complete = 1")
            conn.commit()
            st.success("✅ Flight history cleared.")
            st.rerun()

def user_dashboard(username):
    from datetime import datetime

    # Auto-refresh every 15 seconds unless user manually triggers
    st_autorefresh(interval=5 * 1000, key="user_auto_refresh")

    # Initialize session state key safely
    if 'refresh_key' not in st.session_state:
        st.session_state.refresh_key = 0

    # Fetch shift start/finish from DB
    row = c.execute("SELECT start, finish FROM shifts WHERE username = ?", (username,)).fetchone()
    if row:
        start, finish = row
        st.markdown(f"### 🕒 Your shift: **{start} – {finish}**")
    else:
        st.markdown("### 🕒 Your shift: Not assigned")

    st.title(f"👋 Welcome {username}")
    tabs = st.tabs(["Tasks", "History"])

    def refresh_data():
        st.session_state.refresh_key += 1
        st.rerun()

    _ = st.session_state.refresh_key  # Track manual refreshes

    current_task = get_current_task_for_user(username)
    upcoming = get_future_tasks_for_user(username)
    completed = get_completed_tasks_for_user(username)

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
        st.button("🔄 Refresh My Tasks", on_click=refresh_data)

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
