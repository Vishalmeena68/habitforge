import streamlit as st
import sqlite3
from datetime import date, timedelta

# --- PAGE CONFIG ---
st.set_page_config(page_title="HabitForge", page_icon="🔥", layout="centered")

# --- DATABASE SETUP ---
DB_NAME = "habits.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            icon TEXT DEFAULT '🎯',
            created_at DATE NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS habit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER,
            log_date DATE,
            completed INTEGER,
            UNIQUE(habit_id, log_date),
            FOREIGN KEY(habit_id) REFERENCES habits(id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- DATABASE OPERATIONS ---
def get_habits():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, name, icon FROM habits ORDER BY id ASC")
    rows = c.fetchall()
    conn.close()
    return rows

def add_habit(name, icon):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO habits (name, icon, created_at) VALUES (?, ?, ?)", (name, icon, date.today()))
    conn.commit()
    conn.close()

def delete_habit(habit_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM habit_logs WHERE habit_id = ?", (habit_id,))
    c.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
    conn.commit()
    conn.close()

def toggle_log(habit_id, log_date, status):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    val = 1 if status else 0
    c.execute('''
        INSERT INTO habit_logs (habit_id, log_date, completed)
        VALUES (?, ?, ?)
        ON CONFLICT(habit_id, log_date) DO UPDATE SET completed = excluded.completed
    ''', (habit_id, log_date, val))
    conn.commit()
    conn.close()

def is_done_today(habit_id, today_date):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT completed FROM habit_logs WHERE habit_id = ? AND log_date = ?", (habit_id, today_date))
    row = c.fetchone()
    conn.close()
    return bool(row and row[0] == 1)

# --- ROBUST STREAK ENGINE ---
def calculate_streak(habit_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT log_date FROM habit_logs WHERE habit_id = ? AND completed = 1 ORDER BY log_date DESC", (habit_id,))
    logs = [row[0] for row in c.fetchall()]
    conn.close()

    if not logs:
        return 0

    log_dates = {date.fromisoformat(d) for d in logs}
    today = date.today()
    yesterday = today - timedelta(days=1)

    # Agar aaj ya kal me se koi bhi done nahi hai, streak break ho chuki hai
    if today not in log_dates and yesterday not in log_dates:
        return 0

    current = today if today in log_dates else yesterday
    streak = 0

    while current in log_dates:
        streak += 1
        current -= timedelta(days=1)

    return streak

# --- UI / DASHBOARD ---
st.title("🔥 HabitForge")
st.caption("Build consistency. Stay accountable.")

today = date.today()
habits = get_habits()

# --- ADD NEW HABIT FORM ---
with st.expander("➕ Add New Habit", expanded=False):
    with st.form("new_habit_form", clear_on_submit=True):
        col1, col2 = st.columns([1, 4])
        icon = col1.selectbox("Icon", ["💧", "📖", "🏋️", "💻", "🧘", "🥗", "🎯"])
        name = col2.text_input("Habit Name", placeholder="e.g. Read 20 mins")
        submitted = st.form_submit_button("Save Habit")
        if submitted and name.strip():
            add_habit(name.strip(), icon)
            st.success(f"Added {name}!")
            st.rerun()

st.divider()

# --- METRICS & PROGRESS ---
if habits:
    completed_count = sum(1 for h in habits if is_done_today(h[0], today))
    total_count = len(habits)
    progress = completed_count / total_count if total_count > 0 else 0

    st.subheader("Today's Progress")
    st.progress(progress)
    st.write(f"**{completed_count} / {total_count}** habits completed today ({int(progress * 100)}%)")

    st.divider()

    # --- HABITS LIST ---
    st.subheader("Your Habits")
    for habit_id, habit_name, icon in habits:
        done = is_done_today(habit_id, today)
        streak = calculate_streak(habit_id)

        c1, c2, c3 = st.columns([5, 2, 1])
        
        # Checkbox to complete
        new_status = c1.checkbox(
            f"{icon} {habit_name}",
            value=done,
            key=f"chk_{habit_id}"
        )
        
        if new_status != done:
            toggle_log(habit_id, today, new_status)
            st.rerun()

        # Display Streak
        c2.markdown(f"🔥 **{streak} days**")

        # Delete Button
        if c3.button("🗑️", key=f"del_{habit_id}"):
            delete_habit(habit_id)
            st.rerun()

    # --- 7-DAY RECENT HISTORY ---
    st.divider()
    st.subheader("Weekly Activity (Last 7 Days)")

    days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    cols = st.columns(7)

    for i, d in enumerate(days):
        with cols[i]:
            st.write(f"**{d.strftime('%a')}**")
            st.caption(d.strftime("%d %b"))
            # Count habits done on this date
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM habit_logs WHERE log_date = ? AND completed = 1", (d,))
            cnt = c.fetchone()[0]
            conn.close()

            if cnt == total_count and total_count > 0:
                st.write("🟩")
            elif cnt > 0:
                st.write("🟨")
            else:
                st.write("⬜")
else:
    st.info("Abhi koi habit nahi hai! Upar click karke apni pehli habit add karo.")
