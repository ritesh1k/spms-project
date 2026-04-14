import os
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from auth_utils import (
    generate_temp_password,
    hash_password,
    normalize_email as _normalize_email,
    should_upgrade_password,
    valid_email,
    verify_password,
)
from db_config import get_connection
from login.dashboard import open_dashboard
from modules.sync_legacy_accounts import run_one_time_sync

_BG_IMAGE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bg.png")
_PLACEHOLDER_FG = "#8da0bc"
_INPUT_FG = "#1f2f4a"

def _apply_bg(canvas):
    """Draw image.png stretched to canvas size. Falls back to a solid color."""
    try:
        from PIL import Image, ImageTk
        raw = Image.open(_BG_IMAGE_PATH)

        def _resize(event, c=canvas, r=raw):
            w = max(event.width, 1)
            h = max(event.height, 1)
            img = r.resize((w, h), Image.LANCZOS)
            c._photo = ImageTk.PhotoImage(img)
            if hasattr(c, "_img_id"):
                c.itemconfig(c._img_id, image=c._photo)
            else:
                c._img_id = c.create_image(0, 0, anchor="nw", image=c._photo)
                c.tag_lower(c._img_id)

        canvas.bind("<Configure>", _resize)
    except Exception:
        canvas.configure(bg="#0f2a4d")

def _create_auth_card(parent, relx=0.5, rely=0.5):
    """Create framed login/signup/forgot container similar across auth pages."""
    border = tk.Frame(parent, bg="#7ec8ff", padx=2, pady=2)
    card = tk.Frame(border, bg="#eaf4ff", padx=28, pady=28)
    card.pack(fill="both", expand=True)
    border.place(relx=relx, rely=rely, anchor="center")
    return card

def _create_icon_entry(parent, icon_text, width=32, show=None):
    """Create an input row with a left icon and return (container, entry)."""
    wrap = tk.Frame(parent, bg="#f2f7ff", bd=1, relief="solid")
    tk.Label(
        wrap,
        text=icon_text,
        font=("Segoe UI Emoji", 11),
        bg="#f2f7ff",
        fg="#90a4c2",
        width=2,
    ).pack(side="left", padx=(8, 2))

    entry = tk.Entry(
        wrap,
        width=width,
        font=("Segoe UI", 10),
        bd=0,
        bg="#f2f7ff",
        fg=_INPUT_FG,
        show=show,
    )
    entry.pack(side="left", fill="x", expand=True, padx=(0, 10), pady=6)
    return wrap, entry

def _add_placeholder(entry, placeholder, is_password=False):
    """Set placeholder text with focus behavior and delayed password masking."""
    entry.delete(0, tk.END)
    entry.insert(0, placeholder)
    entry.config(fg=_PLACEHOLDER_FG, show="")

    def _focus_in(_event=None):
        if entry.cget("fg") == _PLACEHOLDER_FG and entry.get() == placeholder:
            entry.delete(0, tk.END)
            entry.config(fg=_INPUT_FG)
            if is_password:
                entry.config(show="*")

    def _focus_out(_event=None):
        if not entry.get().strip():
            entry.delete(0, tk.END)
            entry.insert(0, placeholder)
            entry.config(fg=_PLACEHOLDER_FG, show="")
        elif is_password:
            entry.config(show="*")

    entry.bind("<FocusIn>", _focus_in)
    entry.bind("<FocusOut>", _focus_out)

def _entry_value(entry, placeholder):
    """Return empty value when field is still showing placeholder."""
    value = entry.get().strip()
    if entry.cget("fg") == _PLACEHOLDER_FG and value == placeholder:
        return ""
    return value


def _normalize_date_text(value):
    """Normalize various date inputs to YYYY-MM-DD for DOB comparison."""
    text = str(value or "").strip()
    if not text:
        return ""

    formats = (
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%d.%m.%Y",
    )
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Support accidental datetime text like YYYY-MM-DD HH:MM:SS
    trimmed = text[:10]
    try:
        return datetime.strptime(trimmed, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        return ""


def _email_local_part(value):
    normalized = _normalize_email(value)
    if "@" in normalized:
        return normalized.split("@", 1)[0].strip()
    return normalized


def _fetch_student_from_dob(cursor, email, dob_input):
    """Fallback auth path: allow student login when password is DOB."""
    normalized_dob = _normalize_date_text(dob_input)
    if not normalized_dob:
        return None

    normalized_email = _normalize_email(email)
    email_local = _email_local_part(email)

    cursor.execute(
        """
        SELECT s.name, s.enrollment_no
        FROM students s
        WHERE (LOWER(TRIM(COALESCE(s.email, '')))=%s
               OR LOWER(SUBSTRING_INDEX(TRIM(COALESCE(s.email, '')), '@', 1))=%s)
          AND DATE_FORMAT(s.dob, '%%Y-%%m-%%d') = %s
        LIMIT 1
        """,
        (normalized_email, email_local, normalized_dob),
    )
    student_row = cursor.fetchone()
    if not student_row:
        return None

    student_name = str(student_row[0] or "").strip() or "student"
    enrollment_no = str(student_row[1] or "").strip()

    # Prefer mapped users account if present.
    if enrollment_no:
        cursor.execute(
            """
            SELECT username, enrollment_no
            FROM users
            WHERE role='student' AND enrollment_no=%s
            LIMIT 1
            """,
            (enrollment_no,),
        )
        user_row = cursor.fetchone()
        if user_row:
            return (str(user_row[0] or student_name).strip() or student_name, "student", str(user_row[1] or enrollment_no).strip())

    cursor.execute(
        """
        SELECT username, enrollment_no
        FROM users
        WHERE role='student'
          AND (LOWER(TRIM(COALESCE(email, '')))=%s
               OR LOWER(SUBSTRING_INDEX(TRIM(COALESCE(email, '')), '@', 1))=%s)
        ORDER BY CASE WHEN enrollment_no=%s THEN 0 ELSE 1 END
        LIMIT 1
        """,
        (normalized_email, email_local, enrollment_no),
    )
    user_row = cursor.fetchone()
    if user_row:
        return (
            str(user_row[0] or student_name).strip() or student_name,
            "student",
            str(user_row[1] or enrollment_no).strip(),
        )

    return (student_name, "student", enrollment_no)


def _fetch_teacher_from_dob(cursor, email, dob_input):
    """Fallback auth path: allow teacher login when password is DOB."""
    normalized_dob = _normalize_date_text(dob_input)
    if not normalized_dob:
        return None

    normalized_email = _normalize_email(email)
    email_local = _email_local_part(email)

    cursor.execute(
        """
        SELECT username
        FROM teachers
        WHERE (LOWER(TRIM(COALESCE(email, '')))=%s
               OR LOWER(SUBSTRING_INDEX(TRIM(COALESCE(email, '')), '@', 1))=%s)
          AND DATE_FORMAT(dob, '%%Y-%%m-%%d') = %s
        LIMIT 1
        """,
        (normalized_email, email_local, normalized_dob),
    )
    row = cursor.fetchone()
    if not row:
        return None

    username = str(row[0] or "").strip()
    if not username:
        return None
    return (username, "teacher", "")


def _fetch_user_by_linked_dob(cursor, email, dob_input):
    """Validate DOB against records linked from users table (handles cross-table email mismatches)."""
    normalized_dob = _normalize_date_text(dob_input)
    if not normalized_dob:
        return None

    normalized_email = _normalize_email(email)
    email_local = _email_local_part(email)

    cursor.execute(
        """
        SELECT username, role, COALESCE(enrollment_no, '')
        FROM users
        WHERE (LOWER(TRIM(COALESCE(email, '')))=%s
               OR LOWER(SUBSTRING_INDEX(TRIM(COALESCE(email, '')), '@', 1))=%s)
          AND role IN ('student', 'teacher')
        ORDER BY CASE role WHEN 'student' THEN 1 ELSE 2 END
        """,
        (normalized_email, email_local),
    )
    candidate_users = cursor.fetchall()
    if not candidate_users:
        return None

    for username, role, enrollment_no in candidate_users:
        uname = str(username or "").strip()
        role_text = str(role or "").strip().lower()
        enroll = str(enrollment_no or "").strip()

        if role_text == "student":
            dob_value = None
            resolved_enrollment = enroll

            if enroll:
                cursor.execute(
                    "SELECT DATE_FORMAT(dob, '%Y-%m-%d'), enrollment_no FROM students WHERE enrollment_no=%s LIMIT 1",
                    (enroll,),
                )
                row = cursor.fetchone()
                if row:
                    dob_value = str(row[0] or "").strip()
                    resolved_enrollment = str(row[1] or enroll).strip()

            if not dob_value:
                cursor.execute(
                    """
                    SELECT DATE_FORMAT(dob, '%Y-%m-%d'), enrollment_no
                    FROM students
                    WHERE LOWER(TRIM(COALESCE(name, ''))) = LOWER(TRIM(%s))
                    ORDER BY CASE WHEN LOWER(TRIM(COALESCE(email, '')))=LOWER(TRIM(%s)) THEN 0 ELSE 1 END
                    LIMIT 1
                    """,
                    (uname, normalized_email),
                )
                row = cursor.fetchone()
                if row:
                    dob_value = str(row[0] or "").strip()
                    resolved_enrollment = str(row[1] or resolved_enrollment).strip()

            if not dob_value:
                cursor.execute(
                    """
                    SELECT DATE_FORMAT(dob, '%Y-%m-%d'), enrollment_no
                    FROM students
                    WHERE (LOWER(TRIM(COALESCE(email, '')))=%s
                           OR LOWER(SUBSTRING_INDEX(TRIM(COALESCE(email, '')), '@', 1))=%s)
                    ORDER BY CASE WHEN LOWER(TRIM(COALESCE(name, ''))) = LOWER(TRIM(%s)) THEN 0 ELSE 1 END
                    LIMIT 1
                    """,
                    (normalized_email, email_local, uname),
                )
                row = cursor.fetchone()
                if row:
                    dob_value = str(row[0] or "").strip()
                    resolved_enrollment = str(row[1] or resolved_enrollment).strip()

            if dob_value == normalized_dob:
                return (uname or "student", "student", resolved_enrollment)

        elif role_text == "teacher":
            cursor.execute(
                """
                SELECT DATE_FORMAT(dob, '%Y-%m-%d')
                FROM teachers
                WHERE username=%s
                   OR LOWER(TRIM(COALESCE(email, '')))=%s
                   OR LOWER(SUBSTRING_INDEX(TRIM(COALESCE(email, '')), '@', 1))=%s
                LIMIT 1
                """,
                (uname, normalized_email, email_local),
            )
            row = cursor.fetchone()
            if row and str(row[0] or "").strip() == normalized_dob:
                return (uname or "teacher", "teacher", "")

    return None

try:
    sync_result = run_one_time_sync()
    if sync_result.get("ran"):
        print(
            "One-time legacy sync completed:",
            f"teachers={sync_result.get('teachers_synced', 0)},",
            f"students={sync_result.get('students_synced', 0)}",
        )
except Exception as sync_error:
    print("Legacy sync skipped:", sync_error)

# ---------------- CENTER WINDOW ----------------
def center_window(window, width, height):
    window.update_idletasks()
    sw = window.winfo_screenwidth()
    sh = window.winfo_screenheight()
    x = (sw // 2) - (width // 2)
    y = (sh // 2) - (height // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")

def apply_responsive_geometry(window, preferred_w, preferred_h, min_w=360, min_h=320):
    window.update_idletasks()
    sw = window.winfo_screenwidth()
    sh = window.winfo_screenheight()
    width = min(preferred_w, max(min_w, int(sw * 0.92)))
    height = min(preferred_h, max(min_h, int(sh * 0.9)))
    center_window(window, width, height)
    window.minsize(min_w, min_h)
# ---------------- SIGNUP WINDOW ----------------
def open_signup():
    signup = tk.Toplevel()
    signup.title("Sign Up")
    apply_responsive_geometry(signup, 450, 650, min_w=390, min_h=520)
    signup.configure(bg="#eaf0ff")

    _su_canvas = tk.Canvas(signup, highlightthickness=0)
    _su_canvas.place(x=0, y=0, relwidth=1, relheight=1)
    _apply_bg(_su_canvas)

    tk.Button(_su_canvas, text="<- Back", bg="#7B61FF", fg="white",
              font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2",
              activebackground="#684FE6", activeforeground="white",
              padx=14, pady=6, command=signup.destroy).place(x=18, y=18)

    card = _create_auth_card(_su_canvas)

    # ---------- REGISTER ----------
    def register():
        username = su_username.get().strip()
        password = _entry_value(su_password, "Enter password")
        role = su_role.get().strip()
        enroll = su_enroll.get().strip() if role == "student" else None
        question = su_question.get().strip()
        answer = su_answer.get().strip()
        mobile = su_mobile.get().strip()
        email = _entry_value(su_email, "Enter email")

        if not all([username, password, role, question, answer, mobile, email]):
            messagebox.showerror("Error", "All fields are required")
            return

        if role == "student" and not enroll:
            messagebox.showerror("Error", "Enrollment number required for students")
            return

        if not mobile.isdigit() or len(mobile) != 10:
            messagebox.showerror("Error", "Enter valid 10-digit mobile number")
            return

        if len(password) < 8:
            messagebox.showerror("Error", "Password must be at least 8 characters")
            return

        if not valid_email(email):
            messagebox.showerror("Error", "Enter a valid email")
            return

        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT 1 FROM users WHERE username=%s", (username,))
            if cursor.fetchone():
                messagebox.showerror("Error", "Username already exists")
                conn.close()
                return

            if role == "student":
                cursor.execute("SELECT 1 FROM students WHERE enrollment_no=%s", (enroll,))
                if not cursor.fetchone():
                    cursor.execute(
                        """
                        INSERT INTO students
                        (name, enrollment_no, course, section, dob, email, phone, semester, department)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """,
                        (
                            username,
                            enroll,
                            "General Course",
                            "A",
                            "2000-01-01",
                            email,
                            mobile,
                            "I",
                            "General",
                        ),
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE students
                        SET email=COALESCE(NULLIF(email, ''), %s),
                            phone=COALESCE(NULLIF(phone, ''), %s)
                        WHERE enrollment_no=%s
                        """,
                        (email, mobile, enroll),
                    )

            elif role == "teacher":
                cursor.execute(
                    "SELECT 1 FROM teachers WHERE username=%s OR email=%s",
                    (username, email),
                )
                if not cursor.fetchone():
                    cursor.execute(
                        """
                        INSERT INTO teachers
                        (username, full_name, email, phone, dob, gender, department, designation,
                         qualification, specialization, experience_years, date_of_joining, address, role)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """,
                        (
                            username,
                            username,
                            email,
                            mobile,
                            "1990-01-01",
                            "Other",
                            "General",
                            "Teacher",
                            "Not Provided",
                            None,
                            0,
                            "2020-01-01",
                            "Not Provided",
                            "teacher",
                        ),
                    )

            cursor.execute(
                """INSERT INTO users 
                   (username, password, role, enrollment_no,
                    security_question, security_answer, mobile, email)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (username, password, role, enroll,
                 question, answer, mobile, email)
            )

            conn.commit()
            messagebox.showinfo("Success", "Account created successfully!")
            signup.destroy()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Error", f"Registration failed: {str(e)}")
        finally:
            conn.close()

    # ---------- UI ----------
    tk.Label(card, text="Welcome to SPMS", font=("Segoe UI", 10),
             bg="#eaf4ff", fg="#1976D2").pack(pady=(4, 0))
    tk.Label(card, text="Sign Up to SPMS", font=("Segoe UI", 18, "bold"),
             bg="#eaf4ff", fg="#102442").pack(pady=(0, 12))

    def field(label):
        tk.Label(card, text=label, bg="#eaf4ff", fg="#555555",
                 font=("Segoe UI", 9, "bold"), anchor="w").pack(fill="x", pady=(5, 0))

    field("Username")
    su_username = tk.Entry(card, width=40)
    su_username.pack(fill="x", pady=5)

    field("Password")
    su_password_wrap, su_password = _create_icon_entry(card, "🔒", width=36, show="*")
    su_password_wrap.pack(fill="x", pady=5)
    _add_placeholder(su_password, "Enter password", is_password=True)

    field("Role")
    su_role = tk.StringVar(value="student")
    role_menu = tk.OptionMenu(card, su_role, "admin", "teacher", "student")
    role_menu.pack(fill="x", pady=5)

    field("Enrollment No (Students only)")
    su_enroll = tk.Entry(card, width=40)
    su_enroll.pack(fill="x", pady=5)

    def toggle_enroll(*args):
        if su_role.get() == "student":
            su_enroll.config(state="normal")
        else:
            su_enroll.delete(0, tk.END)
            su_enroll.config(state="disabled")

    su_role.trace_add("write", toggle_enroll)
    toggle_enroll()

    field("Security Question")
    questions = [
        "What is your pet's name?",
        "What is your mother's maiden name?",
        "What is your favorite color?",
        "What is your birth city?"
    ]
    su_question = tk.StringVar(value=questions[0])
    tk.OptionMenu(card, su_question, *questions).pack(fill="x", pady=5)

    field("Security Answer")
    su_answer = tk.Entry(card, width=40)
    su_answer.pack(fill="x", pady=5)

    field("Mobile Number")
    su_mobile = tk.Entry(card, width=40)
    su_mobile.pack(fill="x", pady=5)

    field("Email")
    su_email_wrap, su_email = _create_icon_entry(card, "✉", width=36)
    su_email_wrap.pack(fill="x", pady=5)
    _add_placeholder(su_email, "Enter email")

    tk.Button(card, text="Create Account  \u2192", bg="#1976D2", fg="white",
              font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2",
              activebackground="#1565C0", activeforeground="white",
              height=2, command=register).pack(fill="x", pady=15)

# ---------------- FORGOT PASSWORD ----------------
def open_forgot():
    forgot = tk.Toplevel()
    forgot.title("Forgot Password")
    apply_responsive_geometry(forgot, 400, 350, min_w=360, min_h=300)
    forgot.configure(bg="#0f2a4d")

    fg_canvas = tk.Canvas(forgot, highlightthickness=0)
    fg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
    _apply_bg(fg_canvas)

    tk.Button(fg_canvas, text="<- Back", bg="#7B61FF", fg="white",
              font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2",
              activebackground="#684FE6", activeforeground="white",
              padx=14, pady=6, command=forgot.destroy).place(x=18, y=18)

    frame = _create_auth_card(fg_canvas)

    tk.Label(frame, text="Welcome Back", font=("Segoe UI", 10),
             bg="#eaf4ff", fg="#1976D2")\
        .grid(row=0, column=0, columnspan=2, pady=(4, 0))
    tk.Label(frame, text="Recover Your Account", font=("Segoe UI", 18, "bold"),
             bg="#eaf4ff", fg="#102442")\
        .grid(row=1, column=0, columnspan=2, pady=(0, 12))

    tk.Label(frame, text="Email Address", bg="#eaf4ff", fg="#555555",
             font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky="w")
    fp_email_wrap, fp_username = _create_icon_entry(frame, "✉", width=22)
    fp_email_wrap.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(3, 10))

    tk.Label(frame, text="Security Answer", bg="#eaf4ff", fg="#555555",
             font=("Segoe UI", 9, "bold")).grid(row=4, column=0, sticky="w")
    fp_answer = tk.Entry(frame, width=25)
    fp_answer.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(3, 10), ipady=4)
    _add_placeholder(fp_username, "Enter email")
    _add_placeholder(fp_answer, "Enter answer")

    def recover():
        email_value = _entry_value(fp_username, "Enter email")
        answer_value = _entry_value(fp_answer, "Enter answer")

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT username, role FROM users WHERE email=%s AND security_answer=%s",
            (email_value, answer_value),
        )
        result = cursor.fetchone()
        if not result:
            conn.close()
            messagebox.showerror("Error", "Invalid details")
            return

        temp_password = generate_temp_password(12)
        cursor.execute(
            "UPDATE users SET password=%s WHERE email=%s AND security_answer=%s",
            (hash_password(temp_password), email_value, answer_value),
        )
        conn.commit()
        conn.close()

        messagebox.showinfo(
            "Recovered",
            "Temporary password created. Please sign in and change your password.\n\n" f"Temporary password: {temp_password}",
        )

    tk.Button(frame, text="Recover Password  ->", bg="#1565C0", fg="white",
              font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2",
              activebackground="#0D47A1", activeforeground="white",
              height=2, command=recover)\
        .grid(row=6, column=0, columnspan=2, pady=10, sticky="ew")

# ---------------- LOGIN ----------------
def reset_login_form():
    entry_email.delete(0, tk.END)
    entry_email.insert(0, "Email Id")
    entry_email.config(fg=_PLACEHOLDER_FG, show="")
    entry_password.delete(0, tk.END)
    entry_password.insert(0, "Password")
    entry_password.config(fg=_PLACEHOLDER_FG, show="")

def login():
    email = _entry_value(entry_email, "Email Id")
    password = _entry_value(entry_password, "Password")

    if not email or not password:
        messagebox.showerror("Login Failed", "Email and Password are required")
        return

    normalized_email = _normalize_email(email)
    email_local = _email_local_part(email)

    conn = None
    cursor = None
    user = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT username, role, enrollment_no, password
            FROM users
            WHERE (LOWER(TRIM(COALESCE(email, '')))=%s
                   OR LOWER(SUBSTRING_INDEX(TRIM(COALESCE(email, '')), '@', 1))=%s)
            ORDER BY
                CASE role
                    WHEN 'student' THEN 1
                    WHEN 'teacher' THEN 2
                    WHEN 'admin' THEN 3
                    ELSE 4
                END
            LIMIT 1
            """,
            (normalized_email, email_local),
        )
        row = cursor.fetchone()
        if row:
            stored_password = str(row[3] or "")
            if verify_password(password, stored_password):
                if should_upgrade_password(stored_password):
                    try:
                        cursor.execute(
                            "UPDATE users SET password=%s WHERE username=%s AND role=%s",
                            (hash_password(password), row[0], row[1]),
                        )
                        conn.commit()
                    except Exception:
                        pass
                user = (str(row[0] or "").strip(), str(row[1] or "").strip(), str(row[2] or "").strip())
            else:
                user = None
        else:
            user = None

        # First validate DOB against records linked from users table.
        if not user:
            user = _fetch_user_by_linked_dob(cursor, normalized_email, password)

        # Then handle admin-created records that may not have a users row.
        if not user:
            user = _fetch_student_from_dob(cursor, normalized_email, password)
        if not user:
            user = _fetch_teacher_from_dob(cursor, normalized_email, password)
    finally:
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except Exception:
            pass

    if user:
        opened = open_dashboard(
            username=user[0],
            role=user[1],
            enrollment=user[2],
            parent=root
        )
        if opened:
            reset_login_form()
            root.withdraw()
    else:
        messagebox.showerror("Login Failed", "Invalid Username or Password")


# ---------------- MAIN LOGIN WINDOW ----------------
root = tk.Tk()
root.title("Login - Student Performance Management System")
apply_responsive_geometry(root, 450, 420, min_w=400, min_h=380)
root.configure(bg="#0f2a4d")

_login_canvas = tk.Canvas(root, highlightthickness=0)
_login_canvas.place(x=0, y=0, relwidth=1, relheight=1)
_apply_bg(_login_canvas)

card = _create_auth_card(_login_canvas)

tk.Label(card, text="Welcome Back", font=("Segoe UI", 10),
         bg="#eaf4ff", fg="#1976D2").grid(row=0, column=0, columnspan=2, pady=(8, 0))
tk.Label(card, text="Sign in to SPMS", font=("Segoe UI", 18, "bold"),
         bg="#eaf4ff", fg="#102442").grid(row=1, column=0, columnspan=2, pady=(0, 14))

login_email_wrap, entry_email = _create_icon_entry(card, "✉", width=30)
login_email_wrap.grid(row=2, column=0, columnspan=2, pady=(4, 10), sticky="ew")
_add_placeholder(entry_email, "Email Id")

login_pwd_wrap, entry_password = _create_icon_entry(card, "🔒", width=30, show="*")
login_pwd_wrap.grid(row=3, column=0, columnspan=2, pady=(0, 12), sticky="ew")
_add_placeholder(entry_password, "Password", is_password=True)

tk.Button(card, text="Sign Up", bg="#1565C0", fg="white",
          font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2",
          activebackground="#0D47A1", activeforeground="white",
          height=2, command=open_signup)\
    .grid(row=4, column=0, padx=(0, 4), pady=(0, 12), sticky="ew")

tk.Button(card, text="Forgot Password", bg="#E65100", fg="white",
          font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2",
          activebackground="#BF360C", activeforeground="white",
          height=2, command=open_forgot)\
    .grid(row=4, column=1, padx=(4, 0), pady=(0, 12), sticky="ew")

tk.Button(card, text="Sign In  \u2192", bg="#2E7D32", fg="white",
          font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2",
          activebackground="#1B5E20", activeforeground="white",
          height=2, command=login)\
    .grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 6))

root.mainloop()
