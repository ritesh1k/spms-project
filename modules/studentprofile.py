import tkinter as tk
from tkinter import ttk


TIME_SLOTS = [
    "9:30 - 10:30",
    "10:30-11:30",
    "11:30 - 12:30",
    "12:30-13:30",
    "14:30-15:15",
    "15:15-16:00",
]

WEEK_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


def _normalize_time_component(value):
    text = str(value or "").strip().replace(".", ":")
    if ":" not in text:
        return text
    parts = text.split(":")
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        return text
    return f"{int(parts[0])}:{int(parts[1]):02d}"


def _normalize_slot_key(value):
    text = str(value or "").strip().upper()
    text = text.replace("TO", "-").replace("–", "-").replace("—", "-")
    text = text.replace(" ", "")
    if "-" not in text:
        return text
    left, right = text.split("-", 1)
    left = _normalize_time_component(left)
    right = _normalize_time_component(right)
    return f"{left}-{right}".upper()

def load_student_profile(parent_frame, student_data=None):
    """
    Load the Student Academic Profile UI into the given parent_frame.
    :param parent_frame: Tkinter Frame where the profile should be loaded
    :param student_data: Optional dict with student info, else defaults will be used
    """
    # ---------- Default Student Data ----------
    student = student_data or {
        "name": "N/A",
        "enrollment": "N/A",
        "course": "N/A",
        "semester": "",
        "section": "",
        "batch": "N/A",
        "phone": "N/A",
        "email": "N/A",
        "academic": [],
        "weekly_timetable": [],
        "subject_allocations": [],
    }

    # ---------- Colors ----------
    BG_COLOR = "#eef3f8"
    FRAME_BG = "#ffffff"
    BORDER_COLOR = "#cfe3f1"
    LABEL_COLOR = "#334155"
    VALUE_COLOR = "#0f172a"
    ACCENT = "#0ea5a4"
    MUTED = "#64748b"

    # ---------- Clear Previous Content ----------
    for widget in parent_frame.winfo_children():
        widget.destroy()
    parent_frame.configure(bg=BG_COLOR)

    # ---------- Scrollable Wrapper (Right Scrollbar) ----------
    scroll_host = tk.Frame(parent_frame, bg=BG_COLOR)
    scroll_host.pack(fill="both", expand=True)

    profile_canvas = tk.Canvas(scroll_host, bg=BG_COLOR, highlightthickness=0)
    profile_canvas.pack(side="left", fill="both", expand=True)

    y_scroll = ttk.Scrollbar(scroll_host, orient="vertical", command=profile_canvas.yview)
    y_scroll.pack(side="right", fill="y")
    profile_canvas.configure(yscrollcommand=y_scroll.set)

    content_holder = tk.Frame(profile_canvas, bg=BG_COLOR)
    canvas_window = profile_canvas.create_window((0, 0), window=content_holder, anchor="nw")

    def _sync_scroll_region(_event=None):
        profile_canvas.configure(scrollregion=profile_canvas.bbox("all"))

    def _fit_content_width(event):
        profile_canvas.itemconfigure(canvas_window, width=event.width)

    content_holder.bind("<Configure>", _sync_scroll_region)
    profile_canvas.bind("<Configure>", _fit_content_width)

    def _on_mousewheel(event):
        profile_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    profile_canvas.bind("<Enter>", lambda _e: profile_canvas.bind_all("<MouseWheel>", _on_mousewheel))
    profile_canvas.bind("<Leave>", lambda _e: profile_canvas.unbind_all("<MouseWheel>"))

    # ---------- Header ----------
    header_frame = tk.Frame(content_holder, bg="#0f766e", height=72)
    header_frame.pack(fill="x")
    header_frame.pack_propagate(False)
    tk.Label(
        header_frame,
        text=f"Welcome, {student['name']}",
        bg="#0f766e",
        fg="white",
        font=("Segoe UI", 16, "bold")
    ).pack(anchor="w", padx=18, pady=(10, 0))
    tk.Label(
        header_frame,
        text="Student Academic Profile",
        bg="#0f766e",
        fg="#d1fae5",
        font=("Segoe UI", 10),
    ).pack(anchor="w", padx=18, pady=(0, 10))

    # ---------- Personal Details Section ----------
    personal_frame = tk.Frame(
        content_holder,
        bg=FRAME_BG,
        bd=1,
        relief="solid",
        highlightbackground=BORDER_COLOR,
        highlightcolor=BORDER_COLOR,
        highlightthickness=1,
        padx=15,
        pady=15
    )
    personal_frame.pack(fill="x", padx=16, pady=10)

    tk.Label(
        personal_frame,
        text="Personal Details",
        font=("Segoe UI", 12, "bold"),
        bg=FRAME_BG,
        fg=ACCENT,
    ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0,15))

    label_style = {"font": ("Segoe UI", 11), "bg": FRAME_BG, "fg": LABEL_COLOR}
    value_style = {"font": ("Segoe UI", 11), "bg": FRAME_BG, "fg": VALUE_COLOR}

    # ---------- Two-column layout with spacing using column weights ----------
    pady_value = 8  # vertical spacing

    # Configure columns to spread out left and right
    personal_frame.grid_columnconfigure(0, weight=1)
    personal_frame.grid_columnconfigure(1, weight=2)
    personal_frame.grid_columnconfigure(2, weight=1)
    personal_frame.grid_columnconfigure(3, weight=2)

    # Row 1
    tk.Label(personal_frame, text="Name:", **label_style).grid(row=1, column=0, sticky="w", pady=pady_value)
    tk.Label(personal_frame, text=student["name"], **value_style).grid(row=1, column=1, sticky="w", pady=pady_value)

    tk.Label(personal_frame, text="Enrollment No.:", **label_style).grid(row=1, column=2, sticky="w", pady=pady_value)
    tk.Label(personal_frame, text=student["enrollment"], **value_style).grid(row=1, column=3, sticky="w", pady=pady_value)

    # Row 2
    tk.Label(personal_frame, text="Course:", **label_style).grid(row=2, column=0, sticky="w", pady=pady_value)
    tk.Label(personal_frame, text=student["course"], **value_style).grid(row=2, column=1, sticky="w", pady=pady_value)

    tk.Label(personal_frame, text="Batch:", **label_style).grid(row=2, column=2, sticky="w", pady=pady_value)
    tk.Label(personal_frame, text=student["batch"], **value_style).grid(row=2, column=3, sticky="w", pady=pady_value)

    # Row 3
    tk.Label(personal_frame, text="Phone:", **label_style).grid(row=3, column=0, sticky="w", pady=pady_value)
    tk.Label(personal_frame, text=student["phone"], **value_style).grid(row=3, column=1, sticky="w", pady=pady_value)

    tk.Label(personal_frame, text="Email:", **label_style).grid(row=3, column=2, sticky="w", pady=pady_value)
    tk.Label(personal_frame, text=student["email"], **value_style).grid(row=3, column=3, sticky="w", pady=pady_value)

    # ---------- Academic Performance Table ----------
    table_frame = tk.Frame(
        content_holder,
        bg=FRAME_BG,
        bd=1,
        relief="solid",
        highlightbackground=BORDER_COLOR,
        highlightcolor=BORDER_COLOR,
        highlightthickness=1,
        padx=10,
        pady=10
    )
    table_frame.pack(fill="x", padx=16, pady=8)

    tk.Label(
        table_frame,
        text="Academic Performance",
        font=("Segoe UI", 12, "bold"),
        fg=ACCENT,
        bg=FRAME_BG,
    ).pack(anchor="w", pady=(0, 10))

    table_style = ttk.Style()
    table_style.configure("Profile.Treeview", rowheight=25, font=("Segoe UI", 9))
    table_style.configure("Profile.Treeview.Heading", font=("Segoe UI", 9, "bold"))

    columns = ("Semester", "Total Credits", "Status", "SGPA")
    tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=6, style="Profile.Treeview")
    tree.pack(fill="both", expand=True, padx=5, pady=5)

    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, anchor="center", width=100)

    for row in student["academic"]:
        tree.insert("", "end", values=(row["semester"], row["credits"], row.get("status", "N/A"), row["sgpa"]))

    # ---------- CGPA Calculation ----------
    def calculate_cgpa():
        total_points = sum([row["sgpa"] * row["credits"] for row in student["academic"]])
        total_credits = sum([row["credits"] for row in student["academic"]])
        return round(total_points / total_credits, 2) if total_credits > 0 else 0

    student["total_cgpa"] = calculate_cgpa()
    student["total_percentage"] = round(float(student["total_cgpa"]) * 9.5, 2)

    # Keep cumulative details directly below Academic Performance.
    summary_frame = tk.Frame(table_frame, bg="#f0fdfa", bd=1, relief="solid", highlightbackground="#99f6e4", highlightthickness=1)
    summary_frame.pack(fill="x", padx=5, pady=(8, 2))

    tk.Label(
        summary_frame,
        text="Overall CGPA",
        font=("Segoe UI", 10, "bold"),
        bg="#f0fdfa",
        fg="#115e59",
    ).pack(anchor="w", padx=12, pady=(8, 2))

    tk.Label(
        summary_frame,
        text=f"{student['total_cgpa']}",
        font=("Segoe UI", 16, "bold"),
        bg="#f0fdfa",
        fg="#0f766e",
    ).pack(anchor="w", padx=12, pady=(0, 4))

    tk.Label(
        summary_frame,
        text=f"Percentage: {student['total_percentage']}%",
        font=("Segoe UI", 11, "bold"),
        bg="#f0fdfa",
        fg="#115e59",
    ).pack(anchor="w", padx=12, pady=(0, 10))

    # ---------- Weekly Timetable ----------
    timetable_frame = tk.Frame(
        content_holder,
        bg=FRAME_BG,
        bd=1,
        relief="solid",
        highlightbackground=BORDER_COLOR,
        highlightcolor=BORDER_COLOR,
        highlightthickness=1,
        padx=10,
        pady=10,
    )
    timetable_frame.pack(fill="x", padx=16, pady=8)

    section_text = str(student.get("section", "")).strip().upper() or "N/A"
    semester_text = str(student.get("semester", "")).strip() or "N/A"

    tk.Label(
        timetable_frame,
        text=f"Current Sem Time Table with Sec {section_text}",
        font=("Segoe UI", 12, "bold"),
        fg=ACCENT,
        bg=FRAME_BG,
    ).pack(anchor="w", pady=(0, 6))

    tk.Label(
        timetable_frame,
        text=f"Semester: {semester_text}",
        font=("Segoe UI", 10),
        bg=FRAME_BG,
        fg=MUTED,
    ).pack(anchor="w", pady=(0, 10))

    timetable_grid = tk.Frame(timetable_frame, bg=FRAME_BG)
    timetable_grid.pack(fill="x")

    slot_key_to_label = {_normalize_slot_key(slot): slot for slot in TIME_SLOTS}
    schedule_map = {day: {slot: "-" for slot in TIME_SLOTS} for day in WEEK_DAYS}

    for item in student.get("weekly_timetable", []):
        day_name = str(item.get("day", "")).strip().title()
        code = str(item.get("subject_code", "")).strip() or "-"
        slot_key = _normalize_slot_key(item.get("time", ""))
        slot_label = slot_key_to_label.get(slot_key)
        if not day_name or day_name not in schedule_map or not slot_label:
            continue
        current_value = schedule_map[day_name][slot_label]
        if current_value == "-":
            schedule_map[day_name][slot_label] = code
        elif code != "-" and code not in current_value.split("/"):
            schedule_map[day_name][slot_label] = f"{current_value}/{code}"

    tk.Label(
        timetable_grid,
        text="Day",
        font=("Segoe UI", 10, "bold"),
        bg="#eaf6f4",
        fg="#2c3e50",
        bd=1,
        relief="solid",
        padx=6,
        pady=6,
    ).grid(row=0, column=0, sticky="nsew")

    for col_index, slot in enumerate(TIME_SLOTS, start=1):
        tk.Label(
            timetable_grid,
            text=slot,
            font=("Segoe UI", 9, "bold"),
            bg="#eaf6f4",
            fg="#2c3e50",
            bd=1,
            relief="solid",
            padx=6,
            pady=6,
        ).grid(row=0, column=col_index, sticky="nsew")

    for row_index, day in enumerate(WEEK_DAYS, start=1):
        tk.Label(
            timetable_grid,
            text=day,
            font=("Segoe UI", 9, "bold"),
            bg="#f7fbfa",
            fg="#2c3e50",
            bd=1,
            relief="solid",
            padx=6,
            pady=6,
        ).grid(row=row_index, column=0, sticky="nsew")

        for col_index, slot in enumerate(TIME_SLOTS, start=1):
            tk.Label(
                timetable_grid,
                text=schedule_map[day][slot],
                font=("Segoe UI", 9),
                bg="white",
                fg="#34495e",
                bd=1,
                relief="solid",
                padx=4,
                pady=4,
                wraplength=90,
                justify="center",
            ).grid(row=row_index, column=col_index, sticky="nsew")

    for col_index in range(len(TIME_SLOTS) + 1):
        timetable_grid.grid_columnconfigure(col_index, weight=1)

    tk.Label(
        timetable_frame,
        text="Subject Name / Subject Code / Teacher Name",
        font=("Segoe UI", 11, "bold"),
        fg=ACCENT,
        bg=FRAME_BG,
    ).pack(anchor="w", pady=(12, 6))

    subject_tree = ttk.Treeview(
        timetable_frame,
        columns=("subject_name", "subject_code", "teacher_name"),
        show="headings",
        height=5,
        style="Profile.Treeview",
    )
    subject_tree.pack(fill="x", pady=(0, 6))

    subject_tree.heading("subject_name", text="Subject Name")
    subject_tree.heading("subject_code", text="Subject Code")
    subject_tree.heading("teacher_name", text="Teacher Name")

    subject_tree.column("subject_name", anchor="w", width=260)
    subject_tree.column("subject_code", anchor="center", width=150)
    subject_tree.column("teacher_name", anchor="w", width=240)

    subject_rows = student.get("subject_allocations", [])
    if not subject_rows:
        subject_tree.insert("", "end", values=("No assigned subject found for this section.", "-", "-"))
    else:
        for row in subject_rows:
            subject_tree.insert(
                "",
                "end",
                values=(
                    row.get("subject_name", ""),
                    row.get("subject_code", ""),
                    row.get("teacher_name", "N/A"),
                ),
            )

    bottom_space = tk.Frame(content_holder, bg=BG_COLOR, height=6)
    bottom_space.pack(fill="x")


# ========== Standalone Test ==========
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Student Profile")
    root.geometry("800x600")
    load_student_profile(root)
    root.mainloop()