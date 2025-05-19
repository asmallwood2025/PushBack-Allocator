import streamlit as st
import sqlite3
import pandas as pd
import datetime
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
    "s,chianta": "0002",
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

def admin_dashboard():
    conn = sqlite3.connect("flight_tasks.db", check_same_thread=False)
    cursor = conn.cursor()

    st.sidebar.title("Admin Dashboard")
    tab = st.sidebar.radio("Select Tab", ["Flights", "Users", "Shifts", "History"])

    if tab == "Flights":
        st.header("Flights")

        # Show current tasks sorted by STD
        cursor.execute("SELECT id, flight_number, aircraft, std, assigned_user FROM flights ORDER BY std")
        flights = cursor.fetchall()
        df = pd.DataFrame(flights, columns=["ID", "Flight Number", "Aircraft", "STD", "Assigned User"])
        df["STD"] = pd.to_datetime(df["STD"])
        st.dataframe(df, use_container_width=True)

        # Delete all tasks
        if st.button("❌ Delete All Tasks"):
            st.warning("Are you sure you want to delete all flight tasks?")
            if st.button("✅ Confirm Delete All"):
                cursor.execute("DELETE FROM flights")
                conn.commit()
                st.success("All flight tasks deleted.")

        # Individual delete buttons
        for _, row in df.iterrows():
            with st.expander(f"{row['Flight Number']} ({row['STD']})"):
                if st.button(f"Delete Task {row['ID']}", key=f"delete_{row['ID']}"):
                    cursor.execute("DELETE FROM flights WHERE id = ?", (row['ID'],))
                    conn.commit()
                    st.success(f"Deleted task {row['Flight Number']}")

    elif tab == "Users":
        st.header("User Management")

        # Display users
        cursor.execute("SELECT id, name, pin, active FROM users")
        users = cursor.fetchall()
        user_df = pd.DataFrame(users, columns=["ID", "Name", "PIN", "Active"])
        user_df["Active"] = user_df["Active"].apply(lambda x: "✅" if x else "❌")
        st.dataframe(user_df, use_container_width=True)

        # Add new user
        st.subheader("Add User")
        new_name = st.text_input("Name")
        new_pin = st.text_input("4-digit PIN", max_chars=4)
        if st.button("➕ Add User"):
            if new_name and new_pin.isdigit() and len(new_pin) == 4:
                cursor.execute("INSERT INTO users (name, pin, active) VALUES (?, ?, 1)", (new_name, new_pin))
                conn.commit()
                st.success(f"User '{new_name}' added.")
            else:
                st.error("Please enter a valid name and 4-digit PIN.")

        # Edit users
        st.subheader("Edit Users")
        for user in users:
            uid, name, pin, active = user
            with st.expander(f"Edit: {name}"):
                new_name = st.text_input(f"Name for {name}", value=name, key=f"name_{uid}")
                new_pin = st.text_input(f"PIN for {name}", value=str(pin), max_chars=4, key=f"pin_{uid}")
                new_active = st.checkbox("Active", value=bool(active), key=f"active_{uid}")
                if st.button(f"💾 Save {name}", key=f"save_{uid}"):
                    if new_pin.isdigit() and len(new_pin) == 4:
                        cursor.execute("UPDATE users SET name = ?, pin = ?, active = ? WHERE id = ?",
                                       (new_name, new_pin, int(new_active), uid))
                        conn.commit()
                        st.success(f"Updated user {new_name}.")
                    else:
                        st.error("PIN must be a 4-digit number.")
                if st.button(f"🗑️ Delete {name}", key=f"delete_user_{uid}"):
                    cursor.execute("DELETE FROM users WHERE id = ?", (uid,))
                    conn.commit()
                    st.warning(f"Deleted user {name}.")

    elif tab == "Shifts":
        st.header("Shifts")

        # Display shift status table
        cursor.execute("SELECT name, shift_start, shift_end, is_on_shift FROM users")
        user_shifts = cursor.fetchall()

        if user_shifts:
            df = pd.DataFrame(user_shifts, columns=["Name", "Shift Start", "Shift End", "On Shift"])
            df["Shift Start"] = pd.to_datetime(df["Shift Start"])
            df["Shift End"] = pd.to_datetime(df["Shift End"])
            df["On Shift"] = df["On Shift"].apply(lambda x: "✅" if x else "❌")
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No users found.")

        st.markdown("### Admin Tools")

        # Clear Shifts Button with Confirmation
        if st.button("🧹 Clear All Shifts"):
            st.warning("Are you sure you want to clear **all users'** shift start/end times and reset shift status? This cannot be undone.")
            if st.button("✅ Confirm Clear Shifts"):
                cursor.execute("UPDATE users SET shift_start = NULL, shift_end = NULL, is_on_shift = 0")
                conn.commit()
                st.success("All shift data cleared successfully.")

    elif tab == "History":
        st.header("Completed Tasks History")

        cursor.execute("SELECT id, flight_number, aircraft, std, completed_by, completed_at FROM completed_tasks ORDER BY completed_at DESC")
        history = cursor.fetchall()
        if history:
            df = pd.DataFrame(history, columns=["ID", "Flight Number", "Aircraft", "STD", "Completed By", "Completed At"])
            df["STD"] = pd.to_datetime(df["STD"])
            df["Completed At"] = pd.to_datetime(df["Completed At"])
            st.dataframe(df, use_container_width=True)

            for _, row in df.iterrows():
                with st.expander(f"{row['Flight Number']} completed by {row['Completed By']} at {row['Completed At']}"):
                    if st.button(f"↩️ Mark Incomplete {row['ID']}", key=f"undo_{row['ID']}"):
                        cursor.execute("INSERT INTO flights (flight_number, aircraft, std, assigned_user) VALUES (?, ?, ?, ?)",
                                       (row["Flight Number"], row["Aircraft"], row["STD"], row["Completed By"]))
                        cursor.execute("DELETE FROM completed_tasks WHERE id = ?", (row["ID"],))
                        conn.commit()
                        st.success(f"Task {row['Flight Number']} moved back to active flights.")
        else:
            st.info("No completed tasks found.")

    conn.close()

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
