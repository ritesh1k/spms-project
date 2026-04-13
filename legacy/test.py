import tkinter as tk
from PIL import Image, ImageTk

# ---------- WINDOW ----------
root = tk.Tk()
root.title("SPMS Login")
root.geometry("1200x700")
root.resizable(False, False)

# ---------- BACKGROUND IMAGE ----------
bg = Image.open("bg.png")
bg = bg.resize((1200,700))
bg_img = ImageTk.PhotoImage(bg)

bg_label = tk.Label(root, image=bg_img)
bg_label.place(x=0,y=0,relwidth=1,relheight=1)

# ---------- GLASS LOGIN FRAME ----------
glass = tk.Frame(root, bg="#ffffff", bd=0)
glass.place(relx=0.5, rely=0.5, anchor="center", width=380, height=340)

# simulate transparency
glass.configure(bg="#ffffff")
glass.attributes = None

# ---------- TITLE ----------
title = tk.Label(
    glass,
    text="Login",
    font=("Segoe UI",20,"bold"),
    bg="#ffffff",
    fg="#1b1b1b"
)
title.pack(pady=15)

# ---------- EMAIL ----------
email_wrap = tk.Frame(glass, bg="#eef2ff")
email_wrap.pack(pady=10, ipady=4)

tk.Label(
    email_wrap,
    text="✉",
    font=("Segoe UI Emoji", 12),
    bg="#eef2ff",
    fg="#93a0bf",
    width=2,
).pack(side="left", padx=(8, 2))

email = tk.Entry(
    email_wrap,
    font=("Segoe UI", 12),
    width=24,
    bd=0,
    bg="#eef2ff",
    fg="#4b5b80",
)
email.insert(0, "Email Id")
email.pack(side="left", padx=(0, 12), pady=4)

# ---------- PASSWORD ----------
password_wrap = tk.Frame(glass, bg="#eef2ff")
password_wrap.pack(pady=10, ipady=4)

tk.Label(
    password_wrap,
    text="🔒",
    font=("Segoe UI Emoji", 12),
    bg="#eef2ff",
    fg="#93a0bf",
    width=2,
).pack(side="left", padx=(8, 2))

password = tk.Entry(
    password_wrap,
    font=("Segoe UI", 12),
    width=24,
    bd=0,
    bg="#eef2ff",
    fg="#4b5b80",
)
password.insert(0, "Password")
password.pack(side="left", padx=(0, 12), pady=4)

# ---------- BUTTON FRAME ----------
btn_frame = tk.Frame(glass, bg="#ffffff")
btn_frame.pack(pady=15)

# SIGN UP
signup = tk.Button(
    btn_frame,
    text="Sign Up",
    font=("Segoe UI",11),
    bg="#3b5bff",
    fg="white",
    width=12,
    bd=0
)
signup.grid(row=0,column=0,padx=5)

# FORGOT
forgot = tk.Button(
    btn_frame,
    text="Forgot Password",
    font=("Segoe UI",11),
    bg="#ff9f1c",
    fg="white",
    width=14,
    bd=0
)
forgot.grid(row=0,column=1,padx=5)

# ---------- SIGN IN ----------
signin = tk.Button(
    glass,
    text="Sign In",
    font=("Segoe UI",12,"bold"),
    bg="#4361ee",
    fg="white",
    width=26,
    bd=0
)
signin.pack(pady=10, ipady=5)

root.mainloop()