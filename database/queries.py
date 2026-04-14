"""Database query helpers for SPMS Flask application."""

from database.connection import get_connection
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from auth_utils import verify_password


def authenticate_user(username: str, password: str) -> dict:
    """
    Authenticate user and return user data with role.
    
    Returns:
        dict: {"success": bool, "user": dict, "role": str, "error": str}
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Query users table
        cursor.execute(
            """
            SELECT username, password, role, enrollment_no, email
            FROM users 
            WHERE username = %s
            LIMIT 1
            """,
            (username,)
        )
        user_row = cursor.fetchone()
        conn.close()
        
        if not user_row:
            return {"success": False, "error": "Invalid username or password"}
        
        stored_password = user_row[1]
        if not verify_password(password, stored_password):
            return {"success": False, "error": "Invalid username or password"}
        
        return {
            "success": True,
            "user": {
                "username": user_row[0],
                "enrollment_no": user_row[3],
                "email": user_row[4],
            },
            "role": user_row[2],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_student_profile(enrollment_no: str) -> dict:
    """Get complete student profile data."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT name, enrollment_no, email, phone, course, semester, section, 
                   department, dob, batch
            FROM students 
            WHERE enrollment_no = %s
            LIMIT 1
            """,
            (enrollment_no,)
        )
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return {"error": "Student not found"}
        
        # Get CGPA if available
        cursor.execute(
            """
            SELECT AVG(CAST(grade AS FLOAT)) as cgpa, 
                   SUM(credits) as total_credits
            FROM results 
            WHERE enrollment_no = %s
            """,
            (enrollment_no,)
        )
        perf_row = cursor.fetchone()
        conn.close()
        
        return {
            "name": row[0],
            "enrollment": row[1],
            "email": row[2],
            "phone": row[3],
            "course": row[4],
            "semester": row[5],
            "section": row[6],
            "department": row[7],
            "dob": str(row[8]) if row[8] else "",
            "batch": row[9],
            "cgpa": round(float(perf_row[0] or 0), 2) if perf_row else 0,
        }
    except Exception as e:
        return {"error": str(e)}


def get_student_results(enrollment_no: str, semester: str = None) -> list:
    """Get student exam results."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if semester:
            cursor.execute(
                """
                SELECT subject, internal_total, external_marks, final_total, 
                       grade, status, published_at
                FROM published_results
                WHERE enrollment_no = %s AND semester = %s
                ORDER BY published_at DESC
                """,
                (enrollment_no, semester)
            )
        else:
            cursor.execute(
                """
                SELECT subject, internal_total, external_marks, final_total, 
                       grade, status, published_at
                FROM published_results
                WHERE enrollment_no = %s
                ORDER BY published_at DESC
                LIMIT 50
                """,
                (enrollment_no,)
            )
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "subject": row[0],
                "internal": row[1],
                "external": row[2],
                "total": row[3],
                "grade": row[4],
                "status": row[5],
                "date": str(row[6]) if row[6] else "",
            }
            for row in rows
        ]
    except Exception as e:
        return []


def get_teacher_profile(username: str) -> dict:
    """Get teacher profile data."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT username, full_name, email, phone, department, 
                   designation, specialization, date_of_joining
            FROM teachers
            WHERE username = %s AND role = 'teacher'
            LIMIT 1
            """,
            (username,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return {"error": "Teacher not found"}
        
        return {
            "username": row[0],
            "name": row[1],
            "email": row[2],
            "phone": row[3],
            "department": row[4],
            "designation": row[5],
            "specialization": row[6],
            "date_of_joining": str(row[7]) if row[7] else "",
        }
    except Exception as e:
        return {"error": str(e)}


def get_teacher_assigned_subjects(username: str) -> list:
    """Get subjects assigned to a teacher."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT DISTINCT subject_name, course_name, semester, section
            FROM assigned_subjects
            WHERE teacher_username = %s
            ORDER BY course_name, semester, section
            """,
            (username,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "subject": row[0],
                "course": row[1],
                "semester": row[2],
                "section": row[3],
            }
            for row in rows
        ]
    except Exception as e:
        return []


def submit_internal_marks(teacher_username: str, enrollment_no: str, subject: str,
                         semester: str, assignment: float, attendance: float,
                         ct1: float, ct2: float, ct3: float) -> dict:
    """Submit internal marks for a student."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Calculate best two class tests
        cts = sorted([ct1, ct2, ct3])[1:]  # Get two highest
        ct_best_two = sum(cts)
        
        # Calculate internal total (out of 40)
        internal_total = (assignment + attendance + ct_best_two)
        
        # Insert or update
        cursor.execute(
            """
            INSERT INTO teacher_internal_results
            (enrollment_no, subject, semester, assignment, attendance, ct1, ct2, ct3,
             ct_best_two, internal_total, teacher_username)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                assignment = VALUES(assignment),
                attendance = VALUES(attendance),
                ct1 = VALUES(ct1),
                ct2 = VALUES(ct2),
                ct3 = VALUES(ct3),
                ct_best_two = VALUES(ct_best_two),
                internal_total = VALUES(internal_total),
                updated_at = CURRENT_TIMESTAMP
            """,
            (enrollment_no, subject, semester, assignment, attendance,
             ct1, ct2, ct3, ct_best_two, internal_total, teacher_username)
        )
        conn.commit()
        cursor.close()
        conn.close()
        
        return {"success": True, "internal_total": internal_total}
    except Exception as e:
        return {"success": False, "error": str(e)}


def publish_result(enrollment_no: str, subject: str, semester: str,
                  external_marks: float, admin_username: str = "admin") -> dict:
    """Publish final result after adding external marks."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get internal result
        cursor.execute(
            """
            SELECT internal_total, assignment, attendance, ct1, ct2, ct3, ct_best_two
            FROM teacher_internal_results
            WHERE enrollment_no = %s AND subject = %s AND semester = %s
            """,
            (enrollment_no, subject, semester)
        )
        internal_row = cursor.fetchone()
        
        if not internal_row:
            conn.close()
            return {"success": False, "error": "Internal result not found"}
        
        internal_total = internal_row[0]
        final_total = internal_total + external_marks
        
        # Calculate grade
        if final_total >= 90:
            grade = "A+"
        elif final_total >= 80:
            grade = "A"
        elif final_total >= 70:
            grade = "B"
        elif final_total >= 60:
            grade = "C"
        else:
            grade = "D"
        
        status = "Pass" if final_total >= 40 else "Fail"
        
        # Insert into published results
        cursor.execute(
            """
            INSERT INTO published_results
            (enrollment_no, subject, semester, assignment, attendance, ct1, ct2, ct3,
             ct_best_two, internal_total, external_marks, final_total, grade, status,
             published_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                external_marks = VALUES(external_marks),
                final_total = VALUES(final_total),
                grade = VALUES(grade),
                status = VALUES(status),
                published_by = VALUES(published_by),
                published_at = CURRENT_TIMESTAMP
            """,
            (enrollment_no, subject, semester, internal_row[1], internal_row[2],
             internal_row[3], internal_row[4], internal_row[5], internal_row[6],
             internal_total, external_marks, final_total, grade, status, admin_username)
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "final_total": final_total,
            "grade": grade,
            "status": status,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_admin_stats() -> dict:
    """Get admin dashboard statistics."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Total students
        cursor.execute("SELECT COUNT(*) FROM students")
        total_students = cursor.fetchone()[0] or 0
        
        # Total teachers
        cursor.execute("SELECT COUNT(*) FROM teachers WHERE role = 'teacher'")
        total_teachers = cursor.fetchone()[0] or 0
        
        # Total courses
        cursor.execute("SELECT COUNT(*) FROM courses WHERE is_active = 1")
        total_courses = cursor.fetchone()[0] or 0
        
        # Total departments
        cursor.execute("SELECT COUNT(*) FROM departments WHERE is_active = 1")
        total_departments = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            "students": total_students,
            "teachers": total_teachers,
            "courses": total_courses,
            "departments": total_departments,
        }
    except Exception as e:
        return {"error": str(e)}


def search_students(dept_filter: str = "", course_filter: str = "", 
                   semester_filter: str = "") -> list:
    """Search for students with filters."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = "SELECT name, enrollment_no, course, semester, section, department FROM students WHERE 1=1"
        params = []
        
        if dept_filter:
            query += " AND department LIKE %s"
            params.append(f"%{dept_filter}%")
        
        if course_filter:
            query += " AND course LIKE %s"
            params.append(f"%{course_filter}%")
        
        if semester_filter:
            query += " AND semester = %s"
            params.append(semester_filter)
        
        query += " LIMIT 100"
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "name": row[0],
                "enrollment": row[1],
                "course": row[2],
                "semester": row[3],
                "section": row[4],
                "department": row[5],
            }
            for row in rows
        ]
    except Exception as e:
        return []
