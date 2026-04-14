import csv
import importlib
import os
import tkinter as tk
from datetime import date, datetime
from tkinter import filedialog, messagebox, ttk

from db_config import get_connection
from modules import create_result
from modules.course_aliases import get_course_aliases, course_matches
from modules.result_utils import normalize_semester
from auth_utils import hash_password, verify_password

openpyxl = None
reportlab_canvas = None
A4 = None

try:
    openpyxl = importlib.import_module("openpyxl")
except Exception:
    openpyxl = None

try:
    reportlab_canvas = importlib.import_module("reportlab.pdfgen.canvas")
    A4 = importlib.import_module("reportlab.lib.pagesizes").A4
except Exception:
    reportlab_canvas = None
    A4 = None

try:
    PIL_Image = importlib.import_module("PIL.Image")
    PIL_ImageTk = importlib.import_module("PIL.ImageTk")
    PIL_ImageDraw = importlib.import_module("PIL.ImageDraw")
except Exception:
    PIL_Image = None
    PIL_ImageTk = None
    PIL_ImageDraw = None


LIGHT_THEME = {
    "app_bg": "#f4f7fb",
    "panel": "#ffffff",
    "header": "#2446b7",
    "sidebar": "#0f172a",
    "text": "#1f2937",
    "muted": "#6b7280",
    "accent": "#2563eb",
    "accent2": "#10b981",
    "danger": "#ef4444",
    "card_shadow": "#dbe3f2",
}

DARK_THEME = {
    "app_bg": "#0b1020",
    "panel": "#141c33",
    "header": "#1d4ed8",
    "sidebar": "#020617",
    "text": "#e5e7eb",
    "muted": "#94a3b8",
    "accent": "#3b82f6",
    "accent2": "#22c55e",
    "danger": "#f87171",
    "card_shadow": "#1e293b",
}


class TeacherDashboard:
    def __init__(self, username, parent):
        self.username = username
        self.parent = parent
        self.theme_mode = "light"
        self.current_view = "overview"
        self.student_page = 1
        self.page_size = 10
        self.student_total = 0
        self.attendance_status = {}
        self.class_report_data = []
        self.student_report_data = []
        self.nav_buttons = []
        self.avatar_refs = {}
        self.nav_label_defaults = {}
        self.nav_button_map = {}
        self.notifications_seen_at = datetime(2000, 1, 1)
        self.communication_seen_at = datetime(2000, 1, 1)
        self.badge_refresh_job = None

        self.window = tk.Toplevel(parent)
        self.window.title("SPMS - Teacher Dashboard")
        sw = self.window.winfo_screenwidth()
        sh = self.window.winfo_screenheight()
        win_w = min(1280, max(940, int(sw * 0.92)))
        win_h = min(760, max(580, int(sh * 0.9)))
        x = (sw // 2) - (win_w // 2)
        y = (sh // 2) - (win_h // 2)
        self.window.geometry(f"{win_w}x{win_h}+{x}+{y}")
        self.window.minsize(900, 560)
        self.parent.withdraw()

        self.ensure_tables()
        self.teacher_info = self.get_teacher_info()
        self.build_shell()
        self.render_current_view()
        self.window.bind("<Configure>", self.on_resize)
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

    def theme(self):
        return LIGHT_THEME if self.theme_mode == "light" else DARK_THEME

    def db_execute(self, query, params=(), fetch="all"):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(query, params)
        result = None
        if fetch == "one":
            result = cur.fetchone()
        elif fetch == "all":
            result = cur.fetchall()
        conn.commit()
        conn.close()
        return result

    def ensure_tables(self):
        setup_queries = [
            """
            CREATE TABLE IF NOT EXISTS results (
                id INT AUTO_INCREMENT PRIMARY KEY,
                enrollment_no VARCHAR(100) NOT NULL,
                subject VARCHAR(120) NOT NULL,
                marks DECIMAL(6,2) NOT NULL,
                exam VARCHAR(60) NOT NULL,
                teacher_username VARCHAR(100) NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uniq_result (enrollment_no, subject, exam)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS attendance (
                id INT AUTO_INCREMENT PRIMARY KEY,
                attendance_date DATE NOT NULL,
                enrollment_no VARCHAR(100) NOT NULL,
                department VARCHAR(120) NULL,
                course VARCHAR(120) NULL,
                semester VARCHAR(40) NULL,
                section VARCHAR(40) NULL,
                subject_code VARCHAR(50) NULL,
                subject_name VARCHAR(150) NULL,
                class_name VARCHAR(120) NOT NULL,
                status VARCHAR(20) NOT NULL,
                teacher_username VARCHAR(100) NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uq_attendance_subject (attendance_date, enrollment_no, subject_code)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS teacher_remarks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                enrollment_no VARCHAR(100) NOT NULL,
                teacher_username VARCHAR(100) NOT NULL,
                remark TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS assignments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                teacher_username VARCHAR(100) NOT NULL,
                course_name VARCHAR(150) NULL,
                semester VARCHAR(20) NULL,
                section VARCHAR(20) NULL,
                subject VARCHAR(150) NULL,
                class_name VARCHAR(120) NOT NULL,
                title VARCHAR(180) NOT NULL,
                material_path VARCHAR(300) NULL,
                deadline DATE NOT NULL,
                status VARCHAR(30) DEFAULT 'Open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS assignment_submissions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                assignment_id INT NOT NULL,
                enrollment_no VARCHAR(100) NOT NULL,
                submission_path VARCHAR(300) NOT NULL,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(30) DEFAULT 'Submitted',
                marks DECIMAL(6,2) NULL,
                evaluation TEXT NULL,
                evaluated_by VARCHAR(100) NULL,
                evaluated_at DATETIME NULL,
                UNIQUE KEY uq_assignment_submission (assignment_id, enrollment_no)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS exam_schedule (
                id INT AUTO_INCREMENT PRIMARY KEY,
                teacher_username VARCHAR(100) NOT NULL,
                course_name VARCHAR(150) NULL,
                semester VARCHAR(20) NULL,
                section VARCHAR(20) NULL,
                class_name VARCHAR(120) NOT NULL,
                subject VARCHAR(120) NOT NULL,
                exam_date DATE NOT NULL,
                exam_time VARCHAR(40) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS teacher_announcements (
                id INT AUTO_INCREMENT PRIMARY KEY,
                teacher_username VARCHAR(100) NOT NULL,
                title VARCHAR(180) NOT NULL,
                subject VARCHAR(150) NULL,
                course_name VARCHAR(150) NULL,
                semester VARCHAR(20) NULL,
                section VARCHAR(20) NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS student_queries (
                id INT AUTO_INCREMENT PRIMARY KEY,
                enrollment_no VARCHAR(100) NOT NULL,
                teacher_username VARCHAR(100) NULL,
                teacher_subject VARCHAR(150) NULL,
                query_type VARCHAR(80) NULL,
                doubt_subject VARCHAR(150) NULL,
                course_name VARCHAR(150) NULL,
                semester VARCHAR(20) NULL,
                section VARCHAR(20) NULL,
                query_text TEXT NOT NULL,
                status VARCHAR(40) DEFAULT 'Submitted',
                response TEXT NULL,
                solution_text TEXT NULL,
                teacher_received_at DATETIME NULL,
                solved_at DATETIME NULL,
                student_received_at DATETIME NULL,
                solved_within_2_days TINYINT(1) DEFAULT 0,
                student_acknowledged TINYINT(1) DEFAULT 0,
                student_feedback VARCHAR(200) NULL,
                reopen_count INT DEFAULT 0,
                parent_query_id INT NULL,
                requires_session TINYINT(1) DEFAULT 0,
                session_status VARCHAR(40) NULL,
                session_id INT NULL,
                session_title VARCHAR(180) NULL,
                session_datetime DATETIME NULL,
                session_duration_minutes INT NULL,
                session_note TEXT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS doubt_sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                teacher_username VARCHAR(100) NOT NULL,
                enrollment_no VARCHAR(100) NOT NULL,
                title VARCHAR(180) NOT NULL,
                session_datetime DATETIME NOT NULL,
                duration_minutes INT DEFAULT 20,
                mode VARCHAR(40) DEFAULT 'Offline',
                agenda TEXT NULL,
                status VARCHAR(40) DEFAULT 'Scheduled',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS doubt_session_queries (
                id INT AUTO_INCREMENT PRIMARY KEY,
                session_id INT NOT NULL,
                query_id INT NOT NULL,
                UNIQUE KEY uq_session_query (session_id, query_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS admin_announcements (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(180) NOT NULL,
                message TEXT NOT NULL,
                created_by VARCHAR(100) NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS teacher_settings (
                username VARCHAR(100) PRIMARY KEY,
                notify_email TINYINT(1) DEFAULT 1,
                notify_inapp TINYINT(1) DEFAULT 1,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS teacher_pic (
                username VARCHAR(100) PRIMARY KEY,
                photo VARCHAR(300) NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """,
        ]

        for query in setup_queries:
            try:
                self.db_execute(query, fetch=None)
            except Exception:
                pass

        attendance_alter_queries = [
            "ALTER TABLE attendance ADD COLUMN department VARCHAR(120) NULL AFTER enrollment_no",
            "ALTER TABLE attendance ADD COLUMN course VARCHAR(120) NULL AFTER department",
            "ALTER TABLE attendance ADD COLUMN semester VARCHAR(40) NULL AFTER course",
            "ALTER TABLE attendance ADD COLUMN section VARCHAR(40) NULL AFTER semester",
            "ALTER TABLE attendance ADD COLUMN subject_code VARCHAR(50) NULL AFTER section",
            "ALTER TABLE attendance ADD COLUMN subject_name VARCHAR(150) NULL AFTER subject_code",
        ]
        for query in attendance_alter_queries:
            try:
                self.db_execute(query, fetch=None)
            except Exception:
                pass

        # Migrate from class-level uniqueness to subject-level uniqueness.
        for query in [
            "ALTER TABLE attendance DROP INDEX uniq_attendance",
            "ALTER TABLE attendance ADD UNIQUE KEY uq_attendance_subject (attendance_date, enrollment_no, subject_code)",
        ]:
            try:
                self.db_execute(query, fetch=None)
            except Exception:
                pass

        communication_alter_queries = [
            "ALTER TABLE teacher_announcements ADD COLUMN subject VARCHAR(150) NULL AFTER title",
            "ALTER TABLE teacher_announcements ADD COLUMN course_name VARCHAR(150) NULL AFTER subject",
            "ALTER TABLE teacher_announcements ADD COLUMN semester VARCHAR(20) NULL AFTER course_name",
            "ALTER TABLE teacher_announcements ADD COLUMN section VARCHAR(20) NULL AFTER semester",
            "ALTER TABLE student_queries ADD COLUMN teacher_username VARCHAR(100) NULL AFTER enrollment_no",
            "ALTER TABLE student_queries ADD COLUMN teacher_subject VARCHAR(150) NULL AFTER teacher_username",
            "ALTER TABLE student_queries ADD COLUMN query_type VARCHAR(80) NULL AFTER teacher_subject",
            "ALTER TABLE student_queries ADD COLUMN doubt_subject VARCHAR(150) NULL AFTER query_type",
            "ALTER TABLE student_queries ADD COLUMN course_name VARCHAR(150) NULL AFTER doubt_subject",
            "ALTER TABLE student_queries ADD COLUMN semester VARCHAR(20) NULL AFTER course_name",
            "ALTER TABLE student_queries ADD COLUMN section VARCHAR(20) NULL AFTER semester",
            "ALTER TABLE student_queries ADD COLUMN solution_text TEXT NULL AFTER response",
            "ALTER TABLE student_queries ADD COLUMN teacher_received_at DATETIME NULL AFTER solution_text",
            "ALTER TABLE student_queries ADD COLUMN solved_at DATETIME NULL AFTER teacher_received_at",
            "ALTER TABLE student_queries ADD COLUMN student_received_at DATETIME NULL AFTER solved_at",
            "ALTER TABLE student_queries ADD COLUMN solved_within_2_days TINYINT(1) DEFAULT 0 AFTER student_received_at",
            "ALTER TABLE student_queries ADD COLUMN student_acknowledged TINYINT(1) DEFAULT 0 AFTER solved_within_2_days",
            "ALTER TABLE student_queries ADD COLUMN student_feedback VARCHAR(200) NULL AFTER student_acknowledged",
            "ALTER TABLE student_queries ADD COLUMN reopen_count INT DEFAULT 0 AFTER student_feedback",
            "ALTER TABLE student_queries ADD COLUMN parent_query_id INT NULL AFTER reopen_count",
            "ALTER TABLE student_queries ADD COLUMN requires_session TINYINT(1) DEFAULT 0 AFTER parent_query_id",
            "ALTER TABLE student_queries ADD COLUMN session_status VARCHAR(40) NULL AFTER requires_session",
            "ALTER TABLE student_queries ADD COLUMN session_id INT NULL AFTER session_status",
            "ALTER TABLE student_queries ADD COLUMN session_title VARCHAR(180) NULL AFTER session_id",
            "ALTER TABLE student_queries ADD COLUMN session_datetime DATETIME NULL AFTER session_title",
            "ALTER TABLE student_queries ADD COLUMN session_duration_minutes INT NULL AFTER session_datetime",
            "ALTER TABLE student_queries ADD COLUMN session_note TEXT NULL AFTER session_duration_minutes",
        ]
        for query in communication_alter_queries:
            try:
                self.db_execute(query, fetch=None)
            except Exception:
                pass

        assignment_exam_alter_queries = [
            "ALTER TABLE assignments ADD COLUMN course_name VARCHAR(150) NULL AFTER teacher_username",
            "ALTER TABLE assignments ADD COLUMN semester VARCHAR(20) NULL AFTER course_name",
            "ALTER TABLE assignments ADD COLUMN section VARCHAR(20) NULL AFTER semester",
            "ALTER TABLE assignments ADD COLUMN subject VARCHAR(150) NULL AFTER section",
            "ALTER TABLE exam_schedule ADD COLUMN course_name VARCHAR(150) NULL AFTER teacher_username",
            "ALTER TABLE exam_schedule ADD COLUMN semester VARCHAR(20) NULL AFTER course_name",
            "ALTER TABLE exam_schedule ADD COLUMN section VARCHAR(20) NULL AFTER semester",
        ]
        for query in assignment_exam_alter_queries:
            try:
                self.db_execute(query, fetch=None)
            except Exception:
                pass

    def get_teacher_info(self):
        try:
            row = self.db_execute(
                """
                SELECT full_name, email, phone, department, designation, specialization
                FROM teachers WHERE username=%s LIMIT 1
                """,
                (self.username,),
                fetch="one",
            )
            if row:
                return {
                    "full_name": row[0] or self.username,
                    "email": row[1] or "N/A",
                    "phone": row[2] or "N/A",
                    "department": row[3] or "General",
                    "designation": row[4] or "Teacher",
                    "subject": row[5] or "General Studies",
                }
        except Exception:
            pass

        return {
            "full_name": self.username,
            "email": "N/A",
            "phone": "N/A",
            "department": "General",
            "designation": "Teacher",
            "subject": "General Studies",
        }

    def get_teacher_photo(self):
        row = self.db_safe_one("SELECT photo FROM teacher_pic WHERE username=%s", (self.username,))
        return row[0] if row and row[0] else None

    def set_teacher_photo(self, path):
        self.db_execute(
            """
            INSERT INTO teacher_pic (username, photo)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE photo=VALUES(photo)
            """,
            (self.username, path),
            fetch=None,
        )

    def make_avatar(self, path=None, size=70, circular=True):
        if PIL_Image is None or PIL_ImageTk is None:
            return None
        if path and os.path.exists(path):
            image = PIL_Image.open(path).convert("RGBA").resize((size, size))
        else:
            image = PIL_Image.new("RGBA", (size, size), color="#d1d5db")
            if PIL_ImageDraw:
                draw = PIL_ImageDraw.Draw(image)
                draw.ellipse((10, 6, size - 10, size - 22), fill="white")
                draw.rounded_rectangle((12, size - 26, size - 12, size - 6), radius=8, fill="white")
        if circular and PIL_ImageDraw:
            mask = PIL_Image.new("L", (size, size), 0)
            draw = PIL_ImageDraw.Draw(mask)
            draw.ellipse((0, 0, size, size), fill=255)
            image.putalpha(mask)
        return PIL_ImageTk.PhotoImage(image)

    def get_teacher_assignments(self):
        return self.db_safe_all(
            """
            SELECT DISTINCT course_name, semester, section, subject_name, lecture_day, lecture_time
            FROM assigned_subjects
            WHERE teacher_username=%s
            ORDER BY course_name, semester, section, lecture_day
            """,
            (self.username,),
        )

    def get_department_students(self):
        rows = self.db_safe_all(
            """
            SELECT enrollment_no, name, course, semester, section, email, phone
            FROM students
            WHERE UPPER(TRIM(COALESCE(department, '')))=UPPER(TRIM(%s))
            ORDER BY enrollment_no
            """,
            (self.teacher_info["department"],),
        )

        unique_rows = []
        seen_enrollments = set()
        for row in rows:
            enrollment_no = str(row[0] or "").strip().upper()
            if not enrollment_no or enrollment_no in seen_enrollments:
                continue
            seen_enrollments.add(enrollment_no)
            unique_rows.append(row)
        return unique_rows

    def get_students_for_teacher(self):
        students = self.get_department_students()

        assignments = self.get_teacher_assignments()
        if not assignments:
            return students

        filtered = []
        for student in students:
            student_course = str(student[2] or "").strip()
            student_sem = normalize_semester(str(student[3] or "").strip())
            student_section = str(student[4] or "").strip().upper()

            matched = any(
                (
                    course_matches(student_course, assignment[0])
                    and student_section == str(assignment[2] or "").strip().upper()
                    and (
                        not normalize_semester(str(assignment[1] or "").strip())
                        or not student_sem
                        or student_sem == normalize_semester(str(assignment[1] or "").strip())
                    )
                )
                for assignment in assignments
            )
            if matched:
                filtered.append(student)
        return filtered

    def get_assigned_subjects_display(self):
        try:
            assignments = self.get_teacher_assignments()
            subjects = sorted({str(a[3]).strip() for a in assignments if str(a[3]).strip()})
            if subjects:
                return ", ".join(subjects)
        except Exception:
            pass
        return self.teacher_info.get("subject", "General Studies")

    def to_semester_number(self, sem_value):
        sem_text = str(sem_value or "").strip().upper()
        if not sem_text:
            return ""

        roman = normalize_semester(sem_text).upper()
        roman_to_number = {
            "I": "1",
            "II": "2",
            "III": "3",
            "IV": "4",
            "V": "5",
            "VI": "6",
            "VII": "7",
            "VIII": "8",
        }
        if roman in roman_to_number:
            return roman_to_number[roman]

        digits = "".join(ch for ch in sem_text if ch.isdigit())
        if digits:
            value = int(digits)
            if 1 <= value <= 8:
                return str(value)
        return ""

    def semester_variants(self, sem_value):
        variants = []
        raw = str(sem_value or "").strip()
        normalized = normalize_semester(raw)
        number = self.to_semester_number(raw)
        for value in [raw, normalized, number]:
            val = str(value or "").strip()
            if val and val not in variants:
                variants.append(val)
        return variants

    def get_teacher_assigned_classes(self):
        classes = []
        seen = set()
        for row in self.get_teacher_assignments():
            course_name = str(row[0] or "").strip()
            semester = normalize_semester(str(row[1] or "").strip())
            section = str(row[2] or "").strip().upper()
            if not course_name or not semester or not section:
                continue
            key = (course_name.upper(), semester, section)
            if key in seen:
                continue
            seen.add(key)
            classes.append((course_name, semester, section))

        return sorted(
            classes,
            key=lambda item: (
                str(item[0]).upper(),
                int(self.to_semester_number(item[1]) or 99),
                str(item[2]).upper(),
            ),
        )

    def get_class_performance_rows(self):
        rows = []
        classes = self.get_teacher_assigned_classes()

        for course_name, semester, section in classes:
            sem_values = self.semester_variants(semester)
            sem_placeholders = ",".join(["%s"] * len(sem_values))

            attendance_row = self.db_safe_one(
                f"""
                SELECT
                    SUM(CASE WHEN UPPER(COALESCE(status,''))='PRESENT' THEN 1 ELSE 0 END) AS present_count,
                    COUNT(*) AS total_count
                FROM attendance
                WHERE teacher_username=%s
                  AND UPPER(TRIM(COALESCE(course,'')))=UPPER(TRIM(%s))
                  AND UPPER(TRIM(COALESCE(section,'')))=UPPER(TRIM(%s))
                  AND semester IN ({sem_placeholders})
                """,
                (self.username, course_name, section, *sem_values),
            )

            present_count = float(attendance_row[0] or 0) if attendance_row else 0.0
            total_count = float(attendance_row[1] or 0) if attendance_row else 0.0
            attendance_pct = round((present_count / total_count) * 100, 2) if total_count > 0 else 0.0

            subject_rows = self.db_safe_all(
                f"""
                SELECT DISTINCT UPPER(TRIM(subject_name))
                FROM assigned_subjects
                WHERE teacher_username=%s
                  AND UPPER(TRIM(course_name))=UPPER(TRIM(%s))
                  AND UPPER(TRIM(section))=UPPER(TRIM(%s))
                  AND semester IN ({sem_placeholders})
                  AND TRIM(COALESCE(subject_name,''))<>''
                """,
                (self.username, course_name, section, *sem_values),
            )
            subject_names = [str(r[0]).strip().upper() for r in subject_rows if r and r[0]]

            overall_avg = 0.0
            top_count = 0
            if subject_names:
                subject_placeholders = ",".join(["%s"] * len(subject_names))
                marks_row = self.db_safe_one(
                    f"""
                    SELECT
                        ROUND(AVG(COALESCE(p.final_total, p.internal_total + p.external_marks)),2) AS overall_avg,
                        SUM(CASE WHEN COALESCE(p.final_total, p.internal_total + p.external_marks) >= 85 THEN 1 ELSE 0 END) AS top_scorers
                    FROM published_results p
                    JOIN students s ON s.enrollment_no=p.enrollment_no
                    WHERE UPPER(TRIM(COALESCE(s.course,'')))=UPPER(TRIM(%s))
                      AND UPPER(TRIM(COALESCE(s.section,'')))=UPPER(TRIM(%s))
                      AND p.semester IN ({sem_placeholders})
                      AND UPPER(TRIM(COALESCE(p.subject,''))) IN ({subject_placeholders})
                    """,
                    (course_name, section, *sem_values, *subject_names),
                )
                if marks_row:
                    overall_avg = float(marks_row[0] or 0)
                    top_count = int(marks_row[1] or 0)

            blended = round((attendance_pct * 0.4) + (overall_avg * 0.6), 2)
            semester_no = self.to_semester_number(semester) or semester
            class_label = f"{course_name}-S{semester_no}-{section}"
            rows.append(
                {
                    "label": class_label,
                    "course": course_name,
                    "semester": semester,
                    "section": section,
                    "attendance": attendance_pct,
                    "overall": overall_avg,
                    "top_count": top_count,
                    "score": blended,
                }
            )

        return rows

    def build_shell(self):
        t = self.theme()
        self.window.configure(bg=t["app_bg"])

        self.header = tk.Frame(self.window, bg="#2c3e50", height=130)
        self.header.pack(fill="x", side="top")
        self.header.pack_propagate(False)

        self.header_left = tk.Frame(self.header, bg="#2c3e50")
        self.header_left.pack(side="left", padx=18, pady=8)

        self.profile_photo_label = tk.Label(self.header_left, bg="#2c3e50", cursor="hand2")
        self.profile_photo_label.pack()
        self.profile_photo_label.bind("<Button-1>", self.open_profile_popup)

        self.user_label = tk.Label(
            self.header_left,
            text=self.teacher_info["full_name"],
            bg="#2c3e50",
            fg="white",
            font=("Segoe UI", 10, "bold"),
        )
        self.user_label.pack(pady=(4, 0))

        self.theme_btn = tk.Button(
            self.header_left,
            text="🌙 Dark" if self.theme_mode == "light" else "☀ Light",
            bg="#1d4ed8",
            fg="white",
            bd=0,
            padx=10,
            pady=5,
            cursor="hand2",
            command=self.toggle_theme,
            font=("Segoe UI", 9, "bold"),
        )
        self.theme_btn.pack(pady=(6, 0))

        self.header_center = tk.Frame(self.header, bg="#2c3e50")
        self.header_center.pack(side="left", fill="both", expand=True, padx=12, pady=8)

        self.title_label = tk.Label(
            self.header_center,
            text="SPMS Teacher Panel",
            bg="#2c3e50",
            fg="white",
            font=("Segoe UI", 18, "bold"),
            anchor="w",
        )
        self.title_label.pack(fill="x", pady=(2, 2))

        self.teacher_tag_label = tk.Label(
            self.header_center,
            text=f"{self.get_assigned_subjects_display()}  •  {self.teacher_info['department']}",
            bg="#2c3e50",
            fg="#dbeafe",
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        )
        self.teacher_tag_label.pack(fill="x", pady=(0, 4))

        self.header_stats_row = tk.Frame(self.header_center, bg="#2c3e50")
        self.header_stats_row.pack(fill="x")

        self.header_stat_labels = {}

        def make_header_stat(key, title, color):
            lbl = tk.Label(
                self.header_stats_row,
                text=f"{title}: 0",
                bg=color,
                fg="white",
                font=("Segoe UI", 9, "bold"),
                width=20,
                height=2,
            )
            lbl.pack(side="left", padx=4)
            self.header_stat_labels[key] = lbl

        make_header_stat("students", "🎓 Students", "#3498db")
        make_header_stat("classes", "📘 Classes", "#e67e22")
        make_header_stat("subjects", "📚 Subjects", "#9b59b6")
        make_header_stat("pending", "📝 Evaluations", "#16a085")

        self.load_header_avatar()
        self.refresh_header_stats()

        body = tk.Frame(self.window, bg=t["app_bg"])
        body.pack(fill="both", expand=True)

        self.sidebar = tk.Frame(body, bg="#34495e", width=280)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.content = tk.Frame(body, bg="#ffffff")
        self.content.pack(side="left", fill="both", expand=True, padx=12, pady=12)

        nav_items = [
            ("overview", "🏠 Dashboard"),
            ("students", "👨‍🎓 Student Management"),
            ("classes", "📘 Class & Subjects"),
            ("attendance", "🗓 Attendance"),
            ("marks", "🧾 Marks & Evaluation"),
            ("assignments", "📝 Assignments & Exams"),
            ("reports", "📊 Reports & Analytics"),
            ("communication", "📣 Communication"),
            ("notifications", "🔔 Notifications"),
            ("settings", "⚙ Profile & Settings"),
        ]
        self.nav_label_defaults = {key: label for key, label in nav_items}

        for key, label in nav_items:
            btn = tk.Button(
                self.sidebar,
                text=label,
                bg="#34495e",
                fg="white",
                bd=0,
                anchor="w",
                padx=16,
                pady=12,
                font=("Segoe UI", 10, "bold"),
                cursor="hand2",
                activeforeground="white",
                activebackground="#1e293b",
                command=lambda k=key: self.navigate(k),
            )
            btn.pack(fill="x", pady=1)
            self.bind_nav_hover(btn, key)
            self.nav_buttons.append((key, btn))
            self.nav_button_map[key] = btn

        logout_btn = tk.Button(
            self.sidebar,
            text="⏻ Logout",
            bg=t["danger"],
            fg="white",
            bd=0,
            pady=12,
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
            command=self.logout,
        )
        logout_btn.pack(side="bottom", fill="x", pady=10)

    def load_header_avatar(self):
        photo_path = self.get_teacher_photo()
        avatar = self.make_avatar(photo_path, size=68, circular=True)
        if avatar is None:
            self.profile_photo_label.configure(text="👤", font=("Segoe UI", 26), image="")
            return
        self.avatar_refs["small"] = avatar
        self.profile_photo_label.configure(image=self.avatar_refs["small"], text="")

    def open_profile_popup(self, _event=None):
        popup = tk.Toplevel(self.window)
        popup.title("Teacher Profile")
        popup.geometry("360x430")
        popup.resizable(False, False)

        wrapper = tk.Frame(popup, bg="#f5f7fa")
        wrapper.pack(fill="both", expand=True, padx=12, pady=12)

        photo_path = self.get_teacher_photo()
        big_img = self.make_avatar(photo_path, size=210, circular=False)
        if big_img is None:
            img_label = tk.Label(wrapper, text="👤", font=("Segoe UI", 92), bg="#f5f7fa", fg="white")
            icon_bg = tk.Frame(wrapper, bg="#9ca3af", width=220, height=220)
            icon_bg.pack(pady=(10, 8))
            icon_bg.pack_propagate(False)
            img_label.pack(in_=icon_bg, expand=True)
        else:
            self.avatar_refs["big"] = big_img
            img_label = tk.Label(wrapper, image=self.avatar_refs["big"], bg="#f5f7fa")
            img_label.pack(pady=(10, 8))

        tk.Label(wrapper, text=self.teacher_info["full_name"], bg="#f5f7fa", font=("Segoe UI", 12, "bold"), fg="#1f2937").pack(pady=(0, 12))

        btn_frame = tk.Frame(wrapper, bg="#f5f7fa")
        btn_frame.pack(pady=8)

        def upload_photo():
            path = filedialog.askopenfilename(
                filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All Files", "*.*")]
            )
            if path:
                self.set_teacher_photo(path)
                self.load_header_avatar()
                popup.destroy()

        def remove_photo():
            self.set_teacher_photo(None)
            self.load_header_avatar()
            popup.destroy()

        tk.Button(btn_frame, text="Upload", bg="#27ae60", fg="white", width=12, command=upload_photo).pack(side="left", padx=6)
        tk.Button(btn_frame, text="Remove", bg="#c0392b", fg="white", width=12, command=remove_photo).pack(side="left", padx=6)

    def bind_hover(self, widget, normal, hover):
        widget.bind("<Enter>", lambda _e: widget.configure(bg=hover))
        widget.bind("<Leave>", lambda _e: widget.configure(bg=normal))

    def bind_nav_hover(self, widget, view_key):
        def on_enter(_event):
            if view_key != self.current_view:
                widget.configure(bg="#1e293b")

        def on_leave(_event):
            if view_key == self.current_view:
                widget.configure(bg="#1e293b")
            else:
                widget.configure(bg="#34495e")

        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    def on_resize(self, event):
        if event.widget != self.window:
            return
        self.sidebar.configure(width=280)

    def refresh_header_stats(self):
        students = self.get_students_for_teacher()
        assignments = self.get_teacher_assignments()
        total_students = len(students)
        total_classes = len({(str(a[0]), str(a[1]), str(a[2])) for a in assignments})

        total_subjects = len({str(a[3]).strip() for a in assignments if str(a[3]).strip()})

        pending_eval = self.fetch_scalar(
            "SELECT COUNT(*) FROM assignments WHERE teacher_username=%s AND status='Open'",
            (self.username,),
            0,
        )

        if "students" in self.header_stat_labels:
            self.header_stat_labels["students"].config(text=f"🎓 Students: {total_students}")
        if "classes" in self.header_stat_labels:
            self.header_stat_labels["classes"].config(text=f"📘 Classes: {total_classes}")
        if "subjects" in self.header_stat_labels:
            self.header_stat_labels["subjects"].config(text=f"📚 Subjects: {total_subjects}")
        if "pending" in self.header_stat_labels:
            self.header_stat_labels["pending"].config(text=f"📝 Evaluations: {pending_eval}")

    def clear_content(self):
        for child in self.content.winfo_children():
            child.destroy()

    def navigate(self, view_key):
        if view_key == "notifications":
            self.notifications_seen_at = datetime.now()
        elif view_key == "communication":
            self.communication_seen_at = datetime.now()
        self.current_view = view_key
        self.render_current_view()

    def render_current_view(self):
        self.apply_theme_shell()
        self.refresh_nav_badges()
        self.teacher_tag_label.config(text=f"{self.get_assigned_subjects_display()}  •  {self.teacher_info['department']}")
        self.refresh_header_stats()
        self.clear_content()
        if self.current_view == "overview":
            self.render_overview()
        elif self.current_view == "students":
            self.render_students()
        elif self.current_view == "classes":
            self.render_classes_subjects()
        elif self.current_view == "attendance":
            self.render_attendance()
        elif self.current_view == "marks":
            self.render_marks()
        elif self.current_view == "assignments":
            self.render_assignments()
        elif self.current_view == "reports":
            self.render_reports()
        elif self.current_view == "communication":
            self.render_communication()
        elif self.current_view == "notifications":
            self.render_notifications()
        else:
            self.render_settings()

    def set_nav_badge(self, key, is_new=False, count=0):
        btn = self.nav_button_map.get(key)
        base = self.nav_label_defaults.get(key, "")
        if not btn or not base:
            return
        if is_new:
            suffix = "  📩"
            btn.configure(text=f"{base}{suffix}")
        else:
            btn.configure(text=base)

    def get_new_teacher_notification_count(self):
        admin_count = int(
            self.fetch_scalar(
                "SELECT COUNT(*) FROM admin_announcements WHERE created_at > %s",
                (self.notifications_seen_at,),
                0,
            )
            or 0
        )
        submission_count = int(
            self.fetch_scalar(
                """
                SELECT COUNT(*)
                FROM assignment_submissions s
                JOIN assignments a ON a.id=s.assignment_id
                WHERE a.teacher_username=%s AND s.submitted_at > %s
                """,
                (self.username, self.notifications_seen_at),
                0,
            )
            or 0
        )
        return admin_count + submission_count

    def get_new_teacher_communication_count(self):
        count = self.fetch_scalar(
            """
            SELECT COUNT(*)
            FROM student_queries sq
            WHERE (
                sq.teacher_username=%s
                OR EXISTS (
                    SELECT 1
                    FROM assigned_subjects a
                    WHERE a.teacher_username=%s
                      AND LOWER(TRIM(a.subject_name)) = LOWER(TRIM(COALESCE(sq.doubt_subject, '')))
                      AND LOWER(TRIM(a.course_name)) = LOWER(TRIM(COALESCE(sq.course_name, '')))
                      AND TRIM(a.semester) = TRIM(COALESCE(sq.semester, ''))
                      AND UPPER(TRIM(a.section)) = UPPER(TRIM(COALESCE(sq.section, '')))
                )
            )
              AND sq.updated_at > %s
              AND COALESCE(sq.status, '') IN ('Submitted', 'Reopened', 'Session Required')
            """,
            (self.username, self.username, self.communication_seen_at),
            0,
        )
        return int(count or 0)

    def refresh_nav_badges(self):
        notif_count = self.get_new_teacher_notification_count()
        comm_count = self.get_new_teacher_communication_count()
        self.set_nav_badge("notifications", is_new=notif_count > 0, count=notif_count)
        self.set_nav_badge("communication", is_new=comm_count > 0, count=comm_count)

        if self.window.winfo_exists():
            if self.badge_refresh_job:
                try:
                    self.window.after_cancel(self.badge_refresh_job)
                except Exception:
                    pass
            self.badge_refresh_job = self.window.after(15000, self.refresh_nav_badges)

    def render_notifications(self):
        t = self.theme()
        frame = tk.Frame(self.content, bg=t["app_bg"])
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="Notifications", bg=t["app_bg"], fg=t["text"], font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(0, 10))

        wrapper = tk.Frame(frame, bg=t["panel"])
        wrapper.pack(fill="both", expand=True)

        tree = ttk.Treeview(wrapper, columns=("date", "type", "title", "message", "sender"), show="headings", height=18)
        for col, title, width in [
            ("date", "Date", 130),
            ("type", "Type", 120),
            ("title", "Title", 220),
            ("message", "Message", 420),
            ("sender", "From", 120),
        ]:
            tree.heading(col, text=title)
            tree.column(col, width=width, anchor="w")
        tree.pack(fill="both", expand=True, padx=10, pady=10)

        def refresh_rows():
            for row in tree.get_children():
                tree.delete(row)

            teacher_rows = self.db_safe_all(
                """
                SELECT DATE_FORMAT(created_at, '%Y-%m-%d %H:%i'), 'Teacher', title, message, teacher_username
                FROM teacher_announcements
                WHERE teacher_username=%s
                ORDER BY id DESC
                LIMIT 60
                """,
                (self.username,),
            )

            admin_rows = self.db_safe_all(
                """
                SELECT DATE_FORMAT(created_at, '%Y-%m-%d %H:%i'), 'Admin', title, message, COALESCE(created_by, 'admin')
                FROM admin_announcements
                ORDER BY id DESC
                LIMIT 80
                """,
            )

            submission_rows = self.db_safe_all(
                """
                SELECT DATE_FORMAT(s.submitted_at, '%Y-%m-%d %H:%i'),
                       'Assignment Submission',
                       CONCAT('Assignment #', a.id, ': ', a.title),
                       CONCAT(
                           COALESCE(st.name, s.enrollment_no),
                           ' submitted ',
                           COALESCE(NULLIF(s.submission_path, ''), 'a file'),
                           ' | Course: ', COALESCE(NULLIF(a.course_name, ''), 'N/A'),
                           ' | Sem: ', COALESCE(NULLIF(a.semester, ''), 'N/A'),
                           ' | Sec: ', COALESCE(NULLIF(a.section, ''), 'N/A'),
                           ' | Subject: ', COALESCE(NULLIF(a.subject, ''), 'N/A')
                       ),
                       COALESCE(st.name, s.enrollment_no)
                FROM assignment_submissions s
                JOIN assignments a ON a.id=s.assignment_id
                LEFT JOIN students st ON st.enrollment_no=s.enrollment_no
                WHERE a.teacher_username=%s
                ORDER BY s.id DESC
                LIMIT 120
                """,
                (self.username,),
            )

            rows = sorted((teacher_rows or []) + (admin_rows or []) + (submission_rows or []), key=lambda r: str(r[0] or ""), reverse=True)
            for row in rows:
                tree.insert("", "end", values=row)

        tk.Button(frame, text="Refresh", command=refresh_rows, bg=t["accent"], fg="white", bd=0, padx=12, pady=6).pack(anchor="e", pady=(8, 0))
        refresh_rows()

    def apply_theme_shell(self):
        t = self.theme()
        self.window.configure(bg=t["app_bg"])
        self.header.configure(bg="#2c3e50")
        self.header_left.configure(bg="#2c3e50")
        self.header_center.configure(bg="#2c3e50")
        self.header_stats_row.configure(bg="#2c3e50")
        self.title_label.configure(bg="#2c3e50")
        self.teacher_tag_label.configure(bg="#2c3e50")
        self.user_label.configure(bg="#2c3e50")
        self.profile_photo_label.configure(bg="#2c3e50")
        self.theme_btn.configure(text="🌙 Dark" if self.theme_mode == "light" else "☀ Light")
        self.sidebar.configure(bg="#34495e")
        for key, btn in self.nav_buttons:
            if key == self.current_view:
                btn.configure(bg="#1e293b")
            else:
                btn.configure(bg="#34495e")

    def card(self, parent, title, value, color):
        t = self.theme()
        outer = tk.Frame(parent, bg=t["card_shadow"], bd=0)
        inner = tk.Frame(outer, bg=color, height=96)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        tk.Label(inner, text=title, bg=color, fg="white", font=("Segoe UI", 10, "bold")).pack(pady=(16, 4))
        tk.Label(inner, text=value, bg=color, fg="white", font=("Segoe UI", 18, "bold")).pack()
        self.bind_hover(inner, color, color)
        return outer

    def draw_bar_chart(self, canvas_widget, rows):
        canvas_widget.delete("all")
        w = int(canvas_widget.winfo_width() or 360)
        h = int(canvas_widget.winfo_height() or 220)
        if not rows:
            canvas_widget.create_text(w // 2, h // 2, text="No data", fill="#6b7280", font=("Segoe UI", 11))
            return

        left = 44
        right = 16
        top = 14
        bottom = 42
        plot_w = max(1, w - left - right)
        plot_h = max(1, h - top - bottom)

        canvas_widget.create_line(left, top, left, h - bottom, fill="#64748b", width=1)
        canvas_widget.create_line(left, h - bottom, w - right, h - bottom, fill="#64748b", width=1)
        canvas_widget.create_text(10, top, anchor="w", text="Y", fill="#64748b", font=("Segoe UI", 8, "bold"))
        canvas_widget.create_text(w - 8, h - 8, anchor="e", text="X", fill="#64748b", font=("Segoe UI", 8, "bold"))

        max_val = max(100.0, max(float(r[1]) for r in rows))
        for tick in range(0, 101, 20):
            y = top + plot_h - ((tick / max_val) * plot_h)
            canvas_widget.create_line(left, y, w - right, y, fill="#e2e8f0", width=1)
            canvas_widget.create_text(left - 8, y, text=str(tick), fill="#64748b", font=("Segoe UI", 8), anchor="e")

        step = plot_w / max(1, len(rows))
        bar_width = max(16, int(step * 0.55))
        for idx, row in enumerate(rows):
            label = str(row[0])[:14]
            val = float(row[1])
            bar_h = (val / max_val) * plot_h if max_val else 0
            x_center = left + (idx * step) + (step / 2)
            x1 = x_center - (bar_width / 2)
            y1 = h - bottom - bar_h
            x2 = x_center + (bar_width / 2)
            y2 = h - bottom
            canvas_widget.create_rectangle(x1, y1, x2, y2, fill="#2563eb", outline="")
            canvas_widget.create_text((x1 + x2) / 2, h - 24, text=label, font=("Segoe UI", 8))
            canvas_widget.create_text((x1 + x2) / 2, y1 - 8, text=f"{val:.1f}", font=("Segoe UI", 8))

    def draw_line_chart(self, canvas_widget, rows):
        canvas_widget.delete("all")
        w = int(canvas_widget.winfo_width() or 360)
        h = int(canvas_widget.winfo_height() or 220)
        if not rows or (len(rows) == 1 and rows[0][0] == "No Data"):
            canvas_widget.create_text(w // 2, h // 2, text="No data available", fill="#6b7280", font=("Segoe UI", 11))
            return

        valid_rows = [(r[0], float(r[1])) for r in rows if r[1] is not None and r[1] != ""]
        if not valid_rows:
            canvas_widget.create_text(w // 2, h // 2, text="No data available", fill="#6b7280", font=("Segoe UI", 11))
            return

        max_val = max(float(r[1]) for r in valid_rows) if valid_rows else 100
        max_val = max(max_val, 10)
        points = []
        x_step = max(1, (w - 50) // max(1, len(valid_rows) - 1))
        for i, row in enumerate(valid_rows):
            x = 30 + i * x_step
            y = h - 30 - ((float(row[1]) / max_val) * (h - 70) if max_val else h - 30)
            points.extend([x, y])
            canvas_widget.create_oval(x - 3, y - 3, x + 3, y + 3, fill="#10b981", outline="")
            canvas_widget.create_text(x, h - 12, text=str(row[0])[:9], font=("Segoe UI", 8))
        if len(points) >= 4:
            canvas_widget.create_line(*points, fill="#10b981", width=2, smooth=True)

    def draw_student_trend(self, canvas_widget, records):
        canvas_widget.delete("all")
        t = self.theme()
        w = int(canvas_widget.winfo_width() or 360)
        h = int(canvas_widget.winfo_height() or 220)
        if not records:
            canvas_widget.create_text(w // 2, h // 2, text="Select a student to view marks trend", fill=t["muted"], font=("Segoe UI", 10))
            return

        ordered_records = list(reversed(records[:8]))
        left = 42
        right = 18
        top = 18
        bottom = 42
        plot_w = max(1, w - left - right)
        plot_h = max(1, h - top - bottom)

        for tick in range(0, 101, 20):
            y = top + plot_h - ((tick / 100) * plot_h)
            canvas_widget.create_line(left, y, w - right, y, fill=t["card_shadow"], width=1)
            canvas_widget.create_text(left - 10, y, text=str(tick), fill=t["muted"], font=("Segoe UI", 8))

        canvas_widget.create_line(left, top, left, h - bottom, fill=t["muted"], width=1)
        canvas_widget.create_line(left, h - bottom, w - right, h - bottom, fill=t["muted"], width=1)
        canvas_widget.create_text(left, 8, anchor="w", text="Marks Trend", fill=t["text"], font=("Segoe UI", 10, "bold"))

        step = plot_w / max(1, len(ordered_records) - 1)
        points = []
        for index, record in enumerate(ordered_records):
            subject, exam, marks = record
            mark_value = max(0.0, min(100.0, float(marks or 0)))
            x = left + (index * step if len(ordered_records) > 1 else plot_w / 2)
            y = top + plot_h - ((mark_value / 100) * plot_h)
            label = str(exam or subject or f"Test {index + 1}")[:10]
            points.extend([x, y])
            canvas_widget.create_oval(x - 4, y - 4, x + 4, y + 4, fill=t["accent2"], outline="")
            canvas_widget.create_text(x, y - 12, text=f"{mark_value:.0f}", fill=t["text"], font=("Segoe UI", 8, "bold"))
            canvas_widget.create_text(x, h - bottom + 14, text=label, fill=t["muted"], font=("Segoe UI", 8))

        if len(points) >= 4:
            canvas_widget.create_line(*points, fill=t["accent2"], width=3, smooth=True)

    def draw_pie_chart(self, canvas_widget, rows):
        canvas_widget.delete("all")
        w = int(canvas_widget.winfo_width() or 320)
        h = int(canvas_widget.winfo_height() or 220)
        if not rows:
            canvas_widget.create_text(w // 2, h // 2, text="No data", fill="#6b7280", font=("Segoe UI", 11))
            return

        total = sum(int(r[1]) for r in rows) or 1
        colors = ["#2563eb", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"]
        start = 0
        x1, y1, x2, y2 = 40, 20, 180, 160
        for idx, row in enumerate(rows):
            count = int(row[1])
            extent = (count / total) * 360
            color = colors[idx % len(colors)]
            canvas_widget.create_arc(x1, y1, x2, y2, start=start, extent=extent, fill=color, outline="white")
            canvas_widget.create_rectangle(200, 26 + idx * 24, 214, 40 + idx * 24, fill=color, outline="")
            canvas_widget.create_text(220, 33 + idx * 24, text=f"{row[0]} ({count})", anchor="w", font=("Segoe UI", 9))
            start += extent

    def render_overview(self):
        t = self.theme()
        frame = tk.Frame(self.content, bg=t["app_bg"])
        frame.pack(fill="both", expand=True)

        greeting = tk.Label(
            frame,
            text=f"Welcome back, {self.teacher_info['full_name']}",
            bg=t["app_bg"],
            fg=t["text"],
            font=("Segoe UI", 20, "bold"),
        )
        greeting.pack(anchor="w", pady=(0, 8))

        subtitle = tk.Label(
            frame,
            text=f"Subject: {self.get_assigned_subjects_display()}  •  Department: {self.teacher_info['department']}",
            bg=t["app_bg"],
            fg=t["muted"],
            font=("Segoe UI", 11),
        )
        subtitle.pack(anchor="w", pady=(0, 14))

        stats_row = tk.Frame(frame, bg=t["app_bg"])
        stats_row.pack(fill="x", pady=(0, 12))

        students = self.get_students_for_teacher()
        assignments = self.get_teacher_assignments()
        total_students = len(students)
        classes_assigned = len({(str(a[0]), str(a[1]), str(a[2])) for a in assignments})
        pending_eval = self.fetch_scalar(
            "SELECT COUNT(*) FROM assignments WHERE teacher_username=%s AND status='Open' AND deadline < CURDATE()",
            (self.username,),
            0,
        )
        avg_perf = self.fetch_scalar(
            """
            SELECT ROUND(AVG(r.marks),2)
            FROM results r
            JOIN students s ON s.enrollment_no=r.enrollment_no
            WHERE s.department=%s
            """,
            (self.teacher_info["department"],),
            "N/A",
        )

        cards = [
            self.card(stats_row, "Total Students", str(total_students), "#2563eb"),
            self.card(stats_row, "Classes Assigned", str(classes_assigned), "#4f46e5"),
            self.card(stats_row, "Pending Evaluations", str(pending_eval), "#f59e0b"),
            self.card(stats_row, "Average Performance", f"{avg_perf}", "#10b981"),
        ]

        for idx, c in enumerate(cards):
            c.grid(row=0, column=idx, padx=8, sticky="nsew")
            stats_row.grid_columnconfigure(idx, weight=1)

        chart_wrap = tk.Frame(frame, bg=t["app_bg"])
        chart_wrap.pack(fill="both", expand=True)

        bar_card = tk.Frame(chart_wrap, bg=t["panel"], bd=1, relief="solid")
        line_card = tk.Frame(chart_wrap, bg=t["panel"], bd=1, relief="solid")
        pie_card = tk.Frame(chart_wrap, bg=t["panel"], bd=1, relief="solid")

        bar_card.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        line_card.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        pie_card.grid(row=0, column=2, sticky="nsew", padx=8, pady=8)

        for col in range(3):
            chart_wrap.grid_columnconfigure(col, weight=1)
        chart_wrap.grid_rowconfigure(0, weight=1)

        bar_label = tk.Label(bar_card, text="Class-wise Performance", bg=t["panel"], fg=t["text"], font=("Segoe UI", 11, "bold"))
        bar_label.pack(anchor="w", padx=10, pady=8)
        line_label = tk.Label(line_card, text="Student Progress Over Time (Section-wise)", bg=t["panel"], fg=t["text"], font=("Segoe UI", 11, "bold"))
        line_label.pack(anchor="w", padx=10, pady=8)
        pie_label = tk.Label(pie_card, text="Grade Distribution", bg=t["panel"], fg=t["text"], font=("Segoe UI", 11, "bold"))
        pie_label.pack(anchor="w", padx=10, pady=8)

        bar_canvas = tk.Canvas(bar_card, bg=t["panel"], highlightthickness=0, height=240)
        line_canvas = tk.Canvas(line_card, bg=t["panel"], highlightthickness=0, height=240)
        pie_canvas = tk.Canvas(pie_card, bg=t["panel"], highlightthickness=0, height=240)
        bar_canvas.pack(fill="both", expand=True, padx=8, pady=(0, 10))
        line_canvas.pack(fill="both", expand=True, padx=8, pady=(0, 10))
        pie_canvas.pack(fill="both", expand=True, padx=8, pady=(0, 10))

        class_metrics = self.get_class_performance_rows()
        class_data = [(row["label"], row["score"]) for row in class_metrics]

        line_rows = self.db_safe_all(
                        """
                        SELECT timeline.mon_label, timeline.ym, ROUND(AVG(timeline.score), 2) AS avg_score
                        FROM (
                                SELECT DATE_FORMAT(p.published_at, '%b-%y') AS mon_label,
                                             DATE_FORMAT(p.published_at, '%Y-%m') AS ym,
                                             COALESCE(p.final_total, p.internal_total + p.external_marks) AS score
                                FROM published_results p
                                JOIN students s ON s.enrollment_no = p.enrollment_no
                                JOIN assigned_subjects a
                                    ON a.teacher_username=%s
                                 AND LOWER(TRIM(COALESCE(a.subject_name, ''))) = LOWER(TRIM(COALESCE(p.subject, '')))
                                 AND LOWER(TRIM(COALESCE(a.course_name, ''))) = LOWER(TRIM(COALESCE(s.course, '')))
                                 AND UPPER(TRIM(COALESCE(a.section, ''))) = UPPER(TRIM(COALESCE(s.section, '')))
                                 AND TRIM(COALESCE(a.semester, '')) = TRIM(COALESCE(p.semester, s.semester, ''))
                                WHERE COALESCE(p.final_total, p.internal_total + p.external_marks) IS NOT NULL
                                    AND COALESCE(p.final_total, p.internal_total + p.external_marks) > 0

                                UNION ALL

                                SELECT DATE_FORMAT(r.created_at, '%b-%y') AS mon_label,
                                             DATE_FORMAT(r.created_at, '%Y-%m') AS ym,
                                             r.marks AS score
                                FROM results r
                                JOIN students s ON s.enrollment_no = r.enrollment_no
                                JOIN assigned_subjects a
                                    ON a.teacher_username=%s
                                 AND LOWER(TRIM(COALESCE(a.subject_name, ''))) = LOWER(TRIM(COALESCE(r.subject, '')))
                                 AND LOWER(TRIM(COALESCE(a.course_name, ''))) = LOWER(TRIM(COALESCE(s.course, '')))
                                 AND UPPER(TRIM(COALESCE(a.section, ''))) = UPPER(TRIM(COALESCE(s.section, '')))
                                 AND TRIM(COALESCE(a.semester, '')) = TRIM(COALESCE(s.semester, ''))
                                WHERE r.marks IS NOT NULL
                                    AND r.marks > 0
                        ) AS timeline
                        GROUP BY timeline.mon_label, timeline.ym
                        ORDER BY timeline.ym ASC
                        LIMIT 12
                        """,
                        (self.username, self.username),
                )
        line_data = [(str(row[0] or ""), float(row[2] or 0)) for row in (line_rows or [])]

        if not line_data:
            line_rows = self.db_safe_all(
                """
                SELECT DATE_FORMAT(attendance_date, '%b-%y') AS mon_label,
                       DATE_FORMAT(attendance_date, '%Y-%m') AS ym,
                       ROUND((SUM(CASE WHEN UPPER(COALESCE(status,''))='PRESENT' THEN 1 ELSE 0 END) / COUNT(*)) * 100, 2) AS attendance_pct
                FROM attendance
                WHERE teacher_username=%s
                  AND UPPER(COALESCE(status,'')) IN ('PRESENT', 'ABSENT')
                GROUP BY mon_label, ym
                ORDER BY ym ASC
                LIMIT 12
                """,
                (self.username,),
            )
            line_data = [(str(row[0] or ""), float(row[2] or 0)) for row in (line_rows or [])]

        if not line_data:
            line_data = [("No Data", 0)]

        grade_counts = {"A+": 0, "A": 0, "B": 0, "C": 0, "D": 0}
        marks_rows = self.db_safe_all(
            "SELECT marks FROM results WHERE teacher_username=%s AND marks IS NOT NULL",
            (self.username,),
        )
        for marks_row in marks_rows:
            try:
                value = float(marks_row[0] or 0)
                if value >= 90:
                    grade_counts["A+"] += 1
                elif value >= 80:
                    grade_counts["A"] += 1
                elif value >= 70:
                    grade_counts["B"] += 1
                elif value >= 60:
                    grade_counts["C"] += 1
                else:
                    grade_counts["D"] += 1
            except (ValueError, TypeError):
                pass
        pie_data = [(grade, grade_counts[grade]) for grade in ["A+", "A", "B", "C", "D"] if grade_counts[grade] > 0]
        if not pie_data:
            pie_data = [("No Data", 1)]

        def redraw_charts():
            try:
                self.draw_bar_chart(bar_canvas, class_data)
                self.draw_line_chart(line_canvas, line_data)
                self.draw_pie_chart(pie_canvas, pie_data)
            except Exception:
                pass

        bar_canvas.after(100, redraw_charts)
        line_canvas.after(150, redraw_charts)
        pie_canvas.after(200, redraw_charts)
        
        def on_canvas_configure(_event):
            bar_canvas.after(50, redraw_charts)
        
        bar_canvas.bind("<Configure>", on_canvas_configure)
        line_canvas.bind("<Configure>", on_canvas_configure)
        pie_canvas.bind("<Configure>", on_canvas_configure)

    def render_students(self):
        t = self.theme()
        wrap = tk.Frame(self.content, bg=t["app_bg"])
        wrap.pack(fill="both", expand=True)

        all_students = self.get_department_students()

        top = tk.Frame(wrap, bg=t["panel"])
        top.pack(fill="x", pady=(0, 8))
        tk.Label(top, text="Student Management", bg=t["panel"], fg=t["text"], font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=12, pady=10)
        tk.Label(
            top,
            text="Review assigned learners, search by enrollment, and track individual performance trends.",
            bg=t["panel"],
            fg=t["muted"],
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=12, pady=(0, 10))

        summary_row = tk.Frame(top, bg=t["panel"])
        summary_row.pack(fill="x", padx=12, pady=(0, 10))

        assigned_count_var = tk.StringVar(value=str(len(all_students)))
        filtered_count_var = tk.StringVar(value=str(len(all_students)))
        selected_student_var = tk.StringVar(value="None")
        course_total_var = tk.StringVar(value=str(len({str(s[2]).strip() for s in all_students if str(s[2]).strip()})))

        def build_summary_card(parent, title, value_var, accent):
            card = tk.Frame(parent, bg=t["app_bg"], bd=1, relief="solid", highlightthickness=0)
            tk.Label(card, text=title, bg=t["app_bg"], fg=t["muted"], font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=12, pady=(10, 2))
            tk.Label(card, textvariable=value_var, bg=t["app_bg"], fg=accent, font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=12, pady=(0, 10))
            return card

        for index, card in enumerate(
            [
                build_summary_card(summary_row, "Assigned Students", assigned_count_var, t["accent"]),
                build_summary_card(summary_row, "Filtered Results", filtered_count_var, t["accent2"]),
                build_summary_card(summary_row, "Courses Covered", course_total_var, "#f59e0b"),
                build_summary_card(summary_row, "Selected Student", selected_student_var, "#4f46e5"),
            ]
        ):
            card.grid(row=0, column=index, sticky="nsew", padx=4)
            summary_row.grid_columnconfigure(index, weight=1)

        control = tk.Frame(top, bg=t["panel"])
        control.pack(fill="x", padx=12, pady=(0, 10))

        search_var = tk.StringVar()
        filter_status_var = tk.StringVar(value="Showing all assigned students")

        tk.Label(control, text="Search Enrollment", bg=t["panel"], fg=t["text"]).pack(side="left")
        search_entry = tk.Entry(control, textvariable=search_var, width=28)
        search_entry.pack(side="left", padx=6)
        tk.Label(control, text="Enrollment / Name / Email", bg=t["panel"], fg=t["muted"]).pack(side="left", padx=(0, 8))

        tk.Label(control, text="Course", bg=t["panel"], fg=t["text"]).pack(side="left", padx=(10, 0))
        course_var = tk.StringVar(value="All")
        course_box = ttk.Combobox(control, textvariable=course_var, state="readonly", width=18)
        course_values = sorted({str(s[2]).strip() for s in all_students if str(s[2]).strip()})
        course_box["values"] = ["All"] + course_values
        course_box.current(0)
        course_box.pack(side="left", padx=6)

        filter_status = tk.Label(top, textvariable=filter_status_var, bg=t["panel"], fg=t["muted"], font=("Segoe UI", 9))
        filter_status.pack(anchor="w", padx=12, pady=(0, 10))

        body = tk.PanedWindow(wrap, orient=tk.HORIZONTAL, sashrelief="flat", bg=t["app_bg"])
        body.pack(fill="both", expand=True)

        left = tk.Frame(body, bg=t["panel"])
        right = tk.Frame(body, bg=t["panel"], width=420)
        body.add(left, stretch="always")
        body.add(right)

        tk.Label(left, text="Assigned Students", bg=t["panel"], fg=t["text"], font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=10, pady=(10, 0))
        tk.Label(left, text="Select a student to inspect profile, results, and progress trend.", bg=t["panel"], fg=t["muted"], font=("Segoe UI", 9)).pack(anchor="w", padx=10, pady=(2, 8))

        columns = ("enrollment", "name", "course", "semester", "section", "email")
        tree_wrap = tk.Frame(left, bg=t["panel"])
        tree_wrap.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        tree = ttk.Treeview(tree_wrap, columns=columns, show="headings", height=18)
        for col, text, width in [
            ("enrollment", "Enrollment", 110),
            ("name", "Name", 145),
            ("course", "Course", 110),
            ("semester", "Sem", 60),
            ("section", "Sec", 60),
            ("email", "Email", 170),
        ]:
            tree.heading(col, text=text)
            tree.column(col, width=width, anchor="center")
        tree_scroll = ttk.Scrollbar(tree_wrap, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=tree_scroll.set)
        tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")

        page_lbl = tk.Label(left, text="", bg=t["panel"], fg=t["muted"], font=("Segoe UI", 10, "bold"))
        page_lbl.pack(pady=(0, 8))

        nav = tk.Frame(left, bg=t["panel"])
        nav.pack(fill="x", padx=10, pady=(0, 10))

        profile_card = tk.Frame(right, bg=t["app_bg"], bd=1, relief="solid")
        profile_card.pack(fill="x", padx=10, pady=(10, 8))
        profile_title = tk.Label(profile_card, text="Student Profile", bg=t["app_bg"], fg=t["text"], font=("Segoe UI", 13, "bold"))
        profile_title.pack(anchor="w", padx=12, pady=(10, 2))
        tk.Label(profile_card, text="Academic overview and contact details", bg=t["app_bg"], fg=t["muted"], font=("Segoe UI", 9)).pack(anchor="w", padx=12, pady=(0, 8))

        metrics_row = tk.Frame(profile_card, bg=t["app_bg"])
        metrics_row.pack(fill="x", padx=12, pady=(0, 8))

        attendance_var = tk.StringVar(value="0%")
        average_marks_var = tk.StringVar(value="0")
        exams_count_var = tk.StringVar(value="0")
        trend_caption_var = tk.StringVar(value="Select a student to view latest marks trend")

        def build_metric_tile(parent, title, value_var, accent):
            tile = tk.Frame(parent, bg=t["panel"], bd=1, relief="solid")
            tk.Label(tile, text=title, bg=t["panel"], fg=t["muted"], font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=10, pady=(8, 2))
            tk.Label(tile, textvariable=value_var, bg=t["panel"], fg=accent, font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=10, pady=(0, 8))
            return tile

        for index, tile in enumerate(
            [
                build_metric_tile(metrics_row, "Attendance", attendance_var, t["accent2"]),
                build_metric_tile(metrics_row, "Average Marks", average_marks_var, t["accent"]),
                build_metric_tile(metrics_row, "Recent Exams", exams_count_var, "#f59e0b"),
            ]
        ):
            tile.grid(row=0, column=index, sticky="nsew", padx=4)
            metrics_row.grid_columnconfigure(index, weight=1)

        profile_text = tk.Text(profile_card, height=9, bg=t["app_bg"], fg=t["text"], bd=0, font=("Segoe UI", 10), wrap="word")
        profile_text.pack(fill="x", padx=12, pady=(0, 12))
        profile_text.insert(tk.END, "Select a student from the table to load profile information.")
        profile_text.configure(state="disabled")

        marks_card = tk.Frame(right, bg=t["app_bg"], bd=1, relief="solid")
        marks_card.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        tk.Label(marks_card, text="Latest Result Records", bg=t["app_bg"], fg=t["text"], font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(10, 6))

        marks_wrap = tk.Frame(marks_card, bg=t["app_bg"])
        marks_wrap.pack(fill="x", padx=12, pady=(0, 8))

        marks_tree = ttk.Treeview(marks_wrap, columns=("subject", "exam", "marks"), show="headings", height=6)
        for c in ["subject", "exam", "marks"]:
            marks_tree.heading(c, text=c.title())
            marks_tree.column(c, width=95, anchor="center")
        marks_scroll = ttk.Scrollbar(marks_wrap, orient="vertical", command=marks_tree.yview)
        marks_tree.configure(yscrollcommand=marks_scroll.set)
        marks_tree.pack(side="left", fill="x", expand=True)
        marks_scroll.pack(side="right", fill="y")

        trend_card = tk.Frame(marks_card, bg=t["panel"], bd=0)
        trend_card.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        tk.Label(trend_card, text="Performance Trend", bg=t["panel"], fg=t["text"], font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(8, 0))
        tk.Label(trend_card, textvariable=trend_caption_var, bg=t["panel"], fg=t["muted"], font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 8))

        trend_canvas = tk.Canvas(trend_card, height=190, bg=t["panel"], highlightthickness=0)
        trend_canvas.pack(fill="x", pady=(0, 4))

        feedback_card = tk.Frame(right, bg=t["app_bg"], bd=1, relief="solid")
        feedback_card.pack(fill="x", padx=10, pady=(0, 10))
        tk.Label(feedback_card, text="Add Feedback", bg=t["app_bg"], fg=t["text"], font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=(10, 2))
        tk.Label(feedback_card, text="Share a quick note for the selected student.", bg=t["app_bg"], fg=t["muted"], font=("Segoe UI", 9)).pack(anchor="w", padx=12, pady=(0, 6))
        remark_box = tk.Text(right, height=4, font=("Segoe UI", 10))
        remark_box.pack(in_=feedback_card, fill="x", padx=12, pady=(0, 10))

        def load_students():
            for row in tree.get_children():
                tree.delete(row)

            search = search_var.get().strip().lower()
            course = course_var.get()
            filtered = []
            for student in all_students:
                enrollment_no = str(student[0] or "").strip()
                student_name = str(student[1] or "").strip()
                email = str(student[5] or "").strip()
                searchable_values = (enrollment_no.lower(), student_name.lower(), email.lower())
                if search and not any(search in value for value in searchable_values):
                    continue
                if course != "All" and not course_matches(student[2], course):
                    continue
                filtered.append((student[0], student[1], student[2], student[3], student[4], student[5]))

            self.student_total = len(filtered)
            total_pages = max(1, (self.student_total + self.page_size - 1) // self.page_size)
            if self.student_page > total_pages:
                self.student_page = total_pages

            offset = (self.student_page - 1) * self.page_size
            rows = filtered[offset: offset + self.page_size]

            for row in rows:
                tree.insert("", "end", values=row)
            page_lbl.config(text=f"Page {self.student_page}/{total_pages}  •  Records: {self.student_total}")
            filtered_count_var.set(str(self.student_total))

            active_filters = []
            if search:
                active_filters.append(f"search '{search_var.get().strip()}'")
            if course != "All":
                active_filters.append(f"course {course}")
            if active_filters:
                filter_status_var.set(f"Showing {self.student_total} student{'s' if self.student_total != 1 else ''} for " + " and ".join(active_filters))
            else:
                filter_status_var.set(f"Showing all assigned students ({self.student_total})")

            if rows:
                first_item = tree.get_children()[0]
                tree.selection_set(first_item)
                tree.focus(first_item)
                on_select()
            else:
                selected_student_var.set("None")
                attendance_var.set("0%")
                average_marks_var.set("0")
                exams_count_var.set("0")
                trend_caption_var.set("No records available for the current filters")
                profile_text.configure(state="normal")
                profile_text.delete("1.0", tk.END)
                profile_text.insert(tk.END, "No student matches the selected filters.")
                profile_text.configure(state="disabled")
                for row in marks_tree.get_children():
                    marks_tree.delete(row)
                self.draw_student_trend(trend_canvas, [])

        def apply_student_filters(_event=None):
            self.student_page = 1
            load_students()

        def clear_student_filters():
            search_var.set("")
            course_var.set("All")
            self.student_page = 1
            load_students()

        def prev_page():
            if self.student_page > 1:
                self.student_page -= 1
                load_students()

        def next_page():
            total_pages = max(1, (self.student_total + self.page_size - 1) // self.page_size)
            if self.student_page < total_pages:
                self.student_page += 1
                load_students()

        tk.Button(nav, text="Previous", command=prev_page, bg=t["accent"], fg="white", bd=0, padx=12).pack(side="left", padx=2)
        tk.Button(nav, text="Next", command=next_page, bg=t["accent"], fg="white", bd=0, padx=12).pack(side="left", padx=2)
        tk.Button(control, text="Search", command=apply_student_filters, bg=t["accent"], fg="white", bd=0, padx=12).pack(side="left", padx=4)
        tk.Button(control, text="Clear", command=clear_student_filters, bg=t["accent2"], fg="white", bd=0, padx=12).pack(side="left")

        def draw_trend(records):
            self.draw_student_trend(trend_canvas, records)

        def on_select(_event=None):
            selected = tree.focus()
            if not selected:
                return
            values = tree.item(selected, "values")
            enrollment = values[0]
            selected_student_var.set(str(values[1])[:18] or "None")

            detail = self.db_safe_one(
                """
                SELECT name, enrollment_no, course, semester, section, dob, email, phone
                FROM students WHERE enrollment_no=%s
                """,
                (enrollment,),
            )

            att = self.fetch_scalar(
                "SELECT ROUND((SUM(status='Present')/COUNT(*))*100,2) FROM attendance WHERE enrollment_no=%s",
                (enrollment,),
                0,
            )

            profile_text.configure(state="normal")
            profile_text.delete("1.0", tk.END)
            if detail:
                profile_text.insert(
                    tk.END,
                    f"Name: {detail[0]}\nEnrollment: {detail[1]}\nCourse: {detail[2]}\n"
                    f"Semester: {detail[3]}   Section: {detail[4]}\nDOB: {detail[5]}\n"
                    f"Email: {detail[6]}\nPhone: {detail[7]}\nAttendance: {att}%\n",
                )
            profile_text.configure(state="disabled")
            attendance_var.set(f"{att}%")

            for row in marks_tree.get_children():
                marks_tree.delete(row)

            records = self.db_safe_all(
                "SELECT subject, exam, marks FROM results WHERE enrollment_no=%s ORDER BY id DESC LIMIT 8",
                (enrollment,),
            )
            for rec in records:
                marks_tree.insert("", "end", values=rec)
            exams_count_var.set(str(len(records)))
            if records:
                average_marks_var.set(f"{sum(float(record[2]) for record in records) / len(records):.1f}")
                trend_caption_var.set(f"Latest {len(records)} exam records for {detail[0] if detail else enrollment}")
            else:
                average_marks_var.set("0")
                trend_caption_var.set(f"No marks found for {detail[0] if detail else enrollment}")
            draw_trend(records)

        def save_remark():
            selected = tree.focus()
            if not selected:
                messagebox.showwarning("Select Student", "Please select a student first.")
                return
            text = remark_box.get("1.0", tk.END).strip()
            if not text:
                messagebox.showwarning("Feedback", "Please enter feedback.")
                return
            enrollment = tree.item(selected, "values")[0]
            try:
                self.db_execute(
                    "INSERT INTO teacher_remarks (enrollment_no, teacher_username, remark) VALUES (%s,%s,%s)",
                    (enrollment, self.username, text),
                    fetch=None,
                )
                remark_box.delete("1.0", tk.END)
                messagebox.showinfo("Saved", "Feedback saved.")
            except Exception as err:
                messagebox.showerror("Error", str(err))

        tk.Button(feedback_card, text="Save Feedback", command=save_remark, bg=t["accent2"], fg="white", bd=0, padx=12, pady=6).pack(anchor="e", padx=12, pady=(0, 10))
        tree.bind("<<TreeviewSelect>>", on_select)
        search_entry.bind("<Return>", apply_student_filters)
        course_box.bind("<<ComboboxSelected>>", apply_student_filters)
        load_students()

    def render_classes_subjects(self):
        t = self.theme()
        frame = tk.Frame(self.content, bg=t["app_bg"])
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="Class & Subject Management", bg=t["app_bg"], fg=t["text"], font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(0, 10))

        top = tk.Frame(frame, bg=t["app_bg"])
        top.pack(fill="x")

        class_box = tk.Frame(top, bg=t["panel"])
        subject_box = tk.Frame(top, bg=t["panel"])
        compare_box = tk.Frame(top, bg=t["panel"])

        class_box.pack(side="left", fill="both", expand=True, padx=5)
        subject_box.pack(side="left", fill="both", expand=True, padx=5)
        compare_box.pack(side="left", fill="both", expand=True, padx=5)

        tk.Label(class_box, text="Assigned Classes", bg=t["panel"], fg=t["text"], font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=8)
        class_tree = ttk.Treeview(class_box, columns=("course", "semester", "section", "students"), show="headings", height=10)
        for c, w in [("course", 120), ("semester", 80), ("section", 80), ("students", 80)]:
            class_tree.heading(c, text=c.title())
            class_tree.column(c, width=w, anchor="center")
        class_tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        tk.Label(subject_box, text="Assigned Subjects", bg=t["panel"], fg=t["text"], font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=8)
        subject_list = tk.Listbox(subject_box, height=10)
        subject_list.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        tk.Label(compare_box, text="Class Performance Comparison", bg=t["panel"], fg=t["text"], font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=8)
        compare_canvas = tk.Canvas(compare_box, bg=t["panel"], height=220, highlightthickness=0)
        compare_canvas.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        compare_summary_var = tk.StringVar(value="")
        tk.Label(compare_box, textvariable=compare_summary_var, bg=t["panel"], fg=t["muted"], font=("Segoe UI", 9), justify="left", wraplength=320).pack(anchor="w", padx=10, pady=(0, 10))

        timetable = tk.Frame(frame, bg=t["panel"])
        timetable.pack(fill="both", expand=True, pady=10)
        tk.Label(timetable, text="Class Timetable View", bg=t["panel"], fg=t["text"], font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=8)

        day_search_row = tk.Frame(timetable, bg=t["panel"])
        day_search_row.pack(fill="x", padx=10, pady=(0, 8))

        day_search_var = tk.StringVar(value="Select Day")
        day_hint_var = tk.StringVar(value="Select a day and click See to view the assigned timetable")
        day_order = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")

        tk.Label(day_search_row, text="Day", bg=t["panel"], fg=t["text"]).pack(side="left")
        day_search_entry = ttk.Combobox(day_search_row, textvariable=day_search_var, state="readonly", width=16)
        day_search_entry["values"] = ("Select Day",) + day_order
        day_search_entry.pack(side="left", padx=(8, 6))

        ttree = ttk.Treeview(timetable, columns=("day", "time", "class", "subject"), show="headings", height=6)
        for c, w in [("day", 120), ("time", 140), ("class", 140), ("subject", 180)]:
            ttree.heading(c, text=c.title())
            ttree.column(c, width=w, anchor="center")
        ttree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        tk.Label(timetable, textvariable=day_hint_var, bg=t["panel"], fg=t["muted"], font=("Segoe UI", 9)).pack(anchor="w", padx=10, pady=(0, 10))

        assigned_classes = self.get_teacher_assigned_classes()
        student_counter = {}
        for s in self.get_students_for_teacher():
            key = (
                str(s[2] or "").strip().upper(),
                normalize_semester(str(s[3] or "").strip()),
                str(s[4] or "").strip().upper(),
            )
            student_counter[key] = student_counter.get(key, 0) + 1

        class_rows = []
        for course_name, semester, section in assigned_classes:
            key = (course_name.strip().upper(), semester, section)
            class_rows.append((course_name, semester, section, student_counter.get(key, 0)))

        for row in class_rows:
            class_tree.insert("", "end", values=row)

        subject_names = sorted({str(a[3]).strip() for a in self.get_teacher_assignments() if str(a[3]).strip()})
        if not subject_names:
            fallback_subjects = self.db_safe_all(
                "SELECT subject_name FROM subjects WHERE department=%s AND is_active=1 ORDER BY subject_name",
                (self.teacher_info["department"],),
            )
            subject_names = [str(row[0]).strip() for row in fallback_subjects if row and row[0]]
        for subject_name in subject_names:
            subject_list.insert(tk.END, subject_name)

        class_metrics = self.get_class_performance_rows()
        compare_data = [(row["label"], row["score"]) for row in class_metrics]
        compare_summary_var.set(
            "\n".join(
                [
                    f"{row['label']}: Attendance {row['attendance']:.1f}% | Overall {row['overall']:.1f} | Top Scorers {row['top_count']}"
                    for row in class_metrics
                ]
            )
            if class_metrics
            else "No class performance data found for assigned sections."
        )
        compare_canvas.after(50, lambda: self.draw_bar_chart(compare_canvas, compare_data))

        def refresh_timetable(_event=None):
            day_filter = day_search_var.get().strip()
            for item in ttree.get_children():
                ttree.delete(item)

            if day_filter == "Select Day":
                day_hint_var.set("Please select a day to view the timetable")
                return

            timetable_rows = self.db_safe_all(
                """
                SELECT lecture_day, lecture_time, course_name, semester, section, subject_name
                FROM assigned_subjects
                WHERE teacher_username=%s AND lecture_day=%s
                ORDER BY lecture_time
                """,
                (self.username, day_filter),
            )

            visible_count = 0
            for day, lecture_time, course_name, semester, section, subject_name in timetable_rows:
                day_text = str(day or "").strip()
                class_name = f"{course_name}-{semester}-{section}"
                ttree.insert("", "end", values=(day_text, lecture_time, class_name, subject_name))
                visible_count += 1

            if visible_count:
                day_hint_var.set(f"Showing {visible_count} timetable entr{'y' if visible_count == 1 else 'ies'} for {day_filter}")
            else:
                day_hint_var.set(f"No assigned timetable found for {day_filter}")

        def clear_timetable_search():
            day_search_var.set("Select Day")
            for item in ttree.get_children():
                ttree.delete(item)
            day_hint_var.set("Select a day and click See to view the assigned timetable")

        tk.Button(day_search_row, text="See", command=refresh_timetable, bg=t["accent"], fg="white", bd=0, padx=12).pack(side="left", padx=(8, 4))
        tk.Button(day_search_row, text="Show All", command=clear_timetable_search, bg=t["accent2"], fg="white", bd=0, padx=12).pack(side="left")

        day_search_entry.bind("<Return>", refresh_timetable)

    def render_attendance(self):
        t = self.theme()
        frame = tk.Frame(self.content, bg=t["app_bg"])
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="Attendance Management", bg=t["app_bg"], fg=t["text"], font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(0, 10))

        control = tk.Frame(frame, bg=t["panel"])
        control.pack(fill="x", pady=(0, 10))

        tk.Label(control, text="Date", bg=t["panel"], fg=t["text"]).pack(side="left", padx=(10, 4), pady=8)
        date_entry = tk.Entry(control, width=14)
        date_entry.insert(0, str(date.today()))
        date_entry.pack(side="left", padx=4)

        tk.Label(control, text="Department", bg=t["panel"], fg=t["text"]).pack(side="left", padx=(10, 4))
        department_var = tk.StringVar(value=self.teacher_info["department"])
        department_box = ttk.Combobox(control, textvariable=department_var, state="readonly", values=[self.teacher_info["department"]], width=16)
        department_box.current(0)
        department_box.pack(side="left", padx=4)

        tk.Label(control, text="Course", bg=t["panel"], fg=t["text"]).pack(side="left", padx=(10, 4))
        course_var = tk.StringVar(value="Select")
        course_box = ttk.Combobox(control, textvariable=course_var, state="readonly", values=["Select"], width=14)
        course_box.current(0)
        course_box.pack(side="left", padx=4)

        tk.Label(control, text="Semester", bg=t["panel"], fg=t["text"]).pack(side="left", padx=(10, 4))
        semester_var = tk.StringVar(value="Select")
        semester_box = ttk.Combobox(control, textvariable=semester_var, state="readonly", values=["Select"], width=10)
        semester_box.current(0)
        semester_box.pack(side="left", padx=4)

        tk.Label(control, text="Section", bg=t["panel"], fg=t["text"]).pack(side="left", padx=(10, 4))
        section_var = tk.StringVar(value="Select")
        section_box = ttk.Combobox(control, textvariable=section_var, state="readonly", values=["Select"], width=10)
        section_box.current(0)
        section_box.pack(side="left", padx=4)

        tk.Label(control, text="Subject", bg=t["panel"], fg=t["text"]).pack(side="left", padx=(10, 4))
        subject_var = tk.StringVar(value="Select")
        subject_box = ttk.Combobox(control, textvariable=subject_var, state="readonly", values=["Select"], width=24)
        subject_box.current(0)
        subject_box.pack(side="left", padx=4)

        tree = ttk.Treeview(frame, columns=("enroll", "name", "status"), show="headings", height=13)
        for c, w, txt in [("enroll", 140, "Enrollment"), ("name", 220, "Name"), ("status", 160, "Status  (click to toggle)")]:
            tree.heading(c, text=txt)
            tree.column(c, width=w, anchor="center")
        tree.pack(fill="both", expand=True, pady=(0, 8))
        tree.tag_configure("status_present", foreground="#2563eb")
        tree.tag_configure("status_absent", foreground="#64748b")

        btn_row = tk.Frame(frame, bg=t["app_bg"])
        btn_row.pack(fill="x", pady=6)

        analytics = tk.Label(frame, text="", bg=t["app_bg"], fg=t["muted"], font=("Segoe UI", 10, "bold"))
        analytics.pack(anchor="w", pady=(4, 8))

        def status_text(status):
            return "✓ Present" if status == "Present" else "○ Absent"

        def status_tag(status):
            return "status_present" if status == "Present" else "status_absent"

        def set_row_status(item, status):
            vals = list(tree.item(item, "values"))
            if not vals:
                return
            enrollment = str(vals[0]).strip()
            vals[2] = status_text(status)
            tree.item(item, values=vals, tags=(status_tag(status),))
            self.attendance_status[enrollment] = status

        def load_filter_options():
            rows = []
            for student in self.get_students_for_teacher():
                course_name = str(student[2] or "").strip()
                sem_number = self.to_semester_number(student[3])
                section_name = str(student[4] or "").strip().upper()
                rows.append((course_name, sem_number, section_name))

            courses = sorted({row[0] for row in rows if row[0]})
            semesters = sorted({row[1] for row in rows if row[1]}, key=lambda value: int(value))
            sections = sorted({row[2] for row in rows if row[2]})

            course_box["values"] = ["Select"] + courses
            semester_box["values"] = ["Select"] + semesters
            section_box["values"] = ["Select"] + sections
            subject_box["values"] = ["Select"]
            course_var.set("Select")
            semester_var.set("Select")
            section_var.set("Select")
            subject_var.set("Select")

        def refresh_semester_options(event=None):
            selected_course = course_var.get().strip()
            if selected_course == "Select":
                semester_box["values"] = ["Select"]
                semester_var.set("Select")
                section_box["values"] = ["Select"]
                section_var.set("Select")
                subject_box["values"] = ["Select"]
                subject_var.set("Select")
                return
            sems = sorted(
                {
                    self.to_semester_number(s[3])
                    for s in self.get_students_for_teacher()
                    if course_matches(s[2], selected_course)
                }
                - {""},
                key=lambda value: int(value),
            )
            values = ["Select"] + sems
            semester_box["values"] = values if len(values) > 1 else ["Select"]
            semester_var.set("Select")
            section_box["values"] = ["Select"]
            section_var.set("Select")
            subject_box["values"] = ["Select"]
            subject_var.set("Select")

        def refresh_section_options(event=None):
            selected_course = course_var.get().strip()
            selected_semester = semester_var.get().strip()
            if selected_course == "Select" or selected_semester == "Select":
                section_box["values"] = ["Select"]
                section_var.set("Select")
                subject_box["values"] = ["Select"]
                subject_var.set("Select")
                return
            sects = sorted(
                {
                    str(s[4] or "").strip().upper()
                    for s in self.get_students_for_teacher()
                    if course_matches(s[2], selected_course)
                    and self.to_semester_number(s[3]) == selected_semester
                    and str(s[4] or "").strip()
                }
            )
            values = ["Select"] + sects
            section_box["values"] = values if len(values) > 1 else ["Select"]
            section_var.set("Select")
            subject_box["values"] = ["Select"]
            subject_var.set("Select")

        def refresh_subject_options(event=None):
            selected_course = course_var.get().strip()
            selected_semester = semester_var.get().strip()
            selected_section = section_var.get().strip().upper()
            if (
                selected_course == "Select"
                or selected_semester == "Select"
                or selected_section == "Select"
            ):
                subject_box["values"] = ["Select"]
                subject_var.set("Select")
                return

            sem_variants = []
            for value in [selected_semester, normalize_semester(selected_semester)]:
                value = str(value or "").strip()
                if value and value not in sem_variants:
                    sem_variants.append(value)

            placeholders = ",".join(["%s"] * len(sem_variants))
            rows = self.db_safe_all(
                f"""
                SELECT course_name, subject_code, subject_name
                FROM assigned_subjects
                WHERE teacher_username=%s
                  AND UPPER(TRIM(section))=UPPER(TRIM(%s))
                  AND semester IN ({placeholders})
                ORDER BY subject_name, subject_code
                """,
                (self.username, selected_section, *sem_variants),
            )

            subjects = []
            seen = set()
            for row in rows:
                course_name = str(row[0] or "").strip()
                code = str(row[1] or "").strip()
                name = str(row[2] or "").strip()
                if not code and not name:
                    continue
                if not course_matches(course_name, selected_course):
                    continue
                display = f"{code} - {name}" if code else name
                key = display.upper()
                if key in seen:
                    continue
                seen.add(key)
                subjects.append(display)

            subject_box["values"] = ["Select"] + subjects if subjects else ["Select"]
            subject_var.set("Select")

        def load_students_for_attendance():
            for row in tree.get_children():
                tree.delete(row)
            self.attendance_status = {}
            chosen_course = course_var.get().strip()
            chosen_semester = semester_var.get().strip()
            chosen_section = section_var.get().strip()
            chosen_subject = subject_var.get().strip()
            if (
                chosen_course == "Select"
                or chosen_semester == "Select"
                or chosen_section == "Select"
                or chosen_subject == "Select"
            ):
                messagebox.showwarning("Input", "Select course, semester, section and subject.")
                return
            students = [
                (s[0], s[1])
                for s in self.get_students_for_teacher()
                if course_matches(s[2], chosen_course)
                and self.to_semester_number(s[3]) == chosen_semester
                and str(s[4] or "").strip().upper() == chosen_section.upper()
            ]
            if not students:
                messagebox.showinfo("No Students", "No students found for selected filters.")
                return
            for s in students:
                self.attendance_status[s[0]] = "Present"
                tree.insert("", "end", values=(s[0], s[1], status_text("Present")), tags=(status_tag("Present"),))
            refresh_analytics()

        def toggle_status(event=None):
            if tree.identify("region", event.x, event.y) != "cell":
                return
            if tree.identify_column(event.x) != "#3":
                return

            item = tree.identify_row(event.y)
            if not item:
                return
            vals = list(tree.item(item, "values"))
            if not vals:
                return "break"
            enrollment = vals[0]
            if self.attendance_status.get(enrollment) == "Present":
                set_row_status(item, "Absent")
            else:
                set_row_status(item, "Present")
            refresh_analytics()
            return "break"

        def set_selected(status):
            selected = tree.selection()
            for item in selected:
                set_row_status(item, status)
            refresh_analytics()

        def set_all(status):
            for item in tree.get_children():
                set_row_status(item, status)
            refresh_analytics()

        def submit_attendance():
            if not tree.get_children():
                messagebox.showwarning("No Data", "Please load students first.")
                return
            department = department_var.get().strip()
            chosen_course = course_var.get().strip()
            chosen_semester = semester_var.get().strip()
            chosen_section = section_var.get().strip()
            chosen_subject = subject_var.get().strip()
            dt = date_entry.get().strip()
            if (
                chosen_course == "Select"
                or chosen_semester == "Select"
                or chosen_section == "Select"
                or chosen_subject == "Select"
                or not dt
            ):
                messagebox.showwarning("Input", "Select course, semester, section, subject and date.")
                return

            if " - " in chosen_subject:
                selected_subject_code, selected_subject_name = [p.strip() for p in chosen_subject.split(" - ", 1)]
            else:
                selected_subject_code = chosen_subject.strip()
                selected_subject_name = chosen_subject.strip()

            if not selected_subject_code:
                messagebox.showwarning("Input", "Invalid subject selected.")
                return
            try:
                datetime.strptime(dt, "%Y-%m-%d")
            except ValueError:
                messagebox.showwarning("Date", "Use YYYY-MM-DD date format.")
                return

            all_items = tree.get_children()
            total = len(all_items)
            present_count = sum(
                1 for item in all_items
                if self.attendance_status.get(tree.item(item, "values")[0]) == "Present"
            )

            popup = tk.Toplevel(self.window)
            popup.title("Confirm Attendance")
            popup.geometry("340x180")
            popup.resizable(False, False)
            popup.grab_set()
            popup.transient(self.window)

            tk.Label(
                popup, text="Attendance Summary",
                font=("Segoe UI", 13, "bold"), fg="#1f2937", bg="#f9fafb"
            ).pack(pady=(20, 6))
            popup.configure(bg="#f9fafb")
            tk.Label(
                popup,
                text=f"Subject: {selected_subject_code}  |  Present: {present_count}/{total}",
                font=("Segoe UI", 11), fg="#374151", bg="#f9fafb"
            ).pack(pady=4)

            def confirm_save():
                popup.destroy()
                class_label = f"{chosen_course}-{chosen_semester}-{chosen_section}-{selected_subject_code}"
                try:
                    for item in all_items:
                        enroll, _name, _sym = tree.item(item, "values")
                        status = self.attendance_status.get(enroll, "Absent")
                        self.db_execute(
                            """
                            INSERT INTO attendance
                                (attendance_date, enrollment_no, department, course, semester, section, subject_code, subject_name, class_name, status, teacher_username)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                            ON DUPLICATE KEY UPDATE
                                department=VALUES(department),
                                course=VALUES(course),
                                semester=VALUES(semester),
                                section=VALUES(section),
                                subject_code=VALUES(subject_code),
                                subject_name=VALUES(subject_name),
                                class_name=VALUES(class_name),
                                status=VALUES(status),
                                teacher_username=VALUES(teacher_username)
                            """,
                            (
                                dt,
                                enroll,
                                department,
                                chosen_course,
                                chosen_semester,
                                chosen_section,
                                selected_subject_code,
                                selected_subject_name,
                                class_label,
                                status,
                                self.username,
                            ),
                            fetch=None,
                        )
                    messagebox.showinfo("Saved", "Data saved successfully.")
                    refresh_analytics()
                except Exception as err:
                    messagebox.showerror("Error", str(err))

            tk.Button(
                popup, text="  OK - Save Attendance  ",
                command=confirm_save,
                bg="#2563eb", fg="white",
                font=("Segoe UI", 11, "bold"), bd=0, padx=16, pady=8
            ).pack(pady=14)


        def refresh_analytics():
            month_rate = self.fetch_scalar(
                "SELECT ROUND((SUM(status='Present')/COUNT(*))*100,2) FROM attendance WHERE teacher_username=%s AND MONTH(attendance_date)=MONTH(CURDATE()) AND YEAR(attendance_date)=YEAR(CURDATE())",
                (self.username,),
                0,
            )
            year_rate = self.fetch_scalar(
                "SELECT ROUND((SUM(status='Present')/COUNT(*))*100,2) FROM attendance WHERE teacher_username=%s AND YEAR(attendance_date)=YEAR(CURDATE())",
                (self.username,),
                0,
            )
            analytics.config(text=f"Attendance Analytics  •  Monthly: {month_rate}%   •   Yearly: {year_rate}%")

        def export_csv_file():
            path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
            if not path:
                return
            rows = self.db_safe_all(
                "SELECT attendance_date, enrollment_no, department, course, semester, section, subject_code, subject_name, status FROM attendance WHERE teacher_username=%s ORDER BY attendance_date DESC",
                (self.username,),
            )
            with open(path, "w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(["Date", "Enrollment", "Department", "Course", "Semester", "Section", "Subject Code", "Subject Name", "Status"])
                writer.writerows(rows)
            messagebox.showinfo("Export", "Attendance CSV exported.")

        def export_excel_file():
            if openpyxl is None:
                messagebox.showwarning("Excel Export", "openpyxl not installed. Please install openpyxl for Excel export.")
                return
            path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
            if not path:
                return
            rows = self.db_safe_all(
                "SELECT attendance_date, enrollment_no, department, course, semester, section, subject_code, subject_name, status FROM attendance WHERE teacher_username=%s ORDER BY attendance_date DESC",
                (self.username,),
            )
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Attendance"
            ws.append(["Date", "Enrollment", "Department", "Course", "Semester", "Section", "Subject Code", "Subject Name", "Status"])
            for row in rows:
                ws.append(list(row))
            wb.save(path)
            messagebox.showinfo("Export", "Attendance Excel exported.")

        def export_pdf_file():
            if reportlab_canvas is None or A4 is None:
                messagebox.showwarning("PDF Export", "reportlab not installed. Please install reportlab for PDF export.")
                return
            path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
            if not path:
                return
            rows = self.db_safe_all(
                "SELECT attendance_date, enrollment_no, department, course, semester, section, subject_code, subject_name, status FROM attendance WHERE teacher_username=%s ORDER BY attendance_date DESC LIMIT 45",
                (self.username,),
            )
            pdf = reportlab_canvas.Canvas(path, pagesize=A4)
            y = 800
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(50, y, "Attendance Report")
            y -= 25
            pdf.setFont("Helvetica", 10)
            for row in rows:
                pdf.drawString(50, y, f"{row[0]}  {row[1]}  {row[3]}  {row[4]}  {row[5]}  {row[6]}  {row[8]}")
                y -= 16
                if y < 60:
                    pdf.showPage()
                    y = 800
            pdf.save()
            messagebox.showinfo("Export", "Attendance PDF exported.")

        course_box.bind("<<ComboboxSelected>>", refresh_semester_options)
        semester_box.bind("<<ComboboxSelected>>", refresh_section_options)
        section_box.bind("<<ComboboxSelected>>", refresh_subject_options)
        tree.bind("<ButtonRelease-1>", toggle_status)
        load_filter_options()
        tk.Label(frame, text="✓ Present / ○ Absent  •  Click Status to Toggle", bg=t["app_bg"], fg="#2563eb", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))

        tk.Button(control, text="Load Students", command=load_students_for_attendance, bg=t["accent"], fg="white", bd=0, padx=12).pack(side="left", padx=6)
        tk.Button(btn_row, text="Mark All ✓", command=lambda: set_all("Present"), bg="#2563eb", fg="white", bd=0, padx=10).pack(side="left", padx=4)
        tk.Button(btn_row, text="Mark All ○", command=lambda: set_all("Absent"), bg="#1d4ed8", fg="white", bd=0, padx=10).pack(side="left", padx=4)
        tk.Button(btn_row, text="Submit Attendance", command=submit_attendance, bg="#2563eb", fg="white", bd=0, padx=12, pady=4, font=("Segoe UI", 10, "bold")).pack(side="left", padx=8)
        tk.Button(btn_row, text="Export CSV", command=export_csv_file, bg="#2563eb", fg="white", bd=0, padx=10).pack(side="right", padx=3)
        tk.Button(btn_row, text="Export Excel", command=export_excel_file, bg="#0f766e", fg="white", bd=0, padx=10).pack(side="right", padx=3)
        tk.Button(btn_row, text="Export PDF", command=export_pdf_file, bg="#7c3aed", fg="white", bd=0, padx=10).pack(side="right", padx=3)

        refresh_analytics()

    def render_marks(self):
        create_result.load_module(self.content, teacher_username=self.username)

    def render_assignments(self):
        t = self.theme()
        outer = tk.Frame(self.content, bg=t["app_bg"])
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, bg=t["app_bg"], highlightthickness=0)
        v_scroll = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        frame = tk.Frame(canvas, bg=t["app_bg"])

        frame_window = canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=v_scroll.set)

        def _on_frame_configure(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event):
            canvas.itemconfigure(frame_window, width=event.width)

        def _on_mouse_wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        frame.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)
        canvas.bind("<MouseWheel>", _on_mouse_wheel)
        frame.bind("<MouseWheel>", _on_mouse_wheel)

        canvas.pack(side="left", fill="both", expand=True)
        v_scroll.pack(side="right", fill="y")

        tk.Label(frame, text="Assignments & Exams", bg=t["app_bg"], fg=t["text"], font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(0, 10))

        assignment_rows = self.get_teacher_assignments()
        if not assignment_rows:
            tk.Label(
                frame,
                text="No assigned classes found. Please contact admin to assign course/semester/section/subject first.",
                bg=t["app_bg"],
                fg=t["muted"],
                font=("Segoe UI", 10, "bold"),
            ).pack(anchor="w", padx=4, pady=8)
            return

        class_map = {}
        for row in assignment_rows:
            course_name = str(row[0] or "").strip()
            semester = normalize_semester(str(row[1] or "").strip())
            section = str(row[2] or "").strip().upper()
            subject_name = str(row[3] or "").strip()
            if not course_name or not semester or not section:
                continue
            key = (course_name, semester, section)
            if key not in class_map:
                class_map[key] = set()
            if subject_name:
                class_map[key].add(subject_name)

        classes = sorted(
            class_map.keys(),
            key=lambda item: (item[0].upper(), int(self.to_semester_number(item[1]) or 99), item[2].upper()),
        )
        courses = sorted({cls[0] for cls in classes})

        top = tk.Frame(frame, bg=t["app_bg"])
        top.pack(fill="x")

        assign_panel = tk.Frame(top, bg=t["panel"])
        exam_panel = tk.Frame(top, bg=t["panel"])
        assign_panel.pack(side="left", fill="both", expand=True, padx=(0, 5))
        exam_panel.pack(side="left", fill="both", expand=True, padx=(5, 0))

        tk.Label(assign_panel, text="Create Assignment", bg=t["panel"], fg=t["text"], font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=8)
        assign_filter_row = tk.Frame(assign_panel, bg=t["panel"])
        assign_filter_row.pack(fill="x", padx=10, pady=(0, 8))
        tk.Label(assign_filter_row, text="Course", bg=t["panel"], fg=t["text"]).grid(row=0, column=0, sticky="w")
        tk.Label(assign_filter_row, text="Sem", bg=t["panel"], fg=t["text"]).grid(row=0, column=1, sticky="w", padx=(8, 0))
        tk.Label(assign_filter_row, text="Sec", bg=t["panel"], fg=t["text"]).grid(row=0, column=2, sticky="w", padx=(8, 0))
        tk.Label(assign_filter_row, text="Subject", bg=t["panel"], fg=t["text"]).grid(row=0, column=3, sticky="w", padx=(8, 0))

        a_course_var = tk.StringVar(value=courses[0] if courses else "")
        a_sem_var = tk.StringVar(value="")
        a_sec_var = tk.StringVar(value="")
        a_subject_var = tk.StringVar(value="")

        a_course_box = ttk.Combobox(assign_filter_row, textvariable=a_course_var, state="readonly", width=14, values=courses)
        a_sem_box = ttk.Combobox(assign_filter_row, textvariable=a_sem_var, state="readonly", width=8)
        a_sec_box = ttk.Combobox(assign_filter_row, textvariable=a_sec_var, state="readonly", width=8)
        a_subject_box = ttk.Combobox(assign_filter_row, textvariable=a_subject_var, state="readonly", width=16)
        a_course_box.grid(row=1, column=0, sticky="ew", pady=(2, 0))
        a_sem_box.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(2, 0))
        a_sec_box.grid(row=1, column=2, sticky="ew", padx=(8, 0), pady=(2, 0))
        a_subject_box.grid(row=1, column=3, sticky="ew", padx=(8, 0), pady=(2, 0))
        for col in range(4):
            assign_filter_row.grid_columnconfigure(col, weight=1)

        a_title = tk.Entry(assign_panel)
        a_deadline = tk.Entry(assign_panel)
        a_material = tk.Entry(assign_panel)

        for lbl, widget in [
            ("Title", a_title),
            ("Deadline (YYYY-MM-DD)", a_deadline),
            ("Material Path (.pdf/.doc/.docx/.xls/.xlsx)", a_material),
        ]:
            tk.Label(assign_panel, text=lbl, bg=t["panel"], fg=t["text"]).pack(anchor="w", padx=10)
            widget.pack(fill="x", padx=10, pady=(0, 6))

        def update_assignment_semesters(_event=None):
            selected_course = a_course_var.get().strip()
            sem_values = sorted(
                {cls[1] for cls in classes if course_matches(cls[0], selected_course)},
                key=lambda value: int(self.to_semester_number(value) or 99),
            )
            a_sem_box["values"] = sem_values
            a_sem_var.set(sem_values[0] if sem_values else "")
            update_assignment_sections()

        def update_assignment_sections(_event=None):
            selected_course = a_course_var.get().strip()
            selected_sem = normalize_semester(a_sem_var.get().strip())
            sec_values = sorted(
                {
                    cls[2]
                    for cls in classes
                    if course_matches(cls[0], selected_course) and normalize_semester(cls[1]) == selected_sem
                }
            )
            a_sec_box["values"] = sec_values
            a_sec_var.set(sec_values[0] if sec_values else "")
            update_assignment_subjects()

        def update_assignment_subjects(_event=None):
            selected_course = a_course_var.get().strip()
            selected_sem = normalize_semester(a_sem_var.get().strip())
            selected_sec = a_sec_var.get().strip().upper()
            subject_values = sorted(
                class_map.get((selected_course, selected_sem, selected_sec), set())
            )
            a_subject_box["values"] = subject_values
            a_subject_var.set(subject_values[0] if subject_values else "")

        def browse_material():
            path = filedialog.askopenfilename(
                filetypes=[
                    ("Supported Files", "*.pdf *.doc *.docx *.xls *.xlsx"),
                    ("PDF Files", "*.pdf"),
                    ("Word Files", "*.doc *.docx"),
                    ("Excel Files", "*.xls *.xlsx"),
                    ("All Files", "*.*"),
                ]
            )
            if path:
                a_material.delete(0, tk.END)
                a_material.insert(0, path)

        def save_assignment():
            title = a_title.get().strip()
            deadline = a_deadline.get().strip()
            material = a_material.get().strip()

            course_name = a_course_var.get().strip()
            semester = normalize_semester(a_sem_var.get().strip())
            section = a_sec_var.get().strip().upper()
            subject_name = a_subject_var.get().strip()
            semester_no = self.to_semester_number(semester) or semester
            class_name = f"{course_name}-S{semester_no}-{section}"

            if not all([title, deadline, course_name, semester, section, subject_name]):
                messagebox.showwarning("Input", "Course, semester, section, subject, title and deadline are required.")
                return

            valid_material_extensions = (".pdf", ".doc", ".docx", ".xls", ".xlsx")
            if material and not material.lower().endswith(valid_material_extensions):
                messagebox.showwarning("Material", "Allowed formats: PDF, DOC, DOCX, XLS, XLSX.")
                return

            try:
                datetime.strptime(deadline, "%Y-%m-%d")
                self.db_execute(
                    """
                    INSERT INTO assignments
                    (teacher_username, course_name, semester, section, subject, class_name, title, material_path, deadline, status)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'Open')
                    """,
                    (self.username, course_name, semester, section, subject_name, class_name, title, material, deadline),
                    fetch=None,
                )

                refresh_assignment_tree()
                refresh_submission_tree()
                a_title.delete(0, tk.END)
                a_deadline.delete(0, tk.END)
                a_material.delete(0, tk.END)
                messagebox.showinfo("Created", "Assignment created successfully.")
            except Exception as err:
                messagebox.showerror("Error", str(err))

        tk.Button(assign_panel, text="Browse", command=browse_material, bg="#0f766e", fg="white", bd=0, padx=10).pack(anchor="w", padx=10, pady=4)
        tk.Button(assign_panel, text="Create Assignment", command=save_assignment, bg=t["accent"], fg="white", bd=0, padx=12, pady=6).pack(anchor="w", padx=10, pady=8)

        tk.Label(exam_panel, text="Exam Scheduling", bg=t["panel"], fg=t["text"], font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=8)
        exam_filter_row = tk.Frame(exam_panel, bg=t["panel"])
        exam_filter_row.pack(fill="x", padx=10, pady=(0, 8))
        tk.Label(exam_filter_row, text="Course", bg=t["panel"], fg=t["text"]).grid(row=0, column=0, sticky="w")
        tk.Label(exam_filter_row, text="Sem", bg=t["panel"], fg=t["text"]).grid(row=0, column=1, sticky="w", padx=(8, 0))
        tk.Label(exam_filter_row, text="Sec", bg=t["panel"], fg=t["text"]).grid(row=0, column=2, sticky="w", padx=(8, 0))
        tk.Label(exam_filter_row, text="Subject", bg=t["panel"], fg=t["text"]).grid(row=0, column=3, sticky="w", padx=(8, 0))

        e_course_var = tk.StringVar(value=courses[0] if courses else "")
        e_sem_var = tk.StringVar(value="")
        e_sec_var = tk.StringVar(value="")
        e_subject_var = tk.StringVar(value="")

        e_course_box = ttk.Combobox(exam_filter_row, textvariable=e_course_var, state="readonly", width=14, values=courses)
        e_sem_box = ttk.Combobox(exam_filter_row, textvariable=e_sem_var, state="readonly", width=8)
        e_sec_box = ttk.Combobox(exam_filter_row, textvariable=e_sec_var, state="readonly", width=8)
        e_subject_box = ttk.Combobox(exam_filter_row, textvariable=e_subject_var, state="readonly", width=16)
        e_course_box.grid(row=1, column=0, sticky="ew", pady=(2, 0))
        e_sem_box.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(2, 0))
        e_sec_box.grid(row=1, column=2, sticky="ew", padx=(8, 0), pady=(2, 0))
        e_subject_box.grid(row=1, column=3, sticky="ew", padx=(8, 0), pady=(2, 0))
        for col in range(4):
            exam_filter_row.grid_columnconfigure(col, weight=1)

        e_date = tk.Entry(exam_panel)
        e_time = tk.Entry(exam_panel)

        for lbl, widget in [
            ("Exam Date (YYYY-MM-DD)", e_date),
            ("Exam Time", e_time),
        ]:
            tk.Label(exam_panel, text=lbl, bg=t["panel"], fg=t["text"]).pack(anchor="w", padx=10)
            widget.pack(fill="x", padx=10, pady=(0, 6))

        def update_exam_semesters(_event=None):
            selected_course = e_course_var.get().strip()
            sem_values = sorted(
                {cls[1] for cls in classes if course_matches(cls[0], selected_course)},
                key=lambda value: int(self.to_semester_number(value) or 99),
            )
            e_sem_box["values"] = sem_values
            e_sem_var.set(sem_values[0] if sem_values else "")
            update_exam_sections()

        def update_exam_sections(_event=None):
            selected_course = e_course_var.get().strip()
            selected_sem = normalize_semester(e_sem_var.get().strip())
            sec_values = sorted(
                {
                    cls[2]
                    for cls in classes
                    if course_matches(cls[0], selected_course) and normalize_semester(cls[1]) == selected_sem
                }
            )
            e_sec_box["values"] = sec_values
            e_sec_var.set(sec_values[0] if sec_values else "")
            update_exam_subjects()

        def update_exam_subjects(_event=None):
            selected_course = e_course_var.get().strip()
            selected_sem = normalize_semester(e_sem_var.get().strip())
            selected_sec = e_sec_var.get().strip().upper()
            subject_values = sorted(class_map.get((selected_course, selected_sem, selected_sec), set()))
            e_subject_box["values"] = subject_values
            e_subject_var.set(subject_values[0] if subject_values else "")

        def save_exam():
            course_name = e_course_var.get().strip()
            semester = normalize_semester(e_sem_var.get().strip())
            section = e_sec_var.get().strip().upper()
            subject = e_subject_var.get().strip()
            exam_date = e_date.get().strip()
            exam_time = e_time.get().strip()
            semester_no = self.to_semester_number(semester) or semester
            class_name = f"{course_name}-S{semester_no}-{section}"
            if not all([course_name, semester, section, subject, exam_date, exam_time]):
                messagebox.showwarning("Input", "All exam fields are required.")
                return
            try:
                datetime.strptime(exam_date, "%Y-%m-%d")
                self.db_execute(
                    """
                    INSERT INTO exam_schedule
                    (teacher_username, course_name, semester, section, class_name, subject, exam_date, exam_time)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (self.username, course_name, semester, section, class_name, subject, exam_date, exam_time),
                    fetch=None,
                )
                refresh_exam_tree()
                messagebox.showinfo("Scheduled", "Exam scheduled successfully.")
            except Exception as err:
                messagebox.showerror("Error", str(err))

        tk.Button(exam_panel, text="Schedule Exam", command=save_exam, bg=t["accent2"], fg="white", bd=0, padx=12, pady=6).pack(anchor="w", padx=10, pady=8)

        bottom = tk.Frame(frame, bg=t["app_bg"])
        bottom.pack(fill="both", expand=True, pady=10)

        left = tk.Frame(bottom, bg=t["panel"])
        left.pack(fill="both", expand=True)

        tk.Label(left, text="Assignments", bg=t["panel"], fg=t["text"], font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=8)
        assignment_tree_wrap = tk.Frame(left, bg=t["panel"])
        assignment_tree_wrap.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        assignment_tree_body = tk.Frame(assignment_tree_wrap, bg=t["panel"])
        assignment_tree_body.pack(fill="both", expand=True)
        assignment_tree = ttk.Treeview(
            assignment_tree_body,
            columns=("id", "course", "sem", "sec", "subject", "title", "deadline", "status", "material"),
            show="headings",
            height=10,
        )
        for c, w in [
            ("id", 50), ("course", 90), ("sem", 50), ("sec", 50), ("subject", 120),
            ("title", 130), ("deadline", 95), ("status", 90), ("material", 120),
        ]:
            assignment_tree.heading(c, text=c.title())
            assignment_tree.column(c, width=w, anchor="center")
        assignment_tree_vscroll = ttk.Scrollbar(assignment_tree_body, orient="vertical", command=assignment_tree.yview)
        assignment_tree_hscroll = ttk.Scrollbar(assignment_tree_wrap, orient="horizontal", command=assignment_tree.xview)
        assignment_tree.configure(yscrollcommand=assignment_tree_vscroll.set, xscrollcommand=assignment_tree_hscroll.set)
        assignment_tree.pack(fill="both", expand=True, side="left")
        assignment_tree_vscroll.pack(fill="y", side="right")
        assignment_tree_hscroll.pack(fill="x", side="bottom")

        tk.Label(left, text="Assignment Submissions (Course/Sem/Sec Wise)", bg=t["panel"], fg=t["text"], font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(0, 8))
        submission_filter = tk.Frame(left, bg=t["panel"])
        submission_filter.pack(fill="x", padx=10, pady=(0, 8))
        tk.Label(submission_filter, text="Course", bg=t["panel"], fg=t["text"]).pack(side="left")
        s_course_var = tk.StringVar(value="All")
        s_course_box = ttk.Combobox(submission_filter, textvariable=s_course_var, state="readonly", width=12)
        s_course_box.pack(side="left", padx=(6, 8))
        tk.Label(submission_filter, text="Sem", bg=t["panel"], fg=t["text"]).pack(side="left")
        s_sem_var = tk.StringVar(value="All")
        s_sem_box = ttk.Combobox(submission_filter, textvariable=s_sem_var, state="readonly", width=7)
        s_sem_box.pack(side="left", padx=(6, 8))
        tk.Label(submission_filter, text="Sec", bg=t["panel"], fg=t["text"]).pack(side="left")
        s_sec_var = tk.StringVar(value="All")
        s_sec_box = ttk.Combobox(submission_filter, textvariable=s_sec_var, state="readonly", width=7)
        s_sec_box.pack(side="left", padx=(6, 8))

        submission_tree_wrap = tk.Frame(left, bg=t["panel"])
        submission_tree_wrap.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        submission_tree_body = tk.Frame(submission_tree_wrap, bg=t["panel"])
        submission_tree_body.pack(fill="both", expand=True)
        submission_tree = ttk.Treeview(
            submission_tree_body,
            columns=("sub_id", "assignment_id", "enrollment", "student", "course", "sem", "sec", "title", "submitted_at", "status", "marks", "path"),
            show="headings",
            height=8,
        )
        for c, w in [
            ("sub_id", 55), ("assignment_id", 75), ("enrollment", 100), ("student", 120),
            ("course", 85), ("sem", 50), ("sec", 45), ("title", 120), ("submitted_at", 125),
            ("status", 85), ("marks", 60), ("path", 120),
        ]:
            submission_tree.heading(c, text=c.title())
            submission_tree.column(c, width=w, anchor="center")
        submission_tree_vscroll = ttk.Scrollbar(submission_tree_body, orient="vertical", command=submission_tree.yview)
        submission_tree_hscroll = ttk.Scrollbar(submission_tree_wrap, orient="horizontal", command=submission_tree.xview)
        submission_tree.configure(yscrollcommand=submission_tree_vscroll.set, xscrollcommand=submission_tree_hscroll.set)
        submission_tree.pack(fill="both", expand=True, side="left")
        submission_tree_vscroll.pack(fill="y", side="right")
        submission_tree_hscroll.pack(fill="x", side="bottom")

        eval_box = tk.Frame(left, bg=t["panel"])
        eval_box.pack(fill="x", padx=10, pady=(0, 8))
        tk.Label(eval_box, text="Marks", bg=t["panel"], fg=t["text"]).pack(side="left", padx=(0, 6))
        eval_marks = tk.Entry(eval_box, width=8)
        eval_marks.pack(side="left", padx=(0, 10))
        tk.Label(eval_box, text="Evaluation / Improvement", bg=t["panel"], fg=t["text"]).pack(side="left", padx=(0, 6))
        eval_text = tk.Entry(eval_box)
        eval_text.pack(side="left", fill="x", expand=True, padx=(0, 10))

        exam_label = tk.Label(left, text="Exam Schedule", bg=t["panel"], fg=t["text"], font=("Segoe UI", 11, "bold"))
        exam_label.pack(anchor="w", padx=10, pady=(6, 8))
        exam_tree_wrap = tk.Frame(left, bg=t["panel"])
        exam_tree_wrap.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        exam_tree_body = tk.Frame(exam_tree_wrap, bg=t["panel"])
        exam_tree_body.pack(fill="both", expand=True)
        exam_tree = ttk.Treeview(exam_tree_body, columns=("id", "course", "sem", "sec", "subject", "date", "time"), show="headings", height=10)
        for c, w in [("id", 50), ("course", 90), ("sem", 50), ("sec", 50), ("subject", 140), ("date", 110), ("time", 90)]:
            exam_tree.heading(c, text=c.title())
            exam_tree.column(c, width=w, anchor="center")
        exam_tree_vscroll = ttk.Scrollbar(exam_tree_body, orient="vertical", command=exam_tree.yview)
        exam_tree_hscroll = ttk.Scrollbar(exam_tree_wrap, orient="horizontal", command=exam_tree.xview)
        exam_tree.configure(yscrollcommand=exam_tree_vscroll.set, xscrollcommand=exam_tree_hscroll.set)
        exam_tree.pack(fill="both", expand=True, side="left")
        exam_tree_vscroll.pack(fill="y", side="right")
        exam_tree_hscroll.pack(fill="x", side="bottom")

        selected_assignment_id = {"value": None}

        def refresh_assignment_tree():
            for row in assignment_tree.get_children():
                assignment_tree.delete(row)
            rows = self.db_safe_all(
                """
                SELECT id,
                       COALESCE(course_name, ''),
                       COALESCE(semester, ''),
                       COALESCE(section, ''),
                       COALESCE(subject, ''),
                       title,
                       deadline,
                       CASE WHEN deadline < CURDATE() THEN 'Closed' ELSE status END,
                       COALESCE(material_path, '')
                FROM assignments
                WHERE teacher_username=%s
                ORDER BY id DESC
                """,
                (self.username,),
            )
            for row in rows:
                assignment_tree.insert("", "end", values=row)

        def refresh_submission_tree(assignment_id=None):
            for row in submission_tree.get_children():
                submission_tree.delete(row)

            selected_course = s_course_var.get().strip()
            selected_sem = normalize_semester(s_sem_var.get().strip()) if s_sem_var.get().strip() != "All" else "All"
            selected_sec = s_sec_var.get().strip().upper()

            if assignment_id:
                rows = self.db_safe_all(
                    """
                    SELECT s.id, s.assignment_id, s.enrollment_no,
                           COALESCE(st.name, ''),
                           COALESCE(a.course_name, ''),
                           COALESCE(a.semester, ''),
                           COALESCE(a.section, ''),
                           COALESCE(a.title, ''),
                           DATE_FORMAT(submitted_at, '%Y-%m-%d %H:%i'),
                           s.status, COALESCE(s.marks, ''), s.submission_path
                    FROM assignment_submissions s
                    JOIN assignments a ON a.id=s.assignment_id
                    LEFT JOIN students st ON st.enrollment_no=s.enrollment_no
                    WHERE s.assignment_id=%s
                    ORDER BY s.id DESC
                    """,
                    (assignment_id,),
                )
            else:
                where_sql = ["a.teacher_username=%s"]
                params = [self.username]
                if selected_course != "All":
                    where_sql.append("UPPER(TRIM(COALESCE(a.course_name, ''))) = UPPER(TRIM(%s))")
                    params.append(selected_course)
                if selected_sem != "All":
                    where_sql.append("TRIM(COALESCE(a.semester, '')) = TRIM(%s)")
                    params.append(selected_sem)
                if selected_sec != "All":
                    where_sql.append("UPPER(TRIM(COALESCE(a.section, ''))) = UPPER(TRIM(%s))")
                    params.append(selected_sec)

                rows = self.db_safe_all(
                    f"""
                    SELECT s.id, s.assignment_id, s.enrollment_no,
                           COALESCE(st.name, ''),
                           COALESCE(a.course_name, ''),
                           COALESCE(a.semester, ''),
                           COALESCE(a.section, ''),
                           COALESCE(a.title, ''),
                           DATE_FORMAT(s.submitted_at, '%Y-%m-%d %H:%i'),
                           s.status, COALESCE(s.marks, ''), s.submission_path
                    FROM assignment_submissions s
                    JOIN assignments a ON a.id=s.assignment_id
                    LEFT JOIN students st ON st.enrollment_no=s.enrollment_no
                    WHERE {' AND '.join(where_sql)}
                    ORDER BY s.id DESC
                    LIMIT 300
                    """,
                    tuple(params),
                )
            for row in rows:
                submission_tree.insert("", "end", values=row)

        def evaluate_submission():
            selected = submission_tree.focus()
            if not selected:
                messagebox.showwarning("Submission", "Select a submission first.")
                return
            row = submission_tree.item(selected, "values")
            submission_id = row[0]
            marks_text = eval_marks.get().strip()
            evaluation = eval_text.get().strip()
            if not marks_text:
                messagebox.showwarning("Marks", "Enter marks.")
                return
            try:
                marks = float(marks_text)
            except Exception:
                messagebox.showwarning("Marks", "Marks must be numeric.")
                return
            if marks < 0 or marks > 100:
                messagebox.showwarning("Marks", "Marks should be between 0 and 100.")
                return
            self.db_execute(
                """
                UPDATE assignment_submissions
                SET marks=%s, evaluation=%s, status='Evaluated', evaluated_by=%s, evaluated_at=NOW()
                WHERE id=%s
                """,
                (marks, evaluation, self.username, submission_id),
                fetch=None,
            )
            refresh_submission_tree(selected_assignment_id["value"])
            eval_marks.delete(0, tk.END)
            eval_text.delete(0, tk.END)
            messagebox.showinfo("Saved", "Evaluation updated.")

        def open_submission_file():
            selected = submission_tree.focus()
            if not selected:
                messagebox.showwarning("Submission", "Select a submission first.")
                return
            row = submission_tree.item(selected, "values")
            file_path = str(row[11]).strip()
            if not file_path:
                messagebox.showwarning("File", "No submission file path available.")
                return
            if not os.path.exists(file_path):
                messagebox.showerror("File", "Submitted file not found on this system.")
                return
            try:
                os.startfile(file_path)
            except Exception as err:
                messagebox.showerror("Open File", str(err))

        def on_assignment_select(_event=None):
            selected = assignment_tree.focus()
            if not selected:
                selected_assignment_id["value"] = None
                refresh_submission_tree()
                return
            values = assignment_tree.item(selected, "values")
            selected_assignment_id["value"] = values[0]
            refresh_submission_tree(values[0])

        def on_submission_select(_event=None):
            selected = submission_tree.focus()
            if not selected:
                return
            row = submission_tree.item(selected, "values")
            eval_marks.delete(0, tk.END)
            if str(row[10]).strip():
                eval_marks.insert(0, row[10])

        def refresh_exam_tree():
            for row in exam_tree.get_children():
                exam_tree.delete(row)
            rows = self.db_safe_all(
                """
                SELECT id, COALESCE(course_name, ''), COALESCE(semester, ''), COALESCE(section, ''),
                       subject, exam_date, exam_time
                FROM exam_schedule
                WHERE teacher_username=%s
                ORDER BY id DESC
                """,
                (self.username,),
            )
            for row in rows:
                exam_tree.insert("", "end", values=row)

        def refresh_submission_filter_values():
            course_values = sorted({cls[0] for cls in classes})
            sem_values = sorted({cls[1] for cls in classes}, key=lambda value: int(self.to_semester_number(value) or 99))
            sec_values = sorted({cls[2] for cls in classes})
            s_course_box["values"] = ["All"] + course_values
            s_sem_box["values"] = ["All"] + sem_values
            s_sec_box["values"] = ["All"] + sec_values
            if s_course_var.get() not in s_course_box["values"]:
                s_course_var.set("All")
            if s_sem_var.get() not in s_sem_box["values"]:
                s_sem_var.set("All")
            if s_sec_var.get() not in s_sec_box["values"]:
                s_sec_var.set("All")

        refresh_assignment_tree()
        refresh_exam_tree()
        refresh_submission_filter_values()
        refresh_submission_tree()
        self.window.after(1000, lambda: refresh_submission_tree())

        update_assignment_semesters()
        update_exam_semesters()

        a_course_box.bind("<<ComboboxSelected>>", update_assignment_semesters)
        a_sem_box.bind("<<ComboboxSelected>>", update_assignment_sections)
        a_sec_box.bind("<<ComboboxSelected>>", update_assignment_subjects)

        e_course_box.bind("<<ComboboxSelected>>", update_exam_semesters)
        e_sem_box.bind("<<ComboboxSelected>>", update_exam_sections)
        e_sec_box.bind("<<ComboboxSelected>>", update_exam_subjects)

        s_course_box.bind("<<ComboboxSelected>>", lambda _e: refresh_submission_tree(selected_assignment_id["value"]))
        s_sem_box.bind("<<ComboboxSelected>>", lambda _e: refresh_submission_tree(selected_assignment_id["value"]))
        s_sec_box.bind("<<ComboboxSelected>>", lambda _e: refresh_submission_tree(selected_assignment_id["value"]))

        def bind_table_wheel(tree_widget, container_widget=None):
            def on_mousewheel(event):
                delta = int(-1 * (event.delta / 120)) if event.delta else 0
                if delta:
                    tree_widget.yview_scroll(delta, "units")
                return "break"

            def on_linux_up(_event):
                tree_widget.yview_scroll(-1, "units")
                return "break"

            def on_linux_down(_event):
                tree_widget.yview_scroll(1, "units")
                return "break"

            targets = [tree_widget]
            if container_widget is not None:
                targets.append(container_widget)
            for target in targets:
                target.bind("<MouseWheel>", on_mousewheel)
                target.bind("<Button-4>", on_linux_up)
                target.bind("<Button-5>", on_linux_down)

        bind_table_wheel(assignment_tree, assignment_tree_body)
        bind_table_wheel(submission_tree, submission_tree_body)
        bind_table_wheel(exam_tree, exam_tree_body)

        action_row = tk.Frame(left, bg=t["panel"])
        action_row.pack(fill="x", padx=10, pady=(0, 10), before=exam_label)
        tk.Button(action_row, text="Open Submitted File", command=open_submission_file, bg="#2563eb", fg="white", bd=0, padx=12, pady=6).pack(side="left")
        tk.Button(action_row, text="All Submissions", command=lambda: [selected_assignment_id.update(value=None), refresh_submission_tree()], bg="#475569", fg="white", bd=0, padx=12, pady=6).pack(side="left", padx=6)
        tk.Button(action_row, text="Save Evaluation", command=evaluate_submission, bg=t["accent2"], fg="white", bd=0, padx=12, pady=6).pack(side="right")

        assignment_tree.bind("<<TreeviewSelect>>", on_assignment_select)
        submission_tree.bind("<<TreeviewSelect>>", on_submission_select)

    def render_reports(self):
        t = self.theme()
        frame = tk.Frame(self.content, bg=t["app_bg"])
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="Reports & Analytics", bg=t["app_bg"], fg=t["text"], font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(0, 10))

        control = tk.Frame(frame, bg=t["panel"])
        control.pack(fill="x", pady=(0, 8))

        tk.Label(control, text="Course", bg=t["panel"], fg=t["text"]).pack(side="left", padx=(10, 4), pady=8)
        course_var = tk.StringVar(value="All")
        course_combo = ttk.Combobox(control, textvariable=course_var, state="readonly", width=16)
        course_combo.pack(side="left", padx=4)

        tk.Label(control, text="Semester", bg=t["panel"], fg=t["text"]).pack(side="left", padx=(10, 4))
        semester_var = tk.StringVar(value="All")
        semester_combo = ttk.Combobox(control, textvariable=semester_var, state="readonly", width=10)
        semester_combo.pack(side="left", padx=4)

        tk.Label(control, text="Section", bg=t["panel"], fg=t["text"]).pack(side="left", padx=(10, 4))
        section_var = tk.StringVar(value="All")
        section_combo = ttk.Combobox(control, textvariable=section_var, state="readonly", width=10)
        section_combo.pack(side="left", padx=4)

        tk.Label(control, text="Enrollment", bg=t["panel"], fg=t["text"]).pack(side="left", padx=(10, 4))
        enroll_var = tk.StringVar(value="All")
        enroll_combo = ttk.Combobox(control, textvariable=enroll_var, state="readonly", width=14)
        enroll_combo.pack(side="left", padx=4)

        summary_row = tk.Frame(frame, bg=t["app_bg"])
        summary_row.pack(fill="x", pady=(0, 8))
        summary_students_var = tk.StringVar(value="0")
        summary_avg_var = tk.StringVar(value="0.00")
        summary_top_var = tk.StringVar(value="0")
        summary_need_support_var = tk.StringVar(value="0")

        def build_summary(parent, title, value_var, color):
            card = tk.Frame(parent, bg=t["panel"], bd=1, relief="solid")
            tk.Label(card, text=title, bg=t["panel"], fg=t["muted"], font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=10, pady=(8, 2))
            tk.Label(card, textvariable=value_var, bg=t["panel"], fg=color, font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=10, pady=(0, 8))
            return card

        for idx, card in enumerate(
            [
                build_summary(summary_row, "Students in Report", summary_students_var, t["accent"]),
                build_summary(summary_row, "Class Average", summary_avg_var, t["accent2"]),
                build_summary(summary_row, "Top Performers (>=85)", summary_top_var, "#2563eb"),
                build_summary(summary_row, "Need Support (<60)", summary_need_support_var, "#ef4444"),
            ]
        ):
            card.grid(row=0, column=idx, sticky="nsew", padx=4)
            summary_row.grid_columnconfigure(idx, weight=1)

        report_tree = ttk.Treeview(frame, columns=("enrollment", "name", "course", "sem", "sec", "avg", "grade"), show="headings", height=10)
        for c, w in [("enrollment", 120), ("name", 160), ("course", 110), ("sem", 70), ("sec", 70), ("avg", 90), ("grade", 90)]:
            report_tree.heading(c, text=c.title())
            report_tree.column(c, width=w, anchor="center")
        report_tree.pack(fill="both", expand=True, pady=(0, 8))

        student_report = tk.Text(frame, height=10, font=("Segoe UI", 10), bg=t["panel"], fg=t["text"], bd=0)
        student_report.pack(fill="x")

        action = tk.Frame(frame, bg=t["app_bg"])
        action.pack(fill="x", pady=8)

        def grade_for(m):
            if m >= 90:
                return "A+"
            if m >= 80:
                return "A"
            if m >= 70:
                return "B"
            if m >= 60:
                return "C"
            return "D"

        def load_filter_values():
            rows = [(s[2], s[3], s[4], s[0]) for s in self.get_students_for_teacher()]
            course_values = ["All"]
            semester_values = ["All"]
            section_values = ["All"]
            enroll_values = ["All"]
            for row in rows:
                course = str(row[0] or "").strip()
                semester = str(row[1] or "").strip()
                section = str(row[2] or "").strip()
                enrollment = str(row[3] or "").strip()
                if course and course not in course_values:
                    course_values.append(course)
                if semester and semester not in semester_values:
                    semester_values.append(semester)
                if section and section not in section_values:
                    section_values.append(section)
                if enrollment and enrollment not in enroll_values:
                    enroll_values.append(enrollment)
            course_combo["values"] = course_values
            semester_combo["values"] = semester_values
            section_combo["values"] = section_values
            enroll_combo["values"] = enroll_values
            if course_var.get() not in course_values:
                course_var.set("All")
            if semester_var.get() not in semester_values:
                semester_var.set("All")
            if section_var.get() not in section_values:
                section_var.set("All")
            if enroll_var.get() not in enroll_values:
                enroll_var.set("All")

        def refresh_enrollment_suggestions(_event=None):
            selected_course = course_var.get().strip()
            selected_sem = semester_var.get().strip()
            selected_sec = section_var.get().strip()

            enrollments = ["All"]
            for student in self.get_students_for_teacher():
                if selected_course and selected_course != "All" and not course_matches(student[2], selected_course):
                    continue
                if selected_sem and selected_sem != "All" and str(student[3]).strip() != selected_sem:
                    continue
                if selected_sec and selected_sec != "All" and str(student[4]).strip() != selected_sec:
                    continue
                enrollment = str(student[0]).strip()
                if enrollment and enrollment not in enrollments:
                    enrollments.append(enrollment)

            values = enrollments
            enroll_combo["values"] = values
            if enroll_var.get() not in values:
                enroll_var.set("All")

        def class_report():
            for row in report_tree.get_children():
                report_tree.delete(row)

            selected_course = course_var.get().strip()
            selected_sem = semester_var.get().strip()
            selected_sec = section_var.get().strip()
            selected_enrollment = enroll_var.get().strip()

            filtered_students = []
            for student in self.get_students_for_teacher():
                if selected_course and selected_course != "All" and not course_matches(student[2], selected_course):
                    continue
                if selected_sem and selected_sem != "All" and str(student[3]).strip() != selected_sem:
                    continue
                if selected_sec and selected_sec != "All" and str(student[4]).strip() != selected_sec:
                    continue
                if selected_enrollment and selected_enrollment != "All" and str(student[0]).strip() != selected_enrollment:
                    continue
                filtered_students.append(student)

            enrollments = [str(s[0]).strip() for s in filtered_students if str(s[0]).strip()]
            avg_map = {}
            if enrollments:
                placeholders = ",".join(["%s"] * len(enrollments))
                avg_rows = self.db_safe_all(
                    f"SELECT enrollment_no, ROUND(AVG(marks),2) FROM results WHERE enrollment_no IN ({placeholders}) GROUP BY enrollment_no",
                    tuple(enrollments),
                )
                avg_map = {str(row[0]).strip(): float(row[1]) for row in avg_rows if row and row[0]}

            rows = [
                (
                    str(student[0]).strip(),
                    student[1],
                    student[2],
                    student[3],
                    student[4],
                    avg_map.get(str(student[0]).strip(), 0.0),
                )
                for student in filtered_students
            ]

            if not rows:
                messagebox.showinfo("Report", "No records found for selected filters.")

            self.class_report_data = []
            overall_sum = 0.0
            top_count = 0
            support_count = 0
            for row in rows:
                avg = float(row[5]) if row[5] is not None else 0.0
                g = grade_for(avg)
                val = (row[0], row[1], row[2], row[3], row[4], avg, g)
                self.class_report_data.append(val)
                report_tree.insert("", "end", values=val)
                overall_sum += avg
                if avg >= 85:
                    top_count += 1
                if avg < 60:
                    support_count += 1

            student_count = len(self.class_report_data)
            class_avg = round(overall_sum / student_count, 2) if student_count else 0.0
            summary_students_var.set(str(student_count))
            summary_avg_var.set(f"{class_avg:.2f}")
            summary_top_var.set(str(top_count))
            summary_need_support_var.set(str(support_count))

        def on_report_select(_event=None):
            selected = report_tree.focus()
            if not selected:
                return
            row = report_tree.item(selected, "values")
            if row and len(row) >= 1:
                enroll_var.set(str(row[0]))

        def student_card():
            enrollment = enroll_var.get().strip()
            if not enrollment or enrollment == "All":
                messagebox.showwarning("Input", "Enter enrollment number.")
                return
            allowed_enrollments = {str(s[0]).strip() for s in self.get_students_for_teacher()}
            if enrollment not in allowed_enrollments:
                messagebox.showerror("Access Denied", "This student is not assigned to your classes.")
                return
            detail = self.db_safe_one(
                "SELECT name, course, semester, section, email FROM students WHERE enrollment_no=%s",
                (enrollment,),
            )
            rows = self.db_safe_all(
                "SELECT subject, exam, marks FROM results WHERE enrollment_no=%s ORDER BY id DESC",
                (enrollment,),
            )
            if not detail:
                messagebox.showerror("Not Found", "Student not found.")
                return
            avg = 0
            if rows:
                avg = round(sum(float(r[2]) for r in rows) / len(rows), 2)
            self.student_report_data = [(detail, rows, avg)]
            student_report.delete("1.0", tk.END)
            student_report.insert(tk.END, f"Report Card\n\nName: {detail[0]}\nEnrollment: {enrollment}\nCourse: {detail[1]}\n")
            student_report.insert(tk.END, f"Semester: {detail[2]}   Section: {detail[3]}\nEmail: {detail[4]}\n\n")
            student_report.insert(tk.END, "Marks History:\n")
            for r in rows:
                student_report.insert(tk.END, f"- {r[0]} | {r[1]} | {r[2]}\n")
            if rows:
                best = max(float(r[2] or 0) for r in rows)
                worst = min(float(r[2] or 0) for r in rows)
            else:
                best = 0.0
                worst = 0.0
            student_report.insert(
                tk.END,
                f"\nOverall Average: {avg}  Grade: {grade_for(avg)}\nBest Score: {best}  |  Lowest Score: {worst}",
            )

        def export_class_csv():
            if not self.class_report_data:
                messagebox.showwarning("Export", "Generate class report first.")
                return
            path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
            if not path:
                return
            with open(path, "w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(["Enrollment", "Name", "Course", "Semester", "Section", "Average", "Grade"])
                writer.writerows(self.class_report_data)
            messagebox.showinfo("Export", "Class report exported.")

        def export_student_pdf():
            if reportlab_canvas is None or A4 is None:
                messagebox.showwarning("PDF Export", "reportlab not installed. Please install reportlab for PDF export.")
                return
            if not self.student_report_data:
                messagebox.showwarning("Export", "Generate student report first.")
                return
            path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
            if not path:
                return
            detail, rows, avg = self.student_report_data[0]
            pdf = reportlab_canvas.Canvas(path, pagesize=A4)
            y = 800
            pdf.setFont("Helvetica-Bold", 13)
            pdf.drawString(50, y, "Student Report Card")
            y -= 25
            pdf.setFont("Helvetica", 10)
            pdf.drawString(50, y, f"Name: {detail[0]} | Course: {detail[1]} | Semester: {detail[2]} | Section: {detail[3]}")
            y -= 16
            pdf.drawString(50, y, f"Email: {detail[4]} | Overall Average: {avg}")
            y -= 24
            for r in rows:
                pdf.drawString(50, y, f"{r[0]}   {r[1]}   {r[2]}")
                y -= 16
                if y < 60:
                    pdf.showPage()
                    y = 800
            pdf.save()
            messagebox.showinfo("Export", "Student report PDF exported.")

        tk.Button(control, text="Generate Class Report", command=class_report, bg=t["accent"], fg="white", bd=0, padx=12).pack(side="left", padx=8)
        tk.Button(control, text="Generate Student Card", command=student_card, bg=t["accent2"], fg="white", bd=0, padx=12).pack(side="left", padx=6)

        tk.Button(action, text="Download Class CSV", command=export_class_csv, bg="#2563eb", fg="white", bd=0, padx=12).pack(side="right", padx=4)
        tk.Button(action, text="Download Student PDF", command=export_student_pdf, bg="#7c3aed", fg="white", bd=0, padx=12).pack(side="right", padx=4)

        course_combo.bind("<<ComboboxSelected>>", refresh_enrollment_suggestions)
        semester_combo.bind("<<ComboboxSelected>>", refresh_enrollment_suggestions)
        section_combo.bind("<<ComboboxSelected>>", refresh_enrollment_suggestions)
        report_tree.bind("<<TreeviewSelect>>", on_report_select)

        load_filter_values()
        refresh_enrollment_suggestions()

    def render_communication(self):
        t = self.theme()
        frame = tk.Frame(self.content, bg=t["app_bg"])
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="Communication Module", bg=t["app_bg"], fg=t["text"], font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(0, 10))

        top = tk.Frame(frame, bg=t["app_bg"])
        top.pack(fill="both", expand=True)

        left = tk.Frame(top, bg=t["panel"])
        right = tk.Frame(top, bg=t["panel"])
        left.pack(side="left", fill="both", expand=True, padx=(0, 5))
        right.pack(side="left", fill="both", expand=True, padx=(5, 0))

        tk.Label(left, text="Send Announcement", bg=t["panel"], fg=t["text"], font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=8)
        tk.Label(left, text="Title", bg=t["panel"], fg=t["text"]).pack(anchor="w", padx=10)
        ann_title = tk.Entry(left)
        ann_title.pack(fill="x", padx=10, pady=(0, 6))
        class_filter_row = tk.Frame(left, bg=t["panel"])
        class_filter_row.pack(fill="x", padx=10, pady=(0, 6))
        tk.Label(class_filter_row, text="Subject", bg=t["panel"], fg=t["text"]).pack(side="left")
        ann_subject = ttk.Combobox(class_filter_row, state="readonly", width=18)
        ann_subject.pack(side="left", padx=(6, 8))
        tk.Label(class_filter_row, text="Course", bg=t["panel"], fg=t["text"]).pack(side="left")
        ann_course = ttk.Combobox(class_filter_row, state="readonly", width=12)
        ann_course.pack(side="left", padx=(6, 8))
        tk.Label(class_filter_row, text="Sem", bg=t["panel"], fg=t["text"]).pack(side="left")
        ann_sem = ttk.Combobox(class_filter_row, state="readonly", width=6)
        ann_sem.pack(side="left", padx=(6, 8))
        tk.Label(class_filter_row, text="Sec", bg=t["panel"], fg=t["text"]).pack(side="left")
        ann_sec = ttk.Combobox(class_filter_row, state="readonly", width=6)
        ann_sec.pack(side="left", padx=(6, 0))
        tk.Label(left, text="Message", bg=t["panel"], fg=t["text"]).pack(anchor="w", padx=10)
        ann_msg = tk.Text(left, height=8)
        ann_msg.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        notif_tree = ttk.Treeview(left, columns=("date", "title", "scope"), show="headings", height=8)
        notif_tree.heading("date", text="Date")
        notif_tree.heading("title", text="Title")
        notif_tree.heading("scope", text="Audience")
        notif_tree.column("date", width=110, anchor="center")
        notif_tree.column("title", width=180, anchor="w")
        notif_tree.column("scope", width=160, anchor="w")
        notif_tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        tk.Label(right, text="Doubt / Query Management", bg=t["panel"], fg=t["text"], font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=8)
        stat_row = tk.Frame(right, bg=t["panel"])
        stat_row.pack(fill="x", padx=10, pady=(0, 6))
        solved_var = tk.StringVar(value="Solved: 0")
        unsolved_var = tk.StringVar(value="Not Solved: 0")
        within_var = tk.StringVar(value="Solved <=2 days: 0")
        overdue_var = tk.StringVar(value="Pending >2 days: 0")
        tk.Label(stat_row, textvariable=solved_var, bg=t["panel"], fg="#16a34a", font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 10))
        tk.Label(stat_row, textvariable=unsolved_var, bg=t["panel"], fg="#dc2626", font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 10))
        tk.Label(stat_row, textvariable=within_var, bg=t["panel"], fg="#2563eb", font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 10))
        tk.Label(stat_row, textvariable=overdue_var, bg=t["panel"], fg="#f59e0b", font=("Segoe UI", 10, "bold")).pack(side="left")

        search_row = tk.Frame(right, bg=t["panel"])
        search_row.pack(fill="x", padx=10, pady=(0, 6))
        tk.Label(search_row, text="Search", bg=t["panel"], fg=t["text"]).pack(side="left")
        search_var = tk.StringVar()
        search_entry = tk.Entry(search_row, textvariable=search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=6)

        columns = (
            "id", "enroll", "subject", "type", "status", "session", "asked", "received", "solved", "satisfied", "query", "solution"
        )
        query_tree = ttk.Treeview(right, columns=columns, show="headings", height=13, selectmode="extended")
        for c, title, w, anchor in [
            ("id", "ID", 55, "center"),
            ("enroll", "Enrollment", 110, "center"),
            ("subject", "Subject", 120, "center"),
            ("type", "Type", 120, "center"),
            ("status", "Status", 130, "center"),
            ("session", "Session", 250, "w"),
            ("asked", "Asked On", 115, "center"),
            ("received", "Received On", 115, "center"),
            ("solved", "Solved On", 115, "center"),
            ("satisfied", "Satisfied", 90, "center"),
            ("query", "Doubt", 220, "w"),
            ("solution", "Solution", 220, "w"),
        ]:
            query_tree.heading(c, text=title)
            query_tree.column(c, width=w, anchor=anchor)
        query_tree.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        response_box = tk.Text(right, height=4)
        response_box.pack(fill="x", padx=10, pady=(0, 8))

        session_form = tk.Frame(right, bg=t["panel"])
        session_form.pack(fill="x", padx=10, pady=(0, 8))
        session_title = tk.Entry(session_form)
        session_title.insert(0, "Short Doubt Resolution Session")
        session_date = tk.Entry(session_form, width=11)
        session_date.insert(0, date.today().strftime("%Y-%m-%d"))
        session_time = tk.Entry(session_form, width=8)
        session_time.insert(0, "16:00")
        session_duration = ttk.Combobox(session_form, state="readonly", values=["15", "20", "30", "45"], width=6)
        session_duration.set("20")
        session_mode = ttk.Combobox(session_form, state="readonly", values=["Offline", "Online", "Phone"], width=10)
        session_mode.set("Offline")

        tk.Label(session_form, text="Session", bg=t["panel"], fg=t["text"]).pack(side="left")
        session_title.pack(side="left", padx=(6, 8), fill="x", expand=True)
        tk.Label(session_form, text="Date", bg=t["panel"], fg=t["text"]).pack(side="left")
        session_date.pack(side="left", padx=(6, 8))
        tk.Label(session_form, text="Time", bg=t["panel"], fg=t["text"]).pack(side="left")
        session_time.pack(side="left", padx=(6, 8))
        tk.Label(session_form, text="Min", bg=t["panel"], fg=t["text"]).pack(side="left")
        session_duration.pack(side="left", padx=(6, 8))
        session_mode.pack(side="left")

        session_note_frame = tk.Frame(right, bg=t["panel"])
        session_note_frame.pack(fill="x", padx=10, pady=(0, 8))
        tk.Label(
            session_note_frame,
            text="Session Details",
            bg=t["panel"],
            fg=t["text"],
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w")
        tk.Label(
            session_note_frame,
            text="Add free slot, room/link, or any instruction for the selected student/query set.",
            bg=t["panel"],
            fg=t["muted"],
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(0, 4))
        session_note_box = tk.Text(session_note_frame, height=3)
        session_note_box.pack(fill="x")

        assignments = self.get_teacher_assignments()
        subject_values = sorted({str(a[3]).strip() for a in assignments if str(a[3]).strip()})
        course_values = sorted({str(a[0]).strip() for a in assignments if str(a[0]).strip()})
        sem_values = sorted({str(a[1]).strip() for a in assignments if str(a[1]).strip()})
        sec_values = sorted({str(a[2]).strip().upper() for a in assignments if str(a[2]).strip()})

        ann_subject["values"] = ["All"] + subject_values
        ann_subject.set("All")
        ann_course["values"] = ["All"] + course_values
        ann_course.set("All")
        ann_sem["values"] = ["All"] + sem_values
        ann_sem.set("All")
        ann_sec["values"] = ["All"] + sec_values
        ann_sec.set("All")

        def refresh_notifications():
            for row in notif_tree.get_children():
                notif_tree.delete(row)
            rows = self.db_safe_all(
                """
                SELECT DATE_FORMAT(created_at, '%Y-%m-%d'), title,
                       CONCAT_WS(' / ',
                                 COALESCE(NULLIF(subject, ''), 'All Subjects'),
                                 COALESCE(NULLIF(course_name, ''), 'All Courses'),
                                 COALESCE(NULLIF(semester, ''), 'All Semesters'),
                                 COALESCE(NULLIF(section, ''), 'All Sections'))
                FROM teacher_announcements
                WHERE teacher_username=%s
                ORDER BY id DESC LIMIT 30
                """,
                (self.username,),
            )
            for row in rows:
                notif_tree.insert("", "end", values=row)

        def get_assigned_query_rows():
            return self.db_safe_all(
                """
                SELECT sq.id,
                       sq.enrollment_no,
                       COALESCE(sq.doubt_subject, ''),
                       COALESCE(sq.query_type, ''),
                       COALESCE(sq.status, 'Submitted'),
                       CONCAT_WS(' | ',
                                 COALESCE(NULLIF(sq.session_status, ''), ''),
                                 COALESCE(NULLIF(sq.session_title, ''), ''),
                                 COALESCE(DATE_FORMAT(sq.session_datetime, '%Y-%m-%d %H:%i'), ''),
                                 CASE WHEN sq.session_duration_minutes IS NULL THEN '' ELSE CONCAT(sq.session_duration_minutes, ' mins') END,
                                 COALESCE(NULLIF(sq.session_note, ''), '')),
                       DATE_FORMAT(sq.created_at, '%Y-%m-%d'),
                       DATE_FORMAT(sq.teacher_received_at, '%Y-%m-%d'),
                       DATE_FORMAT(sq.solved_at, '%Y-%m-%d'),
                       CASE
                           WHEN COALESCE(sq.student_acknowledged, 0)=1 THEN 'Yes'
                           WHEN COALESCE(sq.student_feedback, '') <> '' THEN sq.student_feedback
                           ELSE 'Pending'
                       END AS satisfied,
                       sq.query_text,
                       COALESCE(NULLIF(sq.solution_text, ''), COALESCE(sq.response, '')) AS solution,
                       sq.created_at,
                       sq.solved_at,
                       COALESCE(sq.solved_within_2_days, 0),
                       COALESCE(sq.requires_session, 0),
                       sq.session_datetime
                FROM student_queries sq
                WHERE (
                    sq.teacher_username=%s
                    OR EXISTS (
                        SELECT 1
                        FROM assigned_subjects a
                        WHERE a.teacher_username=%s
                          AND LOWER(TRIM(a.subject_name)) = LOWER(TRIM(COALESCE(sq.doubt_subject, '')))
                          AND LOWER(TRIM(a.course_name)) = LOWER(TRIM(COALESCE(sq.course_name, '')))
                          AND TRIM(a.semester) = TRIM(COALESCE(sq.semester, ''))
                          AND UPPER(TRIM(a.section)) = UPPER(TRIM(COALESCE(sq.section, '')))
                    )
                )
                ORDER BY sq.id DESC
                LIMIT 400
                """,
                (self.username, self.username),
            )

        def refresh_queries():
            for row in query_tree.get_children():
                query_tree.delete(row)
            rows = get_assigned_query_rows()

            keyword = search_var.get().strip().lower()
            visible_rows = []
            solved_count = 0
            unsolved_count = 0
            within_2d_count = 0
            pending_overdue_count = 0

            for row in rows:
                status = str(row[4] or "")
                created_at = row[12]
                solved_at = row[13]
                solved_within = int(row[14] or 0)

                if status.lower() in {"solved", "clarification received"}:
                    solved_count += 1
                else:
                    unsolved_count += 1

                if solved_at and solved_within == 1:
                    within_2d_count += 1
                if (not solved_at) and created_at:
                    age_seconds = (datetime.now() - created_at).total_seconds()
                    if age_seconds > 2 * 24 * 3600:
                        pending_overdue_count += 1

                values_for_tree = row[:12]
                haystack = " ".join(str(item or "") for item in values_for_tree).lower()
                if keyword and keyword not in haystack:
                    continue
                visible_rows.append(values_for_tree)

            for row in visible_rows:
                query_tree.insert("", "end", values=row)

            solved_var.set(f"Solved: {solved_count}")
            unsolved_var.set(f"Not Solved: {unsolved_count}")
            within_var.set(f"Solved <=2 days: {within_2d_count}")
            overdue_var.set(f"Pending >2 days: {pending_overdue_count}")

        def send_announcement():
            title = ann_title.get().strip()
            message = ann_msg.get("1.0", tk.END).strip()
            if not title or not message:
                messagebox.showwarning("Input", "Title and message are required.")
                return

            subject = ann_subject.get().strip()
            course_name = ann_course.get().strip()
            semester = ann_sem.get().strip()
            section = ann_sec.get().strip().upper()

            if subject == "All":
                subject = ""
            if course_name == "All":
                course_name = ""
            if semester == "All":
                semester = ""
            if section == "All":
                section = ""

            self.db_execute(
                """
                INSERT INTO teacher_announcements
                (teacher_username, title, subject, course_name, semester, section, message)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                """,
                (self.username, title, subject, course_name, semester, section, message),
                fetch=None,
            )
            ann_title.delete(0, tk.END)
            ann_msg.delete("1.0", tk.END)
            ann_subject.set("All")
            ann_course.set("All")
            ann_sem.set("All")
            ann_sec.set("All")
            refresh_notifications()
            messagebox.showinfo("Sent", "Announcement sent to notification panel.")

        def get_selected_query_ids_and_enrollment():
            selected_items = query_tree.selection()
            if not selected_items:
                return [], ""
            qids = []
            enrollments = set()
            for item in selected_items:
                values = query_tree.item(item, "values")
                qids.append(int(values[0]))
                enrollments.add(str(values[1] or ""))
            if len(enrollments) > 1:
                return qids, "MULTI"
            return qids, (list(enrollments)[0] if enrollments else "")

        def mark_received():
            qids, _enrollment = get_selected_query_ids_and_enrollment()
            if not qids:
                messagebox.showwarning("Query", "Select a query first.")
                return
            placeholders = ",".join(["%s"] * len(qids))
            self.db_execute(
                f"""
                UPDATE student_queries
                SET teacher_username=%s,
                    status='Teacher Received',
                    teacher_received_at=IFNULL(teacher_received_at, NOW())
                WHERE id IN ({placeholders})
                """,
                (self.username, *qids),
                fetch=None,
            )
            refresh_queries()

        def resolve_query():
            selected = query_tree.focus()
            if not selected:
                messagebox.showwarning("Query", "Select a query first.")
                return
            values = query_tree.item(selected, "values")
            qid = values[0]
            current_status = str(values[4] or "").strip().lower()
            response = response_box.get("1.0", tk.END).strip()
            if not response:
                messagebox.showwarning("Response", "Enter response text.")
                return

            query_check = self.db_safe_one(
                "SELECT COALESCE(requires_session,0), session_datetime FROM student_queries WHERE id=%s",
                (qid,),
            )
            if query_check and int(query_check[0] or 0) == 1 and not query_check[1] and current_status in {"session required", "reopened"}:
                messagebox.showwarning("Session Required", "Student is not satisfied second time. Schedule a short session before final solution.")
                return

            self.db_execute(
                """
                UPDATE student_queries
                SET teacher_username=%s,
                    status='Solved',
                    response=%s,
                    solution_text=%s,
                    teacher_received_at=IFNULL(teacher_received_at, NOW()),
                    solved_at=NOW(),
                    solved_within_2_days=CASE
                        WHEN TIMESTAMPDIFF(HOUR, created_at, NOW()) <= 48 THEN 1
                        ELSE 0
                    END
                WHERE id=%s
                """,
                (self.username, response, response, qid),
                fetch=None,
            )
            response_box.delete("1.0", tk.END)
            refresh_queries()

        def schedule_session_for_selected():
            qids, enrollment = get_selected_query_ids_and_enrollment()
            if not qids:
                messagebox.showwarning("Session", "Select one or more queries first.")
                return
            if enrollment == "MULTI":
                messagebox.showwarning("Session", "Select queries of a single student to schedule one session.")
                return

            title = session_title.get().strip()
            date_text = session_date.get().strip()
            time_text = session_time.get().strip()
            details = session_note_box.get("1.0", tk.END).strip()
            if not title or not date_text or not time_text:
                messagebox.showwarning("Session", "Title, date and time are required.")
                return

            try:
                session_dt = datetime.strptime(f"{date_text} {time_text}", "%Y-%m-%d %H:%M")
            except Exception:
                messagebox.showwarning("Session", "Use session date/time format as YYYY-MM-DD and HH:MM.")
                return

            duration_min = int(session_duration.get().strip() or "20")
            mode = session_mode.get().strip() or "Offline"
            session_note = f"Mode: {mode}"
            if details:
                session_note = f"{session_note} | {details}"

            self.db_execute(
                """
                INSERT INTO doubt_sessions (teacher_username, enrollment_no, title, session_datetime, duration_minutes, mode, agenda, status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,'Scheduled')
                """,
                (self.username, enrollment, title, session_dt.strftime("%Y-%m-%d %H:%M:%S"), duration_min, mode, details or "Follow-up doubt resolution"),
                fetch=None,
            )

            session_row = self.db_safe_one(
                """
                SELECT id FROM doubt_sessions
                WHERE teacher_username=%s AND enrollment_no=%s AND title=%s AND session_datetime=%s
                ORDER BY id DESC LIMIT 1
                """,
                (self.username, enrollment, title, session_dt.strftime("%Y-%m-%d %H:%M:%S")),
            )
            session_id = int(session_row[0]) if session_row else 0

            for qid in qids:
                self.db_execute(
                    "INSERT IGNORE INTO doubt_session_queries (session_id, query_id) VALUES (%s,%s)",
                    (session_id, qid),
                    fetch=None,
                )

            placeholders = ",".join(["%s"] * len(qids))
            self.db_execute(
                f"""
                UPDATE student_queries
                SET teacher_username=%s,
                    requires_session=1,
                    session_status='Session Scheduled',
                    session_id=%s,
                    session_title=%s,
                    session_datetime=%s,
                    session_duration_minutes=%s,
                    session_note=%s,
                    status='Session Scheduled'
                WHERE id IN ({placeholders})
                """,
                (
                    self.username,
                    session_id,
                    title,
                    session_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    duration_min,
                    session_note,
                    *qids,
                ),
                fetch=None,
            )
            session_note_box.delete("1.0", tk.END)
            refresh_queries()
            messagebox.showinfo("Session", "Short session scheduled and linked to selected query/query list.")

        def mark_session_completed():
            qids, _enrollment = get_selected_query_ids_and_enrollment()
            if not qids:
                messagebox.showwarning("Session", "Select one or more session-scheduled queries first.")
                return
            placeholders = ",".join(["%s"] * len(qids))
            self.db_execute(
                f"""
                UPDATE student_queries
                SET session_status='Session Completed',
                    status='Session Completed',
                    teacher_received_at=IFNULL(teacher_received_at, NOW())
                WHERE id IN ({placeholders})
                """,
                (*qids,),
                fetch=None,
            )
            refresh_queries()

        tk.Button(left, text="Send Announcement", command=send_announcement, bg=t["accent"], fg="white", bd=0, padx=12, pady=6).pack(anchor="e", padx=10, pady=(0, 10))
        action_row = tk.Frame(right, bg=t["panel"])
        action_row.pack(fill="x", padx=10, pady=(0, 10))
        tk.Button(action_row, text="Search", command=refresh_queries, bg="#1d4ed8", fg="white", bd=0, padx=10, pady=6).pack(side="left")
        tk.Button(action_row, text="Mark Received", command=mark_received, bg="#2563eb", fg="white", bd=0, padx=10, pady=6).pack(side="left", padx=6)
        tk.Button(action_row, text="Submit Solution", command=resolve_query, bg=t["accent2"], fg="white", bd=0, padx=10, pady=6).pack(side="left", padx=6)
        tk.Button(action_row, text="Schedule Session", command=schedule_session_for_selected, bg="#7c3aed", fg="white", bd=0, padx=10, pady=6).pack(side="left", padx=6)
        tk.Button(action_row, text="Session Completed", command=mark_session_completed, bg="#0ea5e9", fg="white", bd=0, padx=10, pady=6).pack(side="left", padx=6)
        tk.Button(action_row, text="Refresh", command=refresh_queries, bg="#64748b", fg="white", bd=0, padx=10, pady=6).pack(side="right")

        def on_query_select(_event=None):
            selected = query_tree.focus()
            if not selected:
                return
            values = query_tree.item(selected, "values")
            existing_solution = str(values[11] or "")
            response_box.delete("1.0", tk.END)
            response_box.insert("1.0", existing_solution)

        query_tree.bind("<<TreeviewSelect>>", on_query_select)
        search_entry.bind("<Return>", lambda _event: refresh_queries())

        refresh_notifications()
        refresh_queries()

    def render_settings(self):
        t = self.theme()
        frame = tk.Frame(self.content, bg=t["app_bg"])
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="Profile & Settings", bg=t["app_bg"], fg=t["text"], font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(0, 10))

        top = tk.Frame(frame, bg=t["app_bg"])
        top.pack(fill="both", expand=True)

        profile = tk.Frame(top, bg=t["panel"])
        security = tk.Frame(top, bg=t["panel"])
        profile.pack(side="left", fill="both", expand=True, padx=(0, 5))
        security.pack(side="left", fill="both", expand=True, padx=(5, 0))

        tk.Label(profile, text="Teacher Profile", bg=t["panel"], fg=t["text"], font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=8)

        entries = {}
        for label, key, default in [
            ("Full Name", "full_name", self.teacher_info["full_name"]),
            ("Email", "email", self.teacher_info["email"]),
            ("Phone", "phone", self.teacher_info["phone"]),
            ("Department", "department", self.teacher_info["department"]),
            ("Designation", "designation", self.teacher_info["designation"]),
        ]:
            tk.Label(profile, text=label, bg=t["panel"], fg=t["text"]).pack(anchor="w", padx=10)
            e = tk.Entry(profile)
            e.insert(0, default)
            e.pack(fill="x", padx=10, pady=(0, 6))
            entries[key] = e

        notify_email = tk.IntVar(value=1)
        notify_inapp = tk.IntVar(value=1)

        pref = self.db_safe_one("SELECT notify_email, notify_inapp FROM teacher_settings WHERE username=%s", (self.username,))
        if pref:
            notify_email.set(pref[0])
            notify_inapp.set(pref[1])

        tk.Checkbutton(profile, text="Email Notifications", variable=notify_email, bg=t["panel"], fg=t["text"], selectcolor=t["panel"]).pack(anchor="w", padx=10)
        tk.Checkbutton(profile, text="In-App Notifications", variable=notify_inapp, bg=t["panel"], fg=t["text"], selectcolor=t["panel"]).pack(anchor="w", padx=10)

        def save_profile():
            data = {k: v.get().strip() for k, v in entries.items()}
            if not all(data.values()):
                messagebox.showwarning("Input", "All profile fields are required.")
                return
            try:
                self.db_execute(
                    """
                    UPDATE teachers
                    SET full_name=%s, email=%s, phone=%s, department=%s, designation=%s
                    WHERE username=%s
                    """,
                    (
                        data["full_name"],
                        data["email"],
                        data["phone"],
                        data["department"],
                        data["designation"],
                        self.username,
                    ),
                    fetch=None,
                )
                self.db_execute(
                    """
                    INSERT INTO teacher_settings (username, notify_email, notify_inapp)
                    VALUES (%s,%s,%s)
                    ON DUPLICATE KEY UPDATE notify_email=VALUES(notify_email), notify_inapp=VALUES(notify_inapp)
                    """,
                    (self.username, notify_email.get(), notify_inapp.get()),
                    fetch=None,
                )
                self.teacher_info = self.get_teacher_info()
                self.user_label.config(text=self.teacher_info["full_name"])
                self.teacher_tag_label.config(text=f"{self.get_assigned_subjects_display()}  •  {self.teacher_info['department']}")
                messagebox.showinfo("Saved", "Profile and preferences updated.")
            except Exception as err:
                messagebox.showerror("Error", str(err))

        tk.Button(profile, text="Save Profile", command=save_profile, bg=t["accent"], fg="white", bd=0, padx=12, pady=6).pack(anchor="e", padx=10, pady=10)

        tk.Label(security, text="Change Password", bg=t["panel"], fg=t["text"], font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=8)

        current_pwd = tk.Entry(security, show="*")
        new_pwd = tk.Entry(security, show="*")
        confirm_pwd = tk.Entry(security, show="*")

        for lbl, entry in [
            ("Current Password", current_pwd),
            ("New Password", new_pwd),
            ("Confirm Password", confirm_pwd),
        ]:
            tk.Label(security, text=lbl, bg=t["panel"], fg=t["text"]).pack(anchor="w", padx=10)
            entry.pack(fill="x", padx=10, pady=(0, 6))

        def update_password():
            current = current_pwd.get().strip()
            new = new_pwd.get().strip()
            confirm = confirm_pwd.get().strip()
            if not all([current, new, confirm]):
                messagebox.showwarning("Input", "All password fields are required.")
                return
            if new != confirm:
                messagebox.showerror("Mismatch", "New and confirm password do not match.")
                return
            if len(new) < 6:
                messagebox.showwarning("Password", "Minimum 6 characters required.")
                return

            row = self.db_safe_one("SELECT password FROM users WHERE username=%s AND role='teacher'", (self.username,))
            if not row:
                messagebox.showerror("Error", "Teacher account not found.")
                return
            if not verify_password(current, str(row[0] or "")):
                messagebox.showerror("Error", "Current password is incorrect.")
                return
            self.db_execute("UPDATE users SET password=%s WHERE username=%s AND role='teacher'", (hash_password(new), self.username), fetch=None)
            current_pwd.delete(0, tk.END)
            new_pwd.delete(0, tk.END)
            confirm_pwd.delete(0, tk.END)
            messagebox.showinfo("Success", "Password updated successfully.")

        tk.Button(security, text="Update Password", command=update_password, bg=t["accent2"], fg="white", bd=0, padx=12, pady=6).pack(anchor="e", padx=10, pady=10)

    def toggle_theme(self):
        self.theme_mode = "dark" if self.theme_mode == "light" else "light"
        self.render_current_view()

    def fetch_scalar(self, query, params=(), default=0):
        try:
            row = self.db_execute(query, params, fetch="one")
            if row and row[0] is not None:
                return row[0]
            return default
        except Exception:
            return default

    def db_safe_all(self, query, params=()):
        try:
            return self.db_execute(query, params, fetch="all")
        except Exception:
            return []

    def db_safe_one(self, query, params=()):
        try:
            return self.db_execute(query, params, fetch="one")
        except Exception:
            return None

    def logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            self.window.destroy()
            self.parent.deiconify()

    def on_close(self):
        self.parent.deiconify()
        self.window.destroy()


def open_teacher_dashboard(username, parent):
    TeacherDashboard(username, parent)
