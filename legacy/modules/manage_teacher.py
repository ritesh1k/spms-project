import tkinter as tk
from tkinter import ttk, messagebox
import re
from datetime import datetime, timedelta
from auth_utils import hash_password
from db_config import get_connection
from modules.course_aliases import canonical_course_name, get_course_aliases


def load_module(parent_frame, update_stats_callback=None):
    for widget in parent_frame.winfo_children():
        widget.destroy()
    parent_frame.configure(bg="#f5f7fa")

    def ensure_teacher_blacklist_columns():
        try:
            conn = get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("ALTER TABLE teachers ADD COLUMN status VARCHAR(20) DEFAULT 'Active'")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE teachers ADD COLUMN blacklist_until DATE NULL")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE teachers ADD COLUMN blacklist_reason TEXT NULL")
            except Exception:
                pass
            conn.commit()
            conn.close()
        except Exception:
            pass

    def ensure_teacher_course_column():
        try:
            conn = get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("ALTER TABLE teachers ADD COLUMN course VARCHAR(120) NULL")
            except Exception:
                pass
            conn.commit()
            conn.close()
        except Exception:
            pass

    ensure_teacher_blacklist_columns()
    ensure_teacher_course_column()

    title_frame = tk.Frame(parent_frame, bg="#3498db", height=60)
    title_frame.pack(fill="x")
    title_frame.pack_propagate(False)

    tk.Label(
        title_frame,
        text="👨‍🏫 Manage Teachers",
        font=("Segoe UI", 16, "bold"),
        bg="#3498db",
        fg="white",
    ).pack(side="left", padx=20, pady=12)

    blacklist_frame = tk.Frame(parent_frame, bg="white", bd=1, relief="solid")
    blacklist_visible = {"value": False}

    def toggle_blacklist_panel():
        if blacklist_visible["value"]:
            blacklist_frame.pack_forget()
            blacklist_visible["value"] = False
            blacklist_toggle_btn.config(text="⚫ Blacklist")
        else:
            blacklist_frame.pack(fill="x", padx=20, pady=(10, 0))
            blacklist_visible["value"] = True
            blacklist_toggle_btn.config(text="✖ Close Blacklist")

    blacklist_toggle_btn = tk.Button(
        title_frame,
        text="⚫ Blacklist",
        bg="#1abc9c",
        fg="white",
        font=("Segoe UI", 10, "bold"),
        bd=0,
        padx=14,
        pady=6,
        cursor="hand2",
        command=toggle_blacklist_panel,
    )
    blacklist_toggle_btn.pack(side="right", padx=20, pady=12)

    content_frame = tk.Frame(parent_frame, bg="#f5f7fa")
    content_frame.pack(fill="both", expand=True, padx=20, pady=20)

    filter_frame = tk.Frame(content_frame, bg="white", bd=1, relief="solid")
    filter_frame.pack(fill="x", padx=10, pady=(0, 10))

    filter_inner = tk.Frame(filter_frame, bg="white")
    filter_inner.pack(pady=8)

    tk.Label(filter_inner, text="Department:", bg="white").grid(row=0, column=0, padx=(8, 4), pady=5, sticky="w")
    department_entry = tk.Entry(filter_inner, width=18)
    department_entry.grid(row=0, column=1, padx=(0, 10), pady=5)

    tk.Label(filter_inner, text="Course:", bg="white").grid(row=0, column=2, padx=(8, 4), pady=5, sticky="w")
    course_entry = tk.Entry(filter_inner, width=18)
    course_entry.grid(row=0, column=3, padx=(0, 10), pady=5)

    tk.Label(filter_inner, text="Username:", bg="white").grid(row=1, column=0, padx=(8, 4), pady=5, sticky="w")
    username_entry = tk.Entry(filter_inner, width=18)
    username_entry.grid(row=1, column=1, padx=(0, 10), pady=5)

    list_frame = tk.Frame(content_frame, bg="white")
    list_frame.pack(fill="both", expand=True, padx=10, pady=10)

    columns = ("username", "full_name", "email", "phone", "department", "course", "designation", "dob", "date_of_joining")
    tree = ttk.Treeview(list_frame, columns=columns, show="headings")

    tree.heading("username", text="Username")
    tree.heading("full_name", text="Name")
    tree.heading("email", text="Email")
    tree.heading("phone", text="Phone")
    tree.heading("department", text="Department")
    tree.heading("course", text="Course")
    tree.heading("designation", text="Designation")
    tree.heading("dob", text="DOB")
    tree.heading("date_of_joining", text="Date Of Joining")

    tree.column("username", width=120, anchor="center")
    tree.column("full_name", width=150, anchor="center")
    tree.column("email", width=180, anchor="center")
    tree.column("phone", width=110, anchor="center")
    tree.column("department", width=130, anchor="center")
    tree.column("course", width=130, anchor="center")
    tree.column("designation", width=130, anchor="center")
    tree.column("dob", width=110, anchor="center")
    tree.column("date_of_joining", width=120, anchor="center")

    tree.pack(side="left", fill="both", expand=True)

    scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
    tree.configure(yscroll=scrollbar.set)
    scrollbar.pack(side="right", fill="y")

    blacklist_inner = tk.Frame(blacklist_frame, bg="white")
    blacklist_inner.pack(fill="x", padx=12, pady=10)

    tk.Label(blacklist_inner, text="Username:", bg="white").grid(row=0, column=0, padx=5, pady=5, sticky="w")
    bl_username_entry = tk.Entry(blacklist_inner, width=20)
    bl_username_entry.grid(row=0, column=1, padx=5, pady=5)

    tk.Label(blacklist_inner, text="Days:", bg="white").grid(row=0, column=2, padx=5, pady=5, sticky="w")
    bl_days_entry = tk.Entry(blacklist_inner, width=8)
    bl_days_entry.insert(0, "7")
    bl_days_entry.grid(row=0, column=3, padx=5, pady=5)

    tk.Label(blacklist_inner, text="Reason:", bg="white").grid(row=0, column=4, padx=5, pady=5, sticky="w")
    bl_reason_entry = tk.Entry(blacklist_inner, width=28)
    bl_reason_entry.grid(row=0, column=5, padx=5, pady=5)

    def fill_teacher_from_selected():
        selected = tree.focus()
        if not selected:
            messagebox.showwarning("Select Teacher", "Please select a teacher first.")
            return
        bl_username_entry.delete(0, tk.END)
        bl_username_entry.insert(0, selected)

    def apply_teacher_blacklist():
        username = bl_username_entry.get().strip()
        days_text = bl_days_entry.get().strip()
        reason = bl_reason_entry.get().strip()

        if not username:
            messagebox.showwarning("Input Error", "Username is required.")
            return
        if not days_text.isdigit() or int(days_text) <= 0:
            messagebox.showwarning("Input Error", "Days must be a positive number.")
            return

        until_date = (datetime.now().date() + timedelta(days=int(days_text)))
        reason_value = reason if reason else "Blacklisted by admin"

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM teachers WHERE username=%s AND role='teacher'", (username,))
            if not cursor.fetchone():
                conn.close()
                messagebox.showwarning("Not Found", "Teacher not found.")
                return

            cursor.execute(
                """
                UPDATE teachers
                SET status='Blacklisted', blacklist_until=%s, blacklist_reason=%s
                WHERE username=%s AND role='teacher'
                """,
                (until_date, reason_value, username),
            )
            conn.commit()
            conn.close()

            messagebox.showinfo("Success", f"Teacher blacklisted until {until_date}.")
            load_teachers(
                username_filter=username_entry.get().strip(),
                department_filter=department_entry.get().strip(),
                course_filter=course_entry.get().strip(),
            )
        except Exception as error:
            messagebox.showerror("Error", str(error))

    def remove_teacher_blacklist():
        username = bl_username_entry.get().strip()
        if not username:
            messagebox.showwarning("Input Error", "Username is required.")
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE teachers
                SET status='Active', blacklist_until=NULL, blacklist_reason=NULL
                WHERE username=%s AND role='teacher'
                """,
                (username,),
            )
            conn.commit()
            affected = cursor.rowcount
            conn.close()

            if affected == 0:
                messagebox.showwarning("Not Found", "Teacher not found.")
                return

            messagebox.showinfo("Success", "Teacher unblacklisted successfully.")
            load_teachers(
                username_filter=username_entry.get().strip(),
                department_filter=department_entry.get().strip(),
                course_filter=course_entry.get().strip(),
            )
        except Exception as error:
            messagebox.showerror("Error", str(error))

    tk.Button(blacklist_inner, text="Use Selected", bg="#95a5a6", fg="white", width=12, command=fill_teacher_from_selected).grid(row=1, column=0, columnspan=2, padx=5, pady=8)
    tk.Button(blacklist_inner, text="Apply Blacklist", bg="#c0392b", fg="white", width=14, command=apply_teacher_blacklist).grid(row=1, column=2, columnspan=2, padx=5, pady=8)
    tk.Button(blacklist_inner, text="Remove Blacklist", bg="#1abc9c", fg="white", width=14, command=remove_teacher_blacklist).grid(row=1, column=4, columnspan=2, padx=5, pady=8)

    def load_teachers(username_filter="", department_filter="", course_filter=""):
        for row in tree.get_children():
            tree.delete(row)

        conn = get_connection()
        cursor = conn.cursor()

        query = """
                 SELECT username, full_name, email, phone, department,
                     COALESCE(NULLIF(course,''), specialization, '') AS course_display,
                     designation, dob, date_of_joining
            FROM teachers
            WHERE role='teacher'
        """
        params = []

        if username_filter:
            query += " AND username=%s"
            params.append(username_filter)

        if department_filter:
            query += " AND department LIKE %s"
            params.append(f"%{department_filter}%")

        if course_filter:
            aliases = get_course_aliases(course_filter)
            placeholders = ",".join(["%s"] * len(aliases))
            query += f" AND (COALESCE(course,'') IN ({placeholders}) OR COALESCE(specialization,'') IN ({placeholders}))"
            params.extend(aliases)
            params.extend(aliases)

        cursor.execute(query, tuple(params))
        teachers = cursor.fetchall()
        conn.close()

        for teacher in teachers:
            tree.insert("", "end", iid=teacher[0], values=teacher)

        return teachers[0] if len(teachers) == 1 else None

    def search_teachers():
        teacher = load_teachers(
            username_filter=username_entry.get().strip(),
            department_filter=department_entry.get().strip(),
            course_filter=course_entry.get().strip(),
        )

        has_full_specific_filters = (
            bool(department_entry.get().strip())
            and bool(course_entry.get().strip())
            and bool(username_entry.get().strip())
        )

        if has_full_specific_filters and teacher:
            open_teacher_popup(teacher)

    tk.Button(
        filter_inner,
        text="Search",
        bg="#3498db",
        fg="white",
        font=("Segoe UI", 10, "bold"),
        command=search_teachers,
    ).grid(row=0, column=4, rowspan=2, padx=(12, 8), pady=8, sticky="ns")

    def open_teacher_popup(teacher_data):
        old_username = teacher_data[0]

        popup = tk.Toplevel(parent_frame)
        popup.title("Edit Teacher")
        popup.geometry("760x600")
        popup.resizable(False, False)
        popup.configure(bg="#f5f7fa")

        current_username = {"value": old_username}

        popup_container = tk.Frame(popup, bg="#f5f7fa")
        popup_container.pack(fill="both", expand=True, padx=16, pady=14)

        form_box = tk.Frame(popup_container, bg="white", bd=1, relief="solid")
        form_box.pack(anchor="center")

        field_opts = {"bg": "white", "font": ("Segoe UI", 10)}
        entry_width = 24

        tk.Label(form_box, text="Username:", **field_opts).grid(row=0, column=0, padx=(16, 6), pady=(12, 6), sticky="w")
        username_edit = tk.Entry(form_box, width=entry_width)
        username_edit.insert(0, teacher_data[0])
        username_edit.grid(row=0, column=1, padx=(0, 14), pady=(12, 6), sticky="w")

        tk.Label(form_box, text="Full Name:", **field_opts).grid(row=0, column=2, padx=(16, 6), pady=(12, 6), sticky="w")
        full_name_edit = tk.Entry(form_box, width=entry_width)
        full_name_edit.insert(0, teacher_data[1] or "")
        full_name_edit.grid(row=0, column=3, padx=(0, 16), pady=(12, 6), sticky="w")

        tk.Label(form_box, text="Email:", **field_opts).grid(row=1, column=0, padx=(16, 6), pady=6, sticky="w")
        email_edit = tk.Entry(form_box, width=entry_width)
        email_edit.insert(0, teacher_data[2] or "")
        email_edit.grid(row=1, column=1, padx=(0, 14), pady=6, sticky="w")

        tk.Label(form_box, text="Phone:", **field_opts).grid(row=1, column=2, padx=(16, 6), pady=6, sticky="w")
        phone_edit = tk.Entry(form_box, width=entry_width)
        phone_edit.insert(0, teacher_data[3] or "")
        phone_edit.grid(row=1, column=3, padx=(0, 16), pady=6, sticky="w")

        tk.Label(form_box, text="DOB (YYYY-MM-DD):", **field_opts).grid(row=2, column=0, padx=(16, 6), pady=6, sticky="w")
        dob_edit = tk.Entry(form_box, width=entry_width)
        dob_edit.insert(0, str(teacher_data[7]) if teacher_data[7] else "")
        dob_edit.grid(row=2, column=1, padx=(0, 14), pady=6, sticky="w")

        tk.Label(form_box, text="Gender:", **field_opts).grid(row=2, column=2, padx=(16, 6), pady=6, sticky="w")
        gender_var = tk.StringVar(value="Select")
        gender_dropdown = ttk.Combobox(form_box, textvariable=gender_var, state="readonly", width=entry_width - 2)
        gender_dropdown["values"] = ["Select", "Male", "Female", "Other"]
        gender_dropdown.grid(row=2, column=3, padx=(0, 16), pady=6, sticky="w")

        tk.Label(form_box, text="Department:", **field_opts).grid(row=3, column=0, padx=(16, 6), pady=6, sticky="w")
        department_edit = tk.Entry(form_box, width=entry_width)
        department_edit.insert(0, teacher_data[4] or "")
        department_edit.grid(row=3, column=1, padx=(0, 14), pady=6, sticky="w")

        tk.Label(form_box, text="Course:", **field_opts).grid(row=3, column=2, padx=(16, 6), pady=6, sticky="w")
        course_var = tk.StringVar(value=(canonical_course_name(teacher_data[5]) if teacher_data[5] else "Select"))
        course_edit = ttk.Combobox(form_box, textvariable=course_var, state="readonly", width=entry_width - 2)
        course_edit.grid(row=3, column=3, padx=(0, 16), pady=6, sticky="w")

        def load_courses_for_department(dept_name):
            if not dept_name:
                course_edit["values"] = ["Select"]
                course_var.set("Select")
                return

            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT department_id FROM departments WHERE department_name=%s", (dept_name,))
                dept_row = cursor.fetchone()

                if not dept_row:
                    conn.close()
                    course_edit["values"] = ["Select"]
                    course_var.set("Select")
                    return

                cursor.execute(
                    """
                    SELECT course_name FROM courses
                    WHERE department_id=%s AND is_active=1
                    ORDER BY course_name
                    """,
                    (dept_row[0],),
                )
                raw_courses = [row[0] for row in cursor.fetchall()]
                conn.close()

                canonical_courses = []
                for course_name in raw_courses:
                    display_name = canonical_course_name(course_name)
                    if display_name not in canonical_courses:
                        canonical_courses.append(display_name)

                options = ["Select"] + canonical_courses
                course_edit["values"] = options
                if course_var.get() not in options:
                    course_var.set("Select")
            except Exception:
                course_edit["values"] = ["Select"]
                if not course_var.get():
                    course_var.set("Select")

        load_courses_for_department(department_edit.get().strip())

        def refresh_courses_on_department_change(_event=None):
            load_courses_for_department(department_edit.get().strip())

        department_edit.bind("<FocusOut>", refresh_courses_on_department_change)

        tk.Label(form_box, text="Designation:", **field_opts).grid(row=4, column=0, padx=(16, 6), pady=6, sticky="w")
        designation_edit = tk.Entry(form_box, width=entry_width)
        designation_edit.insert(0, teacher_data[6] or "")
        designation_edit.grid(row=4, column=1, padx=(0, 14), pady=6, sticky="w")

        tk.Label(form_box, text="Qualification:", **field_opts).grid(row=4, column=2, padx=(16, 6), pady=6, sticky="w")
        qualification_edit = tk.Entry(form_box, width=entry_width)
        qualification_edit.grid(row=4, column=3, padx=(0, 16), pady=6, sticky="w")

        tk.Label(form_box, text="Specialization:", **field_opts).grid(row=5, column=0, padx=(16, 6), pady=6, sticky="w")
        specialization_edit = tk.Entry(form_box, width=entry_width)
        specialization_edit.grid(row=5, column=1, padx=(0, 14), pady=6, sticky="w")

        tk.Label(form_box, text="Experience (Years):", **field_opts).grid(row=5, column=2, padx=(16, 6), pady=6, sticky="w")
        experience_edit = tk.Entry(form_box, width=entry_width)
        experience_edit.grid(row=5, column=3, padx=(0, 16), pady=6, sticky="w")

        tk.Label(form_box, text="Date of Joining (YYYY-MM-DD):", **field_opts).grid(row=6, column=0, padx=(16, 6), pady=6, sticky="w")
        doj_edit = tk.Entry(form_box, width=entry_width)
        doj_edit.insert(0, str(teacher_data[8]) if teacher_data[8] else "")
        doj_edit.grid(row=6, column=1, padx=(0, 14), pady=6, sticky="w")

        tk.Label(form_box, text="Address:", **field_opts).grid(row=6, column=2, padx=(16, 6), pady=6, sticky="w")
        address_edit = tk.Entry(form_box, width=entry_width)
        address_edit.grid(row=6, column=3, padx=(0, 16), pady=6, sticky="w")

        tk.Label(form_box, text="Security Question:", **field_opts).grid(row=7, column=0, padx=(16, 6), pady=6, sticky="w")
        question_edit = tk.Entry(form_box, width=entry_width)
        question_edit.grid(row=7, column=1, padx=(0, 14), pady=6, sticky="w")

        tk.Label(form_box, text="Security Answer:", **field_opts).grid(row=7, column=2, padx=(16, 6), pady=(6, 12), sticky="w")
        answer_edit = tk.Entry(form_box, width=(entry_width * 2) + 10)
        answer_edit.grid(row=7, column=3, padx=(0, 16), pady=(6, 12), sticky="w")

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT gender, qualification, specialization, experience_years, address
                FROM teachers WHERE username=%s AND role='teacher'
                """,
                (old_username,),
            )
            extra_teacher_data = cursor.fetchone()
            cursor.execute(
                """
                SELECT security_question, security_answer
                FROM users WHERE username=%s AND role='teacher'
                """,
                (old_username,),
            )
            user_data = cursor.fetchone()
            conn.close()

            if extra_teacher_data:
                gender_var.set(extra_teacher_data[0] if extra_teacher_data[0] else "Select")
                qualification_edit.insert(0, extra_teacher_data[1] or "")
                specialization_edit.insert(0, extra_teacher_data[2] or "")
                experience_edit.insert(0, str(extra_teacher_data[3]) if extra_teacher_data[3] is not None else "")
                address_edit.insert(0, extra_teacher_data[4] or "")

            if user_data:
                question_edit.insert(0, user_data[0] or "")
                answer_edit.insert(0, user_data[1] or "")
        except Exception:
            pass

        btn_frame = tk.Frame(popup_container, bg="#f5f7fa")
        btn_frame.pack(pady=12)

        def update_teacher():
            new_username = username_edit.get().strip()
            new_full_name = full_name_edit.get().strip()
            new_email = email_edit.get().strip()
            new_phone = phone_edit.get().strip()
            new_dob = dob_edit.get().strip()
            new_gender = gender_var.get().strip()
            new_department = department_edit.get().strip()
            new_course = course_var.get().strip()
            new_designation = designation_edit.get().strip()
            new_qualification = qualification_edit.get().strip()
            new_specialization = specialization_edit.get().strip()
            new_experience = experience_edit.get().strip()
            new_doj = doj_edit.get().strip()
            new_address = address_edit.get().strip()
            new_question = question_edit.get().strip()
            new_answer = answer_edit.get().strip()

            if not all([
                new_username,
                new_full_name,
                new_email,
                new_phone,
                new_dob,
                new_department,
                new_course,
                new_designation,
                new_qualification,
                new_experience,
                new_doj,
                new_address,
                new_question,
                new_answer,
            ]) or new_gender == "Select":
                messagebox.showwarning("Input Error", "All fields are required.")
                return

            if not re.match(r"[^@]+@[^@]+\.[^@]+", new_email):
                messagebox.showwarning("Input Error", "Enter a valid email address.")
                return

            if not new_phone.isdigit() or len(new_phone) != 10:
                messagebox.showwarning("Input Error", "Phone number must be 10 digits.")
                return

            if not re.match(r"\d{4}-\d{2}-\d{2}$", new_dob):
                messagebox.showwarning("Input Error", "DOB must be in YYYY-MM-DD format.")
                return

            if not re.match(r"\d{4}-\d{2}-\d{2}$", new_doj):
                messagebox.showwarning("Input Error", "Date of Joining must be in YYYY-MM-DD format.")
                return

            if not new_experience.isdigit() or int(new_experience) < 0:
                messagebox.showwarning("Input Error", "Experience must be a non-negative number.")
                return

            try:
                conn = get_connection()
                cursor = conn.cursor()

                if new_username != current_username["value"]:
                    cursor.execute("SELECT username FROM users WHERE username=%s", (new_username,))
                    if cursor.fetchone():
                        conn.close()
                        messagebox.showwarning("Duplicate", "This username already exists.")
                        return

                cursor.execute(
                    "SELECT teacher_id FROM teachers WHERE (username=%s OR email=%s) AND username<>%s",
                    (new_username, new_email, current_username["value"]),
                )
                if cursor.fetchone():
                    conn.close()
                    messagebox.showwarning("Duplicate", "Teacher username or email already exists.")
                    return

                cursor.execute(
                    """
                    UPDATE teachers
                    SET username=%s, full_name=%s, email=%s, phone=%s, dob=%s, gender=%s,
                        department=%s, course=%s, designation=%s, qualification=%s, specialization=%s,
                        experience_years=%s, date_of_joining=%s, address=%s
                    WHERE username=%s AND role='teacher'
                    """,
                    (
                        new_username,
                        new_full_name,
                        new_email,
                        new_phone,
                        new_dob,
                        new_gender,
                        new_department,
                        new_course,
                        new_designation,
                        new_qualification,
                        new_specialization,
                        int(new_experience),
                        new_doj,
                        new_address,
                        current_username["value"],
                    ),
                )

                cursor.execute(
                    """
                    UPDATE users
                    SET username=%s, email=%s, mobile=%s, security_question=%s, security_answer=%s
                    WHERE username=%s AND role='teacher'
                    """,
                    (new_username, new_email, new_phone, new_question, new_answer, current_username["value"]),
                )
                conn.commit()
                conn.close()

                current_username["value"] = new_username

                messagebox.showinfo("Success", "Teacher updated successfully!")
                popup.destroy()
                load_teachers(
                    username_filter=username_entry.get().strip(),
                    department_filter=department_entry.get().strip(),
                    course_filter=course_entry.get().strip(),
                )
                if update_stats_callback:
                    update_stats_callback()

            except Exception as error:
                messagebox.showerror("Error", str(error))

        def delete_teacher():
            confirm = messagebox.askyesno("Confirm Delete", f"Do you really want to delete {current_username['value']}?")
            if not confirm:
                return

            try:
                conn = get_connection()
                cursor = conn.cursor()
                current_email = email_edit.get().strip()
                cursor.execute("DELETE FROM teachers WHERE username=%s AND role='teacher'", (current_username["value"],))
                cursor.execute(
                    "DELETE FROM users WHERE role='teacher' AND (username=%s OR email=%s)",
                    (current_username["value"], current_email),
                )
                conn.commit()
                conn.close()

                messagebox.showinfo("Deleted", "Teacher deleted successfully!")
                popup.destroy()
                load_teachers(
                    username_filter=username_entry.get().strip(),
                    department_filter=department_entry.get().strip(),
                    course_filter=course_entry.get().strip(),
                )
                if update_stats_callback:
                    update_stats_callback()

            except Exception as error:
                messagebox.showerror("Error", str(error))

        def reset_teacher_password():
            reset_popup = tk.Toplevel(popup)
            reset_popup.title("Reset Teacher Password")
            reset_popup.geometry("360x220")
            reset_popup.configure(bg="#f5f7fa")

            tk.Label(reset_popup, text=f"Username: {current_username['value']}", bg="#f5f7fa", font=("Segoe UI", 10, "bold")).pack(
                anchor="w", padx=20, pady=(15, 5)
            )

            tk.Label(reset_popup, text="New Password:", bg="#f5f7fa").pack(anchor="w", padx=20, pady=(8, 0))
            new_password_entry = tk.Entry(reset_popup, show="*")
            new_password_entry.pack(fill="x", padx=20)

            tk.Label(reset_popup, text="Confirm Password:", bg="#f5f7fa").pack(anchor="w", padx=20, pady=(8, 0))
            confirm_password_entry = tk.Entry(reset_popup, show="*")
            confirm_password_entry.pack(fill="x", padx=20)

            def save_new_password():
                new_password = new_password_entry.get().strip()
                confirm_password = confirm_password_entry.get().strip()

                if not new_password or not confirm_password:
                    messagebox.showwarning("Input Error", "Both password fields are required.")
                    return

                if new_password != confirm_password:
                    messagebox.showwarning("Input Error", "Passwords do not match.")
                    return

                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE users SET password=%s WHERE username=%s AND role='teacher'",
                        (hash_password(new_password), current_username["value"]),
                    )
                    conn.commit()
                    affected_rows = cursor.rowcount
                    conn.close()

                    if affected_rows == 0:
                        messagebox.showwarning("Not Found", "No teacher login account found for this username.")
                        return

                    messagebox.showinfo("Success", "Teacher password reset successfully!")
                    reset_popup.destroy()
                except Exception as error:
                    messagebox.showerror("Error", str(error))

            tk.Button(
                reset_popup,
                text="Reset Password",
                bg="#3498db",
                fg="white",
                width=16,
                command=save_new_password,
            ).pack(pady=15)

        tk.Button(btn_frame, text="Update", bg="#1abc9c", fg="white", width=12, command=update_teacher).pack(side="left", padx=10)
        tk.Button(btn_frame, text="Delete", bg="#c0392b", fg="white", width=12, command=delete_teacher).pack(side="left", padx=10)
        tk.Button(btn_frame, text="Reset Password", bg="#3498db", fg="white", width=14, command=reset_teacher_password).pack(side="left", padx=10)
        tk.Button(btn_frame, text="Exit", bg="#95a5a6", fg="white", width=10, command=popup.destroy).pack(side="left", padx=10)

    def open_selected(event):
        selected = tree.focus()
        if selected:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                  SELECT username, full_name, email, phone, department,
                      COALESCE(NULLIF(course,''), specialization, '') AS course_display,
                      designation, dob, date_of_joining
                FROM teachers WHERE username=%s AND role='teacher'
                """,
                (selected,),
            )
            teacher = cursor.fetchone()
            conn.close()
            if teacher:
                open_teacher_popup(teacher)

    tree.bind("<Double-1>", open_selected)

    load_teachers()
