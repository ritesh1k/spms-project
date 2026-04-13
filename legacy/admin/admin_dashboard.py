

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw
import os

# Import student/teacher/department/course/subject/result modules
from modules import create_student, manage_student, create_teacher, manage_teacher, create_department, manage_department, create_course, manage_course, create_subject, manage_subject, assign_subject, manage_result

# ================= DB HELPERS =================
def load_admin_photo(username):
    try:
        from db_config import get_connection
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT photo FROM admin_pic WHERE username=%s", (username,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception as e:
        print("Load admin photo error:", e)
        return None

def update_admin_photo(username, path):
    from db_config import get_connection
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO admin_pic (username, photo)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE photo=%s
    """, (username, path, path))
    conn.commit()
    conn.close()

def get_total_students():
    try:
        from db_config import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM students")
        total = cursor.fetchone()[0]
        conn.close()
        return total
    except:
        return 0

def get_total_teachers():
    try:
        from db_config import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM teachers")
        total = cursor.fetchone()[0]
        conn.close()
        return total
    except:
        try:
            from db_config import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users WHERE role='teacher'")
            total = cursor.fetchone()[0]
            conn.close()
            return total
        except:
            return 0

def get_total_departments():
    try:
        from db_config import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM departments WHERE is_active=1")
        total = cursor.fetchone()[0]
        conn.close()
        return total
    except:
        return 0

def get_total_courses():
    try:
        from db_config import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM courses WHERE is_active=1")
        total = cursor.fetchone()[0]
        conn.close()
        return total
    except:
        return 0

def get_total_subjects():
    try:
        from db_config import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM subjects WHERE is_active=1")
        total = cursor.fetchone()[0]
        conn.close()
        return total
    except:
        return 0

def ensure_admin_announcement_table():
    try:
        from db_config import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_announcements (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(180) NOT NULL,
                message TEXT NOT NULL,
                created_by VARCHAR(100) NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

# ================= DASHBOARD =================
def open_admin_dashboard(username, parent):
    window = tk.Toplevel(parent)
    window.title("Admin Dashboard")
    sw = window.winfo_screenwidth()
    sh = window.winfo_screenheight()
    w = min(1200, max(900, int(sw * 0.92)))
    h = min(700, max(580, int(sh * 0.9)))
    x = (sw // 2) - (w // 2)
    y = (sh // 2) - (h // 2)
    window.geometry(f"{w}x{h}+{x}+{y}")
    window.minsize(860, 560)
    window.configure(bg="#f4f6f8")
    ensure_admin_announcement_table()

    # ================= STYLES =================
    HEADER_BG = "#2c3e50"
    SIDEBAR_BG = "#34495e"
    CONTENT_BG = "#ffffff"
    BTN_BG = "#34495e"
    TEXT_COLOR = "#ecf0f1"

    # ================= HELPER: Circular Avatar =================
    def load_circular_avatar(path=None, size=90):
        if not path or not os.path.exists(path):
            img = Image.new("RGB", (size, size), color="#bdc3c7")
            draw = ImageDraw.Draw(img)
            draw.text((size//4, size//4), "👤", fill="white")
        else:
            img = Image.open(path).resize((size, size))

        mask = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)
        img.putalpha(mask)
        return ImageTk.PhotoImage(img)

    # ================= HEADER =================
    header = tk.Frame(window, bg=HEADER_BG, height=120)
    header.pack(side="top", fill="x")
    header.pack_propagate(False)

    # --------- LEFT: Profile (Avatar only, name removed) ---------
    left_frame = tk.Frame(header, bg=HEADER_BG)
    left_frame.pack(side="left", padx=20, pady=10)

    avatar_lbl = None

    def load_header_avatar():
        nonlocal avatar_lbl
        if avatar_lbl:
            avatar_lbl.destroy()

        photo_path = load_admin_photo(username)
        img = load_circular_avatar(photo_path, size=90)
        avatar_lbl_new = tk.Label(left_frame, image=img, bg=HEADER_BG, cursor="hand2")
        avatar_lbl_new.image = img
        avatar_lbl_new.pack()
        avatar_lbl_new.bind("<Button-1>", open_profile_popup)
        avatar_lbl = avatar_lbl_new

    # --------- CENTER: Title ---------
    title_lbl = tk.Label(header, text="SPMS Admin Panel", bg=HEADER_BG,
                         fg="white", font=("Segoe UI", 18, "bold"))
    title_lbl.pack(side="top", pady=10)

    # --------- RIGHT: Stats ---------
    right_frame = tk.Frame(header, bg=HEADER_BG)
    right_frame.pack(side="right", padx=20, pady=10)

    student_stat_label = tk.Label(right_frame,
                                  text=f"🎓 Students: {get_total_students()}",
                                  bg="#9b59b6", fg="white",
                                  font=("Segoe UI", 9, "bold"),
                                  width=18, height=2)
    student_stat_label.pack(side="left", padx=5)

    department_stat_label = tk.Label(right_frame,
                                     text=f"🏢 Departments: {get_total_departments()}",
                                     bg="#1abc9c", fg="white",
                                     font=("Segoe UI", 9, "bold"),
                                     width=18, height=2)
    department_stat_label.pack(side="left", padx=5)

    teacher_stat_label = tk.Label(right_frame,
                                  text=f"👨‍🏫 Teachers: {get_total_teachers()}", bg="#3498db",
                                  fg="white", font=("Segoe UI", 9, "bold"),
                                  width=18, height=2)
    teacher_stat_label.pack(side="left", padx=5)

    course_stat_label = tk.Label(right_frame,
                                 text=f"📘 Courses: {get_total_courses()}",
                                 bg="#e67e22", fg="white",
                                 font=("Segoe UI", 9, "bold"),
                                 width=18, height=2)
    course_stat_label.pack(side="left", padx=5)

    subject_stat_label = tk.Label(right_frame,
                                  text=f"📚 Subjects: {get_total_subjects()}",
                                  bg="#9b59b6", fg="white",
                                  font=("Segoe UI", 9, "bold"),
                                  width=18, height=2)
    subject_stat_label.pack(side="left", padx=5)

    # Function to refresh total students stat
    def refresh_student_stat():
        student_stat_label.config(text=f"🎓 Students: {get_total_students()}")

    def refresh_teacher_stat():
        teacher_stat_label.config(text=f"👨‍🏫 Teachers: {get_total_teachers()}")

    def refresh_department_stat():
        department_stat_label.config(text=f"🏢 Departments: {get_total_departments()}")

    def refresh_course_stat():
        course_stat_label.config(text=f"📘 Courses: {get_total_courses()}")

    def refresh_subject_stat():
        subject_stat_label.config(text=f"📚 Subjects: {get_total_subjects()}")

    def refresh_all_stats():
        refresh_student_stat()
        refresh_teacher_stat()
        refresh_department_stat()
        refresh_course_stat()
        refresh_subject_stat()

    # ================= PROFILE POPUP =================
    def open_profile_popup(event=None):
        popup = tk.Toplevel(window)
        popup.title("Admin Profile")
        popup.geometry("320x380")
        popup.resizable(False, False)

        img_frame = tk.Frame(popup)
        img_frame.pack(pady=15)

        current_photo_path = load_admin_photo(username)
        try:
            if current_photo_path and os.path.exists(current_photo_path):
                big_img = Image.open(current_photo_path).resize((200, 200))
                big_img = ImageTk.PhotoImage(big_img)
                lbl = tk.Label(img_frame, image=big_img)
                lbl.image = big_img
            else:
                raise FileNotFoundError
        except:
            lbl = tk.Label(img_frame, text="👤", font=("Segoe UI", 80))
        lbl.pack()

        tk.Label(popup, text=username, font=("Segoe UI", 12, "bold")).pack(pady=5)

        def upload_photo():
            path = filedialog.askopenfilename(
                filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All Files", "*.*")]
            )
            if path:
                update_admin_photo(username, path)
                messagebox.showinfo("Success", "Photo uploaded successfully.")
                popup.destroy()
                load_header_avatar()

        def remove_photo():
            update_admin_photo(username, None)
            messagebox.showinfo("Removed", "Photo removed.")
            popup.destroy()
            load_header_avatar()

        btn_frame = tk.Frame(popup)
        btn_frame.pack(pady=15)

        tk.Button(btn_frame, text="Upload Photo", bg="#27ae60", fg="white", width=14, command=upload_photo).pack(pady=5)
        tk.Button(btn_frame, text="Remove Photo", bg="#c0392b", fg="white", width=14, command=remove_photo).pack(pady=5)

    # Initial avatar load
    load_header_avatar()

    # ================= BODY =================
    body = tk.Frame(window, bg="#ddd")
    body.pack(fill="both", expand=True)

    sidebar = tk.Frame(body, bg=SIDEBAR_BG, width=260)
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)

    content_container = tk.Frame(body, bg=CONTENT_BG)
    content_container.pack(side="right", fill="both", expand=True)

    content_canvas = tk.Canvas(content_container, bg=CONTENT_BG, highlightthickness=0)
    content_v_scroll = ttk.Scrollbar(content_container, orient="vertical", command=content_canvas.yview)
    content_h_scroll = ttk.Scrollbar(content_container, orient="horizontal", command=content_canvas.xview)
    content_canvas.configure(yscrollcommand=content_v_scroll.set, xscrollcommand=content_h_scroll.set)

    content_v_scroll.pack(side="right", fill="y")
    content_h_scroll.pack(side="bottom", fill="x")
    content_canvas.pack(side="left", fill="both", expand=True)

    content = tk.Frame(content_canvas, bg=CONTENT_BG)
    content_window_id = content_canvas.create_window((0, 0), window=content, anchor="nw")

    def _update_content_scrollregion(_event=None):
        content_canvas.configure(scrollregion=content_canvas.bbox("all"))

    def _fit_content_to_canvas(event):
        req_w = content.winfo_reqwidth()
        new_w = event.width if req_w < event.width else req_w
        content_canvas.itemconfigure(content_window_id, width=new_w)

    content.bind("<Configure>", _update_content_scrollregion)
    content_canvas.bind("<Configure>", _fit_content_to_canvas)

    def _on_admin_resize(event):
        if event.widget is not window:
            return
        win_w = window.winfo_width()
        if win_w >= 1250:
            sidebar.configure(width=260)
        elif win_w >= 1050:
            sidebar.configure(width=220)
        else:
            sidebar.configure(width=185)

    window.bind("<Configure>", _on_admin_resize)

    def clear_content():
        for widget in content.winfo_children():
            widget.destroy()

    # ================= DEFAULT PAGE =================
    def show_default_page():
        clear_content()
        tk.Label(content, text="Welcome to Admin Dashboard", font=("Segoe UI", 20, "bold"),
                 bg=CONTENT_BG).pack(pady=30)
    show_default_page()

    # ================= SIDEBAR MENUS =================
    def toggle(frame):
        if frame.sub.winfo_ismapped():
            frame.sub.pack_forget()
        else:
            frame.sub.pack(fill="x")

    def create_menu(title, options, icon="", menu_bg=None):
        menu_color = menu_bg if menu_bg else SIDEBAR_BG
        frame = tk.Frame(sidebar, bg=SIDEBAR_BG)
        frame.pack(fill="x", pady=2)

        tk.Button(frame, text=f"{icon} ▶ {title}", bg=menu_color, fg=TEXT_COLOR,
                  font=("Segoe UI", 11, "bold"), bd=0, anchor="w", padx=15,
                  command=lambda: toggle(frame)).pack(fill="x")

        sub = tk.Frame(frame, bg=menu_color)
        for opt in options:
            def load_submodule(option=opt):
                clear_content()
                if title == "Student":
                    if option == "Create Student":
                        create_student.load_module(content, update_stats_callback=refresh_all_stats)
                    elif option == "Manage Students":
                        manage_student.load_module(content, update_stats_callback=refresh_all_stats)
                elif title == "Teacher":
                    if option == "Create Teacher":
                        create_teacher.load_module(content, update_stats_callback=refresh_all_stats)
                    elif option == "Manage Teachers":
                        manage_teacher.load_module(content, update_stats_callback=refresh_all_stats)
                elif title == "Department":
                    if option == "Create Department":
                        create_department.load_module(content, update_stats_callback=refresh_all_stats)
                    elif option == "Manage Departments":
                        manage_department.load_module(content, update_stats_callback=refresh_all_stats)
                elif title == "Course":
                    if option == "Create Course":
                        create_course.load_module(content, update_stats_callback=refresh_all_stats)
                    elif option == "Manage Courses":
                        manage_course.load_module(content, update_stats_callback=refresh_all_stats)
                    else:
                        tk.Label(content, text=f"{option} page coming soon", font=("Segoe UI", 18),
                                 bg=CONTENT_BG).pack(pady=30)
                elif title == "Subject":
                    if option == "Create Subject":
                        create_subject.load_module(content, update_stats_callback=refresh_all_stats)
                    elif option == "Manage Subjects":
                        manage_subject.load_module(content, update_stats_callback=refresh_all_stats)
                    elif option == "Assign Subjects":
                        assign_subject.load_module(content, update_stats_callback=refresh_all_stats)
                    else:
                        tk.Label(content, text=f"{option} page coming soon", font=("Segoe UI", 18),
                                 bg=CONTENT_BG).pack(pady=30)
                elif title == "Result":
                    if option == "Publish Result":
                        manage_result.load_module(content, update_stats_callback=refresh_all_stats)
                    else:
                        tk.Label(content, text=f"{option} page coming soon", font=("Segoe UI", 18),
                                 bg=CONTENT_BG).pack(pady=30)
                elif title == "Announcement":
                    load_announcement_module()
                else:
                    tk.Label(content, text=f"{option} page coming soon", font=("Segoe UI", 18),
                             bg=CONTENT_BG).pack(pady=30)

            tk.Button(sub, text=f"   • {opt}", bg=menu_color, fg=TEXT_COLOR,
                      font=("Segoe UI", 10), bd=0, anchor="w", padx=30, command=load_submodule).pack(fill="x")

        frame.sub = sub

    def load_announcement_module():
        clear_content()

        wrapper = tk.Frame(content, bg=CONTENT_BG)
        wrapper.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(wrapper, text="Admin Announcements", font=("Segoe UI", 18, "bold"), bg=CONTENT_BG, fg="#1f2937").pack(anchor="w", pady=(0, 10))

        form_card = tk.Frame(wrapper, bg="white", bd=1, relief="solid")
        form_card.pack(fill="x", pady=(0, 10))

        tk.Label(form_card, text="Title", bg="white", fg="#334155", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=(12, 4))
        title_entry = tk.Entry(form_card, font=("Segoe UI", 10))
        title_entry.pack(fill="x", padx=12, pady=(0, 8))

        tk.Label(form_card, text="Message", bg="white", fg="#334155", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12)
        message_box = tk.Text(form_card, height=6, font=("Segoe UI", 10))
        message_box.pack(fill="x", padx=12, pady=(0, 10))

        list_card = tk.Frame(wrapper, bg="white", bd=1, relief="solid")
        list_card.pack(fill="both", expand=True)

        tree = ttk.Treeview(list_card, columns=("date", "title", "message", "sender"), show="headings", height=14)
        for col, title, width, anchor in [
            ("date", "Date", 150, "center"),
            ("title", "Title", 240, "w"),
            ("message", "Message", 520, "w"),
            ("sender", "Admin", 120, "center"),
        ]:
            tree.heading(col, text=title)
            tree.column(col, width=width, anchor=anchor)
        tree.pack(fill="both", expand=True, padx=10, pady=10)

        def refresh_admin_announcements():
            for row in tree.get_children():
                tree.delete(row)
            try:
                from db_config import get_connection
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT DATE_FORMAT(created_at, '%Y-%m-%d %H:%i'), title, message, COALESCE(created_by, 'admin')
                    FROM admin_announcements
                    ORDER BY id DESC
                    LIMIT 200
                    """
                )
                rows = cursor.fetchall()
                conn.close()
                for row in rows:
                    tree.insert("", "end", values=row)
            except Exception as err:
                messagebox.showerror("Announcement", str(err))

        def send_admin_announcement():
            title = title_entry.get().strip()
            message = message_box.get("1.0", tk.END).strip()
            if not title or not message:
                messagebox.showwarning("Announcement", "Title and message are required.")
                return
            try:
                from db_config import get_connection
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO admin_announcements (title, message, created_by) VALUES (%s,%s,%s)",
                    (title, message, username),
                )
                conn.commit()
                conn.close()
                title_entry.delete(0, tk.END)
                message_box.delete("1.0", tk.END)
                refresh_admin_announcements()
                messagebox.showinfo("Announcement", "Announcement sent successfully.")
            except Exception as err:
                messagebox.showerror("Announcement", str(err))

        action_row = tk.Frame(form_card, bg="white")
        action_row.pack(fill="x", padx=12, pady=(0, 12))
        tk.Button(action_row, text="Send Announcement", bg="#2563eb", fg="white", bd=0, padx=12, pady=6, command=send_admin_announcement).pack(side="left")
        tk.Button(action_row, text="Refresh List", bg="#64748b", fg="white", bd=0, padx=12, pady=6, command=refresh_admin_announcements).pack(side="left", padx=8)

        refresh_admin_announcements()

    # ================= MENUS =================
    create_menu("Student", ["Create Student", "Manage Students"], "🎓")
    create_menu("Teacher", ["Create Teacher", "Manage Teachers"], "👨‍🏫")
    create_menu("Department", ["Create Department", "Manage Departments"], "🏢")
    create_menu("Course", ["Create Course", "Manage Courses"], "📘")
    create_menu("Subject", ["Create Subject", "Manage Subjects", "Assign Subjects"], "📚")
    create_menu("Result", ["Publish Result"], "📢")
    create_menu("Announcement", ["Send Announcement"], "📣")

    # ================= LOGOUT =================
    def logout():
        result = messagebox.askyesno("Logout", "Are you sure you want to logout?")
        if result:
            window.destroy()
            parent.deiconify()

    tk.Button(sidebar, text="⏻ Logout", bg="#c0392b", fg="white",
              font=("Segoe UI", 11, "bold"), bd=0, pady=10,
              command=logout).pack(side="bottom", fill="x", pady=10)

