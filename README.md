# 禅意净土 - Temple of Serenity

A beautiful Chinese Buddhist/Daoist temple-aesthetic website built with Flask.

## Features

- 🏯 Traditional Chinese temple aesthetic design
- 🎨 Dark background with gold accents
- 📿 Incense smoke animation
- 🪷 Lotus flower decorations
- ☯ Floating Chinese characters (佛, 道, 禅, 福, 慧)
- 📸 Photo upload with preview
- 📝 Form submission with name, birthday, and gender
- 💾 SQLite database for storing submissions
- 🔐 Admin panel to view all submissions
- 📱 Fully responsive design

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: SQLite
- **Frontend**: HTML5, CSS3, JavaScript
- **Deployment**: Railway.app (free hosting)

## Local Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   python app.py
   ```

3. Visit: http://127.0.0.1:5000

## Admin Access

- URL: http://127.0.0.1:5000/admin
- Password: `temple2026`

## Deployment to Railway

### Step 1: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `temple-site`
3. Set to Public
4. Click "Create repository"

### Step 2: Push Code to GitHub

```bash
cd F:\temple-site
git remote add origin https://github.com/YOUR_USERNAME/temple-site.git
git branch -M main
git push -u origin main
```

### Step 3: Deploy to Railway

1. Go to https://railway.app
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Connect your GitHub account
5. Select the `temple-site` repository
6. Railway will automatically detect and deploy your Flask app
7. Once deployed, you'll get a public URL like: `https://temple-site-production.up.railway.app`

## Project Structure

```
F:\temple-site\
├── app.py                    # Flask backend
├── requirements.txt          # Python dependencies
├── Procfile                 # Railway deployment config
├── .gitignore              # Git ignore file
├── submissions.db          # SQLite database (auto-created)
├── static\
│   ├── style.css          # Temple aesthetic CSS
│   └── uploads\           # Uploaded photos
└── templates\
    ├── index.html         # Main page
    ├── admin.html         # Admin panel
    └── admin_login.html   # Admin login page
```

## Form Fields

1. **Photo Upload** - Image file upload with preview
2. **姓名 (Name)** - Text input
3. **生日 (Birthday)** - Date picker
4. **性别 (Gender)** - Radio buttons (男/女/其他)

## Design Elements

- Background: #0a0a0a (near black)
- Primary accent: #c9a84c (antique gold)
- Secondary: #8b1a1a (deep red/burgundy)
- Font: "ZCOOL XiaoWei" from Google Fonts
- Animations: Incense smoke, floating characters, lotus glow
- Motifs: Lotus flowers, bamboo, Chinese patterns

## License

MIT License

---

愿福慧增长，吉祥如意 🙏
