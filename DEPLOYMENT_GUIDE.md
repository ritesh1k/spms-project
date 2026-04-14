# SPMS Deployment & Implementation Guide

## Overview

This document provides step-by-step instructions for deploying the SPMS Flask application with real database queries, authentication, and CI/CD pipeline.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Database Queries Implementation](#database-queries-implementation)
3. [Authentication System](#authentication-system)
4. [REST API Implementation](#rest-api-implementation)
5. [Marks Form Migration](#marks-form-migration)
6. [CI/CD Setup](#cicd-setup)
7. [Production Deployment](#production-deployment)

## Quick Start

### 1. Environment Setup (5 min)

```bash
# Activate virtual environment
cd D:\python\SPMS
.\.venv\Scripts\activate

# Install/update dependencies
pip install -r requirements.txt
```

### 2. Database Configuration

Create/update `.env` file:
```env
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DB=spms_db
MYSQL_PORT=3306
SECRET_KEY=your-secret-key-change-this
```

### 3. Start Development Server

```bash
python app.py
```

Visit: http://localhost:5000

## Database Queries Implementation

### What Was Implemented

#### File: `database/queries.py`

24 database helper functions for real data retrieval:

**Authentication:**
- `authenticate_user(username, password)` - Query users table, verify hashed password

**Student Data:**
- `get_student_profile(enrollment_no)` - Fetch student details + CGPA
- `get_student_results(enrollment_no, semester)` - Published results

**Teacher Data:**
- `get_teacher_profile(username)` - Teacher information
- `get_teacher_assigned_subjects(username)` - Subjects assigned to teacher

**Marks Management:**
- `submit_internal_marks(...)` - Insert marks with validation
- `publish_result(...)` - Calculate grade and insert final results

**Admin Functions:**
- `get_admin_stats()` - Dashboard statistics
- `search_students(filters)` - Search with department/course/semester filters

### Integration Points

#### Route: `/login` (Updated)
```python
# BEFORE: Accepted any username/password
session['user'] = username
session['role'] = 'student'

# AFTER: Real authentication
auth_result = authenticate_user(username, password)
if not auth_result["success"]:
    flash(auth_result["error"], "error")
    return redirect(url_for("main.login"))

session['user'] = username
session['role'] = auth_result["role"]
session['enrollment_no'] = auth_result["user"]["enrollment_no"]
```

#### Route: `/student/profile` (Updated)
```python
# BEFORE: Hardcoded student_data dict
student_data = {
    "name": "John Doe",
    "enrollment": "CS001",
    ...
}

# AFTER: Real database query
enrollment_no = session.get('enrollment_no')
student_data = get_student_profile(enrollment_no)
```

#### Route: `/student/results` (Updated)
```python
# BEFORE: Empty template
return render_template("student_results.html")

# AFTER: Real results from database
results = get_student_results(enrollment_no, semester)
return render_template("student_results.html", results=results)
```

#### Route: `/teacher/marks` (Updated)
```python
# POST handler for marks submission
result = submit_internal_marks(
    session.get('user'), enrollment_no, subject, semester,
    assignment, attendance, ct1, ct2, ct3
)
```

#### Route: `/admin/dashboard` (Updated)
```python
# BEFORE: No data
render_template("admin_dashboard.html")

# AFTER: Real statistics
stats = get_admin_stats()
render_template("admin_dashboard.html", stats=stats)
```

## Authentication System

### How It Works

1. **Password Hashing** (in `auth_utils.py`)
   ```python
   # Registration/Update:
   hashed = hash_password(plain_password)  # PBKDF2-SHA256
   
   # Login Verification:
   verify_password(plain_password, stored_hash)  # Returns True/False
   ```

2. **Login Flow**
   ```
   User enters username/password
         ↓
   Query users table by username
         ↓
   Compare password with stored hash
         ↓
   Success: Set session[user], session[role], redirect to dashboard
   Failure: Show error flash message
   ```

3. **Session Management**
   ```python
   # Set after authentication
   session['user'] = username
   session['role'] = role  # 'student', 'teacher', 'admin'
   session['enrollment_no'] = enrollment_no
   
   # Protected routes use decorator
   @require_login(role='teacher')
   def teacher_dashboard():
       pass
   ```

### Testing Authentication

Use test credentials (must exist in users table):
```sql
-- student account
INSERT INTO users (username, password, role, enrollment_no, email)
VALUES ('student001', 'hashed_password', 'student', 'CS2021001', 'student@example.com');

-- teacher account
INSERT INTO users (username, password, role, email)
VALUES ('teacher001', 'hashed_password', 'teacher', 'teacher@example.com');

-- admin account
INSERT INTO users (username, password, role, email)
VALUES ('admin001', 'hashed_password', 'admin', 'admin@example.com');
```

## REST API Implementation

### New API Endpoints

#### 1. Teacher Subjects API
```
GET /api/teacher/subjects
```

Returns:
```json
[
  {
    "subject": "Data Structures",
    "course": "B.Tech CSE",
    "semester": "II",
    "section": "A"
  }
]
```

Usage in JavaScript:
```javascript
fetch('/api/teacher/subjects')
  .then(r => r.json())
  .then(subjects => {
    // Populate dropdown
    subjects.forEach(s => {
      option.textContent = s.subject;
    });
  });
```

#### 2. Student Results API
```
GET /api/student-results/<enrollment>
```

Usage:
```javascript
// Admin viewing student results
fetch('/api/student-results/CS2021001')
  .then(r => r.json())
  .then(results => {
    // Display results table
  });
```

#### 3. Mark Entry API (AJAX)
```
POST /api/mark-entry
Content-Type: application/json

{
  "enrollment_no": "CS2021001",
  "subject": "Data Structures",
  "semester": "II",
  "assignment": 8,
  "attendance": 9,
  "ct1": 18,
  "ct2": 19,
  "ct3": 17
}
```

Response:
```json
{
  "success": true,
  "internal_total": 37
}
```

#### 4. Publish Result API
```
POST /api/publish-result
Content-Type: application/json

{
  "enrollment_no": "CS2021001",
  "subject": "Data Structures",
  "semester": "II",
  "external_marks": 45
}
```

Response:
```json
{
  "success": true,
  "final_total": 82,
  "grade": "A",
  "status": "Pass"
}
```

### JavaScript/AJAX Implementation

Example in `admin_results.html`:
```javascript
document.getElementById('publishResultForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData(this);
    const data = Object.fromEntries(formData);
    
    const response = await fetch('/api/publish-result', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    
    const result = await response.json();
    if (result.success) {
        alert(`Grade: ${result.grade}, Total: ${result.final_total}`);
    }
});
```

## Marks Form Migration

### Legacy Tkinter Implementation

Location: `SPMS/modules/create_result.py`

Features to migrate:
- Subject dropdown (from assigned_subjects table)
- Mark input fields (assignment, attendance, ct1-3)
- Validation (0-10, 0-20 ranges)
- Best 2 class tests calculation
- Insert into teacher_internal_results

### New Flask Implementation

Location: `app/templates/teacher_marks.html` + `app/routes.py`

#### Form Fields
```html
<input type="text" name="enrollment_no" required>
<input type="text" name="subject" required>
<select name="semester" required>
  <option value="I">I</option>
  <option value="II">II</option>
  ...
</select>
<input type="number" name="assignment" min="0" max="10" required>
<input type="number" name="attendance" min="0" max="10" required>
<input type="number" name="ct1" min="0" max="20" required>
<input type="number" name="ct2" min="0" max="20" required>
<input type="number" name="ct3" min="0" max="20" required>
```

#### Processing
```python
@main_bp.route("/teacher/marks", methods=["GET", "POST"])
@require_login(role='teacher')
def teacher_marks():
    if request.method == "POST":
        # Get form data
        enrollment_no = request.form.get("enrollment_no")
        # ... validate and submit
        
        result = submit_internal_marks(
            session.get('user'), enrollment_no, subject, semester,
            assignment, attendance, ct1, ct2, ct3
        )
        
        if result["success"]:
            flash("Marks submitted successfully", "success")
```

### Advantages Over Tkinter

| Feature | Tkinter | Flask |
|---------|---------|-------|
| UI/UX | Desktop only | Web + Mobile |
| Database | Direct connection | Pooled + secure |
| Error handling | Dialog boxes | Flash messages |
| Validation | Python only | Client + Server |
| Deployment | EXE + dependencies | Single Docker container |
| Updates | Manual reinstall | Auto via git pull |

## CI/CD Setup

### GitHub Actions Workflows

#### 1. Continuous Integration (`.github/workflows/tests.yml`)

**Triggers**: On every push/PR to main or develop

**Steps**:
1. Checkout code
2. Setup Python 3.11
3. Install dependencies
4. Start MySQL service
5. Run flake8 linting
6. Run pytest tests
7. Generate coverage report
8. Upload to codecov

**Run locally**:
```bash
# Download GH Actions runner
# Or run tests directly
pytest tests/ -v --cov=app --cov=database
```

#### 2. Deployment Pipeline (`.github/workflows/deploy.yml`)

**Triggers**: On push to main branch

**Current**: Validates Flask app loads (no-op deployment example)

**For production deployment**, uncomment and fill in:

**Heroku**:
```yaml
- name: Deploy to Heroku
  uses: akhileshns/heroku-deploy@v3.12.12
  with:
    heroku_api_key: ${{ secrets.HEROKU_API_KEY }}
    heroku_app_name: spms-prod
    heroku_email: your-email@example.com
```

**AWS EC2**:
```yaml
- name: Deploy to AWS
  env:
    DEPLOY_KEY: ${{ secrets.DEPLOY_KEY }}
  run: |
    ssh -i deploy_key ubuntu@your-ip 'cd /app/spms && git pull && systemctl restart spms'
```

### Setting Up CI/CD

1. **Create GitHub Repository**
```bash
git remote add origin https://github.com/yourusername/spms.git
git branch -M main
git push -u origin main
```

2. **Add Secrets** (in GitHub repo settings → Secrets)
```
HEROKU_API_KEY = your-key
HEROKU_APP_NAME = your-app
HEROKU_EMAIL = your-email
```

3. **Verify Workflows**
- Go to Actions tab
- Watch tests run on every push
- Workflows auto-trigger on PR

### Example: Passing Workflow Run

```
✅ Set up Python 3.11
✅ Install dependencies
✅ Run linting (0 errors)
✅ Run tests (15 passed)
✅ Upload coverage
✅ All checks passed ✓
```

## Production Deployment

### Option 1: Heroku (Easiest)

```bash
# Login
heroku login

# Create app
heroku create spms-production

# Add databases
heroku addons:create cleardb:ignite

# Set environment variables
heroku config:set SECRET_KEY=your-key
heroku config:set MYSQL_HOST=your-cleardb-host
heroku config:set MYSQL_USER=your-user
heroku config:set MYSQL_PASSWORD=your-pass
heroku config:set MYSQL_DB=your-db

# Deploy
git push heroku main

# View logs
heroku logs --tail
```

### Option 2: AWS EC2

#### Setup (30 min)

```bash
# SSH into instance
ssh -i key.pem ec2-user@your-instance-ip

# Install dependencies
sudo yum update -y
sudo yum install python3-pip python3-devel mysql -y

# Clone repo
git clone https://github.com/yourusername/spms.git
cd SPMS

# Setup environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env
nano .env
# Add MYSQL_* and SECRET_KEY

# Install Gunicorn & Nginx
pip install gunicorn
sudo yum install nginx -y

# Create systemd service
sudo nano /etc/systemd/system/spms.service
```

File: `/etc/systemd/system/spms.service`
```ini
[Unit]
Description=SPMS Flask Application
After=network.target

[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user/SPMS
ExecStart=/home/ec2-user/SPMS/venv/bin/gunicorn -w 4 -b 0.0.0.0:8000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable & start service
sudo systemctl daemon-reload
sudo systemctl enable spms
sudo systemctl start spms

# Configure Nginx reverse proxy
sudo nano /etc/nginx/conf.d/spms.conf
```

Nginx Config:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static/ {
        alias /home/ec2-user/SPMS/app/static/;
    }
}
```

```bash
# Test and reload Nginx
sudo nginx -t
sudo systemctl restart nginx

# Verify
curl http://localhost/
```

### Option 3: Docker (Most Flexible)

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=app.py

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:app"]
```

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MYSQL_HOST=db
      - MYSQL_USER=spms
      - MYSQL_PASSWORD=password
      - MYSQL_DB=spms_db
    depends_on:
      - db
    volumes:
      - .:/app

  db:
    image: mysql:8.0
    ports:
      - "3306:3306"
    environment:
      - MYSQL_ROOT_PASSWORD=root
      - MYSQL_DATABASE=spms_db
      - MYSQL_USER=spms
      - MYSQL_PASSWORD=password
    volumes:
      - mysql_data:/var/lib/mysql

volumes:
  mysql_data:
```

Run:
```bash
docker-compose up
```

### SSL Certificate (HTTPS)

#### Using Certbot (Let's Encrypt)

```bash
sudo yum install certbot python3-certbot-nginx -y
sudo certbot certonly --nginx -d your-domain.com
```

Update Nginx:
```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # ... rest of config
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

```bash
sudo systemctl restart nginx
```

### Monitoring & Maintenance

#### Logs
```bash
# Application logs
journalctl -u spms -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# MySQL logs
sudo tail -f /var/log/mysql/error.log
```

#### Backup Database
```bash
# Daily backup
mysqldump -u root -p spms_db > backup_$(date +%Y%m%d).sql

# Automated backup (cron)
0 2 * * * mysqldump -u root -ppassword spms_db > /backups/spms_$(date +\%Y\%m\%d).sql
```

#### Performance Monitoring
```bash
# Check CPU/Memory
top

# Check disk space
df -h

# Monitor app health
curl http://localhost:8000/health
```

## Performance Checklist

- [ ] Database indexes created on username, enrollment_no, enrollment_no+subject
- [ ] Caching implemented for dashboard stats (cache TTL: 5 min)
- [ ] Pagination added for student lists (50 per page)
- [ ] Query optimizations (SELECT specific columns, not *)
- [ ] Connection pooling configured in database.py
- [ ] Static files served by Nginx, not Flask
- [ ] Gzip compression enabled
- [ ] DB backups scheduled daily
- [ ] Error logging configured
- [ ] Performance monitoring set up

## Troubleshooting Deployment

### App won't start
```bash
# Check logs
journalctl -u spms -n 50

# Check syntax
python -m py_compile app.py

# Test import
python -c "from app import create_app; create_app()"
```

### Database connection fails
```bash
# Test MySQL connection
mysql -h HOSTNAME -u USER -p DATABASE

# Check .env variables
cat .env | grep MYSQL

# Verify MySQL is running
sudo systemctl status mysql
```

### Static files not loading
```bash
# Check Nginx config
sudo nginx -t

# Verify files exist
ls -la app/static/css/

# Check permissions
sudo chmod -R 755 app/static/
```

---

**Document Version**: 2.0  
**Last Updated**: 2024  
**Maintained By**: SPMS Team
