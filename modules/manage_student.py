import tkinter as tk
from tkinter import ttk, messagebox
from auth_utils import hash_password
from db_config import get_connection
from datetime import datetime, timedelta
from modules.course_aliases import canonical_course_name, get_course_aliases

def load_module(parent_frame, update_stats_callback=None):
    """
    parent_frame: Tkinter frame where module will be loaded
    update_stats_callback: callback to refresh total students in admin dashboard
    """
    # Clear previous content
    for widget in parent_frame.winfo_children():
        widget.destroy()
    parent_frame.configure(bg="#f5f7fa")

    def ensure_student_blacklist_columns():
        try:
            conn = get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("ALTER TABLE students ADD COLUMN status VARCHAR(20) DEFAULT 'Active'")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE students ADD COLUMN blacklist_until DATE NULL")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE students ADD COLUMN blacklist_reason TEXT NULL")
            except Exception:
                pass
            conn.commit()
            conn.close()
        except Exception:
            pass

    ensure_student_blacklist_columns()

    # ---------- Title ----------
    title_frame = tk.Frame(parent_frame, bg="#9b59b6", height=60)
    title_frame.pack(fill="x")
    title_frame.pack_propagate(False)

    tk.Label(
        title_frame,
        text="🎓 Manage Students",
        font=("Segoe UI", 16, "bold"),
        bg="#9b59b6",
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

    # ---------- Filters ----------
    filter_frame = tk.Frame(content_frame, bg="white", bd=1, relief="solid")
    filter_frame.pack(fill="x", padx=10, pady=(0, 10))

    filter_inner = tk.Frame(filter_frame, bg="white")
    filter_inner.pack(pady=8)

    tk.Label(filter_inner, text="Department:", bg="white").grid(row=0, column=0, padx=(8, 4), pady=5, sticky="w")
    dept_var = tk.StringVar(value="Select")
    dept_dropdown = ttk.Combobox(filter_inner, textvariable=dept_var, state="readonly", width=18)
    dept_dropdown['values'] = ["Select", "Computer Science", "Medical"]
    dept_dropdown.grid(row=0, column=1, padx=(0, 10), pady=5)

    tk.Label(filter_inner, text="Course:", bg="white").grid(row=0, column=2, padx=(8, 4), pady=5, sticky="w")
    course_var = tk.StringVar(value="Select")
    course_dropdown = ttk.Combobox(filter_inner, textvariable=course_var, state="readonly", width=18)
    course_dropdown.grid(row=0, column=3, padx=(0, 10), pady=5)

    tk.Label(filter_inner, text="Semester:", bg="white").grid(row=1, column=0, padx=(8, 4), pady=5, sticky="w")
    sem_var = tk.StringVar(value="Select")
    sem_dropdown = ttk.Combobox(filter_inner, textvariable=sem_var, state="readonly", width=18)
    sem_dropdown['values'] = ["Select", "I","II","III","IV","V","VI"]
    sem_dropdown.grid(row=1, column=1, padx=(0, 10), pady=5)

    tk.Label(filter_inner, text="Section:", bg="white").grid(row=1, column=2, padx=(8, 4), pady=5, sticky="w")
    section_filter_var = tk.StringVar(value="Select")
    section_filter_dropdown = ttk.Combobox(filter_inner, textvariable=section_filter_var, state="readonly", width=18)
    section_filter_dropdown['values'] = ["Select", "A", "B", "C", "D", "E", "F", "G", "H", "I"]
    section_filter_dropdown.grid(row=1, column=3, padx=(0, 10), pady=5)

    tk.Label(filter_inner, text="Enrollment No:", bg="white").grid(row=1, column=4, padx=(8, 4), pady=5, sticky="w")
    enroll_entry = tk.Entry(filter_inner, width=20)
    enroll_entry.grid(row=1, column=5, padx=(0, 10), pady=5)

    # Update courses based on department
    def update_courses(event=None):
        dept = dept_var.get()
        if dept == "Select":
            course_dropdown['values'] = ["Select"]
            course_dropdown.current(0)
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT department_id FROM departments WHERE department_name=%s", (dept,))
            dept_row = cursor.fetchone()

            if not dept_row:
                conn.close()
                course_dropdown['values'] = ["Select"]
                course_dropdown.current(0)
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

            course_dropdown['values'] = ["Select"] + canonical_courses
            course_dropdown.current(0)
        except Exception:
            course_dropdown['values'] = ["Select"]
            course_dropdown.current(0)
    dept_dropdown.bind("<<ComboboxSelected>>", update_courses)
    update_courses()

    # ---------- Search Button ----------
    def search_students():
        student = load_students(
            dept_filter=dept_var.get(),
            course_filter=course_var.get(),
            sem_filter=sem_var.get(),
            section_filter=section_filter_var.get(),
            enroll_filter=enroll_entry.get().strip()
        )

        has_full_specific_filters = (
            dept_var.get() != "Select"
            and course_var.get() != "Select"
            and sem_var.get() != "Select"
            and section_filter_var.get() != "Select"
            and bool(enroll_entry.get().strip())
        )

        if has_full_specific_filters and student:
            open_student_popup(student)

    tk.Button(filter_inner, text="Search", bg="#3498db", fg="white", font=("Segoe UI", 10, "bold"),
              command=search_students).grid(row=0, column=6, rowspan=2, padx=(12, 8), pady=8, sticky="ns")

    # ---------- Student List ----------
    list_frame = tk.Frame(content_frame, bg="white")
    list_frame.pack(fill="both", expand=True, padx=10, pady=10)

    columns = ("enroll", "name", "section", "dob", "email", "phone", "course", "semester", "department", "status")
    tree = ttk.Treeview(list_frame, columns=columns, show="headings")
    for col in columns:
        tree.heading(col, text=col.capitalize())
        if col == "status":
            tree.column(col, width=100, anchor="center")
        else:
            tree.column(col, width=120, anchor="center")

    tree.pack(side="left", fill="both", expand=True)

    # Scrollbar
    scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
    tree.configure(yscroll=scrollbar.set)
    scrollbar.pack(side="right", fill="y")

    blacklist_inner = tk.Frame(blacklist_frame, bg="white")
    blacklist_inner.pack(fill="x", padx=12, pady=10)

    tk.Label(blacklist_inner, text="Enrollment:", bg="white").grid(row=0, column=0, padx=5, pady=5, sticky="w")
    bl_enroll_entry = tk.Entry(blacklist_inner, width=20)
    bl_enroll_entry.grid(row=0, column=1, padx=5, pady=5)

    tk.Label(blacklist_inner, text="Days:", bg="white").grid(row=0, column=2, padx=5, pady=5, sticky="w")
    bl_days_entry = tk.Entry(blacklist_inner, width=8)
    bl_days_entry.insert(0, "7")
    bl_days_entry.grid(row=0, column=3, padx=5, pady=5)

    tk.Label(blacklist_inner, text="Reason:", bg="white").grid(row=0, column=4, padx=5, pady=5, sticky="w")
    bl_reason_entry = tk.Entry(blacklist_inner, width=28)
    bl_reason_entry.grid(row=0, column=5, padx=5, pady=5)

    def fill_student_from_selected():
        selected = tree.focus()
        if not selected:
            messagebox.showwarning("Select Student", "Please select a student first.")
            return
        bl_enroll_entry.delete(0, tk.END)
        bl_enroll_entry.insert(0, selected)

    def apply_student_blacklist():
        enrollment = bl_enroll_entry.get().strip()
        days_text = bl_days_entry.get().strip()
        reason = bl_reason_entry.get().strip()

        if not enrollment:
            messagebox.showwarning("Input Error", "Enrollment is required.")
            return
        if not days_text.isdigit() or int(days_text) <= 0:
            messagebox.showwarning("Input Error", "Days must be a positive number.")
            return

        until_date = (datetime.now().date() + timedelta(days=int(days_text)))
        reason_value = reason if reason else "Blacklisted by admin"

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT enrollment_no FROM students WHERE enrollment_no=%s", (enrollment,))
            if not cursor.fetchone():
                conn.close()
                messagebox.showwarning("Not Found", "Student not found.")
                return

            cursor.execute(
                """
                UPDATE students
                SET status='Blacklisted', blacklist_until=%s, blacklist_reason=%s
                WHERE enrollment_no=%s
                """,
                (until_date, reason_value, enrollment),
            )
            conn.commit()
            conn.close()

            messagebox.showinfo("Success", f"Student blacklisted until {until_date}.")
            load_students(
                dept_filter=dept_var.get(),
                course_filter=course_var.get(),
                sem_filter=sem_var.get(),
                section_filter=section_filter_var.get(),
                enroll_filter=enroll_entry.get().strip(),
            )
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def remove_student_blacklist():
        enrollment = bl_enroll_entry.get().strip()
        if not enrollment:
            messagebox.showwarning("Input Error", "Enrollment is required.")
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE students
                SET status='Active', blacklist_until=NULL, blacklist_reason=NULL
                WHERE enrollment_no=%s
                """,
                (enrollment,),
            )
            conn.commit()
            affected = cursor.rowcount
            conn.close()

            if affected == 0:
                messagebox.showwarning("Not Found", "Student not found.")
                return

            messagebox.showinfo("Success", "Student unblacklisted successfully.")
            load_students(
                dept_filter=dept_var.get(),
                course_filter=course_var.get(),
                sem_filter=sem_var.get(),
                section_filter=section_filter_var.get(),
                enroll_filter=enroll_entry.get().strip(),
            )
        except Exception as e:
            messagebox.showerror("Error", str(e))

    tk.Button(blacklist_inner, text="Use Selected", bg="#95a5a6", fg="white", width=12, command=fill_student_from_selected).grid(row=1, column=0, columnspan=2, padx=5, pady=8)
    tk.Button(blacklist_inner, text="Apply Blacklist", bg="#c0392b", fg="white", width=14, command=apply_student_blacklist).grid(row=1, column=2, columnspan=2, padx=5, pady=8)
    tk.Button(blacklist_inner, text="Remove Blacklist", bg="#1abc9c", fg="white", width=14, command=remove_student_blacklist).grid(row=1, column=4, columnspan=2, padx=5, pady=8)

    # ---------- Load Students ----------
    def load_students(dept_filter="Select", course_filter="Select", sem_filter="Select", section_filter="Select", enroll_filter=""):
        for row in tree.get_children():
            tree.delete(row)
        conn = get_connection()
        cursor = conn.cursor()
        query = """SELECT name, enrollment_no, department, course, semester, section, dob, email, phone, 
                          status, blacklist_until
                   FROM students WHERE 1=1"""
        params = []
        if dept_filter != "Select":
            query += " AND department=%s"
            params.append(dept_filter)
        if course_filter != "Select":
            aliases = get_course_aliases(course_filter)
            query += " AND course IN ({})".format(",".join(["%s"] * len(aliases)))
            params.extend(aliases)
        if sem_filter != "Select":
            query += " AND semester=%s"
            params.append(sem_filter)
        if section_filter != "Select":
            query += " AND section=%s"
            params.append(section_filter)
        if enroll_filter:
            query += " AND enrollment_no=%s"
            params.append(enroll_filter)
        cursor.execute(query, tuple(params))
        students = cursor.fetchall()
        for s in students:
            # Determine display status
            status = s[9] if s[9] else "Active"
            if s[10]:  # blacklist_until exists
                blacklist_date = s[10] if isinstance(s[10], datetime) else datetime.strptime(str(s[10]), '%Y-%m-%d')
                if blacklist_date.date() >= datetime.now().date():
                    status = "Blacklisted"
                else:
                    status = "Active"  # Blacklist expired
            tree.insert("", "end", iid=s[1], values=(s[1], s[0], s[5], s[6], s[7], s[8], s[3], s[4], s[2], status))
        conn.close()
        # return first student if only one found
        return students[0] if len(students)==1 else None

    load_students()

    # ---------- Student Popup for Update/Delete ----------
    def open_student_popup(student_data):
        enrollment_no = student_data[1]
        popup = tk.Toplevel(parent_frame)
        popup.title("Edit Student")
        popup.geometry("760x680")
        popup.resizable(False, False)
        popup.configure(bg="#f5f7fa")

        fields = ["Name", "Enrollment No", "Department", "Course", "Semester", "Section", "DOB", "Email", "Phone"]
        entries = {}

        popup_container = tk.Frame(popup, bg="#f5f7fa")
        popup_container.pack(fill="both", expand=True, padx=16, pady=14)

        form_box = tk.Frame(popup_container, bg="white", bd=1, relief="solid")
        form_box.pack(anchor="center")

        # Name
        tk.Label(form_box, text="Name:", bg="white").grid(row=0, column=0, padx=(16, 6), pady=(12, 6), sticky="w")
        name_entry = tk.Entry(form_box, width=24)
        name_entry.insert(0, student_data[0])
        name_entry.grid(row=0, column=1, padx=(0, 14), pady=(12, 6), sticky="w")
        entries["name"] = name_entry

        # Enrollment
        tk.Label(form_box, text="Enrollment No:", bg="white").grid(row=0, column=2, padx=(16, 6), pady=(12, 6), sticky="w")
        enroll_entry_popup = tk.Entry(form_box, width=24)
        enroll_entry_popup.insert(0, student_data[1])
        enroll_entry_popup.grid(row=0, column=3, padx=(0, 16), pady=(12, 6), sticky="w")
        entries["enrollment_no"] = enroll_entry_popup

        # Department
        tk.Label(form_box, text="Department:", bg="white").grid(row=1, column=0, padx=(16, 6), pady=6, sticky="w")
        dept_var_popup = tk.StringVar(value=student_data[2])
        dept_dropdown = ttk.Combobox(form_box, textvariable=dept_var_popup, state="readonly", width=22)
        dept_dropdown['values'] = ["Computer Science", "Medical"]
        dept_dropdown.grid(row=1, column=1, padx=(0, 14), pady=6, sticky="w")
        entries["department"] = dept_dropdown

        # Course
        tk.Label(form_box, text="Course:", bg="white").grid(row=1, column=2, padx=(16, 6), pady=6, sticky="w")
        course_var_popup = tk.StringVar(value=student_data[3])
        course_dropdown = ttk.Combobox(form_box, textvariable=course_var_popup, state="readonly", width=22)
        courses_dict_popup = {
            "Computer Science": [
                "B.Tech", "Bachelor of Technology",
                "BCA", "Bachelor of Computer Application",
                "MCA", "Master of Computer Application",
                "M.Tech", "Master of Technology",
            ],
            "Medical": ["Nursing", "MBBS", "Dental", "Psychotherapy"]
        }
        course_dropdown['values'] = courses_dict_popup.get(student_data[2], [])
        course_dropdown.grid(row=1, column=3, padx=(0, 16), pady=6, sticky="w")
        entries["course"] = course_dropdown

        # Semester
        tk.Label(form_box, text="Semester:", bg="white").grid(row=2, column=0, padx=(16, 6), pady=6, sticky="w")
        sem_var_popup = tk.StringVar(value=student_data[4])
        sem_dropdown = ttk.Combobox(form_box, textvariable=sem_var_popup, state="readonly", width=22)
        sem_dropdown['values'] = ["I","II","III","IV","V","VI"]
        sem_dropdown.grid(row=2, column=1, padx=(0, 14), pady=6, sticky="w")
        entries["semester"] = sem_dropdown

        # Section
        tk.Label(form_box, text="Section:", bg="white").grid(row=2, column=2, padx=(16, 6), pady=6, sticky="w")
        section_var_popup = tk.StringVar(value=student_data[5])
        section_dropdown = ttk.Combobox(form_box, textvariable=section_var_popup, state="readonly", width=22)
        section_dropdown['values'] = ["A","B","C","D","E","F","G","H","I"]
        section_dropdown.grid(row=2, column=3, padx=(0, 16), pady=6, sticky="w")
        entries["section"] = section_dropdown

        def update_popup_courses(event=None):
            selected_dept = dept_var_popup.get()
            available_courses = courses_dict_popup.get(selected_dept, [])
            course_dropdown['values'] = available_courses
            if course_var_popup.get() not in available_courses:
                course_var_popup.set(available_courses[0] if available_courses else "")

        dept_dropdown.bind("<<ComboboxSelected>>", update_popup_courses)

        # DOB
        tk.Label(form_box, text="DOB:", bg="white").grid(row=3, column=0, padx=(16, 6), pady=6, sticky="w")
        dob_entry = tk.Entry(form_box, width=24)
        dob_entry.insert(0, student_data[6])
        dob_entry.grid(row=3, column=1, padx=(0, 14), pady=6, sticky="w")
        entries["dob"] = dob_entry

        # Email
        tk.Label(form_box, text="Email:", bg="white").grid(row=3, column=2, padx=(16, 6), pady=6, sticky="w")
        email_entry = tk.Entry(form_box, width=24)
        email_entry.insert(0, student_data[7])
        email_entry.grid(row=3, column=3, padx=(0, 16), pady=6, sticky="w")
        entries["email"] = email_entry

        # Phone
        tk.Label(form_box, text="Phone:", bg="white").grid(row=4, column=0, padx=(16, 6), pady=6, sticky="w")
        phone_entry = tk.Entry(form_box, width=24)
        phone_entry.insert(0, student_data[8])
        phone_entry.grid(row=4, column=1, padx=(0, 14), pady=6, sticky="w")
        entries["phone"] = phone_entry

        # Status
        tk.Label(form_box, text="Status:", bg="white").grid(row=4, column=2, padx=(16, 6), pady=6, sticky="w")
        status_var_popup = tk.StringVar(value=student_data[9] if len(student_data) > 9 and student_data[9] else "Active")
        status_dropdown = ttk.Combobox(form_box, textvariable=status_var_popup, state="readonly", width=22)
        status_dropdown['values'] = ["Active", "Inactive"]
        status_dropdown.grid(row=4, column=3, padx=(0, 16), pady=6, sticky="w")
        entries["status"] = status_dropdown

        # Blacklist Section
        tk.Label(form_box, text="Blacklist Management", bg="white", font=("Segoe UI", 9, "bold"), fg="#c0392b").grid(row=5, column=0, columnspan=4, pady=(12, 6))
        
        # Get blacklist data from database
        blacklist_until = None
        blacklist_reason = ""
        try:
            conn_bl = get_connection()
            cursor_bl = conn_bl.cursor()
            cursor_bl.execute("SELECT blacklist_until, blacklist_reason FROM students WHERE enrollment_no=%s", (enrollment_no,))
            bl_data = cursor_bl.fetchone()
            if bl_data:
                blacklist_until = bl_data[0]
                blacklist_reason = bl_data[1] if bl_data[1] else ""
            conn_bl.close()
        except:
            pass
        
        # Blacklist Until Date
        tk.Label(form_box, text="Blacklist Until (YYYY-MM-DD):", bg="white").grid(row=6, column=0, padx=(16, 6), pady=6, sticky="w")
        blacklist_date_entry = tk.Entry(form_box, width=24)
        if blacklist_until:
            blacklist_date_entry.insert(0, str(blacklist_until))
        blacklist_date_entry.grid(row=6, column=1, padx=(0, 14), pady=6, sticky="w")
        entries["blacklist_until"] = blacklist_date_entry
        
        # Blacklist Reason
        tk.Label(form_box, text="Blacklist Reason:", bg="white").grid(row=6, column=2, padx=(16, 6), pady=6, sticky="w")
        blacklist_reason_text = tk.Text(form_box, width=24, height=3)
        if blacklist_reason:
            blacklist_reason_text.insert('1.0', blacklist_reason)
        blacklist_reason_text.grid(row=6, column=3, padx=(0, 16), pady=6, sticky="w")
        entries["blacklist_reason"] = blacklist_reason_text

        # Quick blacklist buttons
        quick_bl_frame = tk.Frame(form_box, bg="white")
        quick_bl_frame.grid(row=7, column=0, columnspan=4, pady=(4, 10))
        
        def set_blacklist_days(days):
            future_date = datetime.now() + timedelta(days=days)
            blacklist_date_entry.delete(0, tk.END)
            blacklist_date_entry.insert(0, future_date.strftime('%Y-%m-%d'))
        
        tk.Button(quick_bl_frame, text="7 Days", bg="#e67e22", fg="white", width=8,
                 command=lambda: set_blacklist_days(7)).pack(side="left", padx=3)
        tk.Button(quick_bl_frame, text="30 Days", bg="#d35400", fg="white", width=8,
                 command=lambda: set_blacklist_days(30)).pack(side="left", padx=3)
        tk.Button(quick_bl_frame, text="90 Days", bg="#c0392b", fg="white", width=8,
                 command=lambda: set_blacklist_days(90)).pack(side="left", padx=3)
        tk.Button(quick_bl_frame, text="Clear", bg="#95a5a6", fg="white", width=8,
                 command=lambda: [blacklist_date_entry.delete(0, tk.END), blacklist_reason_text.delete('1.0', tk.END)]).pack(side="left", padx=3)

        # ---------- Buttons ----------
        btn_frame = tk.Frame(popup_container, bg="#f5f7fa")
        btn_frame.pack(pady=12)

        def update_student():
            try:
                blacklist_date_str = entries["blacklist_until"].get().strip()
                blacklist_reason_str = entries["blacklist_reason"].get('1.0', tk.END).strip()
                
                # Validate blacklist date if provided
                blacklist_date_val = None
                if blacklist_date_str:
                    try:
                        blacklist_date_val = datetime.strptime(blacklist_date_str, '%Y-%m-%d').date()
                    except ValueError:
                        messagebox.showerror("Error", "Invalid blacklist date format. Use YYYY-MM-DD")
                        return
                
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE students SET
                        name=%s, department=%s, course=%s, semester=%s,
                        section=%s, dob=%s, email=%s, phone=%s, status=%s,
                        blacklist_until=%s, blacklist_reason=%s
                    WHERE enrollment_no=%s
                """, (
                    entries["name"].get(),
                    entries["department"].get(),
                    canonical_course_name(entries["course"].get()),
                    entries["semester"].get(),
                    entries["section"].get(),
                    entries["dob"].get(),
                    entries["email"].get(),
                    entries["phone"].get(),
                    entries["status"].get(),
                    blacklist_date_val,
                    blacklist_reason_str if blacklist_reason_str else None,
                    enrollment_no
                ))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", "Student updated successfully!")
                popup.destroy()
                load_students()
                if update_stats_callback:
                    update_stats_callback()
            except Exception as e:
                messagebox.showerror("Error", str(e))

        def delete_student():
            result = messagebox.askyesno("Confirm Delete", f"Do you really want to delete {entries['name'].get()}?")
            if not result:
                return
            try:
                conn = get_connection()
                cursor = conn.cursor()
                current_email = entries["email"].get().strip()
                cursor.execute("DELETE FROM students WHERE enrollment_no=%s", (enrollment_no,))
                cursor.execute(
                    "DELETE FROM users WHERE role='student' AND (enrollment_no=%s OR username=%s OR email=%s)",
                    (enrollment_no, enrollment_no, current_email),
                )
                conn.commit()
                conn.close()
                messagebox.showinfo("Deleted", "Student deleted successfully!")
                popup.destroy()
                load_students()
                if update_stats_callback:
                    update_stats_callback()
            except Exception as e:
                messagebox.showerror("Error", str(e))

        def reset_student_password():
            reset_popup = tk.Toplevel(popup)
            reset_popup.title("Reset Student Password")
            reset_popup.geometry("360x220")
            reset_popup.configure(bg="#f5f7fa")

            tk.Label(reset_popup, text=f"Enrollment: {enrollment_no}", bg="#f5f7fa", font=("Segoe UI", 10, "bold")).pack(
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
                        "UPDATE users SET password=%s WHERE enrollment_no=%s AND role='student'",
                        (hash_password(new_password), enrollment_no),
                    )
                    conn.commit()
                    affected_rows = cursor.rowcount
                    conn.close()

                    if affected_rows == 0:
                        messagebox.showwarning("Not Found", "No student login account found for this enrollment.")
                        return

                    messagebox.showinfo("Success", "Student password reset successfully!")
                    reset_popup.destroy()
                except Exception as e:
                    messagebox.showerror("Error", str(e))

            tk.Button(
                reset_popup,
                text="Reset Password",
                bg="#3498db",
                fg="white",
                width=16,
                command=save_new_password,
            ).pack(pady=15)

        tk.Button(btn_frame, text="💾 Update", bg="#1abc9c", fg="white", width=10, command=update_student).pack(side="left", padx=5)
        tk.Button(btn_frame, text="🗑️ Delete", bg="#c0392b", fg="white", width=10, command=delete_student).pack(side="left", padx=5)
        tk.Button(btn_frame, text="🔑 Reset Password", bg="#3498db", fg="white", width=14, command=reset_student_password).pack(side="left", padx=5)
        tk.Button(btn_frame, text="✖ Exit", bg="#95a5a6", fg="white", width=10, command=popup.destroy).pack(side="left", padx=5)

    # Bind double click to open popup for other students
    def open_selected(event):
        selected = tree.focus()
        if selected:
            enrollment_no = selected
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT name, enrollment_no, department, course, semester, section, dob, email, phone, status, blacklist_until FROM students WHERE enrollment_no=%s", (enrollment_no,))
            student = cursor.fetchone()
            conn.close()
            if student:
                open_student_popup(student)

    tree.bind("<Double-1>", open_selected)

