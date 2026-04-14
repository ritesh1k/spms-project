# create_student.py
import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox
import re

# Add parent folder to path so db_config can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_config import get_connection
from auth_utils import hash_password
from modules.course_aliases import canonical_course_name

def load_module(parent_frame, update_stats_callback=None):
    # Clear previous content
    for widget in parent_frame.winfo_children():
        widget.destroy()
    parent_frame.configure(bg="#f5f7fa")

    # ---------- Title ----------
    title_frame = tk.Frame(parent_frame, bg="#9b59b6", height=60)
    title_frame.pack(fill="x")
    title_frame.pack_propagate(False)
    tk.Label(
        title_frame,
        text="🎓 Create Student",
        font=("Segoe UI", 16, "bold"),
        bg="#9b59b6",
        fg="white",
    ).pack(pady=12)

    content_frame = tk.Frame(parent_frame, bg="#f5f7fa")
    content_frame.pack(fill="both", expand=True, padx=20, pady=20)

    # ---------- Form Frame ----------
    form_frame = tk.Frame(content_frame, bg="white", bd=2, relief="solid", highlightbackground="#9b59b6",
                          highlightcolor="#1abc9c", highlightthickness=2, padx=20, pady=20)
    form_frame.pack(fill="x", padx=10, pady=10)

    # ---------- Style options ----------
    entry_style = {"bg": "white", "fg": "#333333", "relief": "solid", "bd": 1, "font": ("Segoe UI", 11)}
    label_style = {"font": ("Segoe UI", 11), "bg": "white", "fg": "#333333"}
    button_style = {"bg": "#1abc9c", "fg": "white", "activebackground": "#16a085", "activeforeground": "white",
                    "font": ("Segoe UI", 12, "bold"), "cursor": "hand2", "padx": 15, "pady": 8}

    # ---------- Row 1: Name + Enrollment ----------
    tk.Label(form_frame, text="Name:", **label_style).grid(row=0, column=0, sticky="w", pady=5)
    name_entry = tk.Entry(form_frame, **entry_style)
    name_entry.grid(row=0, column=1, padx=10, pady=5)

    tk.Label(form_frame, text="Enrollment No:", **label_style).grid(row=0, column=2, sticky="w", pady=5)
    enroll_entry = tk.Entry(form_frame, **entry_style)
    enroll_entry.grid(row=0, column=3, padx=10, pady=5)

    # ---------- Row 2: Email + Phone ----------
    tk.Label(form_frame, text="Email:", **label_style).grid(row=1, column=0, sticky="w", pady=5)
    email_entry = tk.Entry(form_frame, **entry_style)
    email_entry.grid(row=1, column=1, padx=10, pady=5)

    tk.Label(form_frame, text="Phone:", **label_style).grid(row=1, column=2, sticky="w", pady=5)
    phone_entry = tk.Entry(form_frame, **entry_style)
    phone_entry.grid(row=1, column=3, padx=10, pady=5)

    # ---------- Row 3: Department + Course ----------
    tk.Label(form_frame, text="Department:", **label_style).grid(row=2, column=0, sticky="w", pady=5)
    department_var = tk.StringVar()
    department_dropdown = ttk.Combobox(form_frame, textvariable=department_var, state="readonly",
                                       font=("Segoe UI", 11))
    department_dropdown.grid(row=2, column=1, padx=10, pady=5)
    
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
    
    department_dropdown['values'] = load_departments()
    department_dropdown.current(0)

    tk.Label(form_frame, text="Course:", **label_style).grid(row=2, column=2, sticky="w", pady=5)
    course_var = tk.StringVar()
    course_dropdown = ttk.Combobox(form_frame, textvariable=course_var, state="readonly",
                                   font=("Segoe UI", 11))
    course_dropdown.grid(row=2, column=3, padx=10, pady=5)

    def update_courses(event=None):
        """Load courses from database based on selected department"""
        dept_name = department_var.get()
        
        if dept_name == "Select":
            course_dropdown['values'] = ["Select"]
            course_dropdown.current(0)
            return
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Get department ID first
            cursor.execute("SELECT department_id FROM departments WHERE department_name = %s", (dept_name,))
            dept_result = cursor.fetchone()
            
            if dept_result:
                dept_id = dept_result[0]
                # Get courses for this department
                cursor.execute("""
                    SELECT course_name FROM courses 
                    WHERE department_id = %s AND is_active = 1 
                    ORDER BY course_name
                """, (dept_id,))
                raw_courses = [row[0] for row in cursor.fetchall()]
                canonical_courses = []
                for course_name in raw_courses:
                    display_name = canonical_course_name(course_name)
                    if display_name not in canonical_courses:
                        canonical_courses.append(display_name)
                course_dropdown['values'] = ["Select"] + canonical_courses
            else:
                course_dropdown['values'] = ["Select"]
            
            conn.close()
            course_dropdown.current(0)
        
        except Exception as e:
            print(f"Error loading courses: {e}")
            # Fallback to hardcoded values
            courses_dict = {
                "Computer Science": ["B.Tech", "BCA", "MCA", "M.Tech"],
                "Medical": ["Nursing", "MBBS", "Dental", "Psychotherapy"]
            }
            course_dropdown['values'] = ["Select"] + courses_dict.get(dept_name, [])
            course_dropdown.current(0)

    department_dropdown.bind("<<ComboboxSelected>>", update_courses)
    update_courses()

    # ---------- Row 4: Semester + Section ----------
    tk.Label(form_frame, text="Semester:", **label_style).grid(row=3, column=0, sticky="w", pady=5)
    sem_var = tk.StringVar()
    sem_dropdown = ttk.Combobox(form_frame, textvariable=sem_var, state="readonly",
                                font=("Segoe UI", 11))
    sem_dropdown['values'] = ["Select", "I", "II", "III", "IV", "V", "VI"]
    sem_dropdown.grid(row=3, column=1, padx=10, pady=5)
    sem_dropdown.current(0)

    tk.Label(form_frame, text="Section:", **label_style).grid(row=3, column=2, sticky="w", pady=5)
    section_var = tk.StringVar()
    section_dropdown = ttk.Combobox(form_frame, textvariable=section_var, state="readonly",
                                    font=("Segoe UI", 11))
    section_dropdown['values'] = ["Select", "A","B","C","D","E","F","G","H","I"]
    section_dropdown.grid(row=3, column=3, padx=10, pady=5)
    section_dropdown.current(0)

    # ---------- Row 5: DOB ----------
    tk.Label(form_frame, text="DOB (YYYY-MM-DD):", **label_style).grid(row=4, column=0, sticky="w", pady=5)
    dob_entry = tk.Entry(form_frame, **entry_style)
    dob_entry.grid(row=4, column=1, padx=10, pady=5)

    # ---------- Row 5: Password ----------
    tk.Label(form_frame, text="Password:", **label_style).grid(row=4, column=2, sticky="w", pady=5)
    password_entry = tk.Entry(form_frame, show="*", **entry_style)
    password_entry.grid(row=4, column=3, padx=10, pady=5)

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

    # ---------- Add Student Function ----------
    def add_student():
        name = name_entry.get().strip()
        enroll = enroll_entry.get().strip()
        email = email_entry.get().strip()
        phone = phone_entry.get().strip()
        dob = dob_entry.get().strip()
        password = password_entry.get().strip()
        dept = department_var.get()
        course = course_var.get()
        sem = sem_var.get()
        section_val = section_var.get()

        username_for_users = re.sub(r"\s+", "_", name.lower()).strip("_")

        if not password:
            password = dob

        course = canonical_course_name(course)

        user_mobile = phone if phone else "0000000000"
        user_email = email if email else "none@example.com"
        user_security_question = "None"
        user_security_answer = "None"

        # ---------- Validation ----------
        if not all([name, enroll, email, phone, dob, dept != "Select", course != "Select",
                    sem != "Select", section_val != "Select"]):
            messagebox.showwarning("Input Error", "All fields are required.")
            return
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            messagebox.showwarning("Input Error", "Enter a valid email address.")
            return
        if not phone.isdigit() or len(phone) != 10:
            messagebox.showwarning("Input Error", "Phone number must be 10 digits.")
            return
        if not re.match(r"\d{4}-\d{2}-\d{2}$", dob):
            messagebox.showwarning("Input Error", "DOB must be in YYYY-MM-DD format.")
            return

        if not username_for_users:
            messagebox.showwarning("Input Error", "Name is required to generate username.")
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT enrollment_no FROM students WHERE enrollment_no=%s", (enroll,))
            if cursor.fetchone():
                conn.close()
                messagebox.showwarning("Duplicate", "Enrollment number already exists.")
                return

            cursor.execute("SELECT username FROM users WHERE username=%s", (username_for_users,))
            if cursor.fetchone():
                conn.close()
                messagebox.showwarning("Duplicate", "Generated username from name already exists. Use a unique name.")
                return

            cursor.execute("""
                INSERT INTO students (name, enrollment_no, course, section, dob, email, phone, semester, department)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (name, enroll, course, section_val, dob, email, phone, sem, dept))

            password_hash = hash_password(password)
            cursor.execute(
                """
                INSERT INTO users (username, password, role, enrollment_no, security_question, security_answer, mobile, email)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    username_for_users,
                    password_hash,
                    'student',
                    enroll,
                    user_security_question,
                    user_security_answer,
                    user_mobile,
                    user_email,
                ),
            )

            conn.commit()
            cursor.close()
            conn.close()
            messagebox.showinfo("Success", f"Student {name} added successfully!")

            # Clear form
            for e in [name_entry, enroll_entry, email_entry, phone_entry, dob_entry, password_entry]:
                e.delete(0, tk.END)
            department_dropdown.current(0)
            update_courses()
            sem_dropdown.current(0)
            section_dropdown.current(0)

            # Update admin dashboard total student
            if update_stats_callback:
                update_stats_callback()

        except Exception as e:
            messagebox.showerror("Database Error", str(e))

    # ---------- Create Student Button ----------
    tk.Button(form_frame, text="Create Student", command=add_student, **button_style).grid(
        row=6, column=0, columnspan=4, pady=20)
