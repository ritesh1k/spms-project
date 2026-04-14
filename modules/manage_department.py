import tkinter as tk
from tkinter import ttk, messagebox
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
        text="🏢 Manage Departments",
        font=("Segoe UI", 16, "bold"),
        bg="#1abc9c",
        fg="white",
    ).pack(pady=12)

    content_frame = tk.Frame(parent_frame, bg="#f5f7fa")
    content_frame.pack(fill="both", expand=True, padx=20, pady=20)

    filter_frame = tk.Frame(content_frame, bg="white", bd=1, relief="solid")
    filter_frame.pack(fill="x", padx=10, pady=(0, 10))

    filter_inner = tk.Frame(filter_frame, bg="white")
    filter_inner.pack(pady=8)

    tk.Label(filter_inner, text="Department Name:", bg="white").grid(row=0, column=0, padx=(8, 4), pady=5, sticky="w")
    name_entry = tk.Entry(filter_inner, width=20)
    name_entry.grid(row=0, column=1, padx=(0, 10), pady=5)

    tk.Label(filter_inner, text="Department Code:", bg="white").grid(row=0, column=2, padx=(8, 4), pady=5, sticky="w")
    code_entry = tk.Entry(filter_inner, width=20)
    code_entry.grid(row=0, column=3, padx=(0, 10), pady=5)

    list_frame = tk.Frame(content_frame, bg="white")
    list_frame.pack(fill="both", expand=True, padx=10, pady=10)

    columns = ("department_code", "department_name", "head_of_department", "contact_email", "contact_phone", "established_date", "is_active")
    tree = ttk.Treeview(list_frame, columns=columns, show="headings")

    tree.heading("department_code", text="Code")
    tree.heading("department_name", text="Name")
    tree.heading("head_of_department", text="HOD")
    tree.heading("contact_email", text="Email")
    tree.heading("contact_phone", text="Phone")
    tree.heading("established_date", text="Established")
    tree.heading("is_active", text="Active")

    tree.column("department_code", width=80, anchor="center")
    tree.column("department_name", width=180, anchor="w")
    tree.column("head_of_department", width=150, anchor="w")
    tree.column("contact_email", width=180, anchor="w")
    tree.column("contact_phone", width=110, anchor="center")
    tree.column("established_date", width=110, anchor="center")
    tree.column("is_active", width=70, anchor="center")

    tree.pack(side="left", fill="both", expand=True)

    scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
    tree.configure(yscroll=scrollbar.set)
    scrollbar.pack(side="right", fill="y")

    def load_departments(name_filter="", code_filter=""):
        for row in tree.get_children():
            tree.delete(row)

        conn = get_connection()
        cursor = conn.cursor()

        query = """
            SELECT department_id, department_code, department_name, head_of_department,
                   contact_email, contact_phone, established_date, is_active
            FROM departments
            WHERE 1=1
        """
        params = []

        if name_filter:
            query += " AND department_name LIKE %s"
            params.append(f"%{name_filter}%")

        if code_filter:
            query += " AND department_code LIKE %s"
            params.append(f"%{code_filter}%")

        query += " ORDER BY department_name"

        cursor.execute(query, tuple(params))
        departments = cursor.fetchall()
        conn.close()

        for dept in departments:
            active_text = "Yes" if dept[7] else "No"
            tree.insert("", "end", iid=dept[0], values=(dept[1], dept[2], dept[3] or "", dept[4] or "", dept[5] or "", dept[6] or "", active_text))

        return departments[0] if len(departments) == 1 else None

    def search_departments():
        dept = load_departments(
            name_filter=name_entry.get().strip(),
            code_filter=code_entry.get().strip(),
        )
        if dept:
            open_department_popup(dept)

    tk.Button(
        filter_inner,
        text="Search",
        bg="#3498db",
        fg="white",
        font=("Segoe UI", 10, "bold"),
        command=search_departments,
    ).grid(row=0, column=4, padx=(12, 8), pady=5, sticky="ns")

    def open_department_popup(dept_data):
        dept_id = dept_data[0]

        popup = tk.Toplevel(parent_frame)
        popup.title("Edit Department")
        popup.geometry("760x430")
        popup.resizable(False, False)
        popup.configure(bg="#f5f7fa")

        popup_container = tk.Frame(popup, bg="#f5f7fa")
        popup_container.pack(fill="both", expand=True, padx=16, pady=14)

        form_box = tk.Frame(popup_container, bg="white", bd=1, relief="solid")
        form_box.pack(anchor="center")

        tk.Label(form_box, text="Department Name:", bg="white").grid(row=0, column=0, padx=(16, 6), pady=(12, 6), sticky="w")
        name_edit = tk.Entry(form_box, width=24)
        name_edit.insert(0, dept_data[2] or "")
        name_edit.grid(row=0, column=1, padx=(0, 14), pady=(12, 6), sticky="w")

        tk.Label(form_box, text="Department Code:", bg="white").grid(row=0, column=2, padx=(16, 6), pady=(12, 6), sticky="w")
        code_edit = tk.Entry(form_box, width=24)
        code_edit.insert(0, dept_data[1] or "")
        code_edit.grid(row=0, column=3, padx=(0, 16), pady=(12, 6), sticky="w")

        tk.Label(form_box, text="Head of Department:", bg="white").grid(row=1, column=0, padx=(16, 6), pady=6, sticky="w")
        hod_edit = tk.Entry(form_box, width=24)
        hod_edit.insert(0, dept_data[3] or "")
        hod_edit.grid(row=1, column=1, padx=(0, 14), pady=6, sticky="w")

        tk.Label(form_box, text="Contact Email:", bg="white").grid(row=1, column=2, padx=(16, 6), pady=6, sticky="w")
        email_edit = tk.Entry(form_box, width=24)
        email_edit.insert(0, dept_data[4] or "")
        email_edit.grid(row=1, column=3, padx=(0, 16), pady=6, sticky="w")

        tk.Label(form_box, text="Contact Phone:", bg="white").grid(row=2, column=0, padx=(16, 6), pady=6, sticky="w")
        phone_edit = tk.Entry(form_box, width=24)
        phone_edit.insert(0, dept_data[5] or "")
        phone_edit.grid(row=2, column=1, padx=(0, 14), pady=6, sticky="w")

        tk.Label(form_box, text="Established Date (YYYY-MM-DD):", bg="white").grid(row=2, column=2, padx=(16, 6), pady=6, sticky="w")
        established_edit = tk.Entry(form_box, width=24)
        established_edit.insert(0, str(dept_data[6]) if dept_data[6] else "")
        established_edit.grid(row=2, column=3, padx=(0, 16), pady=6, sticky="w")

        tk.Label(form_box, text="Description:", bg="white").grid(row=3, column=0, padx=(16, 6), pady=6, sticky="w")
        description_edit = tk.Entry(form_box, width=58)
        description_edit.grid(row=3, column=1, columnspan=3, padx=(0, 16), pady=6, sticky="w")

        tk.Label(form_box, text="Active Status:", bg="white").grid(row=4, column=0, padx=(16, 6), pady=(6, 12), sticky="w")
        is_active_var = tk.IntVar(value=dept_data[7] if dept_data[7] is not None else 1)
        tk.Checkbutton(form_box, text="Department is Active", variable=is_active_var, bg="white").grid(row=4, column=1, columnspan=3, padx=(0, 16), pady=(6, 12), sticky="w")

        # Load description from DB
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT description FROM departments WHERE department_id=%s", (dept_id,))
            desc_data = cursor.fetchone()
            conn.close()
            if desc_data and desc_data[0]:
                description_edit.insert(0, desc_data[0])
        except Exception:
            pass

        btn_frame = tk.Frame(popup_container, bg="#f5f7fa")
        btn_frame.pack(pady=12)

        def update_department():
            new_name = name_edit.get().strip()
            new_code = code_edit.get().strip()
            new_hod = hod_edit.get().strip()
            new_email = email_edit.get().strip()
            new_phone = phone_edit.get().strip()
            new_established = established_edit.get().strip()
            new_description = description_edit.get().strip()
            new_active = is_active_var.get()

            if not all([new_name, new_code]):
                messagebox.showwarning("Input Error", "Department Name and Code are required.")
                return

            if new_email and not re.match(r"[^@]+@[^@]+\.[^@]+", new_email):
                messagebox.showwarning("Input Error", "Enter a valid email address.")
                return

            if new_phone and (not new_phone.isdigit() or len(new_phone) != 10):
                messagebox.showwarning("Input Error", "Phone number must be 10 digits.")
                return

            if new_established and not re.match(r"\d{4}-\d{2}-\d{2}$", new_established):
                messagebox.showwarning("Input Error", "Established Date must be in YYYY-MM-DD format.")
                return

            try:
                conn = get_connection()
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT department_id FROM departments WHERE (department_name=%s OR department_code=%s) AND department_id<>%s",
                    (new_name, new_code, dept_id),
                )
                if cursor.fetchone():
                    conn.close()
                    messagebox.showwarning("Duplicate", "Department name or code already exists.")
                    return

                cursor.execute(
                    """
                    UPDATE departments
                    SET department_name=%s, department_code=%s, head_of_department=%s,
                        contact_email=%s, contact_phone=%s, established_date=%s,
                        description=%s, is_active=%s
                    WHERE department_id=%s
                    """,
                    (new_name, new_code, new_hod or None, new_email or None, new_phone or None,
                     new_established or None, new_description or None, new_active, dept_id),
                )
                conn.commit()
                conn.close()

                messagebox.showinfo("Success", "Department updated successfully!")
                popup.destroy()
                load_departments()
                if update_stats_callback:
                    update_stats_callback()

            except Exception as error:
                messagebox.showerror("Error", str(error))

        def delete_department():
            confirm = messagebox.askyesno("Confirm Delete", f"Do you really want to delete {name_edit.get()}?")
            if not confirm:
                return

            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM departments WHERE department_id=%s", (dept_id,))
                conn.commit()
                conn.close()

                messagebox.showinfo("Deleted", "Department deleted successfully!")
                popup.destroy()
                load_departments()
                if update_stats_callback:
                    update_stats_callback()

            except Exception as error:
                messagebox.showerror("Error", str(error))

        tk.Button(btn_frame, text="Update", bg="#1abc9c", fg="white", width=12, command=update_department).pack(side="left", padx=10)
        tk.Button(btn_frame, text="Delete", bg="#c0392b", fg="white", width=12, command=delete_department).pack(side="left", padx=10)
        tk.Button(btn_frame, text="Exit", bg="#95a5a6", fg="white", width=10, command=popup.destroy).pack(side="left", padx=10)

    def open_selected(event):
        selected = tree.focus()
        if selected:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT department_id, department_code, department_name, head_of_department,
                       contact_email, contact_phone, established_date, is_active
                FROM departments WHERE department_id=%s
                """,
                (selected,),
            )
            dept = cursor.fetchone()
            conn.close()
            if dept:
                open_department_popup(dept)

    tree.bind("<Double-1>", open_selected)

    load_departments()
