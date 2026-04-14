
# student_dashboard.py
import os
import re
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
from datetime import datetime
from collections import defaultdict
from db_config import get_connection
from modules.studentprofile import load_student_profile # <-- Import the profile loader
from modules.courseprogress import load_course_module
from modules.course_aliases import course_matches, get_course_aliases
from modules.query_doubt import load_query_doubt_module
from modules.notification import load_notification_module
from auth_utils import hash_password, verify_password

# ================= COLORS =================
PRIMARY = "#1abc9c"
SECONDARY = "#2c3e50"
BG = "#f5f7fa"
CARD = "#ffffff"

# ================= STUDENT DASHBOARD =================
def open_student_dashboard(username, enrollment, parent):
    parent.withdraw()  # hide login window

    root = tk.Toplevel(parent)
    root.title("Student Performance Dashboard")
    root.configure(bg=BG)
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    w = min(1000, max(860, int(sw * 0.9)))
    h = min(600, max(520, int(sh * 0.85)))
    x = (sw // 2) - (w // 2)
    y = (sh // 2) - (h // 2)
    root.geometry(f"{w}x{h}+{x}+{y}")
    root.minsize(820, 500)

    def ensure_assignment_tables():
        conn = None
        cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
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
                """
            )
            cursor.execute(
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
                """
            )
            cursor.execute(
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
                """
            )
            cursor.execute(
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
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS admin_announcements (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(180) NOT NULL,
                    message TEXT NOT NULL,
                    created_by VARCHAR(100) NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            for alter_query in [
                "ALTER TABLE assignments ADD COLUMN course_name VARCHAR(150) NULL AFTER teacher_username",
                "ALTER TABLE assignments ADD COLUMN semester VARCHAR(20) NULL AFTER course_name",
                "ALTER TABLE assignments ADD COLUMN section VARCHAR(20) NULL AFTER semester",
                "ALTER TABLE assignments ADD COLUMN subject VARCHAR(150) NULL AFTER section",
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
            ]:
                try:
                    cursor.execute(alter_query)
                except Exception:
                    pass

            conn.commit()
            cursor.close()
            conn.close()
        except Exception:
            pass

    ensure_assignment_tables()

    # ================= HEADER =================
    header = tk.Frame(root, bg="#4a7abc", height=80)
    header.pack(fill="x", side="top")
    header.pack_propagate(False)

    tk.Label(header, text="Student Performance Management System",
             bg="#4a7abc", fg="white", font=("Arial", 18, "bold")).pack(side="left", padx=20, pady=20)

    # Right: Student Info
    student_frame = tk.Frame(header, bg="#4a7abc")
    student_frame.pack(side="right", padx=30, pady=10)

    photo_label = tk.Label(student_frame, bg="#4a7abc", cursor="hand2")
    photo_label.pack(side="right", padx=10)

    name_label = tk.Label(student_frame, bg="#4a7abc", fg="white", font=("Arial", 12, "bold"))
    name_label.pack(side="right")

    header_images = {}  # Keep PhotoImage references to avoid GC
    default_photo_path = "default_student.png"

    # ---------- Image Helpers ----------
    def get_image(path, size=(50, 50)):
        try:
            img = Image.open(path).convert("RGBA")
        except:
            img = Image.new("RGBA", size, (200, 200, 200, 255))
        img.thumbnail(size)
        return ImageTk.PhotoImage(img)

    def get_large_image(path, size=(200, 200)):
        try:
            img = Image.open(path).convert("RGBA")
        except:
            img = Image.new("RGBA", size, (200, 200, 200, 255))
        img.thumbnail(size)
        return ImageTk.PhotoImage(img)

    # ---------- Fetch DB Info ----------
    def fetch_student_name(enroll):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM students WHERE enrollment_no=%s", (enroll,))
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return result[0] if result else "Guest Student"
        except:
            return "Guest Student"

    def fetch_student_photo(enroll):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT photo_path FROM pic WHERE enrollment_no=%s", (enroll,))
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return result[0] if result else default_photo_path
        except:
            return default_photo_path

    # ---------- Update Header ----------
    def update_header():
        name_label.config(text=fetch_student_name(enrollment))
        photo_path = fetch_student_photo(enrollment)
        small_img = get_image(photo_path)
        header_images['small'] = small_img
        photo_label.config(image=header_images['small'])

    # ---------- Popup for Photo ----------
    def open_photo_popup():
        photo_path = fetch_student_photo(enrollment)
        popup = tk.Toplevel(root)
        popup.title("Profile Photo")
        popup.configure(bg="#f0f0f0")
        popup.resizable(False, False)

        # Center the popup
        popup.update_idletasks()
        w, h = 300, 350
        x = (popup.winfo_screenwidth() - w) // 2
        y = (popup.winfo_screenheight() - h) // 2
        popup.geometry(f"{w}x{h}+{x}+{y}")

        # Large Image Display
        large_img = get_large_image(photo_path, size=(200, 200))
        img_label = tk.Label(popup, image=large_img, bg="#f0f0f0")
        img_label.image = large_img
        img_label.pack(pady=20)

        btn_frame = tk.Frame(popup, bg="#f0f0f0")
        btn_frame.pack(side="bottom", pady=20)

        # Upload Photo
        def upload_photo():
            file_path = filedialog.askopenfilename(title="Select Photo",
                                                   filetypes=[("Image Files", "*.png *.jpg *.jpeg")])
            if file_path:
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO pic(enrollment_no, photo_path) VALUES(%s,%s) "
                        "ON DUPLICATE KEY UPDATE photo_path=%s",
                        (enrollment, file_path, file_path)
                    )
                    conn.commit()
                    cursor.close()
                    conn.close()
                    update_header()
                    popup.destroy()
                    messagebox.showinfo("Upload", "Photo uploaded successfully!")
                except Exception as e:
                    messagebox.showerror("DB Error", str(e))

        upload_btn = tk.Button(btn_frame, text="Upload", font=("Arial", 10, "bold"),
                               bg="#2ecc71", fg="white", padx=15, pady=5, command=upload_photo)
        upload_btn.pack(side="left", padx=10)

        # Remove Photo
        def remove_photo():
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM pic WHERE enrollment_no=%s", (enrollment,))
                conn.commit()
                cursor.close()
                conn.close()
                update_header()
                popup.destroy()
                messagebox.showinfo("Remove", "Photo removed and reverted to default!")
            except Exception as e:
                messagebox.showerror("DB Error", str(e))

        remove_btn = tk.Button(btn_frame, text="Remove", font=("Arial", 10, "bold"),
                               bg="#e74c3c", fg="white", padx=15, pady=5, command=remove_photo)
        remove_btn.pack(side="left", padx=10)

    photo_label.bind("<Button-1>", lambda e: open_photo_popup())
    update_header()

    # ================= MAIN FRAME =================
    main_frame = tk.Frame(root, bg=BG)
    main_frame.pack(fill="both", expand=True)

    # ================= LEFT MENU =================
    menu_frame = tk.Frame(main_frame, bg="#1a1f2b", width=220)
    menu_frame.pack(side="left", fill="y")
    menu_frame.pack_propagate(False)

    # ================= CONTENT =================
    content_frame = tk.Frame(main_frame, bg=BG)
    content_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

    def clear_content():
        for widget in content_frame.winfo_children():
            widget.destroy()

    # ---------------- MENU FUNCTIONS ----------------
    active_button = None

    def set_active(btn):
        nonlocal active_button
        if active_button:
            active_button.configure(bg="#2c3e50", fg="#ecf0f1")
        btn.configure(bg="#34495e", fg="#ffffff")
        active_button = btn

    # ----------- Dynamic Menu Functions -----------

    def marks_to_grade_sgpa(marks):
        try:
            value = float(marks)
        except (TypeError, ValueError):
            value = 0.0

        if value >= 90:
            grade = "A+"
        elif value >= 80:
            grade = "A"
        elif value >= 70:
            grade = "B"
        elif value >= 60:
            grade = "C"
        else:
            grade = "D"

        sgpa = round(max(0.0, min(10.0, value / 10.0)), 2)
        return grade, sgpa

    def resolve_student_semester(cursor, enrollment_no, course_name, section_name, fallback_sem):
        fallback_norm = _normalize_semester(fallback_sem)

        try:
            cursor.execute(
                """
                SELECT semester
                FROM published_results
                WHERE enrollment_no=%s
                ORDER BY published_at DESC, id DESC
                LIMIT 1
                """,
                (enrollment_no,),
            )
            row = cursor.fetchone()
            if row and row[0]:
                return _normalize_semester(row[0])
        except Exception:
            pass

        try:
            cursor.execute(
                """
                SELECT semester
                FROM teacher_internal_results
                WHERE enrollment_no=%s
                ORDER BY updated_at DESC, id DESC
                LIMIT 1
                """,
                (enrollment_no,),
            )
            row = cursor.fetchone()
            if row and row[0]:
                return _normalize_semester(row[0])
        except Exception:
            pass

        try:
            if course_name and section_name:
                course_aliases = get_course_aliases(course_name) or [course_name]
                placeholders = ",".join(["%s"] * len(course_aliases))
                cursor.execute(
                    f"""
                    SELECT semester
                    FROM assigned_subjects
                    WHERE UPPER(TRIM(section))=UPPER(TRIM(%s))
                      AND course_name IN ({placeholders})
                      AND TRIM(semester)<>''
                    ORDER BY id DESC
                    """,
                    (section_name, *course_aliases),
                )
                rows = cursor.fetchall()
                for row in rows:
                    sem_value = _normalize_semester(row[0])
                    if sem_value:
                        return sem_value
        except Exception:
            pass

        return fallback_norm

    def show_profile(btn=None):
        clear_content()
        if btn:
            set_active(btn)

        student_data = {
            "name": username,
            "enrollment": enrollment,
            "course": "N/A",
            "semester": "",
            "section": "",
            "department": "",
            "batch": "N/A",
            "phone": "N/A",
            "email": "N/A",
            "academic": [],
            "weekly_timetable": [],
            "subject_allocations": [],
        }

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT name, enrollment_no, course, semester, section, dob, email, phone, department
                FROM students
                WHERE enrollment_no=%s
                """,
                (enrollment,),
            )
            result = cursor.fetchone()
            if result:
                student_data["name"] = result[0] or username
                student_data["enrollment"] = result[1] or enrollment
                student_data["course"] = result[2] or "N/A"
                student_data["semester"] = _normalize_semester(result[3])
                student_data["section"] = str(result[4] or "").strip().upper()
                student_data["batch"] = f"Semester {student_data['semester'] or 'N/A'}"
                student_data["email"] = result[6] or "N/A"
                student_data["phone"] = result[7] or "N/A"
                student_data["department"] = str(result[8] or "").strip()

                resolved_sem = resolve_student_semester(
                    cursor=cursor,
                    enrollment_no=student_data["enrollment"],
                    course_name=student_data["course"],
                    section_name=student_data["section"],
                    fallback_sem=student_data["semester"],
                )
                student_data["semester"] = resolved_sem
                student_data["batch"] = f"Semester {resolved_sem or 'N/A'}"

            cursor.execute(
                """
                SELECT email, mobile
                FROM users
                WHERE role='student' AND enrollment_no=%s
                LIMIT 1
                """,
                (enrollment,),
            )
            user_result = cursor.fetchone()
            if not user_result:
                cursor.execute(
                    """
                    SELECT email, mobile
                    FROM users
                    WHERE role='student' AND username=%s
                    LIMIT 1
                    """,
                    (username,),
                )
                user_result = cursor.fetchone()
            if user_result:
                student_data["email"] = student_data["email"] if student_data["email"] != "N/A" else (user_result[0] or "N/A")
                student_data["phone"] = student_data["phone"] if student_data["phone"] != "N/A" else (user_result[1] or "N/A")

            cursor.execute(
                """
                SELECT semester,
                       COUNT(*) AS subject_count,
                       ROUND(AVG(final_total), 2) AS sem_average,
                       SUM(CASE WHEN UPPER(COALESCE(status, ''))='FAIL' THEN 1 ELSE 0 END) AS fail_count
                FROM published_results
                WHERE enrollment_no=%s
                GROUP BY semester
                ORDER BY semester
                """,
                (enrollment,),
            )
            published_sem_rows = cursor.fetchall()

            academic_records = []
            for sem_value, subject_count, sem_average, fail_count in published_sem_rows:
                sem_text = str(sem_value or "").strip()
                try:
                    sem_avg_val = float(sem_average or 0)
                except (TypeError, ValueError):
                    sem_avg_val = 0.0

                credits = int(subject_count or 0) * 3
                sem_sgpa = round(max(0.0, min(10.0, sem_avg_val / 10.0)), 2)
                fail_total = int(fail_count or 0)
                subject_total = int(subject_count or 0)
                if fail_total == 0:
                    status_text = "Pass"
                elif fail_total >= subject_total and subject_total > 0:
                    status_text = "Fail"
                else:
                    status_text = "Reappear"

                academic_records.append(
                    {
                        "semester": f"Sem {sem_text}" if sem_text else "Sem N/A",
                        "credits": credits,
                        "status": status_text,
                        "sgpa": sem_sgpa,
                    }
                )

            student_data["academic"] = academic_records

            timetable_rows = []
            subject_rows = []
            try:
                cursor.execute(
                    """
                    SELECT department_name, course_name, semester, section,
                           subject_name, subject_code, lecture_day, lecture_time,
                           teacher_name
                    FROM assigned_subjects
                    WHERE section=%s
                    ORDER BY
                        FIELD(UPPER(lecture_day), 'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY'),
                        lecture_time,
                        subject_code
                    """,
                    (student_data["section"],),
                )
                assigned_rows = cursor.fetchall()

                student_sem = _normalize_semester(student_data.get("semester", ""))
                student_course = student_data.get("course", "")
                student_dept = student_data.get("department", "").strip().upper()

                seen_subjects = set()
                for row in assigned_rows:
                    dept_name, course_name, semester_name, section_name, subject_name, subject_code, lecture_day, lecture_time, teacher_name = row

                    section_text = str(section_name or "").strip().upper()
                    if not section_text or section_text != student_data["section"]:
                        continue

                    sem_text = _normalize_semester(semester_name)
                    if student_sem and sem_text and student_sem != sem_text:
                        continue

                    if student_course and not course_matches(str(course_name or ""), student_course):
                        continue

                    dept_text = str(dept_name or "").strip().upper()
                    if student_dept and dept_text and dept_text != student_dept:
                        continue

                    timetable_rows.append(
                        {
                            "day": str(lecture_day or "").strip(),
                            "time": str(lecture_time or "").strip(),
                            "subject_code": str(subject_code or "").strip(),
                        }
                    )

                    subject_key = (
                        str(subject_code or "").strip().upper(),
                        str(subject_name or "").strip().upper(),
                        str(teacher_name or "").strip().upper(),
                    )
                    if subject_key not in seen_subjects:
                        seen_subjects.add(subject_key)
                        subject_rows.append(
                            {
                                "subject_name": str(subject_name or "").strip(),
                                "subject_code": str(subject_code or "").strip(),
                                "teacher_name": str(teacher_name or "").strip() or "N/A",
                            }
                        )
            except Exception:
                timetable_rows = []
                subject_rows = []

            student_data["weekly_timetable"] = timetable_rows
            student_data["subject_allocations"] = subject_rows
            student_data["section"] = student_data.get("section", "")

        except Exception as e:
            messagebox.showerror("Profile Error", f"Failed to load profile data: {str(e)}")
        finally:
            try:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
            except Exception:
                pass

        load_student_profile(content_frame, student_data)

    # def show_course_progress(btn=None):
    #     clear_content()
    #     if btn: set_active(btn)
    #     tk.Label(content_frame, text="Course Progress Section", font=("Arial", 14)).pack(pady=20)
    def show_course_progress(btn=None):
        clear_content()
        if btn:
         set_active(btn)

    # Load Course Progress Module correctly
        load_course_module(
          parent_frame=content_frame,
                    logged_in_username=username,
                    logged_in_enrollment=enrollment,
        )


    def show_performance(btn=None):
        clear_content()
        if btn:
            set_active(btn)

        tk.Label(
            content_frame,
            text="Performance Overview",
            font=("Arial", 16, "bold"),
            bg=BG,
            fg="#2c3e50",
        ).pack(anchor="w", pady=(0, 10))

        summary_row = tk.Frame(content_frame, bg=BG)
        summary_row.pack(fill="x", pady=(0, 10))

        def make_summary_card(parent_widget, title_text, value_text, color):
            card = tk.Frame(parent_widget, bg="white", bd=1, relief="solid")
            card.pack(side="left", fill="x", expand=True, padx=(0, 8))
            tk.Label(
                card,
                text=title_text,
                bg="white",
                fg="#64748b",
                font=("Arial", 10, "bold"),
            ).pack(anchor="w", padx=10, pady=(8, 2))
            value_label = tk.Label(
                card,
                text=value_text,
                bg="white",
                fg=color,
                font=("Arial", 16, "bold"),
            )
            value_label.pack(anchor="w", padx=10, pady=(0, 8))
            return value_label

        avg_value_label = make_summary_card(summary_row, "Overall Average", "--", "#2563eb")
        best_value_label = make_summary_card(summary_row, "Best Subject", "--", "#16a34a")
        exams_value_label = make_summary_card(summary_row, "Exam Attempts", "0", "#7c3aed")

        table_wrap = tk.Frame(content_frame, bg="white", bd=1, relief="solid")
        table_wrap.pack(fill="both", expand=True)

        columns = ("subject", "attempts", "average", "best", "latest_exam", "latest_marks", "grade")
        performance_tree = ttk.Treeview(table_wrap, columns=columns, show="headings", height=14)
        for col, width in [
            ("subject", 170),
            ("attempts", 90),
            ("average", 90),
            ("best", 90),
            ("latest_exam", 130),
            ("latest_marks", 100),
            ("grade", 90),
        ]:
            performance_tree.heading(col, text=col.replace("_", " ").title())
            performance_tree.column(col, width=width, anchor="center")

        y_scroll = ttk.Scrollbar(table_wrap, orient="vertical", command=performance_tree.yview)
        x_scroll = ttk.Scrollbar(table_wrap, orient="horizontal", command=performance_tree.xview)
        performance_tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        performance_tree.pack(side="top", fill="both", expand=True)
        y_scroll.pack(side="right", fill="y")
        x_scroll.pack(side="bottom", fill="x")

        footnote = tk.Label(
            content_frame,
            text="Subject-wise performance is based on Internal + External published totals.",
            font=("Arial", 10, "bold"),
            bg=BG,
            fg="#475569",
            anchor="w",
        )
        footnote.pack(fill="x", pady=(8, 0))

        def load_performance_rows():
            for item in performance_tree.get_children():
                performance_tree.delete(item)

            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT subject,
                           ROUND(COALESCE(final_total, internal_total + external_marks), 2) AS total_marks,
                           ROUND(internal_total, 2) AS internal_marks,
                           ROUND(external_marks, 2) AS external_marks,
                           COALESCE(grade, '') AS grade,
                           published_at
                    FROM published_results
                    WHERE enrollment_no=%s
                    ORDER BY published_at DESC, id DESC
                    """,
                    (enrollment,),
                )
                rows = cursor.fetchall()
                cursor.close()
                conn.close()
            except Exception as e:
                messagebox.showerror("Performance Error", f"Failed to load performance: {str(e)}")
                return

            if not rows:
                avg_value_label.config(text="--")
                best_value_label.config(text="--")
                exams_value_label.config(text="0")
                footnote.config(text="No result entries available yet.")
                return

            subject_stats = defaultdict(
                lambda: {
                    "attempts": 0,
                    "sum_marks": 0.0,
                    "best": 0.0,
                    "latest_exam": "",
                    "latest_marks": 0.0,
                    "latest_set": False,
                }
            )

            total_marks = 0.0
            total_attempts = 0
            for subject, total_mark, internal_marks, external_marks, published_grade, _published_at in rows:
                stat = subject_stats[str(subject)]
                # Rows are ordered DESC; skip duplicates — only count the latest entry per subject
                if stat["latest_set"]:
                    continue

                try:
                    mark_value = float(total_mark or 0)
                except (TypeError, ValueError):
                    mark_value = 0.0

                stat["attempts"] += 1
                stat["sum_marks"] += mark_value
                stat["best"] = max(stat["best"], mark_value)
                stat["latest_exam"] = f"Int {internal_marks} + Ext {external_marks}"
                stat["latest_marks"] = mark_value
                stat["latest_set"] = True

                total_marks += mark_value
                total_attempts += 1

            best_subject_name = "--"
            best_subject_avg = -1.0

            for subject_name in sorted(subject_stats.keys()):
                stat = subject_stats[subject_name]
                avg_marks = round(stat["sum_marks"] / stat["attempts"], 2) if stat["attempts"] else 0.0
                grade, _sgpa = marks_to_grade_sgpa(avg_marks)

                if avg_marks > best_subject_avg:
                    best_subject_avg = avg_marks
                    best_subject_name = subject_name

                performance_tree.insert(
                    "",
                    "end",
                    values=(
                        subject_name,
                        stat["attempts"],
                        avg_marks,
                        round(stat["best"], 2),
                        stat["latest_exam"],
                        round(stat["latest_marks"], 2),
                        grade,
                    ),
                )

            overall_avg = round(total_marks / total_attempts, 2) if total_attempts else 0.0
            avg_value_label.config(text=f"{overall_avg}/100")
            best_value_label.config(text=f"{best_subject_name} ({round(best_subject_avg, 2)}/100)")
            exams_value_label.config(text=str(total_attempts))
            footnote.config(text="Subject-wise performance is based on Internal + External published totals.")

        action_row = tk.Frame(content_frame, bg=BG)
        action_row.pack(fill="x", pady=(8, 0))
        tk.Button(
            action_row,
            text="Refresh Performance",
            font=("Arial", 10, "bold"),
            bg="#1abc9c",
            fg="white",
            bd=0,
            padx=14,
            pady=6,
            command=load_performance_rows,
            cursor="hand2",
        ).pack(side="left")

        load_performance_rows()

    def fetch_student_class_profile():
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT department, course, semester, section FROM students WHERE enrollment_no=%s LIMIT 1",
                (enrollment,),
            )
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if not row:
                return {"department": "", "course": "", "semester": "", "section": ""}
            return {
                "department": str(row[0] or "").strip(),
                "course": str(row[1] or "").strip(),
                "semester": str(row[2] or "").strip(),
                "section": str(row[3] or "").strip(),
            }
        except Exception:
            return {"department": "", "course": "", "semester": "", "section": ""}

    def fetch_student_subject_allocations():
        profile = fetch_student_class_profile()
        course_name = profile.get("course", "")
        semester = str(profile.get("semester", "")).strip()
        section = str(profile.get("section", "")).strip().upper()
        if not course_name or not semester or not section:
            return []

        course_aliases = get_course_aliases(course_name) or [course_name]
        placeholders = ",".join(["%s"] * len(course_aliases))

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT DISTINCT
                    COALESCE(NULLIF(subject_name, ''), 'General Subject') AS subject_name,
                    COALESCE(NULLIF(teacher_name, ''), 'N/A') AS teacher_name,
                    COALESCE(NULLIF(teacher_username, ''), '') AS teacher_username
                FROM assigned_subjects
                WHERE course_name IN ({placeholders})
                  AND TRIM(semester) = TRIM(%s)
                  AND UPPER(TRIM(section)) = UPPER(TRIM(%s))
                ORDER BY subject_name
                """,
                (*course_aliases, semester, section),
            )
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return rows
        except Exception:
            return []

    def _normalize_semester(value):
        sem_text = str(value or "").strip().upper()
        if not sem_text:
            return ""

        compact = re.sub(r"[^A-Z0-9]", "", sem_text)
        for token in (compact, sem_text):
            if "VIII" in token or "8" in token:
                return "VIII"
            if "VII" in token or "7" in token:
                return "VII"
            if "VI" in token or "6" in token:
                return "VI"
            if "V" in token or "5" in token:
                return "V"
            if "IV" in token or "4" in token:
                return "IV"
            if "III" in token or "3" in token:
                return "III"
            if "II" in token or "2" in token:
                return "II"
            if "I" in token or "1" in token:
                return "I"

        sem_map = {
            "1": "I", "I": "I", "1ST": "I", "FIRST": "I",
            "2": "II", "II": "II", "2ND": "II", "SECOND": "II",
            "3": "III", "III": "III", "3RD": "III", "THIRD": "III",
            "4": "IV", "IV": "IV", "4TH": "IV", "FOURTH": "IV",
            "5": "V", "V": "V", "5TH": "V", "FIFTH": "V",
            "6": "VI", "VI": "VI", "6TH": "VI", "SIXTH": "VI",
            "7": "VII", "VII": "VII", "7TH": "VII", "SEVENTH": "VII",
            "8": "VIII", "VIII": "VIII", "8TH": "VIII", "EIGHTH": "VIII",
        }
        return sem_map.get(sem_text, compact or sem_text)

    def assignment_matches_student(course_name, semester, section, class_name, profile):
        student_course = str(profile.get("course", "")).strip()
        student_sem = _normalize_semester(profile.get("semester", ""))
        student_sec = str(profile.get("section", "")).strip().upper()

        course_text = str(course_name or "").strip()
        sem_text = _normalize_semester(semester)
        sec_text = str(section or "").strip().upper()

        if course_text:
            if not student_course or not course_matches(course_text, student_course):
                return False
        elif class_name and student_course and not course_matches(class_name, student_course):
            return False

        if sem_text and student_sem and sem_text != student_sem:
            return False
        if sec_text and student_sec and sec_text != student_sec:
            return False

        if not (course_text and sem_text and sec_text) and class_name:
            class_text = str(class_name or "").strip().upper().replace(" ", "").replace("_", "-")
            class_parts = [part for part in class_text.split("-") if part]
            legacy_sem = _normalize_semester(class_parts[-2]) if len(class_parts) >= 2 else ""
            legacy_sec = class_parts[-1] if len(class_parts) >= 1 else ""
            if student_sem and legacy_sem and student_sem != legacy_sem:
                return False
            if student_sec and legacy_sec and student_sec != legacy_sec:
                return False

        return True

    def show_notifications(btn=None):
        clear_content()
        if btn:
            set_active(btn)
        badge_state["notifications_seen_at"] = datetime.now()
        load_notification_module(content_frame=content_frame, enrollment=enrollment, bg=BG)
        refresh_student_menu_badges()

    def show_ask_query_doubt(btn=None):
        clear_content()
        if btn:
            set_active(btn)
        badge_state["query_seen_at"] = datetime.now()
        load_query_doubt_module(content_frame=content_frame, enrollment=enrollment, bg=BG)
        refresh_student_menu_badges()

    def show_assignments(btn=None):
        clear_content()
        if btn:
            set_active(btn)

        tk.Label(content_frame, text="Assignments / Online Test", font=("Arial", 16, "bold"), bg=BG, fg="#2c3e50").pack(anchor="w", pady=(0, 10))

        wrapper = tk.Frame(content_frame, bg="white", bd=1, relief="solid")
        wrapper.pack(fill="both", expand=True)

        assignment_tree = ttk.Treeview(
            wrapper,
            columns=("id", "title", "teacher", "course", "sem", "sec", "subject", "deadline", "material", "submit_status", "marks", "evaluation"),
            show="headings",
            height=13,
        )
        for col, width in [
            ("id", 50), ("title", 145), ("teacher", 95), ("course", 90), ("sem", 50), ("sec", 50),
            ("subject", 120), ("deadline", 95), ("material", 120), ("submit_status", 110), ("marks", 65), ("evaluation", 190),
        ]:
            assignment_tree.heading(col, text=col.title())
            assignment_tree.column(col, width=width, anchor="center")
        assignment_tree.pack(fill="both", expand=True, padx=8, pady=8)

        info_var = tk.StringVar(value="Select assignment to view details and submit your document.")
        tk.Label(content_frame, textvariable=info_var, bg=BG, fg="#34495e", font=("Arial", 10, "bold"), anchor="w").pack(fill="x", pady=(8, 0))

        action_row = tk.Frame(content_frame, bg=BG)
        action_row.pack(fill="x", pady=(8, 0))

        selected_assignment = {"id": None, "deadline": None, "material": ""}

        def refresh_assignment_rows():
            for item in assignment_tree.get_children():
                assignment_tree.delete(item)

            student_profile = fetch_student_class_profile()
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """
                          SELECT a.id, a.title, a.teacher_username,
                              COALESCE(a.course_name, ''), COALESCE(a.semester, ''), COALESCE(a.section, ''), COALESCE(a.subject, ''),
                              a.class_name, a.deadline,
                           COALESCE(a.material_path, ''),
                           COALESCE(s.status, 'Not Submitted'),
                           COALESCE(s.marks, ''),
                           COALESCE(s.evaluation, '')
                    FROM assignments a
                    LEFT JOIN assignment_submissions s
                      ON s.assignment_id=a.id AND s.enrollment_no=%s
                    ORDER BY a.id DESC
                    """,
                    (enrollment,),
                )
                rows = cursor.fetchall()
                cursor.close()
                conn.close()

                today = datetime.now().date()
                for row in rows:
                    assignment_id, title, teacher_name, course_name, semester, section, subject, class_name, deadline, material_path, submit_status, marks, evaluation = row
                    if not assignment_matches_student(course_name, semester, section, class_name, student_profile):
                        continue

                    status_text = str(submit_status)
                    try:
                        if status_text == "Not Submitted" and deadline and deadline < today:
                            status_text = "Submission Closed"
                    except Exception:
                        pass

                    assignment_tree.insert(
                        "",
                        "end",
                        values=(
                            assignment_id,
                            title,
                            teacher_name,
                            course_name or student_profile.get("course", ""),
                            _normalize_semester(semester) if semester else _normalize_semester(student_profile.get("semester", "")),
                            str(section or student_profile.get("section", "")).upper(),
                            subject,
                            str(deadline),
                            os.path.basename(material_path) if material_path else "No File",
                            status_text,
                            marks,
                            evaluation,
                        ),
                        tags=(material_path,),
                    )
            except Exception as e:
                messagebox.showerror("Assignment Error", str(e))

        def on_select_assignment(_event=None):
            selected = assignment_tree.focus()
            if not selected:
                selected_assignment["id"] = None
                info_var.set("Select assignment to view details and submit your document.")
                upload_btn.config(state="disabled")
                return

            row = assignment_tree.item(selected, "values")
            tags = assignment_tree.item(selected, "tags")
            selected_assignment["id"] = row[0]
            selected_assignment["deadline"] = row[7]
            selected_assignment["material"] = tags[0] if tags else ""

            info_var.set(
                f"{row[1]} | {row[3]}-Sem {row[4]}-{row[5]} | Subject: {row[6]} | Teacher: {row[2]} | Due: {row[7]} | Status: {row[9]}"
            )

            try:
                deadline_date = datetime.strptime(str(row[7]), "%Y-%m-%d").date()
                if datetime.now().date() > deadline_date:
                    upload_btn.config(state="disabled")
                else:
                    upload_btn.config(state="normal")
            except Exception:
                upload_btn.config(state="disabled")

        def open_material_file():
            path = selected_assignment.get("material") or ""
            if not path:
                messagebox.showwarning("Material", "No assignment material attached.")
                return
            if not os.path.exists(path):
                messagebox.showerror("Material", "Assignment file path is invalid or not found.")
                return
            try:
                os.startfile(path)
            except Exception as e:
                messagebox.showerror("Open File", str(e))

        def upload_submission_file():
            assignment_id = selected_assignment.get("id")
            if not assignment_id:
                messagebox.showwarning("Submission", "Select assignment first.")
                return

            deadline_text = selected_assignment.get("deadline")
            try:
                deadline_date = datetime.strptime(str(deadline_text), "%Y-%m-%d").date()
            except Exception:
                messagebox.showerror("Submission", "Invalid assignment deadline.")
                return

            if datetime.now().date() > deadline_date:
                messagebox.showwarning("Submission Closed", "Submission is disabled after due date.")
                upload_btn.config(state="disabled")
                return

            file_path = filedialog.askopenfilename(
                title="Select Submission File",
                filetypes=[
                    ("Supported Files", "*.pdf *.doc *.docs *.docx *.xls *.xlx *.xlsx"),
                    ("PDF Files", "*.pdf"),
                    ("Word Files", "*.doc *.docs *.docx"),
                    ("Excel Files", "*.xls *.xlx *.xlsx"),
                    ("All Files", "*.*"),
                ],
            )
            if not file_path:
                return

            if not file_path.lower().endswith((".pdf", ".doc", ".docs", ".docx", ".xls", ".xlx", ".xlsx")):
                messagebox.showwarning("Submission", "Allowed submission formats: PDF, DOC, DOCS, DOCX, XLS, XLX, XLSX.")
                return

            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO assignment_submissions (assignment_id, enrollment_no, submission_path, status, marks, evaluation)
                    VALUES (%s,%s,%s,'Submitted',NULL,NULL)
                    ON DUPLICATE KEY UPDATE submission_path=VALUES(submission_path),
                                            status='Submitted',
                                            submitted_at=CURRENT_TIMESTAMP,
                                            marks=NULL,
                                            evaluation=NULL,
                                            evaluated_by=NULL,
                                            evaluated_at=NULL
                    """,
                    (assignment_id, enrollment, file_path),
                )
                conn.commit()
                cursor.close()
                conn.close()
                messagebox.showinfo("Submitted", "Assignment submitted successfully.")
                refresh_assignment_rows()
            except Exception as e:
                messagebox.showerror("Submission Error", str(e))

        tk.Button(
            action_row,
            text="Open Assignment File",
            font=("Arial", 10, "bold"),
            bg="#2563eb",
            fg="white",
            bd=0,
            padx=14,
            pady=6,
            command=open_material_file,
            cursor="hand2",
        ).pack(side="left")

        upload_btn = tk.Button(
            action_row,
            text="Upload Submission File",
            font=("Arial", 10, "bold"),
            bg="#16a34a",
            fg="white",
            bd=0,
            padx=14,
            pady=6,
            command=upload_submission_file,
            cursor="hand2",
            state="disabled",
        )
        upload_btn.pack(side="left", padx=8)

        tk.Button(
            action_row,
            text="Refresh",
            font=("Arial", 10, "bold"),
            bg="#7f8c8d",
            fg="white",
            bd=0,
            padx=14,
            pady=6,
            command=refresh_assignment_rows,
            cursor="hand2",
        ).pack(side="left")

        assignment_tree.bind("<<TreeviewSelect>>", on_select_assignment)
        refresh_assignment_rows()

    def show_results(btn=None):
        clear_content()
        if btn:
            set_active(btn)

        title = tk.Frame(content_frame, bg=BG)
        title.pack(fill="x", pady=(0, 10))

        tk.Label(
            title,
            text="View Results",
            font=("Arial", 16, "bold"),
            bg=BG,
            fg="#2c3e50",
        ).pack(side="left", padx=4)

        semester_var = tk.StringVar(value="")
        current_sem_rows = {"rows": []}

        def fetch_semester_options():
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT DISTINCT semester
                    FROM published_results
                    WHERE enrollment_no=%s
                    ORDER BY semester
                    """,
                    (enrollment,),
                )
                rows = cursor.fetchall()
                cursor.close()
                conn.close()
                sem_list = []
                for row in rows:
                    sem_norm = _normalize_semester(row[0])
                    if sem_norm and sem_norm not in sem_list:
                        sem_list.append(sem_norm)
                return sem_list
            except Exception:
                return []

        search_wrap = tk.Frame(content_frame, bg="white", bd=1, relief="solid")
        search_wrap.pack(fill="x", pady=(0, 10))

        tk.Label(search_wrap, text="Semester", font=("Arial", 10, "bold"), bg="white", fg="#334155").pack(side="left", padx=(10, 6), pady=8)
        semester_values = fetch_semester_options()
        sem_combo = ttk.Combobox(search_wrap, textvariable=semester_var, values=semester_values, state="readonly", width=16)
        if semester_values:
            semester_var.set(semester_values[-1])
        sem_combo.pack(side="left", padx=(0, 10), pady=8)

        table_wrap = tk.Frame(content_frame, bg="white", bd=1, relief="solid")
        table_wrap.pack(fill="both", expand=True)

        columns = (
            "semester",
            "subject",
            "internal_marks",
            "external_marks",
            "total_marks",
            "grade",
            "status",
            "published_at",
        )

        result_tree = ttk.Treeview(table_wrap, columns=columns, show="headings", height=14)
        for col, width in [
            ("semester", 90),
            ("subject", 160),
            ("internal_marks", 110),
            ("external_marks", 110),
            ("total_marks", 95),
            ("grade", 80),
            ("status", 95),
            ("published_at", 170),
        ]:
            result_tree.heading(col, text=col.replace("_", " ").title())
            result_tree.column(col, width=width, anchor="center")

        y_scroll = ttk.Scrollbar(table_wrap, orient="vertical", command=result_tree.yview)
        x_scroll = ttk.Scrollbar(table_wrap, orient="horizontal", command=result_tree.xview)
        result_tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        result_tree.pack(side="top", fill="both", expand=True)
        y_scroll.pack(side="right", fill="y")
        x_scroll.pack(side="bottom", fill="x")

        summary_label = tk.Label(
            content_frame,
            text="",
            font=("Arial", 10, "bold"),
            bg=BG,
            fg="#34495e",
            anchor="w",
        )
        summary_label.pack(fill="x", pady=(8, 0))

        def load_published_results():
            for item in result_tree.get_children():
                result_tree.delete(item)

            sem_text = semester_var.get().strip()
            if not sem_text:
                summary_label.config(text="Please enter semester (example: 1, I, 2, II).")
                return

            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT semester,
                           subject,
                           ROUND(internal_total, 2),
                           ROUND(external_marks, 2),
                           ROUND(final_total, 2),
                           COALESCE(grade, ''),
                           COALESCE(status, ''),
                           DATE_FORMAT(published_at, '%d-%b-%Y %h:%i %p')
                    FROM published_results
                    WHERE enrollment_no=%s
                    ORDER BY subject ASC
                    """,
                    (enrollment,),
                )
                all_rows = cursor.fetchall()
                cursor.close()
                conn.close()

                target_sem = _normalize_semester(sem_text)
                rows = [r for r in all_rows if _normalize_semester(r[0]) == target_sem]

                if not rows:
                    current_sem_rows["rows"] = []
                    summary_label.config(
                        text="No published result found for entered semester."
                    )
                    return

                sem_total = 0.0
                subject_count = 0
                current_sem_rows["rows"] = rows
                for row in rows:
                    result_tree.insert("", "end", values=row)
                    sem_total += float(row[4] or 0)
                    subject_count += 1

                sem_avg = round(sem_total / subject_count, 2) if subject_count else 0
                sem_sgpa = round(max(0.0, min(10.0, sem_avg / 10.0)), 2)
                summary_label.config(
                    text=f"Semester: {rows[0][0]}   |   Subjects: {subject_count}   |   Overall SGPA: {sem_sgpa}"
                )

            except Exception as e:
                current_sem_rows["rows"] = []
                summary_label.config(text="Published results table not available yet.")
                messagebox.showerror("Result Error", f"Failed to load published results: {str(e)}")

        def download_semester_result():
            rows = current_sem_rows.get("rows") or []
            sem_text = semester_var.get().strip()
            if not sem_text:
                messagebox.showwarning("Download", "Please select a semester first.")
                return

            # Export exactly what is currently visible in the result table.
            tree_rows = []
            for item_id in result_tree.get_children():
                vals = result_tree.item(item_id, "values")
                if vals:
                    tree_rows.append(tuple(vals))
            if tree_rows:
                rows = tree_rows

            if not rows:
                messagebox.showwarning("Download", "Search semester result first, then download.")
                return

            try:
                report_canvas = __import__("reportlab.pdfgen.canvas", fromlist=["canvas"])
                pagesize_module = __import__("reportlab.lib.pagesizes", fromlist=["A4", "landscape"])
                A4 = getattr(pagesize_module, "A4")
                landscape_fn = getattr(pagesize_module, "landscape")

                # Auto-save semester result inside a dedicated folder.
                base_dir = os.path.dirname(os.path.dirname(__file__))
                export_dir = os.path.join(base_dir, "downloads", "marksheets")
                os.makedirs(export_dir, exist_ok=True)
                safe_sem = "".join(ch for ch in sem_text if ch.isalnum() or ch in ("-", "_")) or "semester"
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_path = os.path.join(export_dir, f"marksheet_{enrollment}_{safe_sem}_{stamp}.pdf")

                sem_total = sum(float(r[4] or 0) for r in rows)
                subject_count = len(rows)
                sem_avg = round(sem_total / subject_count, 2) if subject_count else 0
                sem_sgpa = round(max(0.0, min(10.0, sem_avg / 10.0)), 2)

                student_info = {
                    "name": "",
                    "enrollment_no": enrollment,
                    "department": "",
                    "course": "",
                    "semester": rows[0][0] if rows else sem_text,
                    "section": "",
                    "dob": "",
                    "email": "",
                    "phone": "",
                    "status": "",
                }

                conn = None
                cursor = None
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        SELECT name, enrollment_no, department, course, semester, section,
                               DATE_FORMAT(dob, '%d-%b-%Y'), COALESCE(email, ''), COALESCE(phone, ''),
                               COALESCE(status, '')
                        FROM students
                        WHERE enrollment_no=%s
                        LIMIT 1
                        """,
                        (enrollment,),
                    )
                    row = cursor.fetchone()
                    if row:
                        student_info = {
                            "name": str(row[0] or ""),
                            "enrollment_no": str(row[1] or enrollment),
                            "department": str(row[2] or ""),
                            "course": str(row[3] or ""),
                            "semester": str(row[4] or (rows[0][0] if rows else sem_text)),
                            "section": str(row[5] or ""),
                            "dob": str(row[6] or ""),
                            "email": str(row[7] or ""),
                            "phone": str(row[8] or ""),
                            "status": str(row[9] or ""),
                        }
                except Exception:
                    pass
                finally:
                    try:
                        if cursor:
                            cursor.close()
                        if conn:
                            conn.close()
                    except Exception:
                        pass

                pdf = report_canvas.Canvas(file_path, pagesize=landscape_fn(A4))
                width, height = landscape_fn(A4)

                def _prepare_white_bg_logo():
                    logo_candidates = [
                        os.path.join(base_dir, "image.png"),
                        os.path.join(base_dir, "spms_logo.png"),
                        os.path.join(base_dir, "logo.png"),
                        os.path.join(base_dir, "bg.png"),
                    ]
                    src_logo = next((p for p in logo_candidates if os.path.exists(p)), "")
                    if not src_logo:
                        return ""

                    try:
                        logo_img = Image.open(src_logo).convert("RGBA")
                        white_bg = Image.new("RGBA", logo_img.size, (255, 255, 255, 255))
                        white_bg.paste(logo_img, (0, 0), logo_img)

                        # Replace near-black background pixels with white for cleaner logo output.
                        cleaned = []
                        for px in white_bg.getdata():
                            r, g, b, a = px
                            if a > 0 and r < 20 and g < 20 and b < 20:
                                cleaned.append((255, 255, 255, a))
                            else:
                                cleaned.append(px)
                        white_bg.putdata(cleaned)

                        out_logo = os.path.join(export_dir, "spms_logo_white.png")
                        white_bg.convert("RGB").save(out_logo, "PNG")
                        return out_logo
                    except Exception:
                        return src_logo

                logo_path = _prepare_white_bg_logo()

                # Marksheet header with institute identity.
                pdf.setFillColorRGB(0.95, 0.97, 1.0)
                pdf.rect(28, height - 112, width - 56, 76, stroke=0, fill=1)
                pdf.setFillColorRGB(0, 0, 0)

                if logo_path and os.path.exists(logo_path):
                    try:
                        pdf.setFillColorRGB(1, 1, 1)
                        pdf.rect(36, height - 97, 72, 56, stroke=1, fill=1)
                        pdf.setFillColorRGB(0, 0, 0)
                        pdf.drawImage(logo_path, 42, height - 91, width=60, height=44, preserveAspectRatio=True, mask='auto')
                    except Exception:
                        pass

                pdf.setFont("Helvetica-Bold", 16)
                pdf.drawString(118, height - 58, "Student Performance Management System")
                pdf.setFont("Helvetica-Bold", 11)
                pdf.drawString(118, height - 76, "Institute Name: SPMS")
                pdf.setFont("Helvetica", 10)
                pdf.drawString(118, height - 92, "Official Semester Marksheet")

                pdf.setLineWidth(1)
                pdf.line(28, height - 116, width - 28, height - 116)

                details_top = height - 132
                pdf.setFillColorRGB(0.98, 0.98, 0.98)
                pdf.rect(28, details_top - 78, width - 56, 74, stroke=1, fill=1)
                pdf.setFillColorRGB(0, 0, 0)
                pdf.setFont("Helvetica-Bold", 9)
                pdf.drawString(38, details_top - 18, "Student Details")
                pdf.setFont("Helvetica", 9)
                pdf.drawString(38, details_top - 32, f"Name: {student_info['name']}")
                pdf.drawString(250, details_top - 32, f"Enrollment No: {student_info['enrollment_no']}")
                pdf.drawString(470, details_top - 32, f"Semester: {rows[0][0]}")

                pdf.drawString(38, details_top - 46, f"Department: {student_info['department']}")
                pdf.drawString(250, details_top - 46, f"Course: {student_info['course']}")
                pdf.drawString(470, details_top - 46, f"Section: {student_info['section']}")

                pdf.drawString(38, details_top - 60, f"DOB: {student_info['dob']}")
                pdf.drawString(250, details_top - 60, f"Email: {student_info['email']}")
                pdf.drawString(470, details_top - 60, f"Phone: {student_info['phone']}")

                pdf.drawString(38, details_top - 74, f"Status: {student_info['status']}")
                pdf.drawString(250, details_top - 74, f"Generated: {datetime.now().strftime('%d-%b-%Y %I:%M %p')}")

                headers = ["Subject", "Internal", "External", "Total", "Grade", "Status", "Published At"]
                col_widths = [220, 70, 70, 70, 60, 70, 150]
                x = 36
                y = details_top - 102

                table_total_w = sum(col_widths)
                pdf.setFillColorRGB(0.91, 0.94, 0.99)
                pdf.rect(x - 4, y - 4, table_total_w + 8, 16, stroke=1, fill=1)
                pdf.setFillColorRGB(0, 0, 0)
                pdf.setFont("Helvetica-Bold", 9)
                for idx, head in enumerate(headers):
                    pdf.drawString(x, y, head)
                    x += col_widths[idx]

                y -= 14
                pdf.setFont("Helvetica", 9)
                for row in rows:
                    x = 36
                    pdf.rect(x - 4, y - 3, table_total_w + 8, 14, stroke=1, fill=0)
                    values = [
                        str(row[1] or "").replace("\n", " ").replace("\r", " ").strip()[:45],
                        str(row[2] or ""),
                        str(row[3] or ""),
                        str(row[4] or ""),
                        str(row[5] or ""),
                        str(row[6] or ""),
                        str(row[7] or ""),
                    ]
                    for idx, value in enumerate(values):
                        pdf.drawString(x, y, value)
                        x += col_widths[idx]
                    y -= 13

                    if y < 70:
                        pdf.showPage()
                        pdf.setFont("Helvetica-Bold", 13)
                        pdf.drawString(36, height - 34, "Official Semester Marksheet (continued)")
                        pdf.setFont("Helvetica", 9)
                        pdf.drawString(36, height - 48, f"Enrollment: {enrollment}   Semester: {rows[0][0]}")
                        pdf.line(36, height - 54, width - 36, height - 54)
                        y = height - 76
                        pdf.setFont("Helvetica", 9)

                y -= 8
                pdf.setFont("Helvetica-Bold", 10)
                pdf.drawString(36, y, f"Subjects: {subject_count}")
                pdf.drawString(170, y, f"Overall SGPA: {sem_sgpa}")
                pdf.drawString(330, y, f"Average Marks: {sem_avg}")
                pdf.drawString(500, y, f"Result: {'PASS' if sem_avg >= 40 else 'FAIL'}")

                sign_y = max(44, y - 44)
                pdf.line(70, sign_y, 220, sign_y)
                pdf.line(290, sign_y, 440, sign_y)
                pdf.line(510, sign_y, 660, sign_y)
                pdf.setFont("Helvetica", 9)
                pdf.drawString(110, sign_y - 13, "Prepared By")
                pdf.drawString(336, sign_y - 13, "Checked By")
                pdf.drawString(564, sign_y - 13, "Principal")
                pdf.save()

                messagebox.showinfo("Download", f"Semester result downloaded successfully.\nSaved at:\n{file_path}")
            except Exception as exc:
                messagebox.showerror("Download Error", f"PDF export failed: {str(exc)}\nInstall package: pip install reportlab")

        action_row = tk.Frame(content_frame, bg=BG)
        action_row.pack(fill="x", pady=(8, 0))
        tk.Button(
            action_row,
            text="Search Result",
            font=("Arial", 10, "bold"),
            bg="#1abc9c",
            fg="white",
            bd=0,
            padx=14,
            pady=6,
            command=load_published_results,
            cursor="hand2",
        ).pack(side="left")

        tk.Button(
            action_row,
            text="Download Semester Result",
            font=("Arial", 10, "bold"),
            bg="#2563eb",
            fg="white",
            bd=0,
            padx=14,
            pady=6,
            command=download_semester_result,
            cursor="hand2",
        ).pack(side="left", padx=8)

    def change_password(btn=None):
        clear_content()
        if btn: set_active(btn)

        cp_frame = tk.Frame(content_frame, bg=BG)
        cp_frame.pack(pady=20, padx=20, fill="x")

        tk.Label(cp_frame, text="Change Password", font=("Arial", 16, "bold"), bg=BG).pack(pady=(0, 20))

        tk.Label(cp_frame, text="Current Password:", font=("Arial", 12), bg=BG).pack(anchor="w", pady=(5,0))
        current_pwd = tk.Entry(cp_frame, font=("Arial", 12), show="*")
        current_pwd.pack(fill="x", pady=(0,10))

        tk.Label(cp_frame, text="New Password:", font=("Arial", 12), bg=BG).pack(anchor="w", pady=(5,0))
        new_pwd = tk.Entry(cp_frame, font=("Arial", 12), show="*")
        new_pwd.pack(fill="x", pady=(0,10))

        tk.Label(cp_frame, text="Confirm New Password:", font=("Arial", 12), bg=BG).pack(anchor="w", pady=(5,0))
        confirm_pwd = tk.Entry(cp_frame, font=("Arial", 12), show="*")
        confirm_pwd.pack(fill="x", pady=(0,15))

        def update_password():
            curr = current_pwd.get().strip()
            new = new_pwd.get().strip()
            confirm = confirm_pwd.get().strip()

            if not curr or not new or not confirm:
                messagebox.showwarning("Input Error", "All fields are required.")
                return

            if new != confirm:
                messagebox.showerror("Mismatch", "New Password and Confirm Password do not match.")
                return

            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT password FROM users WHERE enrollment_no=%s", (enrollment,))
                result = cursor.fetchone()
                if result is None:
                    messagebox.showerror("Error", "Student record not found.")
                    cursor.close()
                    conn.close()
                    return
                if not verify_password(curr, str(result[0] or "")):
                    messagebox.showerror("Error", "Current password is incorrect.")
                    cursor.close()
                    conn.close()
                    return

                cursor.execute("UPDATE users SET password=%s WHERE enrollment_no=%s", (hash_password(new), enrollment))
                conn.commit()
                cursor.close()
                conn.close()
                messagebox.showinfo("Success", "Password updated successfully!")
                current_pwd.delete(0, tk.END)
                new_pwd.delete(0, tk.END)
                confirm_pwd.delete(0, tk.END)
            except Exception as e:
                messagebox.showerror("DB Error", str(e))

        tk.Button(cp_frame, text="Update Password", font=("Arial", 12, "bold"),
                  bg="#2ecc71", fg="white", padx=15, pady=8, command=update_password).pack(pady=10)

    # ---------------- LOGOUT ----------------
    def logout():
        result = messagebox.askyesno("Logout", "Are you sure you want to logout?")
        if result:
            root.destroy()
            parent.deiconify()

    # ---------------- MENU BUTTONS ----------------
    menu_buttons = [
        ("My Profile", show_profile),
        ("Assignments / Online Test", show_assignments),
        ("Course Progress", show_course_progress),
        ("Performance", show_performance),
        ("View Results", show_results),
        ("Ask Query / Doubt", show_ask_query_doubt),
        ("Notifications", show_notifications),
        ("Change Password", change_password)
    ]

    menu_button_refs = {}
    menu_button_labels = {text: text for text, _ in menu_buttons}
    badge_state = {
        "notifications_seen_at": datetime(2000, 1, 1),
        "query_seen_at": datetime(2000, 1, 1),
        "badge_job": None,
    }

    def set_menu_badge(label_text, is_new=False, count=0):
        btn = menu_button_refs.get(label_text)
        if not btn:
            return
        base = menu_button_labels.get(label_text, label_text)
        if is_new:
            suffix = "  📩"
            btn.config(text=f"{base}{suffix}")
        else:
            btn.config(text=base)

    def get_new_query_count():
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM student_queries
                WHERE enrollment_no=%s
                  AND updated_at > %s
                  AND (
                      COALESCE(status, '') IN ('Solved', 'Session Scheduled', 'Session Completed', 'Teacher Received')
                      OR COALESCE(requires_session, 0)=1
                  )
                """,
                (enrollment, badge_state["query_seen_at"]),
            )
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            return int(row[0] or 0) if row else 0
        except Exception:
            return 0

    def get_new_notification_count():
        student_profile = fetch_student_class_profile()
        subject_rows = fetch_student_subject_allocations()
        student_subjects = {str(row[0] or "").strip().lower() for row in subject_rows if row and row[0]}

        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM admin_announcements
                WHERE created_at > %s
                """,
                (badge_state["notifications_seen_at"],),
            )
            admin_count_row = cursor.fetchone()
            admin_count = int(admin_count_row[0] or 0) if admin_count_row else 0

            cursor.execute(
                """
                SELECT COALESCE(subject, ''), COALESCE(course_name, ''), COALESCE(semester, ''), COALESCE(section, '')
                FROM teacher_announcements
                WHERE created_at > %s
                """,
                (badge_state["notifications_seen_at"],),
            )
            teacher_rows = cursor.fetchall()

            filtered_teacher_count = 0
            student_sem = _normalize_semester(student_profile.get("semester", ""))
            student_sec = str(student_profile.get("section", "")).strip().upper()
            for row in teacher_rows:
                ann_subject = str(row[0] or "").strip()
                ann_course = str(row[1] or "").strip()
                ann_sem = _normalize_semester(row[2]) if row[2] else ""
                ann_sec = str(row[3] or "").strip().upper()

                if ann_course and not course_matches(ann_course, student_profile.get("course", "")):
                    continue
                if ann_sem and student_sem and ann_sem != student_sem:
                    continue
                if ann_sec and student_sec and ann_sec != student_sec:
                    continue
                if ann_subject and student_subjects and ann_subject.lower() not in student_subjects:
                    continue
                filtered_teacher_count += 1

            cursor.execute(
                """
                SELECT COALESCE(course_name, ''), COALESCE(semester, ''), COALESCE(section, ''), COALESCE(class_name, '')
                FROM assignments
                WHERE created_at > %s
                """,
                (badge_state["notifications_seen_at"],),
            )
            assignment_rows = cursor.fetchall()
            filtered_assignment_count = 0
            for row in assignment_rows:
                if assignment_matches_student(row[0], row[1], row[2], row[3], student_profile):
                    filtered_assignment_count += 1

            cursor.close()
            conn.close()
            return admin_count + filtered_teacher_count + filtered_assignment_count
        except Exception:
            return 0

    def refresh_student_menu_badges():
        query_count = get_new_query_count()
        notif_count = get_new_notification_count()
        set_menu_badge("Ask Query / Doubt", is_new=query_count > 0, count=query_count)
        set_menu_badge("Notifications", is_new=notif_count > 0, count=notif_count)

        if root.winfo_exists():
            if badge_state.get("badge_job"):
                try:
                    root.after_cancel(badge_state["badge_job"])
                except Exception:
                    pass
            badge_state["badge_job"] = root.after(15000, refresh_student_menu_badges)

    for text, cmd in menu_buttons:
        btn = tk.Button(menu_frame, text=text, font=("Arial", 12, "bold"), fg="#ecf0f1", bg="#2c3e50",
                        bd=0, relief="flat", anchor="w", padx=20, pady=12, cursor="hand2",
                        activeforeground="white", activebackground="#00bcd4")
        btn.configure(command=lambda b=btn, f=cmd: f(b))
        btn.pack(fill="x", pady=3)
        menu_button_refs[text] = btn

    logout_btn = tk.Button(menu_frame, text="Logout", font=("Arial", 12, "bold"), fg="white", bg="#e74c3c",
                           bd=0, relief="flat", anchor="w", padx=20, pady=12, command=logout,
                           activebackground="#c0392b", cursor="hand2")
    logout_btn.pack(side="bottom", fill="x", pady=10)

    # Default content
    show_profile()
    refresh_student_menu_badges()

    # ================= FOOTER =================
    footer = tk.Frame(root, bg="#1f2a36", height=70)
    footer.pack(fill="x", side="bottom")
    footer.pack_propagate(False)

    footer_left = tk.Frame(footer, bg="#1f2a36")
    footer_left.pack(side="left", fill="both", expand=True, padx=15)

    footer_center = tk.Frame(footer, bg="#1f2a36")
    footer_center.pack(side="left", fill="both", expand=True)

    footer_right = tk.Frame(footer, bg="#1f2a36")
    footer_right.pack(side="right", fill="both", expand=True, padx=15)

    tk.Label(footer_left, text="Student Performance Analysis System",
             bg="#1f2a36", fg="white", font=("Arial", 10, "bold")).pack(anchor="w", pady=(10, 0))

    status_label = tk.Label(footer_left, text="● Ready", bg="#1f2a36", fg="#2ecc71", font=("Arial", 9))
    status_label.pack(anchor="w", pady=(3, 0))

    # Footer buttons
    def open_footer_popup(title, msg):
        pop = tk.Toplevel(root)
        pop.title(title)
        pop.geometry("450x250")
        pop.configure(bg="#f5f5f5")
        pop.resizable(False, False)

        tk.Label(pop, text=title, font=("Arial", 16, "bold"),
                 bg="#00bcd4", fg="white", height=2).pack(fill="x")

        tk.Label(pop, text=msg, font=("Arial", 11), bg="#f5f5f5",
                 justify="left", wraplength=420).pack(pady=20, padx=15)

        tk.Button(pop, text="Close", bg="#e74c3c", fg="white",
                  bd=0, padx=15, pady=6, command=pop.destroy).pack(pady=10)

    footer_btn_style = {"bg": "#2c3e50", "fg": "white", "bd": 0, "font": ("Arial", 10),
                        "padx": 14, "pady": 6, "cursor": "hand2"}

    btn_frame = tk.Frame(footer_center, bg="#1f2a36")
    btn_frame.pack(expand=True)

    footer_buttons = [
        ("About", "This system helps manage Students, Courses, Results, Attendance, and Performance Analytics."),
        ("Help", "Use the Navigation Bar to open modules.\n• Student: Add/View/Edit/Delete Students\n• Course: Manage Courses\n• Result: Add & Analyze Marks"),
        ("Contact", "Developer: Ritesh Kumar Singh\nEmail: yourgmail@gmail.com\nMobile: +91-XXXXXXXXXX"),
        ("Privacy", "Your data is stored securely in MySQL.\nOnly authenticated users can access the dashboard.")
    ]

    for i, (text, msg) in enumerate(footer_buttons):
        btn = tk.Button(btn_frame, text=text,
                        command=lambda t=text, m=msg: open_footer_popup(t, m),
                        **footer_btn_style)
        btn.grid(row=0, column=i, padx=6)

    # Live clock
    time_label = tk.Label(footer_right, text="", bg="#1f2a36", fg="white", font=("Arial", 10))
    time_label.pack(anchor="e", pady=(10, 0))

    tk.Label(footer_right, text="© 2026 | Developed by Ritesh", bg="#1f2a36",
             fg="#bdc3c7", font=("Arial", 9)).pack(anchor="e", pady=(3, 0))

    def update_time():
        now = datetime.now()
        time_label.config(text=now.strftime("%d %b %Y  |  %I:%M:%S %p"))
        footer.after(1000, update_time)

    update_time()

    # Handle window close
    def on_close():
        parent.deiconify()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)













