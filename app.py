from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from werkzeug.utils import secure_filename
import sqlite3
import os
from datetime import datetime
import hashlib

app = Flask(__name__)
app.secret_key = 'temple_secret_key_2026'

# Configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ADMIN_PASSWORD = 'temple2026'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    conn = sqlite3.connect('submissions.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS submissions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  birthday TEXT NOT NULL,
                  gender TEXT NOT NULL,
                  photo_filename TEXT,
                  submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    try:
        name = request.form.get('name')
        birthday = request.form.get('birthday')
        gender = request.form.get('gender')
        
        if not all([name, birthday, gender]):
            return jsonify({'success': False, 'message': '请填写所有必填字段'})
        
        photo_filename = None
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Add timestamp to avoid duplicates
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                photo_filename = filename
        
        conn = sqlite3.connect('submissions.db')
        c = conn.cursor()
        c.execute('''INSERT INTO submissions (name, birthday, gender, photo_filename)
                     VALUES (?, ?, ?, ?)''', (name, birthday, gender, photo_filename))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': '感恩您的提交。愿福慧增长，吉祥如意。'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'提交失败: {str(e)}'})

@app.route('/admin')
def admin():
    if not session.get('admin_logged_in'):
        return render_template('admin_login.html')
    
    conn = sqlite3.connect('submissions.db')
    c = conn.cursor()
    c.execute('SELECT * FROM submissions ORDER BY submitted_at DESC')
    submissions = c.fetchall()
    conn.close()
    
    return render_template('admin.html', submissions=submissions)

@app.route('/admin/login', methods=['POST'])
def admin_login():
    password = request.form.get('password')
    if password == ADMIN_PASSWORD:
        session['admin_logged_in'] = True
        return redirect(url_for('admin'))
    return render_template('admin_login.html', error='密码错误')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
