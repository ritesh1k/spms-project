import tkinter as tk
from tkinter import messagebox, ttk
from db_config import get_connection

BG = "#f4f6f9"
MENU_BG = "#34495e"
HEADER_BG = "#2c3e50"
LOGOUT_RED = "#e74c3c"

# ================= CENTER WINDOW =================
def center_window(win, w, h):
    win.update_idletasks()
    x = (win.winfo_screenwidth() // 2) - (w // 2)
    y = (win.winfo_screenheight() // 2) - (h // 2)
    win.geometry(f"{w}x{h}+{x}+{y}")

# ================= ADMIN DASHBOARD =================
def open_admin_dashboard(username, parent):

    parent.withdraw()

    root = tk.Toplevel(parent)
    root.title("Admin Dashboard")
    root.configure(bg=BG)
    center_window(root, 1200, 650)

    # ================= HEADER =================
    header = tk.Frame(root, bg=HEADER_BG, height=60)
    header.pack(fill="x")

    tk.Label(
        header,
        text="Admin Control Panel",
        bg=HEADER_BG,
        fg="white",
        font=("Segoe UI", 16, "bold")
    ).pack(side="left", padx=20)

    tk.Label(
        header,
        text=f"Admin: {username}",
        bg=HEADER_BG,
        fg="white",
        font=("Segoe UI", 11)
    ).pack(side="right", padx=20)

    # ================= BODY =================
    body = tk.Frame(root, bg=BG)
    body.pack(fill="both", expand=True)

    # ================= LEFT MENU =================
    menu = tk.Frame(body, bg=MENU_BG, width=220)
    menu.pack(side="left", fill="y")

    # ================= CONTENT =================
    content = tk.Frame(body, bg="white")
    content.pack(side="right", fill="both", expand=True, padx=15, pady=15)

    def clear_content():
        for w in content.winfo_children():
            w.destroy()

    # ======================================================
    # 👨‍🎓 MANAGE STUDENTS
    # ======================================================
    def manage_students():
        clear_content()

        tk.Label(
            content, text="Manage Students",
            font=("Arial", 18, "bold"), bg="white"
        ).pack(pady=10)

        tree = ttk.Treeview(
            content,
            columns=("Enroll", "Name", "Course", "Semester", "Email"),
            show="headings"
        )
        tree.pack(fill="both", expand=True, pady=10)

        for col in tree["columns"]:
            tree.heading(col, text=col)
            tree.column(col, width=150)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT enrollment_no, name, course, semester, email FROM students"
        )
        for row in cur.fetchall():
            tree.insert("", "end", values=row)
        conn.close()

    # ======================================================
    # 👩‍🏫 MANAGE TEACHERS
    # ======================================================
    def manage_teachers():
        clear_content()

        tk.Label(
            content, text="Manage Teachers",
            font=("Arial", 18, "bold"), bg="white"
        ).pack(pady=10)

        tree = ttk.Treeview(
            content,
            columns=("ID", "Name", "Department", "Email", "Phone"),
            show="headings"
        )
        tree.pack(fill="both", expand=True, pady=10)

        for col in tree["columns"]:
            tree.heading(col, text=col)
            tree.column(col, width=160)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT teacher_id, name, department, email, phone FROM teachers"
        )
        for row in cur.fetchall():
            tree.insert("", "end", values=row)
        conn.close()

    # ======================================================
    # 📊 VIEW RESULTS
    # ======================================================
    def view_results():
        clear_content()

        tk.Label(
            content, text="Student Results",
            font=("Arial", 18, "bold"), bg="white"
        ).pack(pady=10)

        tree = ttk.Treeview(
            content,
            columns=("Enroll", "Subject", "Marks", "Exam"),
            show="headings"
        )
        tree.pack(fill="both", expand=True, pady=10)

        for col in tree["columns"]:
            tree.heading(col, text=col)
            tree.column(col, width=160)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT enrollment_no, subject, marks, exam FROM results"
        )
        for row in cur.fetchall():
            tree.insert("", "end", values=row)
        conn.close()

    # ======================================================
    # 🚪 LOGOUT
    # ======================================================
    def logout():
        root.destroy()
        parent.deiconify()

    # ================= MENU BUTTON STYLE =================
    btn_style = {
        "bg": MENU_BG,
        "fg": "white",
        "bd": 0,
        "font": ("Arial", 11),
        "anchor": "w",
        "padx": 20,
        "height": 2
    }

    tk.Button(menu, text="👨‍🎓 Manage Students", command=manage_students, **btn_style).pack(fill="x")
    tk.Button(menu, text="👩‍🏫 Manage Teachers", command=manage_teachers, **btn_style).pack(fill="x")
    tk.Button(menu, text="📊 View Results", command=view_results, **btn_style).pack(fill="x")

    tk.Button(
        menu, text="🚪 Logout",
        bg=LOGOUT_RED, fg="white",
        bd=0, height=2,
        command=logout
    ).pack(fill="x", pady=20)

    root.protocol("WM_DELETE_WINDOW", logout)

    manage_students()  # default view
