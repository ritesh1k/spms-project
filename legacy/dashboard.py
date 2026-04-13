from admin.admin_dashboard import open_admin_dashboard
from teacher.teacher_dashboard import open_teacher_dashboard
from student.student_dashboard import open_student_dashboard
from tkinter import messagebox
from datetime import date
from db_config import get_connection


def get_student_access_status(enrollment):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT status, blacklist_until, blacklist_reason FROM students WHERE enrollment_no=%s",
            (enrollment,),
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            return False, "Student account not found."

        status = (row[0] or "Active").strip().lower()
        blacklist_until = row[1]
        blacklist_reason = (row[2] or "No reason provided").strip()

        if status == "inactive":
            return False, "Your account is currently inactive. Please contact admin."

        if blacklist_until and blacklist_until >= date.today():
            return (
                False,
                f"Your account is blacklisted until {blacklist_until}.\nReason: {blacklist_reason}",
            )

        return True, ""
    except Exception:
        return False, "Unable to verify account status right now. Please try again."


def resolve_student_enrollment(username, enrollment_hint):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        hint_value = str(enrollment_hint or "").strip()
        if hint_value:
            cursor.execute(
                "SELECT enrollment_no FROM students WHERE enrollment_no=%s LIMIT 1",
                (hint_value,),
            )
            hint_row = cursor.fetchone()
            if hint_row and hint_row[0]:
                cursor.close()
                conn.close()
                return str(hint_row[0]).strip()

        cursor.execute(
            """
            SELECT u.enrollment_no, COALESCE(u.email, ''), COALESCE(u.mobile, '')
            FROM users u
            LEFT JOIN students s ON s.enrollment_no = u.enrollment_no
            WHERE u.role='student' AND u.username=%s
            ORDER BY
                CASE WHEN u.enrollment_no=%s THEN 0 ELSE 1 END,
                CASE WHEN s.enrollment_no IS NOT NULL THEN 0 ELSE 1 END,
                CASE WHEN LOWER(COALESCE(s.name, '')) LIKE CONCAT('%%', LOWER(%s), '%%') THEN 0 ELSE 1 END
            LIMIT 1
            """,
            (username, enrollment_hint, username),
        )
        user_row = cursor.fetchone()
        if not user_row:
            cursor.close()
            conn.close()
            return str(enrollment_hint or "").strip()

        mapped_enrollment = str(user_row[0] or "").strip()
        user_email = str(user_row[1] or "").strip()
        user_mobile = str(user_row[2] or "").strip()

        if mapped_enrollment:
            cursor.execute(
                "SELECT enrollment_no, COALESCE(email, ''), COALESCE(phone, '') FROM students WHERE enrollment_no=%s LIMIT 1",
                (mapped_enrollment,),
            )
            student_row = cursor.fetchone()
            if student_row:
                cursor.close()
                conn.close()
                return mapped_enrollment

        fallback_enrollment = ""

        if user_email:
            cursor.execute(
                "SELECT enrollment_no FROM students WHERE LOWER(email)=LOWER(%s) LIMIT 1",
                (user_email,),
            )
            email_row = cursor.fetchone()
            if email_row and email_row[0]:
                fallback_enrollment = str(email_row[0]).strip()

        if not fallback_enrollment and user_mobile:
            cursor.execute(
                "SELECT enrollment_no FROM students WHERE phone=%s LIMIT 1",
                (user_mobile,),
            )
            mobile_row = cursor.fetchone()
            if mobile_row and mobile_row[0]:
                fallback_enrollment = str(mobile_row[0]).strip()

        if not fallback_enrollment and enrollment_hint:
            cursor.execute(
                "SELECT enrollment_no FROM students WHERE enrollment_no=%s LIMIT 1",
                (enrollment_hint,),
            )
            hint_row = cursor.fetchone()
            if hint_row and hint_row[0]:
                fallback_enrollment = str(hint_row[0]).strip()

        cursor.close()
        conn.close()

        if fallback_enrollment:
            return fallback_enrollment
    except Exception:
        pass
    return str(enrollment_hint or "").strip()

def open_dashboard(username, role, enrollment, parent):

    print("ROLE =", role)

    if role == "admin":
        open_admin_dashboard(username, parent)
        return True

    elif role == "teacher":
        open_teacher_dashboard(username, parent)
        return True

    elif role == "student":
        resolved_enrollment = resolve_student_enrollment(username, enrollment)
        if not resolved_enrollment:
            messagebox.showerror("Access Denied", "Unable to resolve student enrollment for this user.")
            return False

        can_access, message = get_student_access_status(resolved_enrollment)
        if not can_access:
            messagebox.showerror("Access Denied", message)
            return False

        open_student_dashboard(
            username=username,
            enrollment=resolved_enrollment,
            parent=parent
        )
        return True

    else:
        raise ValueError("Invalid role")
