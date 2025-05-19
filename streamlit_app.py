
import streamlit as st
import sqlite3
import pandas as pd
import datetime
import os

# --- DB Setup ---
conn = sqlite3.connect("flight_tasks.db", check_same_thread=False)
c = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flight TEXT,
    aircraft TEXT,
    destination TEXT,
    std TEXT,
    etd TEXT,
    assigned_to TEXT,
    complete INTEGER DEFAULT 0,
    completed_at TEXT
)""")
c.execute("""CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    pin TEXT,
    active INTEGER DEFAULT 1
)""")
conn.commit()

# --- Static User PINs for Login ---
STATIC_USERS = {
    "Adam": "1111",
    "Tadj": "2222",
    "Darren": "3333"
}

# --- Helper Functions ---
def get_status_color(std):
    try:
        std_dt = datetime.datetime.strptime(std, "%H:%M").time()
        now = datetime.datetime.now().time()
        delta = datetime.datetime.combine(datetime.date.today(), std_dt) - datetime.datetime.combine(datetime.date.today(), now)
        minutes = delta.total_seconds() / 60
        if minutes <= 10:
            return "#e63946"  # Red
        elif minutes <= 30:
            return "#ffb703"  # Orange
        else:
            return "#2a9d8f"  # Green
    except:
        return "#6c757d"  # Grey for parse errors

# --- Streamlit App ---
st.set_page_config(page_title="Flight Task Manager", layout="wide")
st.title("🛫 Flight Task Allocation System")

# --- Login ---
if "user" not in st.session_state:
    pin = st.text_input("Enter your 4-digit PIN", type="password")
    if st.button("Login"):
        if pin == "3320":
            st.session_state.user = "admin"
        else:
            for name, user_pin in STATIC_USERS.items():
                if pin == user_pin:
                    st.session_state.user = name
                    break
            else:
                st.error("Invalid PIN")

# --- Admin Dashboard ---
elif st.session_state.user == "admin":
    tab1, tab2, tab3, tab4 = st.tabs(["Flights", "Users", "History", "Logout"])

    with tab1:
        st.subheader("📋 Active Flights")
        uploaded_file = st.file_uploader("Upload Flight Schedule (.xlsx)", type=["xlsx"])
        if uploaded_file:
            df_int = pd.read_excel(uploaded_file, sheet_name='INT', header=None)
            df_dom = pd.read_excel(uploaded_file, sheet_name='DOM', header=None)
            combined_df = pd.concat([df_int, df_dom], ignore_index=True)
            created = 0
            for i, row in combined_df.iterrows():
                try:
                    flight = str(row[3]).strip()
                    if not flight.startswith("QF"):
                        continue

                    aircraft = str(row[1]).strip()
                    destination = str(row[4]).strip()
                    std_raw = row[5]
                    etd_raw = row[6]

                    if not flight or pd.isna(std_raw):
                        raise ValueError("Missing flight or STD")

                    def parse_time(value):
                        if isinstance(value, (int, float)):
                            total_seconds = int(value * 24 * 60 * 60)
                            hours = total_seconds // 3600
                            minutes = (total_seconds % 3600) // 60
                            return f"{hours:02d}:{minutes:02d}"
                        elif isinstance(value, str):
                            parsed = pd.to_datetime(value, errors='coerce')
                            if pd.isna(parsed):
                                parsed = pd.to_datetime(value, format="%H%M", errors='coerce')
                            if pd.isna(parsed):
                                raise ValueError(f"Unrecognized time format: {value}")
                            return parsed.strftime("%H:%M")
                        else:
                            raise ValueError(f"Unsupported time format: {value}")

                    std = parse_time(std_raw)
                    etd = parse_time(etd_raw)

                    c.execute("SELECT COUNT(*) FROM tasks WHERE flight = ? AND std = ?", (flight, std))
                    if c.fetchone()[0] == 0:
                        c.execute("INSERT INTO tasks (flight, aircraft, destination, std, etd) VALUES (?, ?, ?, ?, ?)",
                                  (flight, aircraft, destination, std, etd))
                        created += 1
                except Exception as e:
                    st.warning(f"⚠️ Row {i+1} skipped due to error: {e}")
            conn.commit()
            st.success(f"✅ {created} flight tasks created")

        tasks = c.execute("SELECT id, flight, aircraft, destination, std, etd, assigned_to FROM tasks WHERE complete = 0 ORDER BY std").fetchall()
        users = list(STATIC_USERS.keys())

        for t in tasks:
            st.markdown(f"**{t[1]}** Aircraft: {t[2]} Dest: {t[3]} STD: {t[4]} ETD: {t[5]}")
            cols = st.columns([2, 1, 1])
            assigned = cols[0].selectbox("Assign to", users, key=f"assign_{t[0]}", index=users.index(t[6]) if t[6] in users else 0)
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

        if st.button("❌ Delete All Tasks"):
            c.execute("DELETE FROM tasks")
            conn.commit()
            st.rerun()

    with tab2:
        st.subheader("👥 User Management")
        users_data = c.execute("SELECT id, name, pin, active FROM users").fetchall()
        for u in users_data:
            st.write(f"{u[1]} ({u[2]}) {'✅' if u[3] else '❌'}")
            cols = st.columns(3)
            if cols[0].button("Toggle Active", key=f"toggle_{u[0]}"):
                c.execute("UPDATE users SET active = NOT active WHERE id = ?", (u[0],))
                conn.commit()
                st.rerun()
            if cols[1].button("Delete", key=f"del_{u[0]}"):
                c.execute("DELETE FROM users WHERE id = ?", (u[0],))
                conn.commit()
                st.rerun()

        st.markdown("### ➕ Add User")
        new_name = st.text_input("Name")
        new_pin = st.text_input("PIN", type="password")
        if st.button("Create User"):
            c.execute("INSERT INTO users (name, pin) VALUES (?, ?)", (new_name, new_pin))
            conn.commit()
            st.success("User created")

    with tab3:
        st.subheader("🕓 Completed Tasks")
        completed = c.execute("SELECT id, flight, aircraft, destination, std, etd, assigned_to, completed_at FROM tasks WHERE complete = 1 ORDER BY completed_at DESC").fetchall()
        for t in completed:
            st.markdown(f"✅ **{t[1]}** ({t[2]}) → {t[3]} | STD: {t[4]} | ETD: {t[5]} | Completed by: {t[6]} at {t[7]}")
            if st.button("Mark as Incomplete", key=f"undo_{t[0]}"):
                c.execute("UPDATE tasks SET complete = 0, completed_at = NULL WHERE id = ?", (t[0],))
                conn.commit()
                st.rerun()

    with tab4:
        if st.button("🔒 Logout"):
            del st.session_state.user
            st.rerun()

# --- User View ---
else:
    st.sidebar.write(f"👤 Logged in as **{st.session_state.user}**")
    if st.sidebar.button("Logout"):
        del st.session_state.user
        st.rerun()

    tabs = st.tabs(["Tasks", "Future Tasks", "History"])

    with tabs[0]:
        tasks = c.execute(
            "SELECT id, flight, aircraft, destination, std, etd FROM tasks WHERE assigned_to = ? AND complete = 0 ORDER BY std",
            (st.session_state.user,)
        ).fetchall()

        if tasks:
            current = tasks[0]
            color = get_status_color(current[4])
            st.markdown("### 🟢 **Current Task**")
            with st.container():
                st.markdown(
                    f"""
                    <div style='padding: 20px; background-color: {color}; border-radius: 12px; color: white;'>
                        <h2 style='margin-bottom: 10px;'>✈️ {current[1]}</h2>
                        <p><strong>Aircraft:</strong> {current[2]}</p>
                        <p><strong>Destination:</strong> {current[3]}</p>
                        <p><strong>STD:</strong> {current[4]}</p>
                        <p><strong>ETD:</strong> {current[5]}</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                if st.button("✅ Mark Complete", key=f"done_{current[0]}"):
                    c.execute("UPDATE tasks SET complete = 1, completed_at = ? WHERE id = ?",
                              (datetime.datetime.now().isoformat(), current[0]))
                    conn.commit()
                    st.rerun()

        if len(tasks) > 1:
            next_task = tasks[1]
            st.markdown("### 🕑 **Next Task**")
            st.write(f"✈️ {next_task[1]} ({next_task[2]}) → {next_task[3]} | STD: {next_task[4]} | ETD: {next_task[5]}")

    with tabs[1]:
        for t in tasks[2:]:
            st.markdown(f"✈️ {t[1]} ({t[2]}) → {t[3]} | STD: {t[4]} | ETD: {t[5]}")

    with tabs[2]:
        completed = c.execute(
            "SELECT flight, aircraft, destination, std, etd, completed_at FROM tasks WHERE assigned_to = ? AND complete = 1 ORDER BY completed_at DESC",
            (st.session_state.user,)
        ).fetchall()
        for t in completed:
            st.markdown(f"✅ {t[0]} ({t[1]}) → {t[2]} | STD: {t[3]} | ETD: {t[4]} | Done at {t[5]}")
