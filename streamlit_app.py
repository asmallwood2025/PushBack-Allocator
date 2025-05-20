import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import time
from io import BytesIO
from streamlit_autorefresh import st_autorefresh
import datetime


# ✅ Must be the first Streamlit command
st.set_page_config(page_title="Flight Task Manager", layout="centered")



# DB Setup
conn = sqlite3.connect('flight_tasks.db', check_same_thread=False)
conn.row_factory = sqlite3.Row  # <-- add this line
c = conn.cursor()


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

def get_pending_tasks():
    c.execute("""
        SELECT id, flight_number, ac_type, etd, std, assigned_user_id
        FROM flights
        WHERE status = 'pending' AND assigned_user_id IS NULL
        ORDER BY COALESCE(etd, std) ASC
    """)
    return c.fetchall()

def get_active_users():
    c.execute("""
        SELECT u.id, u.name, s.start AS shift_start, s.finish AS shift_end, u.current_task_id
        FROM users u
        JOIN shifts s ON u.name = s.username
        WHERE u.is_active = 1
    """)
    return c.fetchall()

def get_task_by_id(task_id):
    if not task_id:
        return None
    c.execute("""
        SELECT id, ac_type, etd, std
        FROM flights
        WHERE id = ?
    """, (task_id,))
    return c.fetchone()

def within_shift(start, end, etd):
    buffer = datetime.timedelta(minutes=20)
    return (start - buffer) <= etd <= (end + buffer)

def get_task_time(task):
    return task['etd'] if task['etd'] else task['std']

def assign_task(task_id, user_id):
    c.execute("UPDATE flights SET assigned_user_id = ? WHERE id = ?", (user_id, task_id))
    c.execute("UPDATE users SET current_task_id = ? WHERE id = ?", (task_id, user_id))
    conn.commit()

def is_task_overdue(task_time, now):
    return task_time < now


def auto_allocate_tasks():
    now = datetime.now()
    c = conn.cursor()

    # Get all pending and unassigned tasks
    c.execute("SELECT * FROM flights WHERE status = 'pending' AND assigned_user_id IS NULL")
    pending_tasks = c.fetchall()
    if not pending_tasks:
        st.write("No pending unassigned tasks.")
        return

    # Get all active users with shifts
    c.execute("SELECT u.id, u.name, shift_start, shift_end, u.current_task_id FROM users u JOIN shifts s ON u.name = s.username WHERE u.is_active = 1")
    users = c.fetchall()
    if not users:
        st.write("No active users with shifts.")
        return

    for task in pending_tasks:
        task_id = task[0]
        flight_number = task[1]
        aircraft = task[2]
        etd = task[3]
        std = task[4]
        task_time_str = etd or std

        if not task_time_str:
            st.write(f"Skipping task {task_id}: No ETD/STD")
            continue

        # Convert to datetime
        try:
            task_time = datetime.strptime(task_time_str, "%H:%M").replace(
                year=now.year, month=now.month, day=now.day)
        except ValueError:
            st.write(f"Skipping task {task_id}: Invalid time format: {task_time_str}")
            continue

        best_user = None
        best_score = float('inf')

        st.write(f"Evaluating task {task_id} @ {task_time.strftime('%H:%M')}")

        for user in users:
            user_id, username, shift_start, shift_end, current_task_id = user

            # Check shift boundaries (with 20 min buffer)
            if not within_shift(shift_start, shift_end, task_time):
                st.write(f"- Skipping {username}: task outside shift bounds.")
                continue

            score = 0

            # Calculate travel time from user's current task
            if current_task_id:
                c.execute("SELECT etd, std, aircraft FROM flights WHERE id = ?", (current_task_id,))
                last_task = c.fetchone()
                if last_task:
                    last_time_str = last_task[0] or last_task[1]
                    last_aircraft = last_task[2]

                    try:
                        last_time = datetime.strptime(last_time_str, "%H:%M").replace(
                            year=now.year, month=now.month, day=now.day)
                        travel_time = (task_time - last_time).total_seconds() / 60
                        score -= travel_time  # maximize travel time
                        if last_aircraft != aircraft:
                            score += 10  # aircraft switch penalty
                    except Exception as e:
                        st.write(f"Error parsing last task time for {username}: {e}")
                        continue

            if score < best_score:
                best_score = score
                best_user = user

        if best_user:
            user_id = best_user[0]
            username = best_user[1]
            st.write(f"✔ Assigning task {task_id} to {username} (score {best_score:.1f})")

            c.execute("UPDATE flights SET assigned_user_id = ? WHERE id = ?", (user_id, task_id))
            c.execute("UPDATE users SET current_task_id = ? WHERE id = ?", (task_id, user_id))
            conn.commit()
        else:
            st.write(f"No suitable user found for task {task_id}")

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
    CREATE TABLE IF NOT EXISTS pins (
        username TEXT PRIMARY KEY,
        pin TEXT
    )
''')



c.execute("""
    CREATE TABLE IF NOT EXISTS flights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        flight_number TEXT,
        ac_type TEXT,
        etd TEXT,
        std TEXT,
        assigned_user_id INTEGER,
        status TEXT
    )
""")

# Create users table (if not exists) to support auto-allocation
c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        is_active INTEGER DEFAULT 1,
        shift_start TEXT,
        shift_end TEXT,
        current_task_id INTEGER
    )
''')
conn.commit()




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

    


    # Auto-refresh every 15 seconds unless user manually triggers
    st_autorefresh(interval=5 * 1000, key="user_auto_refresh")
    auto_allocate_tasks()
    
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

     with st.form("shift_edit_form"):
         for user in STATIC_USERS:
             row = c.execute("SELECT shift_start, shift_end FROM users WHERE username = ?", (user,)).fetchone()
             start_val = row[0] if row else ""
             finish_val = row[1] if row else ""

             col1, col2, col3 = st.columns([2, 2, 2])
             col1.markdown(f"**{user}**")
             start = col2.text_input("Start", value=start_val, key=f"start_{user}")
             finish = col3.text_input("Finish", value=finish_val, key=f"finish_{user}")

         submitted = st.form_submit_button("💾 Update All Shifts")
         if submitted:
             for user in STATIC_USERS:
                 start = st.session_state.get(f"start_{user}", "")
                 finish = st.session_state.get(f"finish_{user}", "")
                 c.execute(
                     "REPLACE INTO shifts (username, start, finish) VALUES (?, ?, ?)",
                     (user, start, finish)
                 )
             conn.commit()
             st.success("✅ All shifts updated.")

     # ✅ Clear All Shifts button (now works because form is isolated)
     if st.button("🗑 Clear All Shifts", key="clear_all_shifts_btn"):
         c.execute("DELETE FROM shifts")
         conn.commit()
         st.success("✅ All shifts cleared.")
         st.rerun()
 
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
                             c.execute('''
                                 INSERT INTO flights (flight_number, ac_type, etd, std, status)
                                 VALUES (?, ?, ?, ?, 'pending')
                             ''', (flight, aircraft_type, etd, std))
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
         tasks = c.execute(
             "SELECT id, flight, aircraft, std, etd FROM tasks WHERE assigned_to = ? AND complete = 0 ORDER BY std",
             (username,)
         ).fetchall()
 
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

def get_status_color(etd_str, std_str):


    now = datetime.now()

    time_str = etd_str if etd_str else std_str
    if not time_str:
        return "#cccccc"

    try:
        task_time = datetime.combine(now.date(), datetime.strptime(time_str, "%H:%M").time())
    except:
        return "#cccccc"

    diff = (task_time - now).total_seconds() / 60  # time difference in minutes

    if diff <= 10:
        return "#ff5252"   # red
    elif diff <= 15:
        return "#ff9800"   # orange
    elif diff <= 25:
        return "#4caf50"   # green
    else:
        return "#cccccc"   # grey

    with tabs[0]:
        st.header("🛠️ Your Tasks")
        st.button("🔄 Refresh My Tasks", on_click=refresh_data)

        tasks = c.execute(
            "SELECT id, flight, aircraft, std FROM tasks WHERE assigned_to = ? AND complete = 0 ORDER BY std",
            (username,)
        ).fetchall()

        if tasks:
            current = tasks[0]
            color = get_status_color(current[4], current[3])  # ETD, STD
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
                color = get_status_color(next_task[4], next_task[3])
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
                    col1, col2 = st.columns([5, 1])
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
