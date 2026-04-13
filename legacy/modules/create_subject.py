import tkinter as tk
from tkinter import ttk, messagebox
from db_config import get_connection
from modules.course_aliases import canonical_course_name

def load_module(parent_frame, update_stats_callback=None):
    """Load Create Subject module into parent frame"""
    # Clear existing widgets
    for widget in parent_frame.winfo_children():
        widget.destroy()
    
    # Title section
    title_frame = tk.Frame(parent_frame, bg='#9b59b6', height=60)
    title_frame.pack(fill='x')
    title_frame.pack_propagate(False)
    
    title_label = tk.Label(
        title_frame,
        text="📚 Create New Subject",
        font=('Segoe UI', 18, 'bold'),
        bg='#9b59b6',
        fg='white'
    )
    title_label.pack(pady=15)
    
    # Main content frame
    content_frame = tk.Frame(parent_frame, bg='#f5f7fa')
    content_frame.pack(fill='both', expand=True, padx=40, pady=30)
    
    # Form container
    form_frame = tk.Frame(content_frame, bg='white', relief='flat', bd=0)
    form_frame.pack(fill='both', expand=True)
    
    # Padding frame inside form
    inner_frame = tk.Frame(form_frame, bg='white')
    inner_frame.pack(fill='both', expand=True, padx=50, pady=30)
    
    widgets = {}
    row = 0
    
    # Load departments
    def load_departments():
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT department_id, department_name FROM departments WHERE is_active = 1 ORDER BY department_name")
            departments = cursor.fetchall()
            cursor.close()
            conn.close()
            return departments
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load departments: {str(e)}")
            return []
    
    departments = load_departments()
    dept_dict = {dept[1]: dept[0] for dept in departments}
    dept_names = ["Select Department"] + [dept[1] for dept in departments]
    
    # Department dropdown
    tk.Label(inner_frame, text="Department:", font=('Segoe UI', 11), bg='white', fg='#2c3e50', anchor='w').grid(
        row=row, column=0, sticky='w', pady=10, padx=(0, 20))
    
    department_var = tk.StringVar(value="Select Department")
    department_dropdown = ttk.Combobox(
        inner_frame,
        textvariable=department_var,
        values=dept_names,
        state='readonly',
        font=('Segoe UI', 10),
        width=40
    )
    department_dropdown.grid(row=row, column=1, sticky='ew', pady=10)
    widgets['department'] = department_var
    widgets['department_dropdown'] = department_dropdown
    row += 1
    
    # Course dropdown
    tk.Label(inner_frame, text="Course:", font=('Segoe UI', 11), bg='white', fg='#2c3e50', anchor='w').grid(
        row=row, column=0, sticky='w', pady=10, padx=(0, 20))
    
    course_var = tk.StringVar(value="Select Course")
    course_dropdown = ttk.Combobox(
        inner_frame,
        textvariable=course_var,
        values=["Select Course"],
        state='readonly',
        font=('Segoe UI', 10),
        width=40
    )
    course_dropdown.grid(row=row, column=1, sticky='ew', pady=10)
    widgets['course'] = course_var
    widgets['course_dropdown'] = course_dropdown
    row += 1
    
    # Store course_id mapping
    course_dict = {}

    def build_course_display_values(courses):
        values = []
        mapping = {}
        for course_id, course_name in courses:
            display_name = canonical_course_name(course_name)
            if display_name not in values:
                values.append(display_name)
            mapping[display_name] = course_id
        return values, mapping
    
    def load_courses(event=None):
        """Load courses based on selected department"""
        dept_name = department_var.get()
        
        if dept_name == "Select Department":
            course_dropdown['values'] = ["Select Course"]
            course_dropdown.current(0)
            return
        
        try:
            dept_id = dept_dict.get(dept_name)
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT course_id, course_name FROM courses 
                WHERE department_id = %s AND is_active = 1 
                ORDER BY course_name
            """, (dept_id,))
            courses = cursor.fetchall()
            cursor.close()
            conn.close()
            
            nonlocal course_dict
            course_names, course_dict = build_course_display_values(courses)
            course_names = ["Select Course"] + course_names
            course_dropdown['values'] = course_names
            course_dropdown.current(0)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load courses: {str(e)}")
    
    department_dropdown.bind("<<ComboboxSelected>>", load_courses)
    
    # Semester dropdown
    tk.Label(inner_frame, text="Semester:", font=('Segoe UI', 11), bg='white', fg='#2c3e50', anchor='w').grid(
        row=row, column=0, sticky='w', pady=10, padx=(0, 20))
    
    semester_var = tk.StringVar(value="Select Semester")
    semester_dropdown = ttk.Combobox(
        inner_frame,
        textvariable=semester_var,
        values=["Select Semester", "I", "II", "III", "IV", "V", "VI", "VII", "VIII"],
        state='readonly',
        font=('Segoe UI', 10),
        width=40
    )
    semester_dropdown.grid(row=row, column=1, sticky='ew', pady=10)
    widgets['semester'] = semester_var
    widgets['semester_dropdown'] = semester_dropdown
    row += 1
    
    # Subject Name
    tk.Label(inner_frame, text="Subject Name:", font=('Segoe UI', 11), bg='white', fg='#2c3e50', anchor='w').grid(
        row=row, column=0, sticky='w', pady=10, padx=(0, 20))
    
    subject_name_entry = tk.Entry(inner_frame, font=('Segoe UI', 10), relief='solid', bd=1, width=42)
    subject_name_entry.grid(row=row, column=1, sticky='ew', pady=10)
    widgets['subject_name'] = subject_name_entry
    row += 1
    
    # Subject Code
    tk.Label(inner_frame, text="Subject Code:", font=('Segoe UI', 11), bg='white', fg='#2c3e50', anchor='w').grid(
        row=row, column=0, sticky='w', pady=10, padx=(0, 20))
    
    subject_code_entry = tk.Entry(inner_frame, font=('Segoe UI', 10), relief='solid', bd=1, width=42)
    subject_code_entry.grid(row=row, column=1, sticky='ew', pady=10)
    widgets['subject_code'] = subject_code_entry
    row += 1
    
    # Credits
    tk.Label(inner_frame, text="Credits:", font=('Segoe UI', 11), bg='white', fg='#2c3e50', anchor='w').grid(
        row=row, column=0, sticky='w', pady=10, padx=(0, 20))
    
    credits_entry = tk.Entry(inner_frame, font=('Segoe UI', 10), relief='solid', bd=1, width=42)
    credits_entry.grid(row=row, column=1, sticky='ew', pady=10)
    widgets['credits'] = credits_entry
    row += 1
    
    # Description
    tk.Label(inner_frame, text="Description:", font=('Segoe UI', 11), bg='white', fg='#2c3e50', anchor='w').grid(
        row=row, column=0, sticky='nw', pady=10, padx=(0, 20))
    
    description_text = tk.Text(inner_frame, font=('Segoe UI', 10), height=4, width=42, relief='solid', bd=1)
    description_text.grid(row=row, column=1, sticky='ew', pady=10)
    widgets['description'] = description_text
    row += 1
    
    # Configure grid column weight
    inner_frame.columnconfigure(1, weight=1)
    
    # Button frame
    button_frame = tk.Frame(inner_frame, bg='white')
    button_frame.grid(row=row, column=0, columnspan=2, pady=30)
    
    def clear_form():
        """Clear all form fields"""
        subject_name_entry.delete(0, tk.END)
        subject_code_entry.delete(0, tk.END)
        credits_entry.delete(0, tk.END)
        description_text.delete('1.0', tk.END)
        department_dropdown.current(0)
        course_dropdown.current(0)
        semester_dropdown.current(0)
    
    def save_subject():
        """Save subject to database"""
        # Get values
        dept_name = department_var.get()
        course_name = course_var.get()
        semester = semester_var.get()
        subject_name = subject_name_entry.get().strip()
        subject_code = subject_code_entry.get().strip()
        credits = credits_entry.get().strip()
        description = description_text.get('1.0', tk.END).strip()
        
        # Validation
        if dept_name == "Select Department":
            messagebox.showerror("Error", "Please select a department")
            return
        
        if course_name == "Select Course":
            messagebox.showerror("Error", "Please select a course")
            return
        
        if semester == "Select Semester":
            messagebox.showerror("Error", "Please select a semester")
            return
        
        if not subject_name:
            messagebox.showerror("Error", "Subject name is required")
            return
        
        if not subject_code:
            messagebox.showerror("Error", "Subject code is required")
            return
        
        if not credits or not credits.isdigit():
            messagebox.showerror("Error", "Credits must be a valid number")
            return
        
        # Get IDs
        dept_id = dept_dict.get(dept_name)
        course_id = course_dict.get(course_name)
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Check for duplicate subject code
            cursor.execute("SELECT subject_id FROM subjects WHERE subject_code = %s", (subject_code,))
            if cursor.fetchone():
                messagebox.showerror("Error", f"Subject code '{subject_code}' already exists")
                cursor.close()
                conn.close()
                return
            
            # Insert subject
            insert_sql = """
                INSERT INTO subjects (subject_name, subject_code, department_id, course_id, semester, credits, description, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_sql, (subject_name, subject_code, dept_id, course_id, semester, int(credits), description, 1))
            conn.commit()
            
            cursor.close()
            conn.close()
            
            messagebox.showinfo("Success", f"Subject '{subject_name}' created successfully!")
            clear_form()
            
            # Update dashboard stats if callback provided
            if update_stats_callback:
                update_stats_callback()
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create subject: {str(e)}")
    
    # Create buttons
    save_btn = tk.Button(
        button_frame,
        text="💾 Save Subject",
        font=('Segoe UI', 11, 'bold'),
        bg='#9b59b6',
        fg='white',
        relief='flat',
        cursor='hand2',
        padx=30,
        pady=10,
        command=save_subject
    )
    save_btn.pack(side='left', padx=10)
    
    clear_btn = tk.Button(
        button_frame,
        text="Clear Form",
        font=('Segoe UI', 11),
        bg='#95a5a6',
        fg='white',
        relief='flat',
        cursor='hand2',
        padx=30,
        pady=10,
        command=clear_form
    )
    clear_btn.pack(side='left', padx=10)
