# database.py
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Create notes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        
        # Create tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                deadline TEXT,
                completed INTEGER DEFAULT 0
            )
        """)
        
        # Create alarms table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alarms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time TEXT NOT NULL,
                label TEXT,
                active INTEGER DEFAULT 1
            )
        """)
        conn.commit()

# --- Notes Functions ---

def add_note(content: str) -> str:
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO notes (content, created_at) VALUES (?, ?)",
                (content, created_at)
            )
            conn.commit()
            return f"Catatan berhasil disimpan: '{content}'"
    except Exception as e:
        return f"Gagal menyimpan catatan: {str(e)}"

def get_notes() -> list:
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, content, created_at FROM notes ORDER BY id DESC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception:
        return []

def delete_note(note_id: int) -> str:
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            conn.commit()
            if cursor.rowcount > 0:
                return f"Catatan dengan ID {note_id} berhasil dihapus."
            else:
                return f"Catatan dengan ID {note_id} tidak ditemukan."
    except Exception as e:
        return f"Gagal menghapus catatan: {str(e)}"

# --- Tasks Functions ---

def add_task(title: str, deadline: str = "") -> str:
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO tasks (title, deadline, completed) VALUES (?, ?, 0)",
                (title, deadline)
            )
            conn.commit()
            deadline_str = f" dengan tenggat {deadline}" if deadline else ""
            return f"Tugas berhasil ditambahkan: '{title}'{deadline_str}"
    except Exception as e:
        return f"Gagal menambahkan tugas: {str(e)}"

def get_tasks() -> list:
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, deadline, completed FROM tasks ORDER BY completed ASC, id DESC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception:
        return []

def complete_task(task_id: int) -> str:
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE tasks SET completed = 1 WHERE id = ?", (task_id,))
            conn.commit()
            if cursor.rowcount > 0:
                return f"Tugas dengan ID {task_id} ditandai selesai."
            else:
                return f"Tugas dengan ID {task_id} tidak ditemukan."
    except Exception as e:
        return f"Gagal menyelesaikan tugas: {str(e)}"

def delete_task(task_id: int) -> str:
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            if cursor.rowcount > 0:
                return f"Tugas dengan ID {task_id} berhasil dihapus."
            else:
                return f"Tugas dengan ID {task_id} tidak ditemukan."
    except Exception as e:
        return f"Gagal menghapus tugas: {str(e)}"

# --- Alarms Functions ---

def add_alarm(time: str, label: str = "") -> str:
    # time format should be HH:MM
    try:
        # Validate time format
        datetime.strptime(time, "%H:%M")
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO alarms (time, label, active) VALUES (?, ?, 1)",
                (time, label)
            )
            conn.commit()
            label_str = f" ({label})" if label else ""
            return f"Alarm berhasil diatur pada pukul {time}{label_str}."
    except ValueError:
        return "Format waktu salah. Gunakan format 24 jam HH:MM (contoh: 07:00, 18:30)."
    except Exception as e:
        return f"Gagal menambahkan alarm: {str(e)}"

def get_alarms() -> list:
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, time, label, active FROM alarms ORDER BY time ASC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception:
        return []

def toggle_alarm(alarm_id: int, active: int) -> str:
    # active should be 1 or 0
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE alarms SET active = ? WHERE id = ?", (active, alarm_id))
            conn.commit()
            status = "diaktifkan" if active == 1 else "dinonaktifkan"
            if cursor.rowcount > 0:
                return f"Alarm dengan ID {alarm_id} berhasil {status}."
            else:
                return f"Alarm dengan ID {alarm_id} tidak ditemukan."
    except Exception as e:
        return f"Gagal mengubah status alarm: {str(e)}"

def delete_alarm(alarm_id: int) -> str:
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM alarms WHERE id = ?", (alarm_id,))
            conn.commit()
            if cursor.rowcount > 0:
                return f"Alarm dengan ID {alarm_id} berhasil dihapus."
            else:
                return f"Alarm dengan ID {alarm_id} tidak ditemukan."
    except Exception as e:
        return f"Gagal menghapus alarm: {str(e)}"

# Initialize DB on import
init_db()
