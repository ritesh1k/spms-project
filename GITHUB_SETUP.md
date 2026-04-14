# 🚀 GitHub Setup Instructions for SPMS

Follow these steps to push the SPMS project to GitHub.

## Prerequisites
- GitHub account
- Git installed on your machine

## Step 1: Create Remote Repository on GitHub

1. Go to [GitHub](https://github.com)
2. Log in to your account
3. Click the **+** icon in the top-right corner → **New repository**
4. Fill in the repository details:
   - **Repository name:** `spms-project` (or your preferred name)
   - **Description:** `Student Performance Management System - Flask + MySQL`
   - **Visibility:** Choose Public or Private
   - **Do NOT** initialize with README, .gitignore, or license (we already have these)
5. Click **Create repository**

## Step 2: Configure Git Locally

Run these commands in PowerShell (from D:\python\SPMS):

```powershell
# Set your Git user identity (one-time)
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Verify Git config
git config --global --list
```

## Step 3: Add Remote and Push to GitHub

Run these commands in sequence:

```powershell
# Navigate to SPMS directory
cd D:\python\SPMS

# Add the remote repository (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/spms-project.git

# Verify the remote was added
git remote -v

# Rename branch to main (if not already)
git branch -M main

# Push existing commits to GitHub
git push -u origin main

# Verify the push
git log --oneline origin/main
```

## Step 4: Verify on GitHub

1. Refresh your GitHub repository page
2. You should see all your files and folders
3. Check the commit history in the Commits tab

## Step 5: Configure SSH (Optional but Recommended)

For future pushes without entering credentials:

```powershell
# Generate SSH key
ssh-keygen -t ed25519 -C "your.email@example.com"

# Add SSH key to GitHub
# 1. Copy the public key from ~/.ssh/id_ed25519.pub
# 2. Go to GitHub Settings → SSH and GPG Keys
# 3. Click "New SSH key" and paste it

# Test SSH connection
ssh -T git@github.com
```

Once SSH is configured, you can change the remote to:

```powershell
git remote set-url origin git@github.com:YOUR_USERNAME/spms-project.git
```

## Common Commands for Future Development

```powershell
# Check status
git status

# Add changes
git add .

# Commit changes
git commit -m "Your commit message"

# Push to GitHub
git push origin main

# Pull latest changes
git pull origin main

# View commit history
git log --oneline
```

## Troubleshooting

### "Repository already exists"
- You have already pushed. Use `git push` to update.

### "Permission denied"
- Check if SSH key is configured or use HTTPS with a personal access token.

### "Remote origin already exists"
- Remove and re-add: `git remote remove origin` then `git remote add origin <URL>`

## Next Steps

1. Set up branch protection on GitHub (Settings → Branches)
2. Configure CI/CD if needed
3. Document API endpoints in a POSTMAN collection
4. Create issues for future features

---

For more help, see [GitHub Docs](https://docs.github.com)
