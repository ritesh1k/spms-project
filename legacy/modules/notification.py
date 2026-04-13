import tkinter as tk
from tkinter import ttk, messagebox

from db_config import get_connection
from modules.course_aliases import course_matches, get_course_aliases


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


def _assignment_matches_student(course_name, semester, section, class_name, profile):
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
        class_parts = [p for p in class_text.split("-") if p]
        semester_in_class = _normalize_semester(class_parts[-2]) if len(class_parts) >= 2 else ""
        section_in_class = class_parts[-1] if len(class_parts) >= 1 else ""
        if student_sem and semester_in_class and student_sem != semester_in_class:
            return False
        if student_sec and section_in_class and student_sec != section_in_class:
            return False

    return True


def _fetch_student_subjects(enrollment):
    profile = _fetch_student_profile(enrollment)
    course_name = profile.get("course", "")
    semester = str(profile.get("semester", "")).strip()
    section = str(profile.get("section", "")).strip().upper()
    if not course_name or not semester:
        return set()

    course_aliases = get_course_aliases(course_name) or [course_name]
    placeholders = ",".join(["%s"] * len(course_aliases))

    try:
        conn = get_connection()
        cursor = conn.cursor()
        if section:
            cursor.execute(
                f"""
                SELECT DISTINCT LOWER(TRIM(COALESCE(NULLIF(subject_name, ''), '')))
                FROM assigned_subjects
                WHERE course_name IN ({placeholders})
                  AND TRIM(semester)=TRIM(%s)
                  AND UPPER(TRIM(section))=UPPER(TRIM(%s))
                """,
                (*course_aliases, semester, section),
            )
        else:
            cursor.execute(
                f"""
                SELECT DISTINCT LOWER(TRIM(COALESCE(NULLIF(subject_name, ''), '')))
                FROM assigned_subjects
                WHERE course_name IN ({placeholders})
                  AND TRIM(semester)=TRIM(%s)
                """,
                (*course_aliases, semester),
            )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return {str(row[0] or "").strip() for row in rows if row and row[0]}
    except Exception:
        return set()


def load_notification_module(content_frame, enrollment, bg="#f5f7fa"):
    tk.Label(content_frame, text="Notifications", font=("Arial", 16, "bold"), bg=bg, fg="#2c3e50").pack(anchor="w", pady=(0, 10))

    notif_tree = ttk.Treeview(content_frame, columns=("date", "type", "title", "message"), show="headings", height=18)
    for col, width in [("date", 145), ("type", 140), ("title", 260), ("message", 540)]:
        notif_tree.heading(col, text=col.title())
        notif_tree.column(col, width=width, anchor="w")
    notif_tree.pack(fill="both", expand=True)

    student_profile = _fetch_student_profile(enrollment)
    student_subjects = _fetch_student_subjects(enrollment)

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT DATE_FORMAT(created_at, '%Y-%m-%d %H:%i'),
                   COALESCE(course_name, ''),
                   COALESCE(semester, ''),
                   COALESCE(section, ''),
                   COALESCE(class_name, ''),
                   COALESCE(subject, ''),
                   title,
                   deadline,
                   COALESCE(teacher_username, ''),
                   COALESCE(material_path, '')
            FROM assignments
            ORDER BY id DESC
            LIMIT 150
            """
        )
        for row in cursor.fetchall():
            if not _assignment_matches_student(row[1], row[2], row[3], row[4], student_profile):
                continue
            course_text = str(row[1] or "").strip() or str(student_profile.get("course", "") or "").strip()
            sem_text = _normalize_semester(row[2]) if row[2] else _normalize_semester(student_profile.get("semester", ""))
            sec_text = str(row[3] or "").strip().upper() or str(student_profile.get("section", "") or "").strip().upper()
            subject_text = str(row[5] or "").strip()
            material_name = str(row[9] or "").strip().split("\\")[-1].split("/")[-1] if row[9] else "No material"
            message = (
                f"Subject: {subject_text or 'N/A'} | Teacher: {row[8]} | Due: {row[7]} | "
                f"Class: {course_text} Sem {sem_text} Sec {sec_text} | Material: {material_name}"
            )
            notif_tree.insert("", "end", values=(row[0], "Assignment", row[6], message))

        cursor.execute(
            """
            SELECT DATE_FORMAT(created_at, '%Y-%m-%d %H:%i'), title, message,
                   COALESCE(subject, ''), COALESCE(course_name, ''), COALESCE(semester, ''), COALESCE(section, '')
            FROM teacher_announcements
            ORDER BY id DESC
            LIMIT 100
            """
        )
        for row in cursor.fetchall():
            ann_subject = str(row[3] or "").strip()
            ann_course = str(row[4] or "").strip()
            ann_sem = _normalize_semester(row[5]) if row[5] else ""
            ann_sec = str(row[6] or "").strip().upper()

            if ann_course and not course_matches(ann_course, student_profile.get("course", "")):
                continue

            student_sem = _normalize_semester(student_profile.get("semester", ""))
            if ann_sem and student_sem and ann_sem != student_sem:
                continue

            student_sec = str(student_profile.get("section", "")).strip().upper()
            if ann_sec and student_sec and ann_sec != student_sec:
                continue

            if ann_subject and student_subjects and ann_subject.lower() not in student_subjects:
                continue

            title_text = row[1]
            if ann_subject:
                title_text = f"{title_text} [{ann_subject}]"
            notif_tree.insert("", "end", values=(row[0], "Announcement", title_text, row[2]))

        cursor.execute(
            """
            SELECT DATE_FORMAT(created_at, '%Y-%m-%d %H:%i'), title, message
            FROM admin_announcements
            ORDER BY id DESC
            LIMIT 100
            """
        )
        for row in cursor.fetchall():
            notif_tree.insert("", "end", values=(row[0], "Admin Announcement", row[1], row[2]))

        cursor.close()
        conn.close()
    except Exception as exc:
        messagebox.showerror("Notification Error", str(exc))
