# SPMS - Student Performance Management System

A comprehensive Student Performance Management System (SPMS) built with Flask and MySQL. Originally a Tkinter desktop application, it's now transitioning to a modern web framework while preserving all legacy functionality.

## 🎯 Project Status

- ✅ Flask scaffold created and initialized
- ✅ Database connectivity configured (MySQL)
- ✅ Authentication framework established
- ✅ Web routes for student, teacher, and admin dashboards
- ✅ HTML templates for all major workflows
- ✅ Legacy Tkinter code preserved in `legacy/` folder
- 🔄 Gradual migration from Tkinter to Flask in progress

## 📁 Project Structure

```
SPMS/
├── app/                      # Flask application package
│   ├── __init__.py          # App factory and configuration
│   └── routes.py            # All route handlers
├── config/                  # Configuration management
│   ├── __init__.py
│   └── config.py            # Environment-based config
├── database/                # Database layer
│   ├── __init__.py
│   └── connection.py        # MySQL connection helpers
├── templates/               # HTML templates
│   ├── base.html           # Base template with navigation
│   ├── index.html          # Landing page
│   ├── login.html          # Login form
│   ├── student_dashboard.html
│   ├── student_profile.html
│   ├── student_results.html
│   ├── teacher_dashboard.html
│   ├── teacher_marks.html
│   ├── admin_dashboard.html
│   ├── admin_students.html
│   └── admin_results.html
├── static/                  # Static assets
│   └── css/
│       └── style.css       # Global stylesheet
├── legacy/                  # Original Tkinter/MySQL code (preserved)
│   ├── modules/            # Legacy module implementations
│   └── ...
├── app.py                   # Flask application entry point
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variables template
├── .gitignore              # Git ignore rules
├── Procfile                # Deployment configuration
├── README.md               # This file
└── GITHUB_SETUP.md         # GitHub push instructions
```

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/USERNAME/spms-project.git
cd spms-project
```

### 2. Set Up Python Environment
```powershell
# Create virtual environment
python -m venv .venv

# Activate it
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
```bash
# Copy the example file
copy .env.example .env

# Edit .env with your database credentials
# For Windows:
notepad .env
# Or use your preferred editor
```

### 5. Run the Application
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## 🔐 Authentication & Access

### Test Credentials (Demo Mode)

Currently, the system accepts any username/password combination in demo mode. In production:

```python
# TODO: Implement proper authentication in routes.py
- Query credentials from `users` table
- Verify password using `verify_password()` from auth_utils
- Set session role based on user record
```

### Roles & Routes

| Role | Routes | Accessible From |
|------|--------|-----------------|
| **Student** | /student/dashboard, /student/profile, /student/results | Web & Legacy |
| **Teacher** | /teacher/dashboard, /teacher/marks | Web & Legacy |
| **Admin** | /admin/dashboard, /admin/students, /admin/results | Web Only |

## 🔌 API Endpoints

### Public Routes
- `GET /` - Landing page with health check
- `GET /login` - Login form
- `POST /login` - Process login
- `GET /logout` - Clear session
- `GET /health` - Health check (JSON)

### Student Routes (Protected)
- `GET /student/dashboard` - Main student dashboard
- `GET /student/profile` - View academic profile
- `GET /student/results` - View exam results

### Teacher Routes (Protected)
- `GET /teacher/dashboard` - Main teacher dashboard
- `GET /teacher/marks` - Enter marks form

### Admin Routes (Protected)
- `GET /admin/dashboard` - Admin overview
- `GET /admin/students` - Manage students
- `GET /admin/results` - Publish results

## 🗄️ Database Configuration

### Connection Details (from `.env`)
```
MYSQL_HOST=localhost
MYSQL_USER=student_user
MYSQL_PASSWORD=Student12345
MYSQL_DB=student_performance
MYSQL_PORT=3306
```

### Key Tables
- `users` - Authentication & roles
- `students` - Student records
- `teachers` - Teacher profiles
- `courses` - Course definitions
- `subjects` - Subject/course mappings
- `results` - Student marks and grades
- `teacher_internal_results` - Internal assessment data
- `published_results` - Final published results

## 📦 Dependencies

Core:
- **Flask** >= 3.0 - Web framework
- **mysql-connector-python** >= 9.0 - MySQL driver
- **python-dotenv** >= 1.0 - Environment variable management

Deployment:
- **gunicorn** >= 21.2 - Production WSGI server

Optional:
- **openpyxl** >= 3.1 - Excel report generation
- **reportlab** >= 4.0 - PDF report generation
- **Pillow** >= 10.0 - Image processing

## 🔄 Legacy Code Integration

The original Tkinter and MySQL code is preserved in the `legacy/` directory:
- Full featured GUI dashboards
- Existing module implementations
- Database utilities and helpers

**Plan:** Gradually migrate Tkinter forms to Flask routes while keeping the underlying logic (modules/).

## 🔧 Environment Setup Examples

### Development
```env
SECRET_KEY=dev-key-change-in-production
FLASK_ENV=development
FLASK_DEBUG=True
MYSQL_HOST=localhost
MYSQL_USER=student_user
MYSQL_PASSWORD=Student12345
MYSQL_DB=student_performance
```

### Production
```env
SECRET_KEY=<generate-secure-random-key>
FLASK_ENV=production
FLASK_DEBUG=False
MYSQL_HOST=prod-db-server.example.com
MYSQL_USER=prod_user
MYSQL_PASSWORD=<secure-password>
MYSQL_DB=spms_production
```

## 📝 Development Workflow

### Adding a New Route

1. **Create the route** in `app/routes.py`
2. **Add the decorator** `@require_login(role='student'|'teacher'|'admin')`
3. **Create the template** in `templates/`
4. **Test locally** at `http://localhost:5000/your-route`

### Example:
```python
@main_bp.route("/student/assignments")
@require_login(role='student')
def student_assignments():
    # Fetch data from database
    assignments = db.query("SELECT * FROM assignments WHERE ...")
    return render_template("student_assignments.html", assignments=assignments)
```

## 🚀 Deployment

### Deploy to Heroku
```bash
# Install Heroku CLI
heroku create spms-project
git push heroku main
heroku config:set SECRET_KEY=your-secure-key
```

### Deploy to Other Platforms
Use the included `Procfile`:
```
web: gunicorn app:app
```

## 🐛 Troubleshooting

### "No module named 'app'"
- Ensure you're running `python app.py` from the SPMS root directory

### "Connection to MySQL failed"
- Check `.env` database credentials
- Verify MySQL server is running
- Confirm network access to database host

### "Templates not found"
- Verify `templates/` directory exists
- Check file permissions
- Confirm Flask app is reading correct path

## 📚 Additional Resources

- [GitHub Setup Guide](GITHUB_SETUP.md) - Instructions for pushing to GitHub
- [Flask Documentation](https://flask.palletsprojects.com/)
- [MySQL Connector Python](https://dev.mysql.com/doc/connector-python/en/)
- [Jinja2 Templates](https://jinja.palletsprojects.com/)

## 👥 Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make changes and test locally
3. Commit with clear messages: `git commit -m "Add student assignment view"`
4. Push to your fork and create a Pull Request

## 📄 License

[Specify your license here - e.g., MIT, GPL, etc.]

## 📞 Support

For issues or questions:
1. Check existing GitHub issues
2. Create a new issue with detailed description
3. Include error messages and reproduction steps

---

**Last Updated:** April 14, 2026  
**Status:** Beta - Web migration in progress  
**Maintainer:** Your Name

