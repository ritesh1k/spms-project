import tkinter as tk
from tkinter import ttk, messagebox

from db_config import get_connection
from modules.course_aliases import get_course_aliases


def _normalize_semester(value):
    sem_text = str(value or "").strip().upper()
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
    return sem_map.get(sem_text, sem_text)


def _fetch_student_profile(enrollment):
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
            "section": str(row[3] or "").strip().upper(),
        }
    except Exception:
        return {"department": "", "course": "", "semester": "", "section": ""}


def _fetch_subject_teacher_rows(enrollment):
    profile = _fetch_student_profile(enrollment)
    course_name = profile.get("course", "")
    semester = str(profile.get("semester", "")).strip()
    section = str(profile.get("section", "")).strip().upper()

    if not course_name or not semester:
        return [], profile

    sem_norm = _normalize_semester(semester)
    aliases = get_course_aliases(course_name) or [course_name]
    placeholders = ",".join(["%s"] * len(aliases))

    assigned_rows = []
    subject_rows = []
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT
                subject_id,
                COALESCE(NULLIF(subject_name, ''), 'General Subject') AS subject_name,
                COALESCE(NULLIF(teacher_name, ''), 'Not Assigned') AS teacher_name,
                COALESCE(NULLIF(teacher_username, ''), '') AS teacher_username,
                COALESCE(semester, ''),
                COALESCE(section, ''),
                updated_at,
                assigned_id
            FROM assigned_subjects
            WHERE course_name IN ({placeholders})
            ORDER BY updated_at DESC, assigned_id DESC
            """,
            (*aliases,),
        )
        assigned_rows = cursor.fetchall()

        cursor.execute(
            f"""
            SELECT s.subject_id, COALESCE(NULLIF(s.subject_name, ''), 'General Subject'), COALESCE(s.semester, '')
            FROM subjects s
            JOIN courses c ON c.course_id = s.course_id
            WHERE c.course_name IN ({placeholders})
              AND COALESCE(s.is_active, 1)=1
            ORDER BY s.subject_name
            """,
            (*aliases,),
        )
        subject_rows = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception:
        assigned_rows = []
        subject_rows = []

    def is_sem_match(raw_sem):
        return _normalize_semester(raw_sem) == sem_norm

    def row_score(row_section, teacher_name):
        exact_section = section and str(row_section or "").strip().upper() == section
        teacher_text = str(teacher_name or "").strip().lower()
        has_teacher = teacher_text not in {"", "not assigned", "n/a", "na"}
        return (0 if exact_section else 1, 0 if has_teacher else 1)

    best_by_id = {}
    best_by_name = {}
    for row in assigned_rows:
        sid, sname, tname, tuser, sem_raw, sec_raw = row[0], row[1], row[2], row[3], row[4], row[5]
        if not is_sem_match(sem_raw):
            continue
        score = row_score(sec_raw, tname)
        name_key = str(sname or "").strip().lower()

        if sid is not None:
            prev = best_by_id.get(sid)
            if prev is None or score < prev[0]:
                best_by_id[sid] = (score, row)
        if name_key:
            prev = best_by_name.get(name_key)
            if prev is None or score < prev[0]:
                best_by_name[name_key] = (score, row)

    resolved = []
    for sid, sname, sem_raw in subject_rows:
        if not is_sem_match(sem_raw):
            continue
        teacher_row = None
        if sid in best_by_id:
            teacher_row = best_by_id[sid][1]
        else:
            teacher_row = best_by_name.get(str(sname or "").strip().lower(), (None, None))[1]

        teacher_name = str(teacher_row[2] if teacher_row else "Not Assigned").strip() or "Not Assigned"
        teacher_username = str(teacher_row[3] if teacher_row else "").strip()
        resolved.append((sid, sname, teacher_name, teacher_username))

    if resolved:
        return resolved, profile

    # Final fallback from assigned subjects only when subject master data is unavailable.
    fallback = []
    seen = set()
    for _score, row in sorted(
        (
            (row_score(r[5], r[2]), r)
            for r in assigned_rows
            if is_sem_match(r[4])
        ),
        key=lambda item: item[0],
    ):
        sid, sname, tname, tuser = row[0], row[1], row[2], row[3]
        key = (sid, str(sname or "").strip().lower())
        if key in seen:
            continue
        seen.add(key)
        fallback.append((sid, sname, tname, tuser))

    return fallback, profile


def _build_session_summary(session_status, session_title_text, session_dt, duration_minutes, session_note):
    parts = []
    if str(session_status or "").strip():
        parts.append(str(session_status).strip())
    if str(session_title_text or "").strip():
        parts.append(str(session_title_text).strip())
    if session_dt:
        parts.append(session_dt.strftime("%Y-%m-%d %H:%M"))
    if duration_minutes:
        parts.append(f"{int(duration_minutes)} mins")
    if str(session_note or "").strip():
        parts.append(str(session_note).strip())
    return " | ".join(parts)


def load_query_doubt_module(content_frame, enrollment, bg="#f5f7fa"):
    tk.Label(content_frame, text="Ask Query / Doubt", font=("Arial", 16, "bold"), bg=bg, fg="#2c3e50").pack(anchor="w", pady=(0, 10))

    tk.Label(
        content_frame,
        text="Flow: choose subject + teacher -> write doubt -> submit -> see solution -> click solution for full popup.",
        bg=bg,
        fg="#475569",
        font=("Arial", 9, "bold"),
    ).pack(anchor="w", pady=(0, 8))

    form_card = tk.Frame(content_frame, bg="white", bd=1, relief="solid")
    form_card.pack(fill="x", pady=(0, 8))

    tk.Label(form_card, text="Submit New Doubt", bg="white", fg="#1f2937", font=("Arial", 12, "bold")).pack(anchor="w", padx=12, pady=(12, 8))

    subject_rows, profile = _fetch_subject_teacher_rows(enrollment)
    subject_options = []
    subject_map = {}

    for subject_id, subject_name, teacher_name, teacher_username in subject_rows:
        clean_subject = str(subject_name or "").strip()
        clean_teacher = str(teacher_name or "").strip() or "Not Assigned"
        display = f"{clean_subject}  |  Teacher: {clean_teacher}"
        if display in subject_map:
            continue
        subject_options.append(display)
        subject_map[display] = {
            "subject_id": subject_id,
            "subject_name": clean_subject,
            "teacher_name": clean_teacher,
            "teacher_username": str(teacher_username or "").strip(),
        }

    type_row = tk.Frame(form_card, bg="white")
    type_row.pack(fill="x", padx=12, pady=(0, 6))
    tk.Label(type_row, text="Doubt Type", bg="white", fg="#334155").pack(side="left")
    doubt_type = ttk.Combobox(type_row, state="readonly", values=["Concept Doubt", "Assignment Doubt", "Exam Doubt", "Project Doubt", "Other"], width=22)
    doubt_type.set("Concept Doubt")
    doubt_type.pack(side="left", padx=8)

    subject_row = tk.Frame(form_card, bg="white")
    subject_row.pack(fill="x", padx=12, pady=(0, 6))
    tk.Label(subject_row, text="Subject + Teacher", bg="white", fg="#334155").pack(side="left")
    doubt_subject = ttk.Combobox(subject_row, state="readonly", values=subject_options, width=70)
    if subject_options:
        doubt_subject.set(subject_options[0])
    doubt_subject.pack(side="left", padx=8, fill="x", expand=True)

    if not subject_options:
        tk.Label(
            form_card,
            text="No semester subjects are configured for your course/semester yet. Please contact admin.",
            bg="white",
            fg="#dc2626",
            font=("Arial", 10, "bold"),
        ).pack(anchor="w", padx=12, pady=(0, 8))

    tk.Label(form_card, text="Your Doubt / Query", bg="white", fg="#334155").pack(anchor="w", padx=12)
    doubt_box = tk.Text(form_card, height=5)
    doubt_box.pack(fill="x", padx=12, pady=(0, 8))

    button_row = tk.Frame(form_card, bg="white")
    button_row.pack(fill="x", padx=12, pady=(0, 12))

    list_card = tk.Frame(content_frame, bg="white", bd=1, relief="solid")
    list_card.pack(fill="both", expand=True)

    tk.Label(list_card, text="Your Doubts and Solutions", bg="white", fg="#1f2937", font=("Arial", 12, "bold")).pack(anchor="w", padx=12, pady=(12, 8))

    columns = ("id", "date", "subject", "teacher", "type", "status", "session", "received", "solved", "satisfied", "query", "solution")
    query_tree = ttk.Treeview(list_card, columns=columns, show="headings", height=12)
    for col, title, width, anchor in [
        ("id", "ID", 50, "center"),
        ("date", "Asked", 95, "center"),
        ("subject", "Subject", 140, "w"),
        ("teacher", "Teacher", 115, "w"),
        ("type", "Type", 115, "center"),
        ("status", "Status", 130, "center"),
        ("session", "Session", 220, "w"),
        ("received", "Received", 95, "center"),
        ("solved", "Solved", 95, "center"),
        ("satisfied", "Satisfied", 120, "center"),
        ("query", "Doubt", 180, "w"),
        ("solution", "Solution", 220, "w"),
    ]:
        query_tree.heading(col, text=title)
        query_tree.column(col, width=width, anchor=anchor)
    query_tree.pack(fill="both", expand=True, padx=12, pady=(0, 8))

    feedback_row = tk.Frame(list_card, bg="white")
    feedback_row.pack(fill="x", padx=12, pady=(0, 8))
    tk.Label(feedback_row, text="Satisfaction", bg="white", fg="#334155").pack(side="left")
    satisfaction_var = ttk.Combobox(feedback_row, state="readonly", values=["Yes", "No"], width=8)
    satisfaction_var.set("Yes")
    satisfaction_var.pack(side="left", padx=(8, 10))
    tk.Label(feedback_row, text="Feedback", bg="white", fg="#334155").pack(side="left")
    feedback_entry = tk.Entry(feedback_row)
    feedback_entry.pack(side="left", fill="x", expand=True, padx=8)

    selected_query = {"id": None, "status": ""}

    def refresh_query_rows():
        for item in query_tree.get_children():
            query_tree.delete(item)

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id,
                       DATE_FORMAT(created_at, '%Y-%m-%d'),
                       COALESCE(doubt_subject, ''),
                       COALESCE(teacher_username, ''),
                       COALESCE(query_type, ''),
                       COALESCE(status, 'Submitted'),
                       COALESCE(session_status, ''),
                       COALESCE(session_title, ''),
                       session_datetime,
                       session_duration_minutes,
                       COALESCE(session_note, ''),
                       DATE_FORMAT(teacher_received_at, '%Y-%m-%d'),
                       DATE_FORMAT(solved_at, '%Y-%m-%d'),
                       CASE
                           WHEN COALESCE(student_acknowledged, 0)=1 THEN 'Yes'
                           WHEN COALESCE(student_feedback, '') <> '' THEN student_feedback
                           ELSE 'Pending'
                       END,
                       query_text,
                       COALESCE(NULLIF(solution_text, ''), COALESCE(response, '')),
                       COALESCE(reopen_count, 0)
                FROM student_queries
                WHERE enrollment_no=%s
                ORDER BY id DESC
                """,
                (enrollment,),
            )
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
        except Exception as exc:
            messagebox.showerror("Query Error", str(exc))
            return

        for row in rows:
            session_summary = _build_session_summary(row[6], row[7], row[8], row[9], row[10])
            query_snippet = (str(row[14] or "")[:70] + "...") if len(str(row[14] or "")) > 70 else str(row[14] or "")
            solution_snippet = (str(row[15] or "")[:80] + "...") if len(str(row[15] or "")) > 80 else str(row[15] or "")
            display_values = (
                row[0], row[1], row[2], row[3], row[4], row[5], session_summary,
                row[11], row[12], row[13], query_snippet, solution_snippet,
            )
            query_tree.insert("", "end", values=display_values, tags=(str(row[16]),))

    def submit_doubt():
        if not subject_options:
            messagebox.showwarning("Subject", "No subject-teacher mapping found for your semester.")
            return

        selected_subject_display = doubt_subject.get().strip()
        selected_subject = subject_map.get(selected_subject_display, {})
        query_text = doubt_box.get("1.0", tk.END).strip()

        if not query_text:
            messagebox.showwarning("Input", "Please write your doubt message.")
            return

        teacher_username = selected_subject.get("teacher_username", "")
        subject_name = selected_subject.get("subject_name", "")

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO student_queries
                (enrollment_no, teacher_username, teacher_subject, query_type, doubt_subject, course_name, semester, section, query_text, status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'Submitted')
                """,
                (
                    enrollment,
                    teacher_username or None,
                    subject_name,
                    doubt_type.get().strip(),
                    subject_name,
                    profile.get("course", ""),
                    profile.get("semester", ""),
                    str(profile.get("section", "")).strip().upper(),
                    query_text,
                ),
            )
            conn.commit()
            cursor.close()
            conn.close()
            doubt_box.delete("1.0", tk.END)
            refresh_query_rows()
            messagebox.showinfo("Submitted", "Your doubt has been submitted successfully.")
        except Exception as exc:
            messagebox.showerror("Submit Error", str(exc))

    def on_select_query(_event=None):
        selected = query_tree.focus()
        if not selected:
            selected_query["id"] = None
            selected_query["status"] = ""
            return
        values = query_tree.item(selected, "values")
        selected_query["id"] = values[0]
        selected_query["status"] = str(values[5] or "")

    def open_solution_popup(qid):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COALESCE(query_text, ''), COALESCE(NULLIF(solution_text, ''), COALESCE(response, ''))
                FROM student_queries
                WHERE id=%s AND enrollment_no=%s
                LIMIT 1
                """,
                (qid, enrollment),
            )
            row = cursor.fetchone()
            cursor.close()
            conn.close()
        except Exception as exc:
            messagebox.showerror("Solution", str(exc))
            return

        if not row:
            messagebox.showwarning("Solution", "Could not load selected doubt details.")
            return

        query_text = str(row[0] or "").strip()
        solution_text = str(row[1] or "").strip()

        pop = tk.Toplevel(content_frame)
        pop.title(f"Doubt & Solution - Query ID {qid}")
        pop.geometry("760x520")
        pop.configure(bg="#f8fafc")

        tk.Label(pop, text="Your Doubt", bg="#f8fafc", fg="#1e293b", font=("Arial", 12, "bold")).pack(anchor="w", padx=12, pady=(12, 4))
        query_box = tk.Text(pop, height=9, wrap="word")
        query_box.pack(fill="x", padx=12)
        query_box.insert("1.0", query_text or "No doubt text found.")
        query_box.configure(state="disabled")

        tk.Label(pop, text="Teacher Solution", bg="#f8fafc", fg="#1e293b", font=("Arial", 12, "bold")).pack(anchor="w", padx=12, pady=(12, 4))
        solution_box = tk.Text(pop, height=12, wrap="word")
        solution_box.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        solution_box.insert("1.0", solution_text or "Solution not provided yet.")
        solution_box.configure(state="disabled")

        tk.Button(pop, text="Close", bg="#1d4ed8", fg="white", bd=0, padx=14, pady=6, command=pop.destroy).pack(pady=(0, 12))

    def on_tree_double_click(event):
        item_id = query_tree.identify_row(event.y)
        if not item_id:
            return
        col = query_tree.identify_column(event.x)
        if col != "#12":
            return
        values = query_tree.item(item_id, "values")
        if not values:
            return
        open_solution_popup(values[0])

    def mark_clarification_received():
        qid = selected_query.get("id")
        if not qid:
            messagebox.showwarning("Select", "Please select a solved query first.")
            return

        status = str(selected_query.get("status", "")).lower()
        if status not in {"solved", "clarification received", "session completed"}:
            messagebox.showwarning("Status", "Only solved doubts can be marked as clarification received.")
            return

        feedback_text = feedback_entry.get().strip()
        satisfied = 1 if satisfaction_var.get().strip().lower() == "yes" else 0
        feedback_value = "Satisfied" if satisfied == 1 else "Not Satisfied"
        if feedback_text:
            feedback_value = f"{feedback_value}: {feedback_text}"

        try:
            conn = get_connection()
            cursor = conn.cursor()
            if satisfied == 1:
                cursor.execute(
                    """
                    UPDATE student_queries
                    SET status='Clarification Received',
                        student_acknowledged=1,
                        student_received_at=NOW(),
                        student_feedback=%s
                    WHERE id=%s AND enrollment_no=%s
                    """,
                    (feedback_value, qid, enrollment),
                )
            else:
                cursor.execute(
                    "SELECT COALESCE(reopen_count, 0) FROM student_queries WHERE id=%s AND enrollment_no=%s",
                    (qid, enrollment),
                )
                row = cursor.fetchone()
                reopen_count = int(row[0] or 0) if row else 0
                next_reopen = reopen_count + 1
                requires_session = 1 if next_reopen >= 2 else 0
                next_status = "Session Required" if requires_session else "Reopened"
                cursor.execute(
                    """
                    UPDATE student_queries
                    SET status=%s,
                        reopen_count=%s,
                        requires_session=%s,
                        student_acknowledged=0,
                        student_received_at=NOW(),
                        student_feedback=%s
                    WHERE id=%s AND enrollment_no=%s
                    """,
                    (next_status, next_reopen, requires_session, feedback_value, qid, enrollment),
                )
            conn.commit()
            cursor.close()
            conn.close()
            feedback_entry.delete(0, tk.END)
            refresh_query_rows()
            if satisfied == 1:
                messagebox.showinfo("Updated", "Clarification received status updated.")
            else:
                messagebox.showinfo("Updated", "Doubt marked not satisfied. Teacher will resolve again. On second unresolved cycle, session scheduling is required.")
        except Exception as exc:
            messagebox.showerror("Update Error", str(exc))

    def ask_again_selected_query():
        qid = selected_query.get("id")
        if not qid:
            messagebox.showwarning("Select", "Please select a query first.")
            return
        status = str(selected_query.get("status", "")).strip().lower()
        if status not in {"solved", "clarification received", "session completed"}:
            messagebox.showwarning("Ask Again", "You can ask again only after the teacher has provided a solution or completed the session.")
            return
        followup = feedback_entry.get().strip()
        if not followup:
            messagebox.showwarning("Ask Again", "Write follow-up doubt in feedback box before asking again.")
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COALESCE(reopen_count,0) FROM student_queries WHERE id=%s AND enrollment_no=%s",
                (qid, enrollment),
            )
            row = cursor.fetchone()
            reopen_count = int(row[0] or 0) if row else 0
            next_reopen = reopen_count + 1
            requires_session = 1 if next_reopen >= 2 else 0
            next_status = "Session Required" if requires_session else "Reopened"
            cursor.execute(
                """
                UPDATE student_queries
                SET status=%s,
                    reopen_count=%s,
                    requires_session=%s,
                    student_acknowledged=0,
                    student_feedback=%s,
                    updated_at=NOW()
                WHERE id=%s AND enrollment_no=%s
                """,
                (next_status, next_reopen, requires_session, f"Follow-up: {followup}", qid, enrollment),
            )
            conn.commit()
            cursor.close()
            conn.close()
            feedback_entry.delete(0, tk.END)
            refresh_query_rows()
            messagebox.showinfo("Ask Again", "Follow-up doubt submitted to teacher.")
        except Exception as exc:
            messagebox.showerror("Ask Again", str(exc))

    submit_btn = tk.Button(
        button_row,
        text="Submit Doubt",
        font=("Arial", 10, "bold"),
        bg="#2563eb",
        fg="white",
        bd=0,
        padx=14,
        pady=6,
        command=submit_doubt,
        cursor="hand2",
        state="normal" if subject_options else "disabled",
    )
    submit_btn.pack(side="left")

    tk.Button(button_row, text="Refresh List", font=("Arial", 10, "bold"), bg="#64748b", fg="white", bd=0, padx=14, pady=6, command=refresh_query_rows, cursor="hand2").pack(side="left", padx=8)

    ack_row = tk.Frame(list_card, bg="white")
    ack_row.pack(fill="x", padx=12, pady=(0, 12))
    tk.Button(ack_row, text="Mark Clarification Received", font=("Arial", 10, "bold"), bg="#16a34a", fg="white", bd=0, padx=14, pady=6, command=mark_clarification_received, cursor="hand2").pack(side="left")
    tk.Button(ack_row, text="Ask Again", font=("Arial", 10, "bold"), bg="#2563eb", fg="white", bd=0, padx=14, pady=6, command=ask_again_selected_query, cursor="hand2").pack(side="left", padx=8)

    tk.Label(
        list_card,
        text="Tip: double-click any value in the Solution column to open full doubt and teacher solution.",
        bg="white",
        fg="#475569",
        font=("Arial", 9, "bold"),
    ).pack(anchor="w", padx=12, pady=(0, 10))

    query_tree.bind("<<TreeviewSelect>>", on_select_query)
    query_tree.bind("<Double-1>", on_tree_double_click)
    refresh_query_rows()
