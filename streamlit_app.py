import streamlit as st
import sqlite3
import pandas as pd
import datetime
import time
from io import BytesIO

# ✅ Must be the first Streamlit command
st.set_page_config(page_title="Flight Task Manager", layout="centered")

# DB Setup
conn = sqlite3.connect('flight_tasks.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, active INTEGER DEFAULT 1, pin TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flight TEXT,
    aircraft TEXT,
    std TEXT,
    assigned_to TEXT,
    complete INTEGER DEFAULT 0,
    completed_at TEXT,
    notes TEXT
)''')
conn.commit()

# Auth Functions
def verify_pin(pin):
    if pin == "3320":
        return "admin"
    c.execute("SELECT username FROM users WHERE pin = ? AND active = 1", (pin,))
    row = c.fetchone()
    return row[0] if row else None

# UI Functions
def admin_dashboard():
    st.title("👨‍✈️ Admin Dashboard")
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
                    flight = str(row[8]).strip()
                    if not flight.startswith("QF"):
                        continue

                    aircraft = str(row[1]).strip()
                    std_raw = row[10]

                    if not flight or pd.isna(std_raw):
                        raise ValueError("Missing flight or STD")

                    try:
                        if isinstance(std_raw, (int, float)):
                            total_seconds = int(std_raw * 24 * 60 * 60)
                            hours = total_seconds // 3600
                            minutes = (total_seconds % 3600) // 60
                            std = f"{hours:02d}:{minutes:02d}"
                        elif isinstance(std_raw, str):
                            parsed = pd.to_datetime(std_raw, errors='coerce')
                            if pd.isna(parsed):
                                parsed = pd.to_datetime(std_raw, format="%H%M", errors='coerce')
                            if pd.isna(parsed):
                                raise ValueError(f"Unrecognized string format for STD: {std_raw}")
                            std = parsed.strftime("%H:%M")
                        else:
                            raise ValueError(f"Unsupported STD type: {type(std_raw)}")
                    except Exception as inner_e:
                        raise ValueError(f"Failed to parse STD: {std_raw} ({inner_e})")

                    c.execute("SELECT COUNT(*) FROM tasks WHERE flight = ? AND std = ?", (flight, std))
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

        filter_text = st.text_input("Search by Flight/User")
        tasks = c.execute("SELECT id, flight, aircraft, std, assigned_to, notes FROM tasks WHERE complete = 0 ORDER BY std").fetchall()
        users = [row[0] for row in c.execute("SELECT username FROM users WHERE active = 1").fetchall()]

        filtered = [t for t in tasks if filter_text.lower() in (t[1] + t[4] if t[4] else '').lower()]

        selected_tasks = []
        for t in filtered:
            st.markdown(f"**{t[1]}** Aircraft: {t[2]} STD: {t[3]}")
            cols = st.columns([1, 1, 1, 1])
            assigned = cols[0].selectbox("Assign to", users, key=f"assign_{t[0]}", index=users.index(t[4]) if t[4] in users else 0)
            if cols[1].button("Complete", key=f"complete_{t[0]}"):
                c.execute("UPDATE tasks SET complete = 1, completed_at = ? WHERE id = ?", (datetime.datetime.now().isoformat(), t[0]))
                conn.commit()
                st.rerun()
            if cols[2].button("Delete", key=f"delete_{t[0]}"):
                c.execute("DELETE FROM tasks WHERE id = ?", (t[0],))
                conn.commit()
                st.rerun()
            if cols[3].checkbox("Select", key=f"select_{t[0]}"):
                selected_tasks.append(t[0])

            new_std = st.text_input("Edit STD", value=t[3], key=f"edit_std_{t[0]}")
            new_flight = st.text_input("Edit Flight", value=t[1], key=f"edit_flight_{t[0]}")
            new_ac = st.text_input("Edit Aircraft", value=t[2], key=f"edit_ac_{t[0]}")
            new_note = st.text_area("Notes", value=t[5] or "", key=f"edit_note_{t[0]}")
            if st.button("Save Edits", key=f"save_{t[0]}"):
                c.execute("UPDATE tasks SET std = ?, flight = ?, aircraft = ?, notes = ?, assigned_to = ? WHERE id = ?", (new_std, new_flight, new_ac, new_note, assigned, t[0]))
                conn.commit()
                st.success("Task updated")

        if selected_tasks:
            bulk_user = st.selectbox("Bulk Assign Selected To:", users)
            if st.button("Assign Selected"):
                for tid in selected_tasks:
                    c.execute("UPDATE tasks SET assigned_to = ? WHERE id = ?", (bulk_user, tid))
                conn.commit()
                st.rerun()

        st.download_button("Export Active Tasks to CSV", pd.DataFrame(filtered, columns=["ID", "Flight", "Aircraft", "STD", "Assigned To", "Notes"]).to_csv(index=False), file_name="active_tasks.csv")

    with tabs[2]:
        st.header("📦 History")
        completed = c.execute("SELECT id, flight, aircraft, std, completed_at FROM tasks WHERE complete = 1 ORDER BY completed_at DESC").fetchall()
        st.download_button("Export Completed Tasks to CSV", pd.DataFrame(completed, columns=["ID", "Flight", "Aircraft", "STD", "Completed At"]).to_csv(index=False), file_name="completed_tasks.csv")
        for t in completed:
            col1, col2 = st.columns([4, 1])
            col1.markdown(f"**{t[1]}** Aircraft: {t[2]} STD: {t[3]} Completed: {t[4]}")
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
            return "#ff0000"
        elif diff <= 15:
            return "#ffa500"
        elif diff <= 30:
            return "#4caf50"
        else:
            return "#cccccc"

    with tabs[0]:
        st.header("🛠️ Your Tasks")
        tasks = c.execute("SELECT id, flight, aircraft, std, notes FROM tasks WHERE assigned_to = ? AND complete = 0 ORDER BY std", (username,)).fetchall()

        if tasks:
            current = tasks[0]
            color = get_status_color(current[3])
            st.markdown("### 🟢 **Current Task**")
            with st.container():
                st.markdown(f"""
                <div style='padding: 20px; background-color: {color}; border-radius: 12px; color: white;'>
                    <h2 style='margin-bottom: 10px;'>✈️ {current[1]}</h2>
                    <p><strong>Aircraft:</strong> {current[2]}</p>
                    <p><strong>STD:</strong> {current[3]}</p>
                    <p><strong>Notes:</strong> {current[4] or ''}</p>
                </div>
                """, unsafe_allow_html=True)
                if st.button("✅ Complete Current", key=f"complete_{current[0]}"):
                    c.execute("UPDATE tasks SET complete = 1, completed_at = ? WHERE id = ?", (datetime.now().isoformat(), current[0]))
                    conn.commit()
                    st.rerun()

            if len(tasks) > 1:
                next_task = tasks[1]
                color = get_status_color(next_task[3])
                st.markdown("### 🟡 **Next Task**")
                with st.container():
                    st.markdown(f"""
                    <div style='padding: 20px; background-color: {color}; border-radius: 12px; color: white;'>
                        <h3 style='margin-bottom: 10px;'>✈️ {next_task[1]}</h3>
                        <p><strong>Aircraft:</strong> {next_task[2]}</p>
                        <p><strong>STD:</strong> {next_task[3]}</p>
                        <p><strong>Notes:</strong> {next_task[4] or ''}</p>
                    </div>
                    """, unsafe_allow_html=True)

        else:
            st.info("You currently have no assigned tasks.")

        if len(tasks) > 2:
            with st.expander("📜 View Future Tasks"):
                for t in tasks[2:]:
                    col1, col2 = st.columns([4, 1])
                    col1.markdown(f"**{t[1]}** | Aircraft: {t[2]} | STD: {t[3]} | Notes: {t[4] or ''}")
                    if col2.button("Complete", key=f"user_complete_future_{t[0]}"):
                        c.execute("UPDATE tasks SET complete = 1, completed_at = ? WHERE id = ?", (datetime.now().isoformat(), t[0]))
                        conn.commit()
                        st.rerun()

    with tabs[1]:
        st.header("📦 Completed Tasks")
        completed = c.execute("SELECT id, flight, aircraft, std, completed_at FROM tasks WHERE assigned_to = ? AND complete = 1 ORDER BY completed_at DESC", (username,)).fetchall()
        for t in completed:
            col1, col2 = st.columns([4, 1])
            col1.markdown(f"**{t[1]}** | Aircraft: {t[2]} | STD: {t[3]} | Done: {t[4]}")
            if col2.button("🔁 Reactivate", key=f"reactivate_{t[0]}"):
                c.execute("UPDATE tasks SET complete = 0, completed_at = NULL WHERE id = ?", (t[0],))
                conn.commit()
                st.rerun()

# App Entry
with st.sidebar:
    if "user" in st.session_state:
        st.markdown(f"**Logged in as:** {st.session_state['user']}")
        if st.button("Logout"):
            del st.session_state["user"]
            st.rerun()
    else:
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
        user_dashboard(st.session_state.user)
