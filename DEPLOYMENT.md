# 部署指南 - Deployment Guide

## 🚀 Quick Deployment to Railway

Since GitHub CLI is not available in this environment, please follow these manual steps to deploy your temple website to Railway.

### Step 1: Create GitHub Repository

1. Go to https://github.com/new
2. Fill in the details:
   - **Repository name**: `temple-site`
   - **Description**: `Chinese Buddhist/Daoist Temple Aesthetic Website`
   - **Public/Private**: Select `Public`
   - **Initialize**: ❌ Do NOT check "Add a README file" (we already have one)
3. Click **"Create repository"**

### Step 2: Push Code to GitHub

Open PowerShell/Terminal and run:

```bash
cd "F:\temple-site"

# Replace YOUR_USERNAME with your actual GitHub username
git remote add origin https://github.com/YOUR_USERNAME/temple-site.git

# Rename branch to main (GitHub default)
git branch -M main

# Push code to GitHub
git push -u origin main
```

**Note**: You may need to authenticate with GitHub. Use your username and personal access token (not password).

### Step 3: Deploy to Railway

1. Go to https://railway.app
2. Click **"Start a New Project"**
3. Select **"Deploy from GitHub repo"**
4. If not already connected, click **"Connect GitHub"** and authorize Railway
5. Select the `temple-site` repository
6. Railway will automatically:
   - Detect the Python/Flask application
   - Install dependencies from `requirements.txt`
   - Start the application using `Procfile`
7. Wait for deployment to complete (usually 2-3 minutes)
8. Once deployed, Railway will provide a public URL like:
   ```
   https://temple-site-production.up.railway.app
   ```

### Step 4: Verify Deployment

1. Visit your Railway-provided URL
2. Test the form submission
3. Test the admin panel at `/admin` (password: `temple2026`)

---

## 🔧 Troubleshooting

### If Git push fails:
```bash
# Make sure you're in the right directory
cd "F:\temple-site"

# Check git status
git status

# Check remote
git remote -v

# If needed, update remote URL
git remote set-url origin https://github.com/YOUR_USERNAME/temple-site.git
```

### If Railway deployment fails:
1. Check the build logs in Railway dashboard
2. Make sure `requirements.txt` includes all dependencies
3. Verify `Procfile` is correctly named (capital P)
4. Ensure the Flask app uses `host='0.0.0.0'` (already configured)

---

## 📁 Project Files Summary

All files are located at `F:\temple-site\`:

```
F:\temple-site\
│
├── app.py                      # Flask backend server
├── requirements.txt           # Python dependencies
├── Procfile                  # Railway deployment config
├── README.md                 # Project documentation
├── DEPLOYMENT.md            # This file
├── .gitignore              # Git ignore rules
│
├── static\
│   ├── style.css          # Temple aesthetic CSS (19KB)
│   └── uploads\           # Photo upload directory
│
└── templates\
    ├── index.html         # Main page (11KB)
    ├── admin.html         # Admin panel
    └── admin_login.html   # Admin login
```

---

## 🎨 Features Implemented

✅ **Backend (Flask)**
- SQLite database with `submissions.db`
- Form submission handling (POST /submit)
- Photo upload with secure filename
- Admin authentication
- Admin panel with submission viewer

✅ **Frontend (Temple Aesthetic)**
- Dark background (#0a0a0a) with gold accents (#c9a84c)
- Chinese calligraphy font (ZCOOL XiaoWei)
- Incense smoke animation (CSS)
- Floating Chinese characters (佛, 道, 禅, 福, 慧, 静)
- Lotus flower SVG decorations
- Photo upload with preview
- Responsive design

✅ **Deployment Ready**
- `requirements.txt` with all dependencies
- `Procfile` for Railway
- `.gitignore` for clean repository
- Git repository initialized and committed

---

## 🌐 After Deployment

Once deployed to Railway, your website will be accessible globally at:
```
https://temple-site-production.up.railway.app
```

**Admin Panel**: `https://temple-site-production.up.railway.app/admin`
- Password: `temple2026`

---

## 📝 Next Steps (Optional)

1. **Custom Domain**: In Railway dashboard, go to Settings → Domains to add a custom domain
2. **Environment Variables**: Add `SECRET_KEY` in Railway for production
3. **Database**: Upgrade to PostgreSQL if you expect high traffic
4. **Monitoring**: Enable Railway metrics for monitoring

---

**愿此网站广度众生，吉祥如意！** 🙏

For issues or questions, please refer to:
- Flask docs: https://flask.palletsprojects.com/
- Railway docs: https://docs.railway.app/
