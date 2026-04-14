from flask import Blueprint, jsonify, render_template, request, session, redirect, url_for, flash
from functools import wraps

from database.connection import test_connection

main_bp = Blueprint("main", __name__)


def require_login(role=None):
    """Decorator to require login and optionally check role."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session:
                return redirect(url_for('main.login'))
            if role and session.get('role') != role:
                return redirect(url_for('main.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@main_bp.route("/")
def index():
    db_ready = test_connection()
    return render_template("index.html", db_ready=db_ready)


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        
        if not username or not password:
            flash("Username and password required", "error")
            return redirect(url_for("main.login"))
        
        session['user'] = username
        session['role'] = 'student'
        
        flash(f"Welcome, {username}!", "success")
        return redirect(url_for("main.student_dashboard"))
    
    return render_template("login.html")


@main_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))


@main_bp.route("/student/dashboard")
@require_login(role='student')
def student_dashboard():
    return render_template("student_dashboard.html", username=session.get('user'))


@main_bp.route("/student/profile")
@require_login(role='student')
def student_profile():
    student_data = {
        "name": "John Doe",
        "enrollment": "CS001",
        "course": "B.Tech CSE",
        "semester": "IV",
        "section": "A",
        "batch": "2022",
        "phone": "9876543210",
        "email": "john@example.com",
        "cgpa": 8.5,
        "percentage": 85.0,
    }
    return render_template("student_profile.html", student=student_data)


@main_bp.route("/student/results")
@require_login(role='student')
def student_results():
    return render_template("student_results.html")


@main_bp.route("/teacher/dashboard")
@require_login(role='teacher')
def teacher_dashboard():
    return render_template("teacher_dashboard.html", username=session.get('user'))


@main_bp.route("/teacher/marks")
@require_login(role='teacher')
def teacher_marks():
    return render_template("teacher_marks.html")


@main_bp.route("/admin/dashboard")
@require_login(role='admin')
def admin_dashboard():
    return render_template("admin_dashboard.html", username=session.get('user'))


@main_bp.route("/admin/students")
@require_login(role='admin')
def admin_students():
    return render_template("admin_students.html")


@main_bp.route("/admin/results")
@require_login(role='admin')
def admin_results():
    return render_template("admin_results.html")


@main_bp.route("/health")
def health():
    return jsonify(
        status="ok",
        database="connected" if test_connection() else "unavailable",
    )