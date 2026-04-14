from admin.admin_dashboard import open_admin_dashboard
from Teacher.teacher_dashboard import open_teacher_dashboard
from Student.student_dashboard import open_student_dashboard

def open_dashboard(username, role, enrollment, parent):

    print("ROLE =", role)

    if role == "admin":
        open_admin_dashboard(username, parent)

    elif role == "teacher":
        open_teacher_dashboard(username, parent)

    elif role == "student":
        open_student_dashboard(
            username=username,
            enrollment=enrollment,
            parent=parent
        )

    else:
        raise ValueError("Invalid role")
