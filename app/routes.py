from flask import Blueprint, render_template, request, session, redirect, url_for
from database.connection import get_connection
import sys
import os

# Import legacy auth utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'legacy'))
from auth_utils import verify_password, hash_password

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        
        if not email or not password:
            return render_template("login.html", error="Email and password required")
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Query the users table
            cursor.execute(
                "SELECT username, password, role FROM users WHERE LOWER(email) = %s LIMIT 1",
                (email,)
            )
            user_row = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if user_row and verify_password(password, user_row[1]):
                session["user_email"] = email
                session["username"] = user_row[0]
                session["role"] = user_row[2]
                return redirect(url_for("main.dashboard"))
            else:
                return render_template("login.html", error="Invalid email or password")
        
        except Exception as e:
            return render_template("login.html", error=f"Database error: {str(e)}")
    
    return render_template("login.html")


@bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        
        if not email or not password:
            return render_template("signup.html", error="Email and password required")
        
        if password != confirm_password:
            return render_template("signup.html", error="Passwords do not match")
        
        if len(password) < 8:
            return render_template("signup.html", error="Password must be at least 8 characters")
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Check if email already exists
            cursor.execute("SELECT 1 FROM users WHERE LOWER(email) = %s", (email,))
            if cursor.fetchone():
                cursor.close()
                conn.close()
                return render_template("signup.html", error="Email already registered")
            
            # Hash password and insert new user
            password_hash = hash_password(password)
            username = email.split("@")[0]
            
            cursor.execute(
                """
                INSERT INTO users (username, email, password, role, mobile, security_question, security_answer)
                VALUES (%s, %s, %s, 'student', '', 'None', 'None')
                """,
                (username, email, password_hash)
            )
            conn.commit()
            cursor.close()
            conn.close()
            
            session["user_email"] = email
            session["username"] = username
            session["role"] = "student"
            return redirect(url_for("main.dashboard"))
        
        except Exception as e:
            return render_template("signup.html", error=f"Signup failed: {str(e)}")
    
    return render_template("signup.html")


@bp.route("/dashboard")
def dashboard():
    user_email = session.get("user_email")
    username = session.get("username")
    role = session.get("role")
    
    if not user_email:
        return redirect(url_for("main.login"))
    
    return render_template("dashboard.html", user_email=user_email, username=username, role=role)


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.index"))
