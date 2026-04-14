# SPMS - Student Performance Management System

A comprehensive Flask-based web application for managing student academic performance, marks, and results.

## Table of Contents

1. [Project Overview](#project-overview)
2. [Features](#features)
3. [Technology Stack](#technology-stack)
4. [Project Structure](#project-structure)
5. [Installation & Setup](#installation--setup)
6. [Database Schema](#database-schema)
7. [API Routes](#api-routes)
8. [Authentication](#authentication)
9. [Deployment](#deployment)
10. [Testing](#testing)
11. [Troubleshooting](#troubleshooting)

## Project Overview

SPMS is a modern Flask-based replacement for the legacy Tkinter desktop application. It provides:
- **3-tier role-based access**: Students, Teachers, and Administrators
- **Real-time marks management**: Teachers can submit internal marks (assignment, attendance, class tests)
- **Result publication**: Admins can finalize and publish student results with grades
- **Performance tracking**: Students can view their CGPA and semester results
- **Responsive UI**: Works on desktop, tablet, and mobile devices

## Features

### Student Dashboard
- View personal profile with academic details
- Check exam results and grades (CGPA, total marks)
- Filter results by semester
- Secure session-based login

### Teacher Dashboard  
- View assigned subjects and courses
- Submit internal marks for students:
  - Assignment marks (0-10)
  - Attendance (0-10)
  - Class tests 1-3 (best 2 considered, 0-20 each)
  - System auto-calculates best 2 class tests
  - Internal total = 40 marks
- Auto-submission confirmation

### Admin Dashboard
- Dashboard statistics (students, teachers, courses, departments)
- Search and filter students by department/course/semester
- Publish final results with external marks
- Calculate grades automatically (A+, A, B, C, D)
- Determine Pass/Fail status

## Technology Stack

```
Backend:
- Flask 3.0+ (Web framework)
- MySQL 8.0 (Database)
- Python 3.11+ (Runtime)

Frontend:
- HTML5 + Jinja2 (Templates)
- CSS3 (Responsive styling)
- JavaScript (AJAX calls)

Tools:
- Gunicorn (Production WSGI server)
- pytest (Testing framework)
- GitHub Actions (CI/CD)
```

## Project Structure

```
SPMS/
├── app/
│   ├── __init__.py           # Flask app factory
│   ├── routes.py             # All route handlers & API endpoints
│   ├── templates/            # Jinja2 HTML templates
│   │   ├── base.html         # Base template with navbar
│   │   ├── login.html        # Login page
│   │   ├── index.html        # Home page
│   │   ├── student_dashboard.html
│   │   ├── student_profile.html
│   │   ├── student_results.html
│   │   ├── teacher_dashboard.html
│   │   ├── teacher_marks.html
│   │   ├── admin_dashboard.html
│   │   ├── admin_students.html
│   │   └── admin_results.html
│   └── static/
│       └── css/
│           └── style.css     # Main stylesheet
├── config/
│   ├── __init__.py
│   └── config.py             # Configuration management
├── database/
│   ├── __init__.py
│   ├── connection.py         # MySQL connection helpers
│   └── queries.py            # Database query functions
├── tests/
│   ├── conftest.py           # pytest configuration
│   ├── test_routes.py        # Route tests
│   └── test_database.py      # Database tests
├── .github/
│   └── workflows/
│       ├── tests.yml         # CI/CD testing pipeline
│       └── deploy.yml        # Deployment pipeline
├── app.py                    # Application entry point
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
└── README.md                 # This file
```

## Installation & Setup

### Prerequisites

- Python 3.11+
- MySQL 8.0+
- Git

### Step 1: Clone and Setup Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/spms.git
cd SPMS

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.\.venv\Scripts\activate
# On Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your database credentials
# Required variables:
# - MYSQL_HOST=localhost
# - MYSQL_USER=root
# - MYSQL_PASSWORD=your_password
# - MYSQL_DB=spms_db
# - MYSQL_PORT=3306
# - SECRET_KEY=your-secret-key-here
```

### Step 3: Initialize Database

```bash
# Create database
mysql -u root -p < schema.sql

# Or use existing database from legacy system
# The app will work with existing tables
```

### Step 4: Run Application

```bash
# Development mode
python app.py

# Production mode with Gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

Visit `http://localhost:5000` (dev) or `http://localhost:8000` (production)

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(256) NOT NULL,  -- PBKDF2-SHA256 hashed
    role ENUM('student', 'teacher', 'admin') NOT NULL,
    enrollment_no VARCHAR(20),       -- For students
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Students Table
```sql
CREATE TABLE students (
    id INT PRIMARY KEY AUTO_INCREMENT,
    enrollment_no VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    phone VARCHAR(15),
    course VARCHAR(50),
    semester INT,
    section VARCHAR(10),
    department VARCHAR(50),
    dob DATE,
    batch YEAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Teachers Table
```sql
CREATE TABLE teachers (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    full_name VARCHAR(100),
    role VARCHAR(20) DEFAULT 'teacher',
    email VARCHAR(100),
    phone VARCHAR(15),
    department VARCHAR(50),
    designation VARCHAR(50),
    specialization VARCHAR(100),
    date_of_joining DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Results Tables
```sql
-- Internal marks submitted by teachers
CREATE TABLE teacher_internal_results (
    id INT PRIMARY KEY AUTO_INCREMENT,
    enrollment_no VARCHAR(20),
    subject VARCHAR(100),
    semester INT,
    assignment FLOAT,           -- 0-10
    attendance FLOAT,           -- 0-10
    ct1 FLOAT, ct2 FLOAT, ct3 FLOAT,  -- 0-20 each
    ct_best_two FLOAT,          -- Sum of best 2 CTs
    internal_total FLOAT,       -- 40 marks
    teacher_username VARCHAR(50),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Final published results
CREATE TABLE published_results (
    id INT PRIMARY KEY AUTO_INCREMENT,
    enrollment_no VARCHAR(20),
    subject VARCHAR(100),
    semester INT,
    assignment FLOAT,
    attendance FLOAT,
    ct1 FLOAT, ct2 FLOAT, ct3 FLOAT,
    ct_best_two FLOAT,
    internal_total FLOAT,       -- 40
    external_marks FLOAT,        -- 0-60
    final_total FLOAT,          -- 0-100
    grade VARCHAR(5),           -- A+, A, B, C, D
    status VARCHAR(20),          -- Pass/Fail
    published_by VARCHAR(50),
    published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Other Tables
- `courses` - Course information
- `departments` - Department details
- `subjects` - Subject listings
- `assigned_subjects` - Teacher-subject assignments

## API Routes

### Authentication Routes
```
POST   /login              - Student/Teacher/Admin login
GET    /logout             - Clear session and logout
```

### Student Routes
```
GET    /student/dashboard  - Student dashboard
GET    /student/profile    - Student profile & details
GET    /student/results    - Student exam results
```

### Teacher Routes
```
GET    /teacher/dashboard  - Teacher dashboard with assigned subjects
GET    /teacher/marks      - Marks entry form
POST   /teacher/marks      - Submit internal marks
```

### Admin Routes
```
GET    /admin/dashboard    - Admin statistics dashboard
GET    /admin/students     - Search & filter students
GET    /admin/results      - Result publishing interface
```

### REST API Endpoints (Return JSON)
```
GET    /api/teacher/subjects              - Teacher's assigned subjects
GET    /api/student-results/<enrollment>  - Student results data
POST   /api/publish-result                - Publish result (JSON)
POST   /api/mark-entry                    - Submit marks via AJAX
GET    /api/admin/statistics              - Dashboard statistics
GET    /health                            - Health check
```

## Authentication

### Password Security
- Algorithm: PBKDF2-SHA256
- Iterations: 180,000
- Constant-time comparison to prevent timing attacks

### Session Management
- Server-side session via Flask
- Session data: `user`, `role`, `enrollment_no`
- Role-based route decorators: `@require_login(role='admin')`

### User Roles
1. **Student** - View own profile and results only
2. **Teacher** - Submit marks for assigned subjects
3. **Admin** - Full system access, publish results

## Deployment

### Development
```bash
python app.py
```

### Production (Heroku Example)
```bash
# Create Procfile
echo "web: gunicorn app:app" > Procfile

# Deploy
heroku create your-app-name
heroku config:set MYSQL_HOST=xxx MYSQL_USER=xxx MYSQL_PASSWORD=xxx
git push heroku main
```

### Production (AWS EC2)
```bash
# SSH into instance
ssh -i key.pem ubuntu@instance-ip

# Install dependencies
sudo apt update && sudo apt install python3-pip mysql-server

# Clone repo and setup
git clone your-repo
cd SPMS
pip install -r requirements.txt

# Run with systemd
sudo systemctl start spms
sudo systemctl enable spms
```

### CI/CD with GitHub Actions
- Automated tests on every push
- Lint checks with flake8/pylint
- Deploy on successful main branch push
- See `.github/workflows/` for configuration

## Testing

### Run Tests
```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov=database

# Run specific test file
pytest tests/test_routes.py -v
```

### Test Database Setup
```bash
# Create test database
mysql -u root -p -e "CREATE DATABASE spms_test_db"

# Set connection string in .env.test
MYSQL_DB=spms_test_db
```

## Troubleshooting

### Import Errors
```
ModuleNotFoundError: No module named 'database'

Solution: Ensure you're running from project root and PYTHONPATH includes project directory
```

### Database Connection Refused
```
Error: Connection refused on localhost:3306

Solutions:
1. Check MySQL is running: sudo systemctl status mysql
2. Verify credentials in .env
3. Ensure MYSQL_HOST is correct
```

### Emojis Not Rendering
```
UnicodeDecodeError in terminal output

Solution: Set environment variable PYTHONIOENCODING=utf-8
```

### Port Already in Use
```
Address already in use on port 5000

Solution: Use different port: python app.py --port 5001
Or: kill process on 5000: lsof -ti:5000 | xargs kill -9
```

### CSRF Errors
```
Token missing or incorrect

Solution: Ensure CSRF protection enabled in app, use session.get() for tokens
```

## Performance Optimization

1. **Database Indexing**: Add indexes on frequently queried columns
   ```sql
   CREATE INDEX idx_enrollment ON students(enrollment_no);
   CREATE INDEX idx_username ON users(username);
   ```

2. **Caching**: Use Flask-Caching for dashboard stats
   ```python
   from flask_caching import Cache
   cache = Cache(app, config={'CACHE_TYPE': 'simple'})
   ```

3. **Pagination**: Implement for large student lists
   ```python
   students = search_students().paginate(page=1, per_page=50)
   ```

4. **Query Optimization**: Use select_related/prefetch_related equivalents

## Future Enhancements

- [ ] Email notifications for result publication
- [ ] PDF report generation for transcripts
- [ ] Analytics dashboard for department heads
- [ ] Mobile app (React Native/Flutter)
- [ ] Real-time notifications with WebSocket
- [ ] Import/Export students via CSV

## Contributing

1. Fork repository
2. Create feature branch (`git checkout -b feature/new-feature`)
3. Commit changes (`git commit -am 'Add new feature'`)
4. Push to branch (`git push origin feature/new-feature`)
5. Create Pull Request

## License

MIT License - See LICENSE file for details

## Support

For issues and questions:
- GitHub Issues: https://github.com/yourusername/spms/issues
- Email: support@spms.example.com

---

**Last Updated**: 2024
**Version**: 2.0 (Flask Migration)
**Status**: Production Ready
