from flask import Flask, render_template, request, jsonify, redirect, url_for, session, Response
from werkzeug.utils import secure_filename
import sqlite3
import os
import csv
import io
from datetime import datetime, timedelta
import hashlib

app = Flask(__name__)
app.secret_key = 'temple_secret_key_2026'

# Configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ADMIN_PASSWORD = 'temple2026'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db():
    conn = sqlite3.connect('submissions.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = sqlite3.connect('submissions.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS submissions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  birthday TEXT NOT NULL,
                  gender TEXT NOT NULL,
                  photo_filename TEXT,
                  email TEXT,
                  submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    # Add email column if missing (for existing DB)
    try:
        c.execute('ALTER TABLE submissions ADD COLUMN email TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    try:
        name = request.form.get('name', '').strip()
        birthday = request.form.get('birthday', '').strip()
        gender = request.form.get('gender', '').strip()
        email = request.form.get('email', '').strip() or None
        
        if not all([name, birthday, gender]):
            return jsonify({'success': False, 'message': '请填写所有必填字段'})
        
        photo_filename = None
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                photo_filename = filename
        
        conn = get_db()
        c = conn.cursor()
        c.execute('''INSERT INTO submissions (name, birthday, gender, photo_filename, email)
                     VALUES (?, ?, ?, ?, ?)''', (name, birthday, gender, photo_filename, email))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': '感恩您的提交。愿福慧增长，吉祥如意。'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'提交失败: {str(e)}'})

# ─── Admin Routes ────────────────────────────────────────────

@app.route('/admin')
def admin():
    if not session.get('admin_logged_in'):
        return render_template('admin_login.html')
    return render_template('admin.html')

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

# ─── Admin API Routes (JSON) ─────────────────────────────────

@app.route('/admin/api/stats')
def admin_api_stats():
    if not session.get('admin_logged_in'):
        return jsonify({'error': '未登录'}), 401
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) FROM submissions')
    total = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM submissions WHERE photo_filename IS NOT NULL AND photo_filename != ""')
    with_photo = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM submissions WHERE submitted_at >= date("now", "start of day")')
    today = c.fetchone()[0]
    
    # Gender breakdown
    c.execute('SELECT gender, COUNT(*) as cnt FROM submissions GROUP BY gender')
    gender_stats = {row['gender']: row['cnt'] for row in c.fetchall()}
    
    # Recent 7 days trend
    trend = []
    for i in range(6, -1, -1):
        day = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        c.execute("SELECT COUNT(*) FROM submissions WHERE date(submitted_at) = ?", (day,))
        trend.append({'date': day, 'count': c.fetchone()[0]})
    
    conn.close()
    
    return jsonify({
        'total': total,
        'with_photo': with_photo,
        'today': today,
        'gender_stats': gender_stats,
        'trend': trend
    })

@app.route('/admin/api/submissions')
def admin_api_submissions():
    if not session.get('admin_logged_in'):
        return jsonify({'error': '未登录'}), 401
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)
    search = request.args.get('search', '').strip()
    gender_filter = request.args.get('gender', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    sort_by = request.args.get('sort_by', 'submitted_at')
    sort_order = request.args.get('sort_order', 'DESC')
    
    allowed_sort = {'id', 'name', 'birthday', 'gender', 'submitted_at'}
    if sort_by not in allowed_sort:
        sort_by = 'submitted_at'
    if sort_order.upper() not in ('ASC', 'DESC'):
        sort_order = 'DESC'
    
    conditions = []
    params = []
    
    if search:
        conditions.append('(name LIKE ? OR email LIKE ?)')
        params.extend([f'%{search}%', f'%{search}%'])
    
    if gender_filter and gender_filter != 'all':
        conditions.append('gender = ?')
        params.append(gender_filter)
    
    if date_from:
        conditions.append('date(submitted_at) >= ?')
        params.append(date_from)
    
    if date_to:
        conditions.append('date(submitted_at) <= ?')
        params.append(date_to)
    
    where_clause = ' WHERE ' + ' AND '.join(conditions) if conditions else ''
    
    conn = get_db()
    c = conn.cursor()
    
    # Count total
    c.execute(f'SELECT COUNT(*) FROM submissions{where_clause}', params)
    total = c.fetchone()[0]
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, total_pages)
    offset = (page - 1) * per_page
    
    # Fetch data
    c.execute(f'SELECT * FROM submissions{where_clause} ORDER BY {sort_by} {sort_order} LIMIT ? OFFSET ?',
              params + [per_page, offset])
    rows = c.fetchall()
    
    submissions = []
    for row in rows:
        submissions.append({
            'id': row['id'],
            'name': row['name'],
            'birthday': row['birthday'],
            'gender': row['gender'],
            'photo_filename': row['photo_filename'],
            'email': row['email'],
            'submitted_at': row['submitted_at']
        })
    
    conn.close()
    
    return jsonify({
        'submissions': submissions,
        'page': page,
        'per_page': per_page,
        'total': total,
        'total_pages': total_pages
    })

@app.route('/admin/api/submissions/<int:submission_id>')
def admin_api_submission_detail(submission_id):
    if not session.get('admin_logged_in'):
        return jsonify({'error': '未登录'}), 401
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM submissions WHERE id = ?', (submission_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        return jsonify({'error': '记录不存在'}), 404
    
    return jsonify({
        'id': row['id'],
        'name': row['name'],
        'birthday': row['birthday'],
        'gender': row['gender'],
        'photo_filename': row['photo_filename'],
        'email': row['email'],
        'submitted_at': row['submitted_at']
    })

@app.route('/admin/api/submissions/<int:submission_id>/delete', methods=['POST'])
def admin_api_delete_submission(submission_id):
    if not session.get('admin_logged_in'):
        return jsonify({'error': '未登录'}), 401
    
    conn = get_db()
    c = conn.cursor()
    
    # Get photo filename to delete file
    c.execute('SELECT photo_filename FROM submissions WHERE id = ?', (submission_id,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        return jsonify({'error': '记录不存在'}), 404
    
    # Delete photo file
    if row['photo_filename']:
        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], row['photo_filename'])
        if os.path.exists(photo_path):
            try:
                os.remove(photo_path)
            except:
                pass
    
    c.execute('DELETE FROM submissions WHERE id = ?', (submission_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': '已删除'})

@app.route('/admin/api/submissions/export')
def admin_api_export():
    if not session.get('admin_logged_in'):
        return jsonify({'error': '未登录'}), 401
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM submissions ORDER BY submitted_at DESC')
    rows = c.fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', '姓名', '生日', '性别', '邮箱', '照片文件', '提交时间'])
    
    for row in rows:
        writer.writerow([
            row['id'], row['name'], row['birthday'],
            row['gender'], row['email'] or '',
            row['photo_filename'] or '', row['submitted_at']
        ])
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=submissions_{timestamp}.csv'}
    )

# ─── Picture viewer ──────────────────────────────────────────

@app.route('/admin/photo/<filename>')
def admin_photo(filename):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))
    return redirect(url_for('static', filename=f'uploads/{filename}'))


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
