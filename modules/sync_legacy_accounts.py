from db_config import get_connection


TEACHER_SYNC_KEY = "legacy_users_to_teachers_v2"
STUDENT_SYNC_KEY = "legacy_users_to_students_v2"


def _ensure_sync_table(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS system_sync_log (
            sync_key VARCHAR(120) PRIMARY KEY,
            details VARCHAR(255) DEFAULT NULL,
            executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def _ensure_teachers_table(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS teachers (
            teacher_id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) NOT NULL UNIQUE,
            full_name VARCHAR(120) NOT NULL,
            email VARCHAR(150) NOT NULL UNIQUE,
            phone VARCHAR(15) NOT NULL,
            dob DATE NOT NULL,
            gender ENUM('Male','Female','Other') NOT NULL,
            department VARCHAR(120) NOT NULL,
            designation VARCHAR(120) NOT NULL,
            qualification VARCHAR(150) NOT NULL,
            specialization VARCHAR(150) DEFAULT NULL,
            experience_years INT NOT NULL DEFAULT 0,
            date_of_joining DATE NOT NULL,
            address TEXT NOT NULL,
            role VARCHAR(20) NOT NULL DEFAULT 'teacher',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_teachers_department (department),
            INDEX idx_teachers_full_name (full_name),
            INDEX idx_teachers_role (role)
        )
        """
    )


def _is_sync_done(cursor, sync_key):
    cursor.execute("SELECT 1 FROM system_sync_log WHERE sync_key=%s", (sync_key,))
    return cursor.fetchone() is not None


def _mark_sync_done(cursor, sync_key, details):
    cursor.execute(
        """
        INSERT INTO system_sync_log (sync_key, details)
        VALUES (%s, %s)
        """,
        (sync_key, details),
    )


def _run_teacher_sync(cursor):
    if _is_sync_done(cursor, TEACHER_SYNC_KEY):
        return 0

    cursor.execute(
        """
        INSERT INTO teachers
        (username, full_name, email, phone, dob, gender, department, designation,
         qualification, specialization, experience_years, date_of_joining, address, role)
        SELECT
            u.username,
            u.username,
            COALESCE(NULLIF(u.email, ''), CONCAT(u.username, '@example.com')),
            CASE
                WHEN u.mobile REGEXP '^[0-9]{10}$' THEN u.mobile
                ELSE '0000000000'
            END,
            '1990-01-01',
            'Other',
            'General',
            'Teacher',
            'Not Provided',
            NULL,
            0,
            CURDATE(),
            'Not Provided',
            'teacher'
        FROM users u
        LEFT JOIN teachers t ON t.username = u.username
        WHERE u.role = 'teacher' AND t.teacher_id IS NULL
        """
    )
    count = cursor.rowcount
    _mark_sync_done(cursor, TEACHER_SYNC_KEY, f"teachers={count}")
    return count


def _run_student_sync(cursor):
    if _is_sync_done(cursor, STUDENT_SYNC_KEY):
        return 0

    cursor.execute(
        """
        INSERT INTO students
        (name, enrollment_no, course, section, dob, email, phone, semester, department)
        SELECT
            COALESCE(NULLIF(u.username, ''), 'Student'),
            COALESCE(
                NULLIF(u.enrollment_no, ''),
                CONCAT('AUTO-', UPPER(LEFT(REPLACE(u.username, ' ', ''), 20)), '-', LPAD(u.id, 4, '0'))
            ) AS resolved_enrollment,
            'General Course',
            'A',
            '2000-01-01',
            COALESCE(NULLIF(u.email, ''), CONCAT(u.username, '@example.com')),
            CASE
                WHEN u.mobile REGEXP '^[0-9]{10}$' THEN u.mobile
                ELSE '0000000000'
            END,
            'I',
            'General'
        FROM users u
        LEFT JOIN students s
            ON s.enrollment_no = COALESCE(
                NULLIF(u.enrollment_no, ''),
                CONCAT('AUTO-', UPPER(LEFT(REPLACE(u.username, ' ', ''), 20)), '-', LPAD(u.id, 4, '0'))
            )
        WHERE u.role = 'student'
          AND s.enrollment_no IS NULL
        """
    )
    count = cursor.rowcount
    _mark_sync_done(cursor, STUDENT_SYNC_KEY, f"students={count}")
    return count


def run_one_time_sync():
    """
    One-time migration utility:
    - Imports existing teacher accounts from users -> teachers
    - Imports existing student accounts from users -> students
    - Prevents duplicate runs using per-module sync keys in system_sync_log
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        _ensure_sync_table(cursor)
        _ensure_teachers_table(cursor)

        teachers_synced = _run_teacher_sync(cursor)
        students_synced = _run_student_sync(cursor)

        conn.commit()
        return {
            "ran": bool(teachers_synced or students_synced),
            "teachers_synced": teachers_synced,
            "students_synced": students_synced,
        }
    finally:
        conn.close()


def run_student_sync_once():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        _ensure_sync_table(cursor)
        students_synced = _run_student_sync(cursor)
        conn.commit()
        return {
            "ran": bool(students_synced),
            "students_synced": students_synced,
        }
    finally:
        conn.close()
