import tkinter as tk
from tkinter import ttk, messagebox
from db_config import get_connection
from modules.course_aliases import canonical_course_name

def load_module(parent_frame, update_stats_callback=None):
    """Load Create Course module into parent frame"""
    # Clear existing widgets
    for widget in parent_frame.winfo_children():
        widget.destroy()
    
    # Title section
    title_frame = tk.Frame(parent_frame, bg='#e67e22', height=60)
    title_frame.pack(fill='x')
    title_frame.pack_propagate(False)
    
    title_label = tk.Label(
        title_frame,
        text="📘 Create New Course",
        font=('Segoe UI', 18, 'bold'),
        bg='#e67e22',
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
    
    # Define form fields
    fields_data = [
        ("Course Name", "course_name", "text"),
        ("Course Code", "course_code", "text"),
        ("Department", "department", "dropdown"),
        ("Duration", "duration", "dropdown_duration"),
        ("Credits", "credits", "text"),
        ("Description", "description", "textbox")
    ]
    
    widgets = {}
    row = 0
    
    # Load departments for dropdown
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
    dept_dict = {dept[1]: dept[0] for dept in departments}  # name: id mapping
    dept_names = ["Select Department"] + [dept[1] for dept in departments]
    
    duration_options = ["Select Duration", "1 Year", "2 Years", "3 Years", "4 Years", "5 Years"]
    
    for label_text, field_name, field_type in fields_data:
        # Label
        label = tk.Label(
            inner_frame,
            text=label_text + ":",
            font=('Segoe UI', 11),
            bg='white',
            fg='#2c3e50',
            anchor='w'
        )
        label.grid(row=row, column=0, sticky='w', pady=10, padx=(0, 20))
        
        # Input widget
        if field_type == "dropdown":
            department_var = tk.StringVar(value="Select Department")
            dropdown = ttk.Combobox(
                inner_frame,
                textvariable=department_var,
                values=dept_names,
                state='readonly',
                font=('Segoe UI', 10),
                width=40
            )
            dropdown.grid(row=row, column=1, sticky='ew', pady=10)
            widgets[field_name] = department_var
            widgets[field_name + "_dropdown"] = dropdown
        
        elif field_type == "dropdown_duration":
            duration_var = tk.StringVar(value="Select Duration")
            dropdown = ttk.Combobox(
                inner_frame,
                textvariable=duration_var,
                values=duration_options,
                state='readonly',
                font=('Segoe UI', 10),
                width=40
            )
            dropdown.grid(row=row, column=1, sticky='ew', pady=10)
            widgets[field_name] = duration_var
            widgets[field_name + "_dropdown"] = dropdown
        
        elif field_type == "textbox":
            text_widget = tk.Text(
                inner_frame,
                font=('Segoe UI', 10),
                height=4,
                width=42,
                relief='solid',
                bd=1
            )
            text_widget.grid(row=row, column=1, sticky='ew', pady=10)
            widgets[field_name] = text_widget
        
        else:  # text
            entry = tk.Entry(
                inner_frame,
                font=('Segoe UI', 10),
                relief='solid',
                bd=1,
                width=42
            )
            entry.grid(row=row, column=1, sticky='ew', pady=10)
            widgets[field_name] = entry
        
        row += 1
    
    # Configure grid column weight
    inner_frame.columnconfigure(1, weight=1)
    
    # Button frame
    button_frame = tk.Frame(inner_frame, bg='white')
    button_frame.grid(row=row, column=0, columnspan=2, pady=30)
    
    def clear_form():
        """Clear all form fields"""
        for field_widget in widgets.values():
            if isinstance(field_widget, tk.Entry):
                field_widget.delete(0, tk.END)
            elif isinstance(field_widget, tk.Text):
                field_widget.delete('1.0', tk.END)
            elif isinstance(field_widget, tk.StringVar):
                # Skip the dropdown widget references
                pass
        
        # Reset dropdowns
        widgets['department_dropdown'].current(0)
        widgets['duration_dropdown'].current(0)
    
    def save_course():
        """Save course to database"""
        # Get values
        course_name = canonical_course_name(widgets['course_name'].get().strip())
        course_code = widgets['course_code'].get().strip()
        department_name = widgets['department'].get()
        duration = widgets['duration'].get()
        credits = widgets['credits'].get().strip()
        description = widgets['description'].get('1.0', tk.END).strip()
        
        # Validation
        if not course_name:
            messagebox.showerror("Error", "Course name is required")
            return
        
        if not course_code:
            messagebox.showerror("Error", "Course code is required")
            return
        
        if department_name == "Select Department":
            messagebox.showerror("Error", "Please select a department")
            return
        
        if duration == "Select Duration":
            messagebox.showerror("Error", "Please select duration")
            return
        
        if not credits or not credits.isdigit():
            messagebox.showerror("Error", "Credits must be a valid number")
            return
        
        # Get department ID
        department_id = dept_dict.get(department_name)
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Check for duplicate course code
            cursor.execute("SELECT course_id FROM courses WHERE course_code = %s", (course_code,))
            if cursor.fetchone():
                messagebox.showerror("Error", f"Course code '{course_code}' already exists")
                cursor.close()
                conn.close()
                return
            
            # Check for duplicate course name
            cursor.execute("SELECT course_id FROM courses WHERE course_name = %s", (course_name,))
            if cursor.fetchone():
                messagebox.showerror("Error", f"Course name '{course_name}' already exists")
                cursor.close()
                conn.close()
                return
            
            # Insert course
            insert_sql = """
                INSERT INTO courses (course_name, course_code, department_id, duration, credits, description, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_sql, (course_name, course_code, department_id, duration, int(credits), description, 1))
            conn.commit()
            
            cursor.close()
            conn.close()
            
            messagebox.showinfo("Success", f"Course '{course_name}' created successfully!")
            clear_form()
            
            # Update dashboard stats if callback provided
            if update_stats_callback:
                update_stats_callback()
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create course: {str(e)}")
    
    # Create buttons
    save_btn = tk.Button(
        button_frame,
        text="Save Course",
        font=('Segoe UI', 11, 'bold'),
        bg='#e67e22',
        fg='white',
        relief='flat',
        cursor='hand2',
        padx=30,
        pady=10,
        command=save_course
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
