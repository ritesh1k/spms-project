import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
import re
from db_config import get_connection
from modules.course_aliases import get_course_aliases
from modules.result_utils import normalize_semester

# ------------------ Course Module ------------------
def load_course_module(parent_frame, logged_in_username, db_config=None, logged_in_enrollment=None):
    def open_db_connection():
        if db_config:
            return mysql.connector.connect(**db_config)
        return get_connection()


    for w in parent_frame.winfo_children():
        w.destroy()

    parent_frame.configure(bg="#eef2f7")

    # ---------- CENTER CONTAINER ----------
    container = tk.Frame(
        parent_frame,
        bg="white",
        highlightbackground="#1abc9c",
        highlightthickness=2,
        bd=0
    )
    container.pack(padx=60, pady=30, fill="both", expand=True)

    tk.Label(
        container,
        text="Course Progress",
        font=("Segoe UI", 18, "bold"),
        bg="white",
        fg="#1e293b"
    ).pack(pady=(20, 15))

    # ------------------ Input ------------------
    input_frame = tk.Frame(container, bg="white")
    input_frame.pack(fill="x", padx=40, pady=10)

    tk.Label(input_frame, text="Enrollment:", bg="white", fg="#334155",
             font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")

    enrollment_entry = tk.Entry(
        input_frame,
        width=18,
        relief="solid",
        bd=1
    )
    enrollment_entry.grid(row=0, column=1, padx=6)

    tk.Label(input_frame, text="Semester:", bg="white", fg="#334155",
             font=("Segoe UI", 10, "bold")).grid(row=0, column=2, sticky="w")

    semester_var = tk.StringVar(value="1")
    ttk.Combobox(
        input_frame,
        textvariable=semester_var,
        values=[1, 2, 3, 4, 5, 6, 7, 8],
        width=8,
        state="readonly"
    ).grid(row=0, column=3, padx=6)

    # ---------- Styled Button ----------
    view_btn = tk.Button(
        input_frame,
        text="View",
        bg="#16bc69",
        fg="white",
        font=("Segoe UI", 10, "bold"),
        relief="flat",
        padx=18,
        pady=6,
        cursor="hand2"
    )
    view_btn.grid(row=0, column=4, padx=15)

    # Hover Effect
    def on_enter(e):
        view_btn.config(bg="#075418")

    def on_leave(e):
        view_btn.config(bg="#16bc69")

    view_btn.bind("<Enter>", on_enter)
    view_btn.bind("<Leave>", on_leave)

    # ------------------ TABLE STYLE ------------------
    style = ttk.Style()
    style.theme_use("default")

    style.configure(
        "Treeview",
        background="white",
        foreground="#1e293b",
        rowheight=34,
        fieldbackground="white",
        bordercolor="#cbd5e1",
        borderwidth=1
    )

    style.configure(
        "Treeview.Heading",
        background="#f1f5f9",
        foreground="#1e293b",
        font=("Segoe UI", 11, "bold")
    )

    style.map("Treeview.Heading",
              background=[("active", "#e2e8f0")])

    # ------------------ Table ------------------
    columns = ("Code", "Subject", "Progress", "Status")
    tree = ttk.Treeview(
        container,
        columns=columns,
        show="headings",
        height=8
    )
    tree.pack(fill="both", expand=True, padx=40, pady=(15, 25))

    for c in columns:
        tree.heading(c, text=c)
        tree.column(c, anchor="center", width=150)

    # ------------------ Status Logic ------------------
    def status_of(p):
        if p < 60: return "Bad"
        if p < 75: return "Average"
        if p < 90: return "Good"
        return "Very Good"

    status_color = {
        "Bad": "#e74c3c",
        "Average": "#f39c12",
        "Good": "#16a34a",
        "Very Good": "#2563eb"
    }

    status_background = {
        "Bad": "#fde8e8",
        "Average": "#fff4db",
        "Good": "#e8f7ed",
        "Very Good": "#e8f0fe",
        "No Data": "#f1f5f9",
    }

    for s, c in status_color.items():
        tree.tag_configure(
            s,
            foreground=c,
            background=status_background.get(s, "white"),
            font=("Segoe UI", 10, "bold"),
        )

    tree.tag_configure(
        "No Data",
        foreground="#64748b",
        background=status_background["No Data"],
        font=("Segoe UI", 10, "bold"),
    )



    def _safe_int(value, default=0):
        try:
            return int(str(value).strip())
        except Exception:
            return default

    def _subject_key(value):
        return str(value or "").strip().upper()

    def _canonical_subject_key(value):
        text = _subject_key(value)
        if not text:
            return ""
        return re.sub(r"[^A-Z0-9]+", "", text)

    def _class_subject_token(class_name):
        class_key = _subject_key(class_name)
        if not class_key:
            return ""
        if "-" in class_key:
            return class_key.split("-")[-1].strip()
        return class_key

    def _build_subject_lookup_keys(subject_code, subject_name, class_name=""):
        keys = set()

        for raw in (subject_code, subject_name, class_name, _class_subject_token(class_name)):
            normal = _subject_key(raw)
            if normal:
                keys.add(normal)
            canonical = _canonical_subject_key(raw)
            if canonical:
                keys.add(f"CANON:{canonical}")

        return keys

    def _semester_values(semester_text):
        sem_raw = str(semester_text or "").strip()
        sem_norm = normalize_semester(sem_raw)
        vals = [sem_raw, sem_norm]
        seen = []
        for item in vals:
            if item and item not in seen:
                seen.append(item)
        return seen

    def _fetch_student_profile(cursor, enrollment_no):
        cursor.execute(
            """
            SELECT department, course, section
            FROM students
            WHERE enrollment_no=%s
            LIMIT 1
            """,
            (enrollment_no,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "department": str(row[0] or "").strip().upper(),
            "course": str(row[1] or "").strip(),
            "section": str(row[2] or "").strip().upper(),
        }

    def _fetch_subjects_for_semester(cursor, enrollment_no, semester_text):
        student_profile = _fetch_student_profile(cursor, enrollment_no)
        if not student_profile:
            return []

        student_department = student_profile["department"]
        student_course = student_profile["course"]
        student_section = student_profile["section"]

        if not student_course or not student_section:
            return []

        sem_values = _semester_values(semester_text)
        if not sem_values:
            return []

        course_aliases = get_course_aliases(student_course) or [student_course]
        course_aliases = [str(alias).strip() for alias in course_aliases if str(alias).strip()]
        if not course_aliases:
            course_aliases = [student_course]

        sem_placeholders = ",".join(["%s"] * len(sem_values))
        course_placeholders = ",".join(["%s"] * len(course_aliases))
        query = f"""
            SELECT subject_code, subject_name
            FROM assigned_subjects
            WHERE UPPER(TRIM(section))=UPPER(TRIM(%s))
              AND semester IN ({sem_placeholders})
              AND course_name IN ({course_placeholders})
              AND (
                %s=''
             OR UPPER(TRIM(COALESCE(department_name,'')))=UPPER(TRIM(%s))
              )
            ORDER BY subject_code, subject_name
        """

        params = [student_section] + sem_values + course_aliases + [student_department, student_department]
        cursor.execute(query, params)
        rows = cursor.fetchall()

        subjects = []
        seen = set()
        for row in rows:
            code = str(row[0] or "").strip()
            name = str(row[1] or "").strip()
            if not code and not name:
                continue

            pair = (code, name)
            if pair in seen:
                continue

            seen.add(pair)
            subjects.append(pair)

        return subjects

    def _fetch_progress_from_attendance_logs(cursor, enrollment_no, semester_text, student_profile):
        sem_values = _semester_values(semester_text)
        if not sem_values or not student_profile:
            return {}

        student_department = str(student_profile.get("department") or "").strip().upper()
        student_course = str(student_profile.get("course") or "").strip()
        student_section = str(student_profile.get("section") or "").strip().upper()
        if not student_course or not student_section:
            return {}

        course_aliases = get_course_aliases(student_course) or [student_course]
        course_aliases = [str(alias).strip() for alias in course_aliases if str(alias).strip()]
        if not course_aliases:
            course_aliases = [student_course]

        sem_placeholders = ",".join(["%s"] * len(sem_values))
        course_placeholders = ",".join(["%s"] * len(course_aliases))
        rows = []
        used_legacy_fallback = False
        try:
            cursor.execute(
                f"""
                SELECT subject_code,
                       subject_name,
                       '' AS class_name,
                       SUM(CASE WHEN enrollment_no=%s AND UPPER(COALESCE(status,''))='PRESENT' THEN 1 ELSE 0 END) AS present_count,
                       COUNT(DISTINCT attendance_date) AS total_count
                FROM attendance
                WHERE semester IN ({sem_placeholders})
                  AND UPPER(TRIM(section))=UPPER(TRIM(%s))
                  AND course IN ({course_placeholders})
                  AND (
                    %s=''
                 OR UPPER(TRIM(COALESCE(department,'')))=UPPER(TRIM(%s))
                  )
                  AND TRIM(COALESCE(subject_code,''))<>''
                GROUP BY subject_code, subject_name
                """,
                [enrollment_no] + sem_values + [student_section] + course_aliases + [student_department, student_department],
            )
            rows = cursor.fetchall()
        except Exception:
            # Backward compatibility: old attendance schema without subject_code/subject_name.
            try:
                used_legacy_fallback = True
                cursor.execute(
                    f"""
                    SELECT class_name,
                           SUM(CASE WHEN enrollment_no=%s AND UPPER(COALESCE(status,''))='PRESENT' THEN 1 ELSE 0 END) AS present_count,
                           COUNT(DISTINCT attendance_date) AS total_count
                    FROM attendance
                    WHERE semester IN ({sem_placeholders})
                      AND UPPER(TRIM(section))=UPPER(TRIM(%s))
                      AND course IN ({course_placeholders})
                      AND (
                        %s=''
                     OR UPPER(TRIM(COALESCE(department,'')))=UPPER(TRIM(%s))
                      )
                    GROUP BY class_name
                    """,
                    [enrollment_no] + sem_values + [student_section] + course_aliases + [student_department, student_department],
                )
                legacy_rows = cursor.fetchall()
                rows = [("", "", class_name, present_count, total_count) for class_name, present_count, total_count in legacy_rows]
            except Exception:
                return {}

        progress = {}

        def _add_metric(progress_key, present, total):
            if not progress_key:
                return
            if progress_key not in progress:
                progress[progress_key] = {"present": 0, "total": 0, "percent": 0}
            progress[progress_key]["present"] += present
            progress[progress_key]["total"] += total

        has_subject_specific_rows = False
        for subject_code, subject_name, class_name, present_count, total_count in rows:
            total = _safe_int(total_count, 0)
            present = _safe_int(present_count, 0)
            if total <= 0:
                continue

            code_key = _subject_key(subject_code)
            name_key = _subject_key(subject_name)

            if code_key or name_key:
                has_subject_specific_rows = True

            # Index each attendance aggregate row under multiple keys for resilient matching.
            row_keys = _build_subject_lookup_keys(subject_code, subject_name, class_name)
            for key in row_keys:
                _add_metric(key, present, total)

        if (used_legacy_fallback or not has_subject_specific_rows) and rows:
            total_present = 0
            total_classes = 0
            for _subject_code, _subject_name, _class_name, present_count, total_count in rows:
                total_present += _safe_int(present_count, 0)
                total_classes += _safe_int(total_count, 0)
            if total_classes > 0:
                progress["__SEM_DEFAULT__"] = {
                    "present": total_present,
                    "total": total_classes,
                    "percent": int(round((total_present / total_classes) * 100)),
                }

        # Finalize percentages after aggregated merges.
        for key, metric in progress.items():
            if key == "__SEM_DEFAULT__":
                continue
            total = _safe_int(metric.get("total"), 0)
            present = _safe_int(metric.get("present"), 0)
            metric["percent"] = int(round((present / total) * 100)) if total > 0 else 0

        return progress

    def _resolve_subject_progress(code, name, attendance_map):
        code_key = _subject_key(code)
        name_key = _subject_key(name)
        code_canon = _canonical_subject_key(code)
        name_canon = _canonical_subject_key(name)

        direct_keys = [
            code_key,
            name_key,
            f"CANON:{code_canon}" if code_canon else "",
            f"CANON:{name_canon}" if name_canon else "",
        ]

        for key in direct_keys:
            if key and key in attendance_map:
                return attendance_map[key], True

        for class_key, metric in attendance_map.items():
            if class_key.startswith("__"):
                continue
            if code_key and code_key in class_key:
                return metric, True
            if name_key and name_key in class_key:
                return metric, True
            if code_canon and f"CANON:{code_canon}" in class_key:
                return metric, True
            if name_canon and f"CANON:{name_canon}" in class_key:
                return metric, True

        if "__SEM_DEFAULT__" in attendance_map:
            return attendance_map["__SEM_DEFAULT__"], True

        return {"present": 0, "total": 0, "percent": 0}, False

    # ------------------ Autofill Enrollment ------------------
    try:
        resolved_enrollment = str(logged_in_enrollment or "").strip()
        if not resolved_enrollment:
            conn = open_db_connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT enrollment_no FROM users WHERE username=%s",
                (logged_in_username,)
            )
            row = cur.fetchone()
            cur.close()
            conn.close()
            if row and row[0]:
                resolved_enrollment = str(row[0]).strip()

        if resolved_enrollment:
            enrollment_entry.insert(0, resolved_enrollment)
            enrollment_entry.config(state="readonly")
    except:
        pass

    # ------------------ View ------------------
    def view_subjects():
        tree.delete(*tree.get_children())
        sem = semester_var.get().strip()
        enroll = enrollment_entry.get().strip()

        if not enroll:
            messagebox.showwarning("Input", "Enrollment number is required.")
            return

        if not sem:
            messagebox.showwarning("Input", "Semester is required.")
            return

        try:
            conn = open_db_connection()
            cur = conn.cursor()

            student_profile = _fetch_student_profile(cur, enroll)
            if not student_profile:
                messagebox.showinfo("No Data", "Student record not found.")
                cur.close()
                conn.close()
                return

            subjects = _fetch_subjects_for_semester(cur, enroll, sem)
            if not subjects:
                messagebox.showinfo("No Data", "No subjects found for selected semester.")
                cur.close()
                conn.close()
                return

            attendance_progress = _fetch_progress_from_attendance_logs(cur, enroll, sem, student_profile)

            cur.close()
            conn.close()

        except Exception as err:
            messagebox.showerror("Error", f"Unable to load course progress: {err}")
            return

        for code, name in subjects:
            metric, has_data = _resolve_subject_progress(code, name, attendance_progress)
            percent = int(metric.get("percent", 0))
            present = int(metric.get("present", 0))
            total = int(metric.get("total", 0))
            st = status_of(percent) if has_data else "No Data"

            blocks = int(percent / 10)
            bar = "█" * blocks + "░" * (10 - blocks)
            progress_text = f"{bar} {percent}% ({present}/{total})" if total > 0 else f"{bar} {percent}%"

            tree.insert(
                "",
                "end",
                values=(code, name, progress_text, st),
                tags=(st,)
            )

    view_btn.config(command=view_subjects)