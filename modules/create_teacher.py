import tkinter as tk
from tkinter import messagebox, ttk
import re
from db_config import get_connection
from auth_utils import hash_password
from modules.course_aliases import canonical_course_name


def load_module(parent_frame, update_stats_callback=None):
    for widget in parent_frame.winfo_children():
        widget.destroy()
    parent_frame.configure(bg="#f5f7fa")

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

    ensure_teacher_course_column()

    title_frame = tk.Frame(parent_frame, bg="#3498db", height=60)
    title_frame.pack(fill="x")
    title_frame.pack_propagate(False)
    tk.Label(
        title_frame,
        text="👨‍🏫 Create Teacher",
        font=("Segoe UI", 16, "bold"),
        bg="#3498db",
        fg="white",
    ).pack(pady=12)

    content_frame = tk.Frame(parent_frame, bg="#f5f7fa")
    content_frame.pack(fill="both", expand=True, padx=20, pady=20)

    form_frame = tk.Frame(
        content_frame,
        bg="white",
        bd=2,
        relief="solid",
        highlightbackground="#3498db",
        highlightcolor="#1abc9c",
        highlightthickness=2,
        padx=20,
        pady=20,
    )
    form_frame.pack(fill="x", padx=10, pady=10)

    entry_style = {"bg": "white", "fg": "#333333", "relief": "solid", "bd": 1, "font": ("Segoe UI", 11)}
    label_style = {"font": ("Segoe UI", 11), "bg": "white", "fg": "#333333"}
    button_style = {
        "bg": "#1abc9c",
        "fg": "white",
        "activebackground": "#16a085",
        "activeforeground": "white",
        "font": ("Segoe UI", 12, "bold"),
        "cursor": "hand2",
        "padx": 15,
        "pady": 8,
    }

    tk.Label(form_frame, text="Username:", **label_style).grid(row=0, column=0, sticky="w", pady=5)
    username_entry = tk.Entry(form_frame, **entry_style)
    username_entry.grid(row=0, column=1, padx=10, pady=5)

    tk.Label(form_frame, text="Password:", **label_style).grid(row=0, column=2, sticky="w", pady=5)
    password_entry = tk.Entry(form_frame, show="*", **entry_style)
    password_entry.grid(row=0, column=3, padx=10, pady=5)

    tk.Label(form_frame, text="Full Name:", **label_style).grid(row=1, column=0, sticky="w", pady=5)
    full_name_entry = tk.Entry(form_frame, **entry_style)
    full_name_entry.grid(row=1, column=1, padx=10, pady=5)

    def sync_username_from_name(event=None):
        generated = re.sub(r"\s+", "_", full_name_entry.get().strip().lower()).strip("_")
        username_entry.delete(0, tk.END)
        username_entry.insert(0, generated)

    full_name_entry.bind("<KeyRelease>", sync_username_from_name)
    full_name_entry.bind("<FocusOut>", sync_username_from_name)

    tk.Label(form_frame, text="Email:", **label_style).grid(row=1, column=2, sticky="w", pady=5)
    email_entry = tk.Entry(form_frame, **entry_style)
    email_entry.grid(row=1, column=3, padx=10, pady=5)

    tk.Label(form_frame, text="Mobile:", **label_style).grid(row=2, column=0, sticky="w", pady=5)
    mobile_entry = tk.Entry(form_frame, **entry_style)
    mobile_entry.grid(row=2, column=1, padx=10, pady=5)

    tk.Label(form_frame, text="DOB (YYYY-MM-DD):", **label_style).grid(row=2, column=2, sticky="w", pady=5)
    dob_entry = tk.Entry(form_frame, **entry_style)
    dob_entry.grid(row=2, column=3, padx=10, pady=5)

    def autofill_password_from_dob(event=None):
        dob_val = dob_entry.get().strip()
        current_password = password_entry.get().strip()
        if dob_val and (not current_password or current_password == getattr(autofill_password_from_dob, "last_dob", "")):
            password_entry.delete(0, tk.END)
            password_entry.insert(0, dob_val)
        autofill_password_from_dob.last_dob = dob_val

    autofill_password_from_dob.last_dob = ""
    dob_entry.bind("<KeyRelease>", autofill_password_from_dob)
    dob_entry.bind("<FocusOut>", autofill_password_from_dob)

    tk.Label(form_frame, text="Gender:", **label_style).grid(row=3, column=0, sticky="w", pady=5)
    gender_var = tk.StringVar(value="Select")
    gender_dropdown = ttk.Combobox(form_frame, textvariable=gender_var, state="readonly", font=("Segoe UI", 11))
    gender_dropdown["values"] = ["Select", "Male", "Female", "Other"]
    gender_dropdown.grid(row=3, column=1, padx=10, pady=5)
    gender_dropdown.current(0)

    tk.Label(form_frame, text="Department:", **label_style).grid(row=3, column=2, sticky="w", pady=5)
    department_var = tk.StringVar(value="Select")
    department_dropdown = ttk.Combobox(form_frame, textvariable=department_var, state="readonly", font=("Segoe UI", 11))
    
    # Load departments from database
    def load_departments():
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT department_name FROM departments WHERE is_active=1 ORDER BY department_name")
            departments = [row[0] for row in cursor.fetchall()]
            conn.close()
            return ["Select"] + departments
        except:
            return ["Select", "Computer Science", "Medical"]
    
    department_dropdown["values"] = load_departments()
    department_dropdown.grid(row=3, column=3, padx=10, pady=5)
    department_dropdown.current(0)

    tk.Label(form_frame, text="Course:", **label_style).grid(row=4, column=0, sticky="w", pady=5)
    course_var = tk.StringVar(value="Select")
    course_dropdown = ttk.Combobox(form_frame, textvariable=course_var, state="readonly", font=("Segoe UI", 11))
    course_dropdown.grid(row=4, column=1, padx=10, pady=5)

    def update_courses(event=None):
        dept_name = department_var.get()

        if dept_name == "Select":
            course_dropdown["values"] = ["Select"]
            course_dropdown.current(0)
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT department_id FROM departments WHERE department_name = %s", (dept_name,))
            dept_result = cursor.fetchone()

            if dept_result:
                dept_id = dept_result[0]
                cursor.execute(
                    """
                    SELECT course_name FROM courses
                    WHERE department_id = %s AND is_active = 1
                    ORDER BY course_name
                    """,
                    (dept_id,),
                )
                raw_courses = [row[0] for row in cursor.fetchall()]
                canonical_courses = []
                for course_name in raw_courses:
                    display_name = canonical_course_name(course_name)
                    if display_name not in canonical_courses:
                        canonical_courses.append(display_name)
                course_dropdown["values"] = ["Select"] + canonical_courses
            else:
                course_dropdown["values"] = ["Select"]

            conn.close()
            course_dropdown.current(0)

        except Exception:
            course_dropdown["values"] = ["Select"]
            course_dropdown.current(0)

    department_dropdown.bind("<<ComboboxSelected>>", update_courses)
    update_courses()

    tk.Label(form_frame, text="Designation:", **label_style).grid(row=5, column=0, sticky="w", pady=5)
    designation_entry = tk.Entry(form_frame, **entry_style)
    designation_entry.grid(row=5, column=1, padx=10, pady=5)

    tk.Label(form_frame, text="Qualification:", **label_style).grid(row=5, column=2, sticky="w", pady=5)
    qualification_entry = tk.Entry(form_frame, **entry_style)
    qualification_entry.grid(row=5, column=3, padx=10, pady=5)

    tk.Label(form_frame, text="Specialization:", **label_style).grid(row=6, column=0, sticky="w", pady=5)
    specialization_entry = tk.Entry(form_frame, **entry_style)
    specialization_entry.grid(row=6, column=1, padx=10, pady=5)

    tk.Label(form_frame, text="Experience (Years):", **label_style).grid(row=6, column=2, sticky="w", pady=5)
    experience_entry = tk.Entry(form_frame, **entry_style)
    experience_entry.grid(row=6, column=3, padx=10, pady=5)

    tk.Label(form_frame, text="Date of Joining (YYYY-MM-DD):", **label_style).grid(row=7, column=0, sticky="w", pady=5)
    doj_entry = tk.Entry(form_frame, **entry_style)
    doj_entry.grid(row=7, column=1, padx=10, pady=5)

    tk.Label(form_frame, text="Address:", **label_style).grid(row=7, column=2, sticky="w", pady=5)
    address_entry = tk.Entry(form_frame, **entry_style)
    address_entry.grid(row=7, column=3, padx=10, pady=5)

    tk.Label(form_frame, text="Security Question:", **label_style).grid(row=8, column=0, sticky="w", pady=5)
    security_question_entry = tk.Entry(form_frame, **entry_style)
    security_question_entry.grid(row=8, column=1, padx=10, pady=5)

    tk.Label(form_frame, text="Security Answer:", **label_style).grid(row=8, column=2, sticky="w", pady=5)
    security_answer_entry = tk.Entry(form_frame, **entry_style)
    security_answer_entry.grid(row=8, column=3, padx=10, pady=5)

    def add_teacher():
        username = username_entry.get().strip()
        password = password_entry.get().strip()
        full_name = full_name_entry.get().strip()
        email = email_entry.get().strip()
        mobile = mobile_entry.get().strip()
        dob = dob_entry.get().strip()
        gender = gender_var.get().strip()
        department = department_var.get().strip()
        course = canonical_course_name(course_var.get().strip())
        designation = designation_entry.get().strip()
        qualification = qualification_entry.get().strip()
        specialization = specialization_entry.get().strip()
        experience_years = experience_entry.get().strip()
        date_of_joining = doj_entry.get().strip()
        address = address_entry.get().strip()
        security_question = security_question_entry.get().strip()
        security_answer = security_answer_entry.get().strip()

        generated_username = re.sub(r"\s+", "_", full_name.lower()).strip("_")
        username = generated_username
        username_entry.delete(0, tk.END)
        username_entry.insert(0, username)

        if not password:
            password = dob

        user_mobile = mobile if mobile else "0000000000"
        user_email = email if email else "none@example.com"
        user_security_question = security_question if security_question else "None"
        user_security_answer = security_answer if security_answer else "None"

        if not all([
            username,
            full_name,
            email,
            mobile,
            dob,
            department,
            course,
            designation,
            qualification,
            experience_years,
            date_of_joining,
            address,
        ]) or gender == "Select" or department == "Select" or course == "Select":
            messagebox.showwarning("Input Error", "All fields are required.")
            return

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            messagebox.showwarning("Input Error", "Enter a valid email address.")
            return

        if not mobile.isdigit() or len(mobile) != 10:
            messagebox.showwarning("Input Error", "Mobile number must be 10 digits.")
            return

        if not re.match(r"\d{4}-\d{2}-\d{2}$", dob):
            messagebox.showwarning("Input Error", "DOB must be in YYYY-MM-DD format.")
            return

        if not username:
            messagebox.showwarning("Input Error", "Full name is required to generate username.")
            return

        if not re.match(r"\d{4}-\d{2}-\d{2}$", date_of_joining):
            messagebox.showwarning("Input Error", "Date of Joining must be in YYYY-MM-DD format.")
            return

        if not experience_years.isdigit() or int(experience_years) < 0:
            messagebox.showwarning("Input Error", "Experience must be a non-negative number.")
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM users WHERE username=%s", (username,))
            if cursor.fetchone():
                messagebox.showwarning("Duplicate", "This username already exists.")
                conn.close()
                return

            cursor.execute("SELECT teacher_id FROM teachers WHERE username=%s OR email=%s", (username, email))
            if cursor.fetchone():
                messagebox.showwarning("Duplicate", "Teacher username or email already exists.")
                conn.close()
                return

            password_hash = hash_password(password)
            cursor.execute(
                """
                INSERT INTO users (username, password, role, enrollment_no, security_question, security_answer, mobile, email)
                VALUES (%s, %s, 'teacher', NULL, %s, %s, %s, %s)
                """,
                (username, password_hash, user_security_question, user_security_answer, user_mobile, user_email),
            )

            cursor.execute(
                """
                INSERT INTO teachers
                (username, full_name, email, phone, dob, gender, department, designation,
                 course, qualification, specialization, experience_years, date_of_joining, address)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    username,
                    full_name,
                    email,
                    mobile,
                    dob,
                    gender,
                    department,
                    designation,
                    course,
                    qualification,
                    specialization,
                    int(experience_years),
                    date_of_joining,
                    address,
                ),
            )
            conn.commit()
            conn.close()

            messagebox.showinfo("Success", f"Teacher {username} added successfully!")

            for widget in [
                username_entry,
                password_entry,
                full_name_entry,
                email_entry,
                mobile_entry,
                dob_entry,
                designation_entry,
                qualification_entry,
                specialization_entry,
                experience_entry,
                doj_entry,
                address_entry,
                security_question_entry,
                security_answer_entry,
            ]:
                widget.delete(0, tk.END)
            gender_dropdown.current(0)
            department_dropdown.current(0)
            update_courses()

            if update_stats_callback:
                update_stats_callback()

        except Exception as error:
            messagebox.showerror("Database Error", str(error))

    tk.Button(form_frame, text="Create Teacher", command=add_teacher, **button_style).grid(
        row=9, column=0, columnspan=4, pady=20
    )
