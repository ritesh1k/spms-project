"""Database module for SPMS Flask application."""

from database.connection import get_connection, test_connection
from database.queries import (
    authenticate_user,
    get_student_profile,
    get_student_results,
    get_teacher_profile,
    get_teacher_assigned_subjects,
    submit_internal_marks,
    publish_result,
    get_admin_stats,
    search_students,
)

__all__ = [
    'get_connection',
    'test_connection',
    'authenticate_user',
    'get_student_profile',
    'get_student_results',
    'get_teacher_profile',
    'get_teacher_assigned_subjects',
    'submit_internal_marks',
    'publish_result',
    'get_admin_stats',
    'search_students',
]