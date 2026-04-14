import tkinter as tk
from tkinter import ttk, messagebox
from db_config import get_connection
from modules.course_aliases import canonical_course_name, get_course_aliases

def load_module(parent_frame, update_stats_callback=None):
    """Load Manage Courses module into parent frame"""
    # Clear existing widgets
    for widget in parent_frame.winfo_children():
        widget.destroy()
    
    # Title section
    title_frame = tk.Frame(parent_frame, bg='#e67e22', height=60)
    title_frame.pack(fill='x')
    title_frame.pack_propagate(False)
    
    title_label = tk.Label(
        title_frame,
        text="📘 Manage Courses",
        font=('Segoe UI', 18, 'bold'),
        bg='#e67e22',
        fg='white'
    )
    title_label.pack(pady=15)
    
    # Main content frame
    content_frame = tk.Frame(parent_frame, bg='#f5f7fa')
    content_frame.pack(fill='both', expand=True, padx=20, pady=20)
    
    # Search frame
    search_frame = tk.Frame(content_frame, bg='white', bd=1, relief='solid')
    search_frame.pack(fill='x', pady=(0, 20))
    
    search_inner = tk.Frame(search_frame, bg='white')
    search_inner.pack(pady=12)
    
    # Course Name filter
    tk.Label(
        search_inner,
        text="Course Name:",
        font=('Segoe UI', 10),
        bg='white'
    ).pack(side='left', padx=(0, 10))
    
    name_entry = tk.Entry(search_inner, font=('Segoe UI', 10), width=20)
    name_entry.pack(side='left', padx=(0, 20))
    
    # Department filter
    tk.Label(
        search_inner,
        text="Department:",
        font=('Segoe UI', 10),
        bg='white'
    ).pack(side='left', padx=(0, 10))
    
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
    
    dept_var = tk.StringVar(value="All Departments")
    dept_dropdown = ttk.Combobox(
        search_inner,
        textvariable=dept_var,
        values=load_departments(),
        state='readonly',
        font=('Segoe UI', 10),
        width=18
    )
    dept_dropdown.pack(side='left', padx=(0, 20))
    
    # Course list frame
    list_frame = tk.Frame(content_frame, bg='white')
    list_frame.pack(fill='both', expand=True)
    
    # Treeview with scrollbar
    tree_scroll = tk.Scrollbar(list_frame)
    tree_scroll.pack(side='right', fill='y')
    
    columns = ('ID', 'Course Name', 'Code', 'Department', 'Duration', 'Credits', 'Active')
    course_tree = ttk.Treeview(
        list_frame,
        columns=columns,
        show='headings',
        yscrollcommand=tree_scroll.set,
        height=15
    )
    
    tree_scroll.config(command=course_tree.yview)
    
    # Define column headings and widths
    widths = [50, 250, 100, 180, 100, 80, 80]
    for col, width in zip(columns, widths):
        course_tree.heading(col, text=col)
        course_tree.column(col, width=width, anchor='center' if col in ['ID', 'Credits', 'Active'] else 'w')
    
    course_tree.pack(fill='both', expand=True, padx=10, pady=10)
    
    def load_courses():
        """Load courses from database"""
        # Clear existing items
        for item in course_tree.get_children():
            course_tree.delete(item)
        
        # Get filter values
        name_filter = name_entry.get().strip()
        dept_filter = dept_var.get()
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Build query with filters
            query = """
                SELECT c.course_id, c.course_name, c.course_code, 
                       COALESCE(d.department_name, 'N/A'), c.duration, c.credits, c.is_active
                FROM courses c
                LEFT JOIN departments d ON c.department_id = d.department_id
                WHERE 1=1
            """
            params = []
            
            if name_filter:
                query += " AND c.course_name LIKE %s"
                params.append(f"%{name_filter}%")
            
            if dept_filter != "All Departments":
                query += " AND d.department_name = %s"
                params.append(dept_filter)
            
            query += " ORDER BY c.course_name"
            
            cursor.execute(query, params)
            courses = cursor.fetchall()
            
            for course in courses:
                active_status = "Yes" if course[6] else "No"
                course_tree.insert('', 'end', values=(
                    course[0], course[1], course[2], course[3], 
                    course[4], course[5], active_status
                ))
            
            cursor.close()
            conn.close()

            return courses
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load courses: {str(e)}")
            return []

    def search_courses():
        courses = load_courses()
        if len(courses) == 1:
            course = courses[0]
            display_data = (
                course[0], course[1], course[2], course[3],
                course[4], course[5], "Yes" if course[6] else "No"
            )
            open_course_popup(display_data)
    
    # Search button
    search_btn = tk.Button(
        search_inner,
        text="🔍 Search",
        font=('Segoe UI', 10, 'bold'),
        bg='#e67e22',
        fg='white',
        relief='flat',
        cursor='hand2',
        padx=14,
        pady=5,
        command=search_courses
    )
    search_btn.pack(side='left', padx=5)
    
    # Refresh button
    refresh_btn = tk.Button(
        search_inner,
        text="🔄 Refresh",
        font=('Segoe UI', 10),
        bg='#95a5a6',
        fg='white',
        relief='flat',
        cursor='hand2',
        padx=14,
        pady=5,
        command=lambda: [name_entry.delete(0, tk.END), dept_var.set("All Departments"), load_courses()]
    )
    refresh_btn.pack(side='left', padx=5)
    
    def open_course_popup(course_data):
        """Open popup to edit course details"""
        popup = tk.Toplevel()
        popup.title("Edit Course")
        popup.geometry("760x560")
        popup.configure(bg='#f5f7fa')
        popup.resizable(False, False)
        
        # Center popup
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() // 2) - (760 // 2)
        y = (popup.winfo_screenheight() // 2) - (560 // 2)
        popup.geometry(f"760x560+{x}+{y}")
        
        # Header
        header = tk.Frame(popup, bg='#3498db', height=60)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        tk.Label(
            header,
            text="✏️ Edit Course Details",
            font=('Segoe UI', 16, 'bold'),
            bg='#3498db',
            fg='white'
        ).pack(pady=15)
        
        # Form frame
        form_area = tk.Frame(popup, bg='#f5f7fa')
        form_area.pack(fill='both', expand=True, padx=20, pady=14)

        form_frame = tk.Frame(form_area, bg='white', bd=1, relief='solid')
        form_frame.pack(anchor='center', padx=10, pady=8)
        
        # Load departments
        def load_dept_list():
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
        
        departments = load_dept_list()
        dept_dict = {dept[1]: dept[0] for dept in departments}
        dept_names = ["Select Department"] + [dept[1] for dept in departments]
        
        # Get current department name
        current_dept_id = None
        current_dept_name = "Select Department"
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT department_name FROM departments WHERE department_id = %s", (course_data[3],))
            result = cursor.fetchone()
            if result:
                current_dept_name = result[0]
                current_dept_id = course_data[3]
            cursor.close()
            conn.close()
        except:
            pass
        
        # Form fields
        fields = []
        
        # Course ID (read-only)
        row = 0
        tk.Label(form_frame, text="Course ID:", font=('Segoe UI', 10), bg='white', anchor='w').grid(
            row=row, column=0, sticky='w', pady=8, padx=(0, 10))
        id_label = tk.Label(form_frame, text=str(course_data[0]), font=('Segoe UI', 10, 'bold'), bg='white', fg='#7f8c8d')
        id_label.grid(row=row, column=1, sticky='w', pady=8)
        
        # Course Name
        row += 1
        tk.Label(form_frame, text="Course Name:", font=('Segoe UI', 10), bg='white', anchor='w').grid(
            row=row, column=0, sticky='w', pady=8, padx=(0, 10))
        name_entry = tk.Entry(form_frame, font=('Segoe UI', 10), width=26)
        name_entry.insert(0, course_data[1])
        name_entry.grid(row=row, column=1, sticky='w', pady=8)
        fields.append(("name", name_entry))
        
        # Course Code
        row += 1
        tk.Label(form_frame, text="Course Code:", font=('Segoe UI', 10), bg='white', anchor='w').grid(
            row=row, column=0, sticky='w', pady=8, padx=(0, 10))
        code_entry = tk.Entry(form_frame, font=('Segoe UI', 10), width=26)
        code_entry.insert(0, course_data[2])
        code_entry.grid(row=row, column=1, sticky='w', pady=8)
        fields.append(("code", code_entry))
        
        # Department
        row += 1
        tk.Label(form_frame, text="Department:", font=('Segoe UI', 10), bg='white', anchor='w').grid(
            row=row, column=0, sticky='w', pady=8, padx=(0, 10))
        dept_var_edit = tk.StringVar(value=current_dept_name)
        dept_combo = ttk.Combobox(form_frame, textvariable=dept_var_edit, values=dept_names, 
                                   state='readonly', font=('Segoe UI', 10), width=24)
        dept_combo.grid(row=row, column=1, sticky='w', pady=8)
        fields.append(("department", dept_var_edit))
        
        # Duration
        row += 1
        tk.Label(form_frame, text="Duration:", font=('Segoe UI', 10), bg='white', anchor='w').grid(
            row=row, column=0, sticky='w', pady=8, padx=(0, 10))
        duration_options = ["Select Duration", "1 Year", "2 Years", "3 Years", "4 Years", "5 Years"]
        duration_var = tk.StringVar(value=course_data[4] if course_data[4] else "Select Duration")
        duration_combo = ttk.Combobox(form_frame, textvariable=duration_var, values=duration_options,
                                      state='readonly', font=('Segoe UI', 10), width=24)
        duration_combo.grid(row=row, column=1, sticky='w', pady=8)
        fields.append(("duration", duration_var))
        
        # Credits
        row += 1
        tk.Label(form_frame, text="Credits:", font=('Segoe UI', 10), bg='white', anchor='w').grid(
            row=row, column=0, sticky='w', pady=8, padx=(0, 10))
        credits_entry = tk.Entry(form_frame, font=('Segoe UI', 10), width=26)
        credits_entry.insert(0, str(course_data[5]))
        credits_entry.grid(row=row, column=1, sticky='w', pady=8)
        fields.append(("credits", credits_entry))
        
        # Description
        row += 1
        tk.Label(form_frame, text="Description:", font=('Segoe UI', 10), bg='white', anchor='w').grid(
            row=row, column=0, sticky='nw', pady=8, padx=(0, 10))
        desc_text = tk.Text(form_frame, font=('Segoe UI', 10), width=26, height=4)
        # Load description from database
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT description FROM courses WHERE course_id = %s", (course_data[0],))
            desc_result = cursor.fetchone()
            if desc_result and desc_result[0]:
                desc_text.insert('1.0', desc_result[0])
            cursor.close()
            conn.close()
        except:
            pass
        desc_text.grid(row=row, column=1, sticky='w', pady=8)
        fields.append(("description", desc_text))
        
        # Active status
        row += 1
        tk.Label(form_frame, text="Active Status:", font=('Segoe UI', 10), bg='white', anchor='w').grid(
            row=row, column=0, sticky='w', pady=8, padx=(0, 10))
        is_active_var = tk.BooleanVar(value=(course_data[6] == "Yes"))
        active_check = tk.Checkbutton(
            form_frame,
            text="Active",
            variable=is_active_var,
            font=('Segoe UI', 10),
            bg='white'
        )
        active_check.grid(row=row, column=1, sticky='w', pady=8)
        fields.append(("active", is_active_var))
        
        def save_changes():
            """Save course updates"""
            # Get values
            course_name = canonical_course_name(name_entry.get().strip())
            course_code = code_entry.get().strip()
            dept_name = dept_var_edit.get()
            duration = duration_var.get()
            credits = credits_entry.get().strip()
            description = desc_text.get('1.0', tk.END).strip()
            is_active = 1 if is_active_var.get() else 0
            
            # Validation
            if not course_name:
                messagebox.showerror("Error", "Course name is required")
                return
            
            if not course_code:
                messagebox.showerror("Error", "Course code is required")
                return
            
            if dept_name == "Select Department":
                messagebox.showerror("Error", "Please select a department")
                return
            
            if duration == "Select Duration":
                messagebox.showerror("Error", "Please select duration")
                return
            
            if not credits or not credits.isdigit():
                messagebox.showerror("Error", "Credits must be a valid number")
                return
            
            dept_id = dept_dict.get(dept_name)
            
            try:
                conn = get_connection()
                cursor = conn.cursor()
                
                # Check for duplicate course code (excluding current)
                cursor.execute(
                    "SELECT course_id FROM courses WHERE course_code = %s AND course_id != %s",
                    (course_code, course_data[0])
                )
                if cursor.fetchone():
                    messagebox.showerror("Error", f"Course code '{course_code}' already exists")
                    cursor.close()
                    conn.close()
                    return
                
                # Check for duplicate course name (excluding current)
                name_aliases = get_course_aliases(course_name)
                cursor.execute(
                    "SELECT course_id FROM courses WHERE course_name IN ({}) AND course_id != %s".format(",".join(["%s"] * len(name_aliases))),
                    tuple(name_aliases + [course_data[0]])
                )
                if cursor.fetchone():
                    messagebox.showerror("Error", f"Course name '{course_name}' already exists")
                    cursor.close()
                    conn.close()
                    return
                
                # Update course
                update_sql = """
                    UPDATE courses 
                    SET course_name = %s, course_code = %s, department_id = %s, 
                        duration = %s, credits = %s, description = %s, is_active = %s
                    WHERE course_id = %s
                """
                cursor.execute(update_sql, (
                    course_name, course_code, dept_id, duration, int(credits), 
                    description, is_active, course_data[0]
                ))
                conn.commit()
                
                cursor.close()
                conn.close()
                
                messagebox.showinfo("Success", "Course updated successfully!")
                popup.destroy()
                load_courses()
                
                if update_stats_callback:
                    update_stats_callback()
            
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update course: {str(e)}")
        
        def delete_course():
            """Delete the course"""
            confirm = messagebox.askyesno(
                "Confirm Delete",
                f"Are you sure you want to delete course '{course_data[1]}'?\nThis action cannot be undone."
            )
            
            if confirm:
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    
                    cursor.execute("DELETE FROM courses WHERE course_id = %s", (course_data[0],))
                    conn.commit()
                    
                    cursor.close()
                    conn.close()
                    
                    messagebox.showinfo("Success", "Course deleted successfully!")
                    popup.destroy()
                    load_courses()
                    
                    if update_stats_callback:
                        update_stats_callback()
                
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to delete course: {str(e)}")
        
        # Button frame
        btn_frame = tk.Frame(form_frame, bg='white')
        btn_frame.grid(row=row+1, column=0, columnspan=2, pady=20)
        
        # Update button
        update_btn = tk.Button(
            btn_frame,
            text="✔ Update",
            font=('Segoe UI', 10, 'bold'),
            bg='#1abc9c',
            fg='white',
            relief='flat',
            cursor='hand2',
            padx=20,
            pady=8,
            command=save_changes
        )
        update_btn.pack(side='left', padx=5)
        
        # Delete button
        delete_btn = tk.Button(
            btn_frame,
            text="🗑️ Delete",
            font=('Segoe UI', 10),
            bg='#c0392b',
            fg='white',
            relief='flat',
            cursor='hand2',
            padx=20,
            pady=8,
            command=delete_course
        )
        delete_btn.pack(side='left', padx=5)
        
        # Exit button
        exit_btn = tk.Button(
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
        exit_btn.pack(side='left', padx=5)
    
    def on_double_click(event):
        """Handle double-click on course row"""
        selection = course_tree.selection()
        if selection:
            item = course_tree.item(selection[0])
            course_data = item['values']
            
            # Get full course data from database
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT c.course_id, c.course_name, c.course_code, c.department_id, 
                           c.duration, c.credits, c.is_active
                    FROM courses c
                    WHERE c.course_id = %s
                """, (course_data[0],))
                full_data = cursor.fetchone()
                cursor.close()
                conn.close()
                
                if full_data:
                    # Convert to display format
                    display_data = (
                        full_data[0], full_data[1], full_data[2], full_data[3],
                        full_data[4], full_data[5], "Yes" if full_data[6] else "No"
                    )
                    open_course_popup(display_data)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load course details: {str(e)}")
    
    course_tree.bind('<Double-1>', on_double_click)
    
    # Initial load
    load_courses()
