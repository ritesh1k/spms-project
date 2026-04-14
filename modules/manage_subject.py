import tkinter as tk
from tkinter import ttk, messagebox
from db_config import get_connection
from modules.course_aliases import get_course_aliases, canonical_course_name

def load_module(parent_frame, update_stats_callback=None):
    """Load Manage Subjects module into parent frame"""

    def build_course_display_values(courses):
        values = []
        mapping = {}
        for course_id, course_name in courses:
            display_name = canonical_course_name(course_name)
            if display_name not in values:
                values.append(display_name)
            mapping[display_name] = course_id
        return values, mapping

    # Clear existing widgets
    for widget in parent_frame.winfo_children():
        widget.destroy()
    
    # Title section with Add button
    title_frame = tk.Frame(parent_frame, bg='#8e44ad', height=60)
    title_frame.pack(fill='x')
    title_frame.pack_propagate(False)
    
    title_label = tk.Label(
        title_frame,
        text="📚 Manage Subjects",
        font=('Segoe UI', 18, 'bold'),
        bg='#8e44ad',
        fg='white'
    )
    title_label.pack(side='left', pady=15, padx=20)
    
    # Add Subject button (top right corner)
    def open_add_subject_popup():
        """Open popup to add new subject"""
        from modules import create_subject
        
        popup = tk.Toplevel()
        popup.title("Add New Subject")
        popup.geometry("650x550")
        popup.configure(bg='#f5f7fa')
        popup.resizable(False, False)
        
        # Center popup
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() // 2) - (650 // 2)
        y = (popup.winfo_screenheight() // 2) - (550 // 2)
        popup.geometry(f"650x550+{x}+{y}")
        
        # Load create_subject module in popup
        create_subject.load_module(popup, update_stats_callback=lambda: [load_subjects(), update_stats_callback() if update_stats_callback else None])
    
    add_btn = tk.Button(
        title_frame,
        text="+ Add Subject",
        font=('Segoe UI', 11, 'bold'),
        bg='#3498db',
        fg='white',
        relief='flat',
        cursor='hand2',
        padx=20,
        pady=8,
        command=open_add_subject_popup
    )
    add_btn.pack(side='right', pady=15, padx=20)
    
    # Main content frame
    content_frame = tk.Frame(parent_frame, bg='#f5f7fa')
    content_frame.pack(fill='both', expand=True, padx=20, pady=20)
    
    # Filter frame
    filter_frame = tk.Frame(content_frame, bg='white', bd=1, relief='solid')
    filter_frame.pack(fill='x', pady=(0, 20))
    
    filter_inner = tk.Frame(filter_frame, bg='white')
    filter_inner.pack(pady=12)
    
    # Load departments for filter
    def load_departments():
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT department_name FROM departments WHERE is_active = 1 ORDER BY department_name")
            depts = cursor.fetchall()
            cursor.close()
            conn.close()
            return ["All Departments"] + [dept[0] for dept in depts]
        except:
            return ["All Departments"]
    
    # Department filter
    tk.Label(filter_inner, text="Department:", font=('Segoe UI', 10), bg='white').pack(side='left', padx=(0, 10))
    
    dept_var = tk.StringVar(value="All Departments")
    dept_dropdown = ttk.Combobox(
        filter_inner,
        textvariable=dept_var,
        values=load_departments(),
        state='readonly',
        font=('Segoe UI', 10),
        width=16
    )
    dept_dropdown.pack(side='left', padx=(0, 20))
    
    # Course filter
    tk.Label(filter_inner, text="Course:", font=('Segoe UI', 10), bg='white').pack(side='left', padx=(0, 10))
    
    course_var = tk.StringVar(value="All Courses")
    course_dropdown = ttk.Combobox(
        filter_inner,
        textvariable=course_var,
        values=["All Courses"],
        state='readonly',
        font=('Segoe UI', 10),
        width=16
    )
    course_dropdown.pack(side='left', padx=(0, 20))
    
    # Semester filter
    tk.Label(filter_inner, text="Semester:", font=('Segoe UI', 10), bg='white').pack(side='left', padx=(0, 10))
    
    sem_var = tk.StringVar(value="All Semesters")
    sem_dropdown = ttk.Combobox(
        filter_inner,
        textvariable=sem_var,
        values=["All Semesters", "I", "II", "III", "IV", "V", "VI", "VII", "VIII"],
        state='readonly',
        font=('Segoe UI', 10),
        width=14
    )
    sem_dropdown.pack(side='left', padx=(0, 20))
    
    # Subject name filter
    tk.Label(filter_inner, text="Subject:", font=('Segoe UI', 10), bg='white').pack(side='left', padx=(0, 10))
    
    subject_entry = tk.Entry(filter_inner, font=('Segoe UI', 10), width=16)
    subject_entry.pack(side='left', padx=(0, 20))
    
    # Load courses based on department selection
    def load_courses_filter(event=None):
        dept_name = dept_var.get()
        
        if dept_name == "All Departments":
            course_dropdown['values'] = ["All Courses"]
            course_dropdown.current(0)
            return
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT c.course_id, c.course_name 
                FROM courses c
                JOIN departments d ON c.department_id = d.department_id
                WHERE d.department_name = %s AND c.is_active = 1
                ORDER BY c.course_name
            """, (dept_name,))
            courses = cursor.fetchall()
            cursor.close()
            conn.close()
            
            course_names, _ = build_course_display_values(courses)
            course_names = ["All Courses"] + course_names
            course_dropdown['values'] = course_names
            course_dropdown.current(0)
        except:
            course_dropdown['values'] = ["All Courses"]
            course_dropdown.current(0)
    
    dept_dropdown.bind("<<ComboboxSelected>>", load_courses_filter)
    
    # Subject list frame
    list_frame = tk.Frame(content_frame, bg='white')
    list_frame.pack(fill='both', expand=True)
    
    # Treeview with scrollbar
    tree_scroll = tk.Scrollbar(list_frame)
    tree_scroll.pack(side='right', fill='y')
    
    columns = ('ID', 'Subject Name', 'Code', 'Dept', 'Course', 'Sem', 'Credits', 'Active')
    subject_tree = ttk.Treeview(
        list_frame,
        columns=columns,
        show='headings',
        yscrollcommand=tree_scroll.set,
        height=15
    )
    
    tree_scroll.config(command=subject_tree.yview)
    
    # Define column headings and widths
    widths = [50, 220, 100, 150, 150, 60, 70, 70]
    for col, width in zip(columns, widths):
        subject_tree.heading(col, text=col)
        subject_tree.column(col, width=width, anchor='center' if col in ['ID', 'Sem', 'Credits', 'Active'] else 'w')
    
    subject_tree.pack(fill='both', expand=True, padx=10, pady=10)
    
    def load_subjects():
        """Load subjects from database"""
        # Clear existing items
        for item in subject_tree.get_children():
            subject_tree.delete(item)
        
        # Get filter values
        dept_filter = dept_var.get()
        course_filter = course_var.get()
        sem_filter = sem_var.get()
        subject_filter = subject_entry.get().strip()
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Build query with filters
            query = """
                SELECT s.subject_id, s.subject_name, s.subject_code,
                       COALESCE(d.department_name, 'N/A'),
                       COALESCE(c.course_name, 'N/A'),
                       s.semester, s.credits, s.is_active
                FROM subjects s
                LEFT JOIN departments d ON s.department_id = d.department_id
                LEFT JOIN courses c ON s.course_id = c.course_id
                WHERE 1=1
            """
            params = []
            
            if dept_filter != "All Departments":
                query += " AND d.department_name = %s"
                params.append(dept_filter)
            
            if course_filter != "All Courses":
                course_aliases = get_course_aliases(course_filter)
                query += " AND c.course_name IN ({})".format(",".join(["%s"] * len(course_aliases)))
                params.extend(course_aliases)
            
            if sem_filter != "All Semesters":
                query += " AND s.semester = %s"
                params.append(sem_filter)
            
            if subject_filter:
                query += " AND s.subject_name LIKE %s"
                params.append(f"%{subject_filter}%")
            
            query += " ORDER BY d.department_name, c.course_name, s.semester, s.subject_name"
            
            cursor.execute(query, params)
            subjects = cursor.fetchall()
            
            for subject in subjects:
                active_status = "Yes" if subject[7] else "No"
                subject_tree.insert('', 'end', values=(
                    subject[0], subject[1], subject[2], subject[3],
                    subject[4], subject[5], subject[6], active_status
                ))
            
            cursor.close()
            conn.close()

            return subjects
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load subjects: {str(e)}")
            return []

    def search_subjects():
        subjects = load_subjects()
        if len(subjects) == 1:
            subject = subjects[0]
            display_data = (
                subject[0], subject[1], subject[2], subject[3],
                subject[4], subject[5], subject[6], "Yes" if subject[7] else "No"
            )
            open_subject_popup(display_data)
    
    # Search button
    search_btn = tk.Button(
        filter_inner,
        text="🔍 Search",
        font=('Segoe UI', 10, 'bold'),
        bg='#8e44ad',
        fg='white',
        relief='flat',
        cursor='hand2',
        padx=14,
        pady=5,
        command=search_subjects
    )
    search_btn.pack(side='left', padx=5)
    
    # Refresh button
    refresh_btn = tk.Button(
        filter_inner,
        text="🔄 Refresh",
        font=('Segoe UI', 10),
        bg='#95a5a6',
        fg='white',
        relief='flat',
        cursor='hand2',
        padx=14,
        pady=5,
        command=lambda: [subject_entry.delete(0, tk.END), dept_var.set("All Departments"), 
                        course_var.set("All Courses"), sem_var.set("All Semesters"), load_subjects()]
    )
    refresh_btn.pack(side='left', padx=5)

    
    def open_subject_popup(subject_data):
        """Open popup to edit subject details"""
        popup = tk.Toplevel()
        popup.title("Edit Subject")
        popup.geometry("760x560")
        popup.configure(bg='#f5f7fa')
        popup.resizable(False, False)
        
        # Center popup
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() // 2) - (760 // 2)
        y = (popup.winfo_screenheight() // 2) - (560 // 2)
        popup.geometry(f"760x560+{x}+{y}")
        
        # Header
        header = tk.Frame(popup, bg='#8e44ad', height=60)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        tk.Label(
            header,
            text="✏️ Edit Subject Details",
            font=('Segoe UI', 16, 'bold'),
            bg='#8e44ad',
            fg='white'
        ).pack(pady=15)
        
        # Form frame
        form_area = tk.Frame(popup, bg='#f5f7fa')
        form_area.pack(fill='both', expand=True, padx=20, pady=14)

        form_frame = tk.Frame(form_area, bg='white', bd=1, relief='solid')
        form_frame.pack(anchor='center', padx=10, pady=8)
        
        # Get full subject data from database
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.subject_id, s.subject_name, s.subject_code, 
                       s.department_id, s.course_id, s.semester, s.credits, 
                       s.description, s.is_active,
                       d.department_name, c.course_name
                FROM subjects s
                LEFT JOIN departments d ON s.department_id = d.department_id
                LEFT JOIN courses c ON s.course_id = c.course_id
                WHERE s.subject_id = %s
            """, (subject_data[0],))
            full_data = cursor.fetchone()
            cursor.close()
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load subject details: {str(e)}")
            popup.destroy()
            return
        
        if not full_data:
            messagebox.showerror("Error", "Subject not found")
            popup.destroy()
            return
        
        # Load departments and courses
        def load_depts():
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT department_id, department_name FROM departments WHERE is_active = 1")
                depts = cursor.fetchall()
                cursor.close()
                conn.close()
                return depts
            except:
                return []
        
        departments = load_depts()
        dept_dict = {dept[1]: dept[0] for dept in departments}
        dept_names = ["Select Department"] + [dept[1] for dept in departments]
        
        course_dict = {}
        
        # Form fields
        row = 0
        
        # Subject ID (read-only)
        tk.Label(form_frame, text="Subject ID:", font=('Segoe UI', 10), bg='white', anchor='w').grid(
            row=row, column=0, sticky='w', pady=8, padx=(0, 10))
        tk.Label(form_frame, text=str(full_data[0]), font=('Segoe UI', 10, 'bold'), bg='white', fg='#7f8c8d').grid(
            row=row, column=1, sticky='w', pady=8)
        row += 1
        
        # Department
        tk.Label(form_frame, text="Department:", font=('Segoe UI', 10), bg='white', anchor='w').grid(
            row=row, column=0, sticky='w', pady=8, padx=(0, 10))
        dept_var_edit = tk.StringVar(value=full_data[9] if full_data[9] else "Select Department")
        dept_combo = ttk.Combobox(form_frame, textvariable=dept_var_edit, values=dept_names,
                      state='readonly', font=('Segoe UI', 10), width=24)
        dept_combo.grid(row=row, column=1, sticky='w', pady=8)
        row += 1
        
        # Course
        tk.Label(form_frame, text="Course:", font=('Segoe UI', 10), bg='white', anchor='w').grid(
            row=row, column=0, sticky='w', pady=8, padx=(0, 10))
        course_var_edit = tk.StringVar(value=full_data[10] if full_data[10] else "Select Course")
        course_combo = ttk.Combobox(form_frame, textvariable=course_var_edit, values=["Select Course"],
                        state='readonly', font=('Segoe UI', 10), width=24)
        course_combo.grid(row=row, column=1, sticky='w', pady=8)
        row += 1
        
        def load_courses_edit(event=None):
            """Load courses for edit popup"""
            dept_name = dept_var_edit.get()
            
            if dept_name == "Select Department":
                course_combo['values'] = ["Select Course"]
                course_combo.current(0)
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
                course_combo['values'] = course_names
                
                # Keep current value if exists
                current_aliases = get_course_aliases(full_data[10]) if full_data[10] else []
                existing_value = next((alias for alias in current_aliases if alias in course_names), None)
                if existing_value:
                    course_var_edit.set(existing_value)
                elif full_data[10] and full_data[10] in course_names:
                    course_var_edit.set(full_data[10])
                else:
                    course_combo.current(0)
            except Exception as e:
                print(f"Error loading courses: {e}")
        
        dept_combo.bind("<<ComboboxSelected>>", load_courses_edit)
        load_courses_edit()  # Initial load
        
        # Semester
        tk.Label(form_frame, text="Semester:", font=('Segoe UI', 10), bg='white', anchor='w').grid(
            row=row, column=0, sticky='w', pady=8, padx=(0, 10))
        sem_var_edit = tk.StringVar(value=full_data[5] if full_data[5] else "Select Semester")
        sem_combo = ttk.Combobox(form_frame, textvariable=sem_var_edit, 
                    values=["Select Semester", "I", "II", "III", "IV", "V", "VI", "VII", "VIII"],
                    state='readonly', font=('Segoe UI', 10), width=24)
        sem_combo.grid(row=row, column=1, sticky='w', pady=8)
        row += 1
        
        # Subject Name
        tk.Label(form_frame, text="Subject Name:", font=('Segoe UI', 10), bg='white', anchor='w').grid(
            row=row, column=0, sticky='w', pady=8, padx=(0, 10))
        name_entry = tk.Entry(form_frame, font=('Segoe UI', 10), width=26)
        name_entry.insert(0, full_data[1])
        name_entry.grid(row=row, column=1, sticky='w', pady=8)
        row += 1
        
        # Subject Code
        tk.Label(form_frame, text="Subject Code:", font=('Segoe UI', 10), bg='white', anchor='w').grid(
            row=row, column=0, sticky='w', pady=8, padx=(0, 10))
        code_entry = tk.Entry(form_frame, font=('Segoe UI', 10), width=26)
        code_entry.insert(0, full_data[2])
        code_entry.grid(row=row, column=1, sticky='w', pady=8)
        row += 1
        
        # Credits
        tk.Label(form_frame, text="Credits:", font=('Segoe UI', 10), bg='white', anchor='w').grid(
            row=row, column=0, sticky='w', pady=8, padx=(0, 10))
        credits_entry = tk.Entry(form_frame, font=('Segoe UI', 10), width=26)
        credits_entry.insert(0, str(full_data[6]))
        credits_entry.grid(row=row, column=1, sticky='w', pady=8)
        row += 1
        
        # Description
        tk.Label(form_frame, text="Description:", font=('Segoe UI', 10), bg='white', anchor='nw').grid(
            row=row, column=0, sticky='nw', pady=8, padx=(0, 10))
        desc_text = tk.Text(form_frame, font=('Segoe UI', 10), width=26, height=4)
        if full_data[7]:
            desc_text.insert('1.0', full_data[7])
        desc_text.grid(row=row, column=1, sticky='w', pady=8)
        row += 1
        
        # Active status
        tk.Label(form_frame, text="Active Status:", font=('Segoe UI', 10), bg='white', anchor='w').grid(
            row=row, column=0, sticky='w', pady=8, padx=(0, 10))
        is_active_var = tk.BooleanVar(value=(full_data[8] == 1))
        active_check = tk.Checkbutton(form_frame, text="Active", variable=is_active_var, font=('Segoe UI', 10), bg='white')
        active_check.grid(row=row, column=1, sticky='w', pady=8)
        row += 1
        
        def save_changes():
            """Save subject updates"""
            dept_name = dept_var_edit.get()
            course_name = course_var_edit.get()
            semester = sem_var_edit.get()
            subject_name = name_entry.get().strip()
            subject_code = code_entry.get().strip()
            credits = credits_entry.get().strip()
            description = desc_text.get('1.0', tk.END).strip()
            is_active = 1 if is_active_var.get() else 0
            
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
            
            dept_id = dept_dict.get(dept_name)
            course_id = course_dict.get(course_name)
            
            try:
                conn = get_connection()
                cursor = conn.cursor()
                
                # Check for duplicate subject code (excluding current)
                cursor.execute(
                    "SELECT subject_id FROM subjects WHERE subject_code = %s AND subject_id != %s",
                    (subject_code, full_data[0])
                )
                if cursor.fetchone():
                    messagebox.showerror("Error", f"Subject code '{subject_code}' already exists")
                    cursor.close()
                    conn.close()
                    return
                
                # Update subject
                update_sql = """
                    UPDATE subjects 
                    SET subject_name = %s, subject_code = %s, department_id = %s, 
                        course_id = %s, semester = %s, credits = %s, 
                        description = %s, is_active = %s
                    WHERE subject_id = %s
                """
                cursor.execute(update_sql, (
                    subject_name, subject_code, dept_id, course_id, semester, 
                    int(credits), description, is_active, full_data[0]
                ))
                conn.commit()
                
                cursor.close()
                conn.close()
                
                messagebox.showinfo("Success", "Subject updated successfully!")
                popup.destroy()
                load_subjects()
                
                if update_stats_callback:
                    update_stats_callback()
            
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update subject: {str(e)}")
        
        def delete_subject():
            """Delete the subject"""
            confirm = messagebox.askyesno(
                "Confirm Delete",
                f"Are you sure you want to delete subject '{full_data[1]}'?\nThis action cannot be undone."
            )
            
            if confirm:
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    
                    cursor.execute("DELETE FROM subjects WHERE subject_id = %s", (full_data[0],))
                    conn.commit()
                    
                    cursor.close()
                    conn.close()
                    
                    messagebox.showinfo("Success", "Subject deleted successfully!")
                    popup.destroy()
                    load_subjects()
                    
                    if update_stats_callback:
                        update_stats_callback()
                
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to delete subject: {str(e)}")
        
        # Button frame
        btn_frame = tk.Frame(form_frame, bg='white')
        btn_frame.grid(row=row, column=0, columnspan=2, pady=20)
        
        # Save button
        save_btn = tk.Button(
            btn_frame,
            text="💾 Save Changes",
            font=('Segoe UI', 10, 'bold'),
            bg='#1abc9c',
            fg='white',
            relief='flat',
            cursor='hand2',
            padx=20,
            pady=8,
            command=save_changes
        )
        save_btn.pack(side='left', padx=5)
        
        # Delete button
        delete_btn = tk.Button(
            btn_frame,
            text="🗑️ Delete Subject",
            font=('Segoe UI', 10),
            bg='#c0392b',
            fg='white',
            relief='flat',
            cursor='hand2',
            padx=20,
            pady=8,
            command=delete_subject
        )
        delete_btn.pack(side='left', padx=5)
        
        # Close button
        close_btn = tk.Button(
            btn_frame,
            text="Exit",
            font=('Segoe UI', 10),
            bg='#95a5a6',
            fg='white',
            relief='flat',
            cursor='hand2',
            padx=20,
            pady=8,
            command=popup.destroy
        )
        close_btn.pack(side='left', padx=5)
    
    def on_double_click(event):
        """Handle double-click on subject row"""
        selection = subject_tree.selection()
        if selection:
            item = subject_tree.item(selection[0])
            subject_data = item['values']
            open_subject_popup(subject_data)
    
    subject_tree.bind('<Double-1>', on_double_click)
    
    # Initial load
    load_subjects()
