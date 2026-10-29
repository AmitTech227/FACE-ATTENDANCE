import sqlite3
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "student_management.db"
FACES_DIR = BASE_DIR / "faces"
ATTENDANCE_DIR = BASE_DIR / "attendance"

FACES_DIR.mkdir(exist_ok=True)
ATTENDANCE_DIR.mkdir(exist_ok=True)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _column_names(conn, table):
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT DEFAULT ''
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                father_name TEXT DEFAULT '',
                roll_no TEXT DEFAULT '',
                course TEXT DEFAULT '',
                semester TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                email TEXT DEFAULT '',
                gender TEXT DEFAULT '',
                dob TEXT DEFAULT '',
                address TEXT DEFAULT '',
                status TEXT DEFAULT 'Active',
                department TEXT DEFAULT '',
                academic_year TEXT DEFAULT '',
                alternate_phone TEXT DEFAULT '',
                guardian_name TEXT DEFAULT '',
                guardian_phone TEXT DEFAULT '',
                blood_group TEXT DEFAULT '',
                admission_date TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Keeps compatibility with the older SBBSU database.
        migrations = {
            "father_name": "TEXT DEFAULT ''",
            "roll_no": "TEXT DEFAULT ''",
            "course": "TEXT DEFAULT ''",
            "semester": "TEXT DEFAULT ''",
            "phone": "TEXT DEFAULT ''",
            "email": "TEXT DEFAULT ''",
            "gender": "TEXT DEFAULT ''",
            "dob": "TEXT DEFAULT ''",
            "address": "TEXT DEFAULT ''",
            "status": "TEXT DEFAULT 'Active'",
            "department": "TEXT DEFAULT ''",
            "academic_year": "TEXT DEFAULT ''",
            "alternate_phone": "TEXT DEFAULT ''",
            "guardian_name": "TEXT DEFAULT ''",
            "guardian_phone": "TEXT DEFAULT ''",
            "blood_group": "TEXT DEFAULT ''",
            "admission_date": "TEXT DEFAULT ''",
            "created_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
            "updated_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
        }
        existing = _column_names(conn, "students")
        for col, definition in migrations.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE students ADD COLUMN {col} {definition}")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS face_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL UNIQUE,
                sample_count INTEGER DEFAULT 0,
                model_label INTEGER UNIQUE,
                registered_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                attendance_date TEXT NOT NULL,
                attendance_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Present',
                method TEXT NOT NULL DEFAULT 'Face Recognition',
                UNIQUE(student_id, attendance_date),
                FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE
            )
        """)

        defaults = {
            "institution": "SBBSU",
            "system_name": "Face Attendance System",
            "theme": "light",
            "camera_index": "0",
        }
        for key, value in defaults.items():
            conn.execute(
                "INSERT OR IGNORE INTO app_settings(key, value) VALUES (?, ?)",
                (key, value)
            )
        conn.commit()


def get_setting(key, default=""):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key=?", (key,)
        ).fetchone()
        return row["value"] if row else default


def set_setting(key, value):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO app_settings(key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """, (key, str(value)))
        conn.commit()


def add_student(data):
    keys = [
        "student_id", "name", "father_name", "roll_no", "course", "semester",
        "phone", "email", "gender", "dob", "address", "status", "department",
        "academic_year", "alternate_phone", "guardian_name", "guardian_phone",
        "blood_group", "admission_date"
    ]
    values = [data.get(k, "") for k in keys]
    with get_connection() as conn:
        cur = conn.execute(
            f"INSERT INTO students ({','.join(keys)}) VALUES ({','.join('?' for _ in keys)})",
            values
        )
        conn.commit()
        return cur.lastrowid


def update_student(original_student_id, data):
    keys = [
        "student_id", "name", "father_name", "roll_no", "course", "semester",
        "phone", "email", "gender", "dob", "address", "status", "department",
        "academic_year", "alternate_phone", "guardian_name", "guardian_phone",
        "blood_group", "admission_date"
    ]
    values = [data.get(k, "") for k in keys]
    with get_connection() as conn:
        cur = conn.execute(
            f"""UPDATE students
                SET {','.join(k + '=?' for k in keys)},
                    updated_at=CURRENT_TIMESTAMP
                WHERE student_id=?""",
            values + [original_student_id]
        )
        conn.commit()
        return cur.rowcount > 0


def delete_student(student_id):
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM students WHERE student_id=?", (student_id,))
        conn.commit()
        return cur.rowcount > 0


def get_student(student_id):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM students WHERE student_id=?", (student_id,)
        ).fetchone()


def get_students(search=""):
    with get_connection() as conn:
        if search:
            like = f"%{search}%"
            return conn.execute("""
                SELECT * FROM students
                WHERE student_id LIKE ?
                   OR name LIKE ?
                   OR father_name LIKE ?
                   OR roll_no LIKE ?
                   OR course LIKE ?
                   OR department LIKE ?
                   OR phone LIKE ?
                   OR email LIKE ?
                ORDER BY id DESC
            """, (like,) * 8).fetchall()
        return conn.execute("SELECT * FROM students ORDER BY id DESC").fetchall()


def student_count():
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]


def active_student_count():
    with get_connection() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM students WHERE status='Active'"
        ).fetchone()[0]


def inactive_student_count():
    with get_connection() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM students WHERE status!='Active'"
        ).fetchone()[0]


def course_count():
    with get_connection() as conn:
        return conn.execute(
            "SELECT COUNT(DISTINCT NULLIF(TRIM(course),'')) FROM students"
        ).fetchone()[0]


def department_count():
    with get_connection() as conn:
        return conn.execute(
            "SELECT COUNT(DISTINCT NULLIF(TRIM(department),'')) FROM students"
        ).fetchone()[0]


def next_face_label():
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COALESCE(MAX(model_label), 0) + 1 AS n FROM face_profiles"
        ).fetchone()
        return int(row["n"])


def save_face_profile(student_id, sample_count, model_label):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO face_profiles(student_id, sample_count, model_label)
            VALUES (?, ?, ?)
            ON CONFLICT(student_id) DO UPDATE SET
                sample_count=excluded.sample_count,
                model_label=excluded.model_label,
                updated_at=CURRENT_TIMESTAMP
        """, (student_id, sample_count, model_label))
        conn.commit()


def delete_face_profile(student_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM face_profiles WHERE student_id=?", (student_id,))
        conn.commit()


def get_face_profile(student_id):
    with get_connection() as conn:
        return conn.execute(
            """SELECT fp.*, s.name, s.roll_no, s.course
               FROM face_profiles fp
               JOIN students s ON s.student_id=fp.student_id
               WHERE fp.student_id=?""", (student_id,)
        ).fetchone()


def get_face_profiles():
    with get_connection() as conn:
        return conn.execute("""
            SELECT fp.*, s.name, s.roll_no, s.course, s.department
            FROM face_profiles fp
            JOIN students s ON s.student_id=fp.student_id
            ORDER BY s.name
        """).fetchall()


def mark_attendance(student_id, status="Present", method="Face Recognition"):
    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    time = now.strftime("%H:%M:%S")
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM attendance WHERE student_id=? AND attendance_date=?",
            (student_id, date)
        ).fetchone()
        if existing:
            return False
        conn.execute("""
            INSERT INTO attendance
                (student_id, attendance_date, attendance_time, status, method)
            VALUES (?, ?, ?, ?, ?)
        """, (student_id, date, time, status, method))
        conn.commit()
        return True


def attendance_today():
    date = datetime.now().strftime("%Y-%m-%d")
    with get_connection() as conn:
        return conn.execute("""
            SELECT a.*, s.name, s.roll_no, s.course, s.department
            FROM attendance a
            JOIN students s ON s.student_id=a.student_id
            WHERE a.attendance_date=?
            ORDER BY a.attendance_time DESC
        """, (date,)).fetchall()


def attendance_count_today():
    date = datetime.now().strftime("%Y-%m-%d")
    with get_connection() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM attendance WHERE attendance_date=?", (date,)
        ).fetchone()[0]


def get_attendance(date_text=""):
    with get_connection() as conn:
        if date_text:
            return conn.execute("""
                SELECT a.*, s.name, s.roll_no, s.course, s.department
                FROM attendance a
                JOIN students s ON s.student_id=a.student_id
                WHERE a.attendance_date=?
                ORDER BY a.attendance_date DESC, a.attendance_time DESC
            """, (date_text,)).fetchall()
        return conn.execute("""
            SELECT a.*, s.name, s.roll_no, s.course, s.department
            FROM attendance a
            JOIN students s ON s.student_id=a.student_id
            ORDER BY a.attendance_date DESC, a.attendance_time DESC
        """).fetchall()


def attendance_stats_for_student(student_id):
    with get_connection() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM attendance WHERE student_id=? AND status='Present'",
            (student_id,)
        ).fetchone()[0]


init_db()
def clear_attendance_today():
    date_text = datetime.now().strftime("%Y-%m-%d")

    with get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM attendance WHERE attendance_date = ?",
            (date_text,)
        )
        conn.commit()

        return cur.rowcount