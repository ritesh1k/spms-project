import tkinter as tk
from tkinter import messagebox
import re
from db_config import get_connection


def load_module(parent_frame, update_stats_callback=None):
    for widget in parent_frame.winfo_children():
        widget.destroy()
    parent_frame.configure(bg="#f5f7fa")

    title_frame = tk.Frame(parent_frame, bg="#1abc9c", height=60)
    title_frame.pack(fill="x")
    title_frame.pack_propagate(False)
    tk.Label(
        title_frame,
        text="🏢 Create Department",
        font=("Segoe UI", 16, "bold"),
        bg="#1abc9c",
        fg="white",
    ).pack(pady=12)

    content_frame = tk.Frame(parent_frame, bg="#f5f7fa")
    content_frame.pack(fill="both", expand=True, padx=20, pady=20)

    form_frame = tk.Frame(
        content_frame,
        bg="white",
        bd=2,
        relief="solid",
        highlightbackground="#1abc9c",
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

    tk.Label(form_frame, text="Department Name:", **label_style).grid(row=0, column=0, sticky="w", pady=5)
    dept_name_entry = tk.Entry(form_frame, **entry_style)
    dept_name_entry.grid(row=0, column=1, padx=10, pady=5)

    tk.Label(form_frame, text="Department Code:", **label_style).grid(row=0, column=2, sticky="w", pady=5)
    dept_code_entry = tk.Entry(form_frame, **entry_style)
    dept_code_entry.grid(row=0, column=3, padx=10, pady=5)

    tk.Label(form_frame, text="Head of Department:", **label_style).grid(row=1, column=0, sticky="w", pady=5)
    hod_entry = tk.Entry(form_frame, **entry_style)
    hod_entry.grid(row=1, column=1, padx=10, pady=5)

    tk.Label(form_frame, text="Contact Email:", **label_style).grid(row=1, column=2, sticky="w", pady=5)
    email_entry = tk.Entry(form_frame, **entry_style)
    email_entry.grid(row=1, column=3, padx=10, pady=5)

    tk.Label(form_frame, text="Contact Phone:", **label_style).grid(row=2, column=0, sticky="w", pady=5)
    phone_entry = tk.Entry(form_frame, **entry_style)
    phone_entry.grid(row=2, column=1, padx=10, pady=5)

    tk.Label(form_frame, text="Established Date (YYYY-MM-DD):", **label_style).grid(row=2, column=2, sticky="w", pady=5)
    established_entry = tk.Entry(form_frame, **entry_style)
    established_entry.grid(row=2, column=3, padx=10, pady=5)

    tk.Label(form_frame, text="Description:", **label_style).grid(row=3, column=0, sticky="w", pady=5)
    description_entry = tk.Entry(form_frame, **entry_style)
    description_entry.grid(row=3, column=1, columnspan=3, padx=10, pady=5, sticky="ew")

    def add_department():
        dept_name = dept_name_entry.get().strip()
        dept_code = dept_code_entry.get().strip()
        hod = hod_entry.get().strip()
        email = email_entry.get().strip()
        phone = phone_entry.get().strip()
        established = established_entry.get().strip()
        description = description_entry.get().strip()

        if not all([dept_name, dept_code]):
            messagebox.showwarning("Input Error", "Department Name and Code are required.")
            return

        if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            messagebox.showwarning("Input Error", "Enter a valid email address.")
            return

        if phone and (not phone.isdigit() or len(phone) != 10):
            messagebox.showwarning("Input Error", "Phone number must be 10 digits.")
            return

        if established and not re.match(r"\d{4}-\d{2}-\d{2}$", established):
            messagebox.showwarning("Input Error", "Established Date must be in YYYY-MM-DD format.")
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT department_id FROM departments WHERE department_name=%s OR department_code=%s", (dept_name, dept_code))
            if cursor.fetchone():
                messagebox.showwarning("Duplicate", "Department name or code already exists.")
                conn.close()
                return

            cursor.execute(
                """
                INSERT INTO departments
                (department_name, department_code, description, head_of_department, contact_email, contact_phone, established_date, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 1)
                """,
                (dept_name, dept_code, description or None, hod or None, email or None, phone or None, established or None),
            )
            conn.commit()
            conn.close()

            messagebox.showinfo("Success", f"Department {dept_name} added successfully!")

            for widget in [dept_name_entry, dept_code_entry, hod_entry, email_entry, phone_entry, established_entry, description_entry]:
                widget.delete(0, tk.END)

            if update_stats_callback:
                update_stats_callback()

        except Exception as error:
            messagebox.showerror("Database Error", str(error))

    tk.Button(form_frame, text="Create Department", command=add_department, **button_style).grid(
        row=4, column=0, columnspan=4, pady=20
    )
