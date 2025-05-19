import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# DB SETUP
conn = sqlite3.connect('flight_tasks.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    pin TEXT,
    active INTEGER DEFAULT 1
)''')
c.execute('''CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flight TEXT,
    aircraft TEXT,
    std TEXT,
    etd TEXT,
    destination TEXT,
    assigned_to TEXT,
    complete INTEGER DEFAULT 0,
    notes TEXT,
    completed_at TEXT
)''')
conn.commit()

st.set_page_config(page_title="Flight Task Manager", layout="wide")

# LOGIN
if "auth" not in st.session_state:
    st.session_state.auth = None
    st.session_state.username = ""

if st.session_state.auth is None:
    st.title("🔒 Enter 4-digit PIN")
    pin_input = st.text_input("PIN", type="password")
    if st.button("Login"):
        if pin_input == "3320":
            st.session_state.auth = "admin"
        else:
            user = c.execute("SELECT name FROM users WHERE pin = ? AND active = 1", (pin_input,)).fetchone()
            if user:
                st.session_state.auth = "user"
                st.session_state.username = user[0]
            else:
                st.error("Invalid PIN")

# ADMIN DASHBOARD
elif st.session_state.auth == "admin":
    st.sidebar.title("Admin")
    section = st.sidebar.radio("Go to", ["Users", "Flights"])

    if section == "Users":
        st.header("User Management")
        with st.form("Create User"):
            name = st.text_input("Name")
            pin = st.text_input("4-digit PIN")
            if st.form_submit_button("Create"):
                c.execute("INSERT INTO users (name, pin) VALUES (?, ?)", (name, pin))
                conn.commit()
                st.success("User created")

        st.subheader("Existing Users")
        users = c.execute("SELECT * FROM users").fetchall()
        for u in users:
            col1, col2, col3, col4 = st.columns(4)
            col1.write(f"{u[1]}")
            col2.write(f"PIN: {u[2]}")
            if col3.button("Toggle Active" if u[3] else "Activate", key=f"toggle_{u[0]}"):
                c.execute("UPDATE users SET active = ? WHERE id = ?", (0 if u[3] else 1, u[0]))
                conn.commit()
            if col4.button("Delete", key=f"delete_{u[0]}"):
                c.execute("DELETE FROM users WHERE id = ?", (u[0],))
                conn.commit()

    elif section == "Flights":
        st.header("Flight Tasks")
        uploaded_file = st.file_uploader("Upload XLSX File", type="xlsx")

        if uploaded_file:
            df_int = pd.read_excel(uploaded_file, sheet_name='INT', header=None)
            df_dom = pd.read_excel(uploaded_file, sheet_name='DOM', header=None)
            combined_df = pd.concat([df_int, df_dom], ignore_index=True)
            created = 0
            for i, row in combined_df.iterrows():
                try:
                    flight = str(row[8]).strip()
                    if not flight.startswith("QF"):
                        continue

                    aircraft = str(row[1]).strip()
                    destination = str(row[9]).strip()
                    std_raw = row[10]
                    etd_raw = row[11]

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
                                raise ValueError(f"Unrecognized string format: {value}")
                            return parsed.strftime("%H:%M")
                        else:
                            return None

                    std = parse_time(std_raw)
                    etd = parse_time(etd_raw)

                    c.execute("SELECT COUNT(*) FROM tasks WHERE flight = ? AND std = ?", (flight, std))
                    if c.fetchone()[0] == 0:
                        c.execute("INSERT INTO tasks (flight, aircraft, std, etd, destination) VALUES (?, ?, ?, ?, ?)",
                                  (flight, aircraft, std, etd, destination))
                        created += 1
                except Exception as e:
                    st.warning(f"⚠️ Row {i+1} skipped: {e}")
            conn.commit()
            st.success(f"✅ {created} flight tasks created")

        st.subheader("Current Tasks")
        tasks = c.execute("SELECT id, flight, aircraft, std, etd, destination, assigned_to, notes FROM tasks WHERE complete = 0 ORDER BY std").fetchall()
        for t in tasks:
            st.markdown(f"**{t[1]}** | Aircraft: {t[2]} | Dest: {t[5]} | STD: {t[3]} | ETD: {t[4]} | Assigned to: {t[6] or 'Unassigned'}")
            col1, col2, col3 = st.columns([3, 3, 1])
            with col1:
                users = [u[1] for u in c.execute("SELECT name FROM users WHERE active = 1").fetchall()]
                assigned_user = st.selectbox("Assign to", [""] + users, index=users.index(t[6]) + 1 if t[6] in users else 0, key=f"assign_{t[0]}")
                if assigned_user:
                    c.execute("UPDATE tasks SET assigned_to = ? WHERE id = ?", (assigned_user, t[0]))
                    conn.commit()
            with col2:
                new_note = st.text_input("Add/Edit Note", value=t[7] or "", key=f"note_{t[0]}")
                if st.button("Save Note", key=f"savenote_{t[0]}"):
                    c.execute("UPDATE tasks SET notes = ? WHERE id = ?", (new_note, t[0]))
                    conn.commit()
            with col3:
                if st.button("Delete Task", key=f"del_{t[0]}"):
                    c.execute("DELETE FROM tasks WHERE id = ?", (t[0],))
                    conn.commit()
                    st.experimental_rerun()

        if st.button("Delete All Tasks"):
            c.execute("DELETE FROM tasks")
            conn.commit()
            st.experimental_rerun()

        st.subheader("History")
        history = c.execute("SELECT id, flight, aircraft, std, etd, destination, assigned_to, completed_at, notes FROM tasks WHERE complete = 1 ORDER BY completed_at DESC").fetchall()
        for h in history:
            st.markdown(f"✅ {h[1]} | Aircraft: {h[2]} | Dest: {h[5]} | STD: {h[3]} | ETD: {h[4]} | Assigned to: {h[6]} | Done at: {h[7]} | Note: {h[8] or 'None'}")
            if st.button("Mark as Incomplete", key=f"undo_{h[0]}"):
                c.execute("UPDATE tasks SET complete = 0, completed_at = NULL WHERE id = ?", (h[0],))
                conn.commit()
                st.experimental_rerun()

# USER DASHBOARD
elif st.session_state.auth == "user":
    st.sidebar.title(f"👤 {st.session_state.username}")
    tab = st.sidebar.radio("", ["Tasks", "Future Tasks", "History"])

    if tab == "Tasks":
        st.header("Your Tasks")
        tasks = c.execute("SELECT id, flight, aircraft, std, etd, destination, notes FROM tasks WHERE assigned_to = ? AND complete = 0 ORDER BY std", (st.session_state.username,)).fetchall()
        if tasks:
            current = tasks[0]
            std_hour = int(current[3].split(":")[0])
            color = "green" if std_hour >= 12 else "blue"
            st.markdown(
                f"""
                <div style='padding: 20px; background-color: {color}; border-radius: 12px; color: white;'>
                    <h2 style='margin-bottom: 10px;'>✈️ {current[1]}</h2>
                    <p><strong>Aircraft:</strong> {current[2]}</p>
                    <p><strong>Destination:</strong> {current[5]}</p>
                    <p><strong>STD:</strong> {current[3]}</p>
                    <p><strong>ETD:</strong> {current[4]}</p>
                    <p><strong>Note:</strong> {current[6] or 'None'}</p>
                </div>
                """,
                unsafe_allow_html=True
            )
            if st.button("Push Complete"):
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                c.execute("UPDATE tasks SET complete = 1, completed_at = ? WHERE id = ?", (now, current[0]))
                conn.commit()
                st.experimental_rerun()
        else:
            st.info("No tasks assigned")

    elif tab == "Future Tasks":
        st.header("Upcoming Tasks")
        tasks = c.execute("SELECT flight, aircraft, std, etd, destination, notes FROM tasks WHERE assigned_to = ? AND complete = 0 ORDER BY std", (st.session_state.username,)).fetchall()
        for t in tasks[1:]:
            st.markdown(f"✈️ {t[0]} | Aircraft: {t[1]} | Dest: {t[4]} | STD: {t[2]} | ETD: {t[3]} | Note: {t[5] or 'None'}")

    elif tab == "History":
        st.header("Completed Tasks")
        history = c.execute("SELECT flight, aircraft, std, etd, destination, completed_at, notes FROM tasks WHERE assigned_to = ? AND complete = 1 ORDER BY completed_at DESC", (st.session_state.username,)).fetchall()
        for h in history:
            st.markdown(f"✅ {h[0]} | Aircraft: {h[1]} | Dest: {h[4]} | STD: {h[2]} | ETD: {h[3]} | Done at: {h[5]} | Note: {h[6] or 'None'}")
