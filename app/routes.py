from flask import Blueprint, jsonify, render_template, request, session, redirect, url_for, flash
from functools import wraps

from database.connection import test_connection
from database.queries import (
    authenticate_user, get_student_profile, get_student_results,
    get_teacher_profile, get_teacher_assigned_subjects, submit_internal_marks,
    publish_result, get_admin_stats, search_students
)

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
        
        # Authenticate with database
        auth_result = authenticate_user(username, password)
        
        if not auth_result["success"]:
            flash(auth_result.get("error", "Authentication failed"), "error")
            return redirect(url_for("main.login"))
        
        # Set session data
        session['user'] = username
        session['role'] = auth_result["role"]
        session['enrollment_no'] = auth_result["user"].get("enrollment_no")
        
        flash(f"Welcome, {username}!", "success")
        
        # Redirect based on role
        if auth_result["role"] == "teacher":
            return redirect(url_for("main.teacher_dashboard"))
        elif auth_result["role"] == "admin":
            return redirect(url_for("main.admin_dashboard"))
        else:  # student
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
    enrollment_no = session.get('enrollment_no')
    student_data = get_student_profile(enrollment_no)
    
    if "error" in student_data:
        flash(student_data["error"], "warning")
    
    return render_template("student_profile.html", student=student_data)


@main_bp.route("/student/results")
@require_login(role='student')
def student_results():
    enrollment_no = session.get('enrollment_no')
    semester = request.args.get('semester', None)
    results = get_student_results(enrollment_no, semester)
    return render_template("student_results.html", results=results)


@main_bp.route("/teacher/dashboard")
@require_login(role='teacher')
def teacher_dashboard():
    username = session.get('user')
    subjects = get_teacher_assigned_subjects(username)
    return render_template("teacher_dashboard.html", username=username, subjects=subjects)


@main_bp.route("/teacher/marks", methods=["GET", "POST"])
@require_login(role='teacher')
def teacher_marks():
    if request.method == "POST":
        # Handle marks submission
        enrollment_no = request.form.get("enrollment_no")
        subject = request.form.get("subject")
        semester = request.form.get("semester")
        assignment = float(request.form.get("assignment", 0))
        attendance = float(request.form.get("attendance", 0))
        ct1 = float(request.form.get("ct1", 0))
        ct2 = float(request.form.get("ct2", 0))
        ct3 = float(request.form.get("ct3", 0))
        
        result = submit_internal_marks(
            session.get('user'), enrollment_no, subject, semester,
            assignment, attendance, ct1, ct2, ct3
        )
        
        if result.get("success"):
            flash(f"Marks submitted successfully! Internal total: {result['internal_total']}", "success")
        else:
            flash(result.get("error", "Error submitting marks"), "error")
        
        return redirect(url_for("main.teacher_marks"))
    
    username = session.get('user')
    subjects = get_teacher_assigned_subjects(username)
    return render_template("teacher_marks.html", subjects=subjects)


@main_bp.route("/admin/dashboard")
@require_login(role='admin')
def admin_dashboard():
    stats = get_admin_stats()
    return render_template("admin_dashboard.html", username=session.get('user'), stats=stats)


@main_bp.route("/admin/students")
@require_login(role='admin')
def admin_students():
    dept_filter = request.args.get('department', '')
    course_filter = request.args.get('course', '')
    semester_filter = request.args.get('semester', '')
    
    students = search_students(dept_filter, course_filter, semester_filter)
    return render_template("admin_students.html", students=students)


@main_bp.route("/admin/results")
@require_login(role='admin')
def admin_results():
    return render_template("admin_results.html")


# ============= API ENDPOINTS FOR AJAX CALLS =============

@main_bp.route("/api/teacher/subjects")
@require_login(role='teacher')
def api_teacher_subjects():
    """Get subjects assigned to logged-in teacher."""
    username = session.get('user')
    subjects = get_teacher_assigned_subjects(username)
    return jsonify(subjects)


@main_bp.route("/api/student-results/<enrollment_no>")
@require_login()
def api_student_results(enrollment_no):
    """Get student results (for admin/teacher views)."""
    if session.get('role') not in ['admin', 'teacher']:
        return jsonify({"error": "Unauthorized"}), 403
    
    results = get_student_results(enrollment_no)
    return jsonify(results)


@main_bp.route("/api/publish-result", methods=["POST"])
@require_login(role='admin')
def api_publish_result():
    """Publish result with external marks (admin only)."""
    data = request.get_json()
    
    result = publish_result(
        data.get('enrollment_no'),
        data.get('subject'),
        data.get('semester'),
        float(data.get('external_marks', 0))
    )
    
    return jsonify(result)


@main_bp.route("/api/mark-entry", methods=["POST"])
@require_login(role='teacher')
def api_mark_entry():
    """Submit internal marks via API (for AJAX forms)."""
    data = request.get_json()
    
    result = submit_internal_marks(
        session.get('user'),
        data.get('enrollment_no'),
        data.get('subject'),
        data.get('semester'),
        float(data.get('assignment', 0)),
        float(data.get('attendance', 0)),
        float(data.get('ct1', 0)),
        float(data.get('ct2', 0)),
        float(data.get('ct3', 0))
    )
    
    return jsonify(result)


@main_bp.route("/api/admin/statistics")
@require_login(role='admin')
def api_admin_statistics():
    """Get dashboard statistics."""
    stats = get_admin_stats()
    return jsonify(stats)


@main_bp.route("/health")
def health():
    return jsonify(
        status="ok",
        database="connected" if test_connection() else "unavailable",
    )