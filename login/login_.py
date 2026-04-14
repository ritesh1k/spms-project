import tkinter as tk
from tkinter import messagebox
from db_config import get_connection
from dashboard import open_dashboard  

# ---------------- CENTER WINDOW ----------------
def center_window(window, width, height):
    window.update_idletasks()
    sw = window.winfo_screenwidth()
    sh = window.winfo_screenheight()
    x = (sw // 2) - (width // 2)
    y = (sh // 2) - (height // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")

# ---------------- SIGNUP WINDOW ----------------
def open_signup():
    signup = tk.Toplevel()
    signup.title("Sign Up")
    center_window(signup, 450, 650)
    signup.configure(bg="#eaf0ff")

    card = tk.Frame(signup, bg="white", padx=30, pady=30)
    card.place(relx=0.5, rely=0.5, anchor="center")

    # ---------- REGISTER ----------
    def register():
        username = su_username.get()
        password = su_password.get()
        role = su_role.get()
        enroll = su_enroll.get() if role == "student" else None
        question = su_question.get()
        answer = su_answer.get()
        mobile = su_mobile.get()
        email = su_email.get()

        if not all([username, password, role, question, answer, mobile, email]):
            messagebox.showerror("Error", "All fields are required")
            return

        if role == "student" and not enroll:
            messagebox.showerror("Error", "Enrollment number required for students")
            return

        if not mobile.isdigit() or len(mobile) != 10:
            messagebox.showerror("Error", "Enter valid 10-digit mobile number")
            return

        if "@" not in email or ".com" not in email:
            messagebox.showerror("Error", "Enter valid email")
            return

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        if cursor.fetchone():
            messagebox.showerror("Error", "Username already exists")
            conn.close()
            return

        cursor.execute(
            """INSERT INTO users 
               (username, password, role, enrollment_no,
                security_question, security_answer, mobile, email)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            (username, password, role, enroll,
             question, answer, mobile, email)
        )
        conn.commit()
        conn.close()

        messagebox.showinfo("Success", "Account created successfully!")
        signup.destroy()

    # ---------- UI ----------
    tk.Label(card, text="Sign Up", font=("Arial", 20, "bold"), bg="white").pack(pady=10)

    def field(label):
        tk.Label(card, text=label, bg="white", anchor="w").pack(fill="x", pady=(5,0))

    field("Username")
    su_username = tk.Entry(card, width=40)
    su_username.pack(fill="x", pady=5)

    field("Password")
    su_password = tk.Entry(card, show="*", width=40)
    su_password.pack(fill="x", pady=5)

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
    su_email = tk.Entry(card, width=40)
    su_email.pack(fill="x", pady=5)

    tk.Button(card, text="Sign Up", bg="#2196F3", fg="white",
              height=2, command=register).pack(fill="x", pady=15)

# ---------------- FORGOT PASSWORD ----------------
def open_forgot():
    forgot = tk.Toplevel()
    forgot.title("Forgot Password")
    center_window(forgot, 400, 350)
    forgot.configure(bg="#f2f6ff")

    frame = tk.Frame(forgot, bg="white", padx=20, pady=20)
    frame.place(relx=0.5, rely=0.5, anchor="center")

    tk.Label(frame, text="Recover Password",
             font=("Arial", 18, "bold"), bg="white")\
        .grid(row=0, column=0, columnspan=2, pady=10)

    tk.Label(frame, text="Username", bg="white").grid(row=1, column=0)
    fp_username = tk.Entry(frame, width=25)
    fp_username.grid(row=1, column=1)

    tk.Label(frame, text="Security Answer", bg="white").grid(row=2, column=0)
    fp_answer = tk.Entry(frame, width=25)
    fp_answer.grid(row=2, column=1)

    def recover():
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT password FROM users WHERE username=%s AND security_answer=%s",
            (fp_username.get(), fp_answer.get())
        )
        result = cursor.fetchone()
        conn.close()

        if result:
            messagebox.showinfo("Recovered", f"Password: {result[0]}")
        else:
            messagebox.showerror("Error", "Invalid details")

    tk.Button(frame, text="Recover", bg="#2196F3", fg="white",
              width=20, command=recover)\
        .grid(row=3, column=0, columnspan=2, pady=15)

# ---------------- LOGIN ----------------
def reset_login_form():
    entry_username.delete(0, tk.END)
    entry_password.delete(0, tk.END)

def login():
    username = entry_username.get()
    password = entry_password.get()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT username, role, enrollment_no FROM users WHERE username=%s AND password=%s",
        (username, password)
    )
    user = cursor.fetchone()
    conn.close()

    if user:
        reset_login_form()
        root.withdraw()
        open_dashboard(
            username=user[0],
            role=user[1],
            enrollment=user[2],
            parent=root
        )
    else:
        messagebox.showerror("Login Failed", "Invalid Username or Password")


# ---------------- MAIN LOGIN WINDOW ----------------
root = tk.Tk()
root.title("Login - Student Performance Management System")
center_window(root, 450, 420)
root.configure(bg="#eaf0ff")

card = tk.Frame(root, bg="white", padx=30, pady=30)
card.place(relx=0.5, rely=0.5, anchor="center")

tk.Label(card, text="Login", font=("Arial", 20, "bold"),
         bg="white").grid(row=0, column=0, columnspan=2, pady=10)

tk.Label(card, text="Username", bg="white").grid(row=1, column=0, columnspan=2, sticky="w")
entry_username = tk.Entry(card, width=35)
entry_username.grid(row=2, column=0, columnspan=2)

tk.Label(card, text="Password", bg="white").grid(row=3, column=0, columnspan=2, sticky="w")
entry_password = tk.Entry(card, show="*", width=35)
entry_password.grid(row=4, column=0, columnspan=2)

tk.Button(card, text="Sign Up", bg="#2196F3", fg="white",
          height=2, command=open_signup)\
    .grid(row=5, column=0, padx=5, pady=15, sticky="ew")

tk.Button(card, text="Forgot Password", bg="#FF9800", fg="white",
          height=2, command=open_forgot)\
    .grid(row=5, column=1, padx=5, pady=15, sticky="ew")

tk.Button(card, text="Sign In", bg="#4CAF50", fg="white",
          height=2, command=login)\
    .grid(row=6, column=0, columnspan=2, sticky="ew")

root.mainloop()
