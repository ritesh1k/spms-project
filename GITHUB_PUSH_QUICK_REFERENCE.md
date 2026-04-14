# 📋 Quick GitHub Push Commands

## TL;DR - Copy & Paste Ready Commands

Run these in PowerShell from `D:\python\SPMS`:

### Step 1: Verify Git Status
```powershell
git status
```

### Step 2: Commit Any Uncommitted Changes
```powershell
git add .
git commit -m "Add Flask routes and web templates for student/teacher/admin dashboards"
```

### Step 3: After Creating Remote on GitHub

Replace `USERNAME` with your actual GitHub username:

```powershell
git remote add origin https://github.com/USERNAME/spms-project.git
git branch -M main
git push -u origin main
```

### Step 4: Verify Push Success
```powershell
git log --oneline -5
git remote -v
```

## 🔗 Create Remote First!

Before running the push commands above:

1. Go to https://github.com/new
2. Repository name: `spms-project`
3. Description: `Student Performance Management System - Flask + MySQL`
4. Choose visibility (Public/Private)
5. **DO NOT** check "Initialize this repository"
6. Click **Create repository**

## Then Run All Push Commands

```powershell
# Navigate to project
cd D:\python\SPMS

# Configure Git (one-time per machine)
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Add remote (replace USERNAME)
git remote add origin https://github.com/USERNAME/spms-project.git

# Rename branch to main
git branch -M main

# Push to GitHub
git push -u origin main

# Verify
git log origin/main -1
```

## 🔐 Using SSH (Optional - Easier for Future Pushes)

```powershell
# Generate SSH key (if you don't have one)
ssh-keygen -t ed25519 -C "your.email@example.com"

# Add to GitHub:
# 1. https://github.com/settings/ssh/new
# 2. Paste contents of ~/.ssh/id_ed25519.pub
# 3. Add key

# Test SSL connection
ssh -T git@github.com

# Then change remote to SSH
git remote set-url origin git@github.com:USERNAME/spms-project.git

# Push with SSH
git push -u origin main
```

## ✅ Verification Checklist

After pushing:
- [ ] Check https://github.com/USERNAME/spms-project
- [ ] Verify all files are visible
- [ ] Check commit history (Commits tab)
- [ ] Confirm README.md displays correctly
- [ ] Check `app/` folder structure is present

## 🔄 Future Pushes

After the initial setup, for any future changes:

```powershell
git add .
git commit -m "Describe your changes"
git push origin main
```

## 🆘 Issues?

| Issue | Solution |
|-------|----------|
| "Repository already exists" | You already pushed. Use `git push` to update. |
| "permission denied" | Use SSH key or GitHub personal access token. |
| "Remote origin already exists" | `git remote remove origin` then re-add. |
| "fatal: not a git repo" | You're not in SPMS folder. Run `cd D:\python\SPMS` |

---

**See [GITHUB_SETUP.md](GITHUB_SETUP.md) for detailed instructions.**
