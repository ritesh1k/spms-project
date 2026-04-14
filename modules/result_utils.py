from db_config import get_connection


def ensure_result_tables(include_published=False):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS teacher_internal_results (
            id INT AUTO_INCREMENT PRIMARY KEY,
            enrollment_no VARCHAR(100) NOT NULL,
            subject VARCHAR(120) NOT NULL,
            semester VARCHAR(20) NOT NULL,
            assignment DECIMAL(5,2) NOT NULL DEFAULT 0,
            attendance DECIMAL(5,2) NOT NULL DEFAULT 0,
            ct1 DECIMAL(5,2) NOT NULL DEFAULT 0,
            ct2 DECIMAL(5,2) NOT NULL DEFAULT 0,
            ct3 DECIMAL(5,2) NOT NULL DEFAULT 0,
            ct_best_two DECIMAL(5,2) NOT NULL DEFAULT 0,
            internal_total DECIMAL(6,2) NOT NULL DEFAULT 0,
            teacher_username VARCHAR(100) DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uq_internal_unique (enrollment_no, subject, semester)
        )
        """
    )

    if include_published:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS published_results (
                id INT AUTO_INCREMENT PRIMARY KEY,
                enrollment_no VARCHAR(100) NOT NULL,
                subject VARCHAR(120) NOT NULL,
                semester VARCHAR(20) NOT NULL,
                assignment DECIMAL(5,2) NOT NULL DEFAULT 0,
                attendance DECIMAL(5,2) NOT NULL DEFAULT 0,
                ct1 DECIMAL(5,2) NOT NULL DEFAULT 0,
                ct2 DECIMAL(5,2) NOT NULL DEFAULT 0,
                ct3 DECIMAL(5,2) NOT NULL DEFAULT 0,
                ct_best_two DECIMAL(5,2) NOT NULL DEFAULT 0,
                internal_total DECIMAL(6,2) NOT NULL DEFAULT 0,
                external_marks DECIMAL(6,2) NOT NULL DEFAULT 0,
                final_total DECIMAL(6,2) NOT NULL DEFAULT 0,
                grade VARCHAR(10),
                status VARCHAR(20),
                published_by VARCHAR(100),
                published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_published_unique (enrollment_no, subject, semester)
            )
            """
        )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS results (
            id INT AUTO_INCREMENT PRIMARY KEY,
            enrollment_no VARCHAR(100) NOT NULL,
            subject VARCHAR(120) NOT NULL,
            marks DECIMAL(6,2) NOT NULL,
            exam VARCHAR(60) NOT NULL,
            teacher_username VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_results (enrollment_no, subject, exam)
        )
        """
    )
    conn.commit()
    conn.close()


def grade_for_score(score):
    if score >= 90:
        return "A+"
    if score >= 80:
        return "A"
    if score >= 70:
        return "B"
    if score >= 60:
        return "C"
    return "D"


def normalize_semester(sem_value):
    sem_text = str(sem_value).strip().upper()
    sem_map = {
        "1": "I", "I": "I", "1ST": "I", "FIRST": "I",
        "2": "II", "II": "II", "2ND": "II", "SECOND": "II",
        "3": "III", "III": "III", "3RD": "III", "THIRD": "III",
        "4": "IV", "IV": "IV", "4TH": "IV", "FOURTH": "IV",
        "5": "V", "V": "V", "5TH": "V", "FIFTH": "V",
        "6": "VI", "VI": "VI", "6TH": "VI", "SIXTH": "VI",
        "7": "VII", "VII": "VII", "7TH": "VII", "SEVENTH": "VII",
        "8": "VIII", "VIII": "VIII", "8TH": "VIII", "EIGHTH": "VIII",
    }
    return sem_map.get(sem_text, sem_text)


def next_semester(sem_value):
    sem_order = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"]
    current = normalize_semester(sem_value)
    if current not in sem_order:
        return current
    idx = sem_order.index(current)
    return sem_order[idx + 1] if idx < len(sem_order) - 1 else current


def promote_student_if_passed(enrollment_no, final_total):
    # Auto-promoting on each published subject is incorrect because a student can
    # have multiple subjects in the same semester. Semester progression should be
    # handled explicitly through an admin-controlled workflow, not during per-subject
    # result publication.
    return
