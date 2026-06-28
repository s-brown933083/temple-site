from flask import Flask, render_template, request, jsonify, redirect, url_for, session, Response, make_response
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import os as _os

# Load .env before reading any environment variables
_dotenv_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '.env')
load_dotenv(_dotenv_path)

import sqlite3
import os

# Lazy import psycopg2 — only when DATABASE_URL is set (production)
# This prevents crash on platforms without libpq (e.g. CloudBase slim images)
_psycopg2 = None
_psycopg2_extras = None

def _get_psycopg2():
    global _psycopg2, _psycopg2_extras
    if _psycopg2 is None:
        import psycopg2 as _pg2
        import psycopg2.extras as _pg2e
        _psycopg2 = _pg2
        _psycopg2_extras = _pg2e
    return _psycopg2, _psycopg2_extras
import csv
import io
from datetime import datetime, timedelta
import hashlib
import smtplib
import threading
import re
from collections import defaultdict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'temple_secret_key_2026')

# ─── Security Headers ─────────────────────────────────────────
@app.after_request
def security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response

# ─── Simple Rate Limiting ─────────────────────────────────────
# Per-IP submission rate limiting (sliding window, 5 submissions per hour)
_submit_rates = defaultdict(list)

def rate_limit(max_requests=5, window_seconds=3600):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            ip = request.remote_addr or '127.0.0.1'
            now = datetime.now().timestamp()
            _submit_rates[ip] = [t for t in _submit_rates[ip] if now - t < window_seconds]
            if len(_submit_rates[ip]) >= max_requests:
                return jsonify({
                    'success': False,
                    'message': '提交过于频繁，请稍后再试。'
                }), 429
            _submit_rates[ip].append(now)
            return f(*args, **kwargs)
        return wrapped
    return decorator

# Configuration
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(os.path.dirname(__file__), 'static', 'uploads'))
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ADMIN_PASSWORD = 'zx897007360'

# Email Configuration (环境变量优先，支持 Gmail / QQ / QQ企业邮箱 / SendGrid 等)
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER = os.environ.get('SMTP_USER', 'your-email@gmail.com')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', 'your-app-password')
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@temple-serenity.org')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ─── Database: SQLite (dev) / PostgreSQL (production via DATABASE_URL) ─────
_DB_TYPE = None

def _detect_db_type():
    """Detect database type: 'postgres' if DATABASE_URL is set, else 'sqlite'."""
    global _DB_TYPE
    if _DB_TYPE is None:
        _DB_TYPE = 'postgres' if os.environ.get('DATABASE_URL') else 'sqlite'
    return _DB_TYPE

class _CursorWrapper:
    """Wraps sqlite3/psycopg2 cursors so ? placeholders auto-convert to %s for PG."""
    def __init__(self, cursor, is_pg):
        self._c = cursor
        self._pg = is_pg
    def execute(self, sql, params=None):
        if self._pg:
            sql = sql.replace('?', '%s')
            sql = sql.replace('date(submitted_at)', 'submitted_at::date')
            sql = sql.replace('date("now", "start of day")', 'CURRENT_DATE')
        if params:
            self._c.execute(sql, params)
        else:
            self._c.execute(sql)
    def fetchone(self):
        return self._c.fetchone()
    def fetchall(self):
        return self._c.fetchall()
    @property
    def lastrowid(self):
        return self._c.lastrowid
    @property
    def rowcount(self):
        return self._c.rowcount

class _DBWrapper:
    """Wraps sqlite3/psycopg2 connections to provide a unified interface."""
    def __init__(self, conn, is_pg):
        self._conn = conn
        self._pg = is_pg
    def cursor(self):
        return _CursorWrapper(self._conn.cursor(), self._pg)
    def commit(self):
        self._conn.commit()
    def close(self):
        self._conn.close()

def get_db():
    """Return a database connection (SQLite for dev, PostgreSQL for production)."""
    if _detect_db_type() == 'postgres':
        psycopg2, psycopg2_extras = _get_psycopg2()
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        conn.cursor_factory = psycopg2_extras.RealDictCursor
        return _DBWrapper(conn, True)
    else:
        db_path = os.environ.get('DATABASE_PATH', os.path.join(os.path.dirname(__file__), 'submissions.db'))
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return _DBWrapper(conn, False)

def init_db():
    """Create tables if not exist — works for both SQLite and PostgreSQL."""
    if _detect_db_type() == 'postgres':
        psycopg2, _ = _get_psycopg2()
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        conn.autocommit = True
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS submissions
                     (id SERIAL PRIMARY KEY,
                      name TEXT NOT NULL,
                      birthday TEXT NOT NULL,
                      gender TEXT NOT NULL,
                      photo_filename TEXT,
                      email TEXT,
                      message TEXT,
                      submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        conn.commit()
        conn.close()
    else:
        conn = sqlite3.connect('submissions.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS submissions
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      name TEXT NOT NULL,
                      birthday TEXT NOT NULL,
                      gender TEXT NOT NULL,
                      photo_filename TEXT,
                      email TEXT,
                      message TEXT,
                      submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        # Add email column if missing (for existing DB)
        try:
            c.execute('ALTER TABLE submissions ADD COLUMN email TEXT')
        except sqlite3.OperationalError:
            pass
        # Add message column if missing
        try:
            c.execute('ALTER TABLE submissions ADD COLUMN message TEXT')
        except sqlite3.OperationalError:
            pass
        conn.commit()
        conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health():
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT COUNT(*) as cnt FROM submissions')
        count = c.fetchone()['cnt']
        conn.close()
        return {'status': 'ok', 'service': 'temple-site', 'submissions': count}
    except Exception as e:
        return {'status': 'ok', 'service': 'temple-site', 'error': str(e)}

@app.route('/submit', methods=['POST'])
@rate_limit(max_requests=5, window_seconds=3600)
def submit():
    try:
        name = request.form.get('name', '').strip()
        birthday = request.form.get('birthday', '').strip()
        gender = request.form.get('gender', '').strip()
        email = request.form.get('email', '').strip() or None
        message = request.form.get('message', '').strip() or None
        
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
        c.execute('''INSERT INTO submissions (name, birthday, gender, photo_filename, email, message)
                     VALUES (?, ?, ?, ?, ?, ?)''', (name, birthday, gender, photo_filename, email, message))
        submission_id = c.lastrowid
        conn.commit()
        conn.close()
        
        # 后台异步发送通知邮件（不阻塞提交响应）
        # 注意：send_admin_notification 内部已经使用线程，不会阻塞
        try:
            threading.Thread(
                target=send_admin_notification,
                args=(name, birthday, gender, email, photo_filename, message, submission_id),
                daemon=True
            ).start()
        except Exception as e:
            print(f'通知邮件发送失败: {e}')

        return jsonify({'success': True, 'message': '感恩您的提交。愿福慧增长，吉祥如意。', 'submission_id': submission_id})
    
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
    
    c.execute('SELECT COUNT(*) as cnt FROM submissions')
    total = c.fetchone()['cnt']
    
    c.execute('SELECT COUNT(*) as cnt FROM submissions WHERE photo_filename IS NOT NULL AND photo_filename != ""')
    with_photo = c.fetchone()['cnt']
    
    c.execute('SELECT COUNT(*) as cnt FROM submissions WHERE submitted_at >= date("now", "start of day")')
    today = c.fetchone()['cnt']
    
    # Gender breakdown
    c.execute('SELECT gender, COUNT(*) as cnt FROM submissions GROUP BY gender')
    gender_stats = {row['gender']: row['cnt'] for row in c.fetchall()}
    
    # Recent 7 days trend
    trend = []
    for i in range(6, -1, -1):
        day = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        c.execute("SELECT COUNT(*) as cnt FROM submissions WHERE date(submitted_at) = ?", (day,))
        trend.append({'date': day, 'count': c.fetchone()['cnt']})
    
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
    c.execute(f'SELECT COUNT(*) as cnt FROM submissions{where_clause}', params)
    total = c.fetchone()['cnt']
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
            'message': row['message'],
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
        'message': row['message'],
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
    writer.writerow(['ID', '姓名', '生日', '性别', '邮箱', '留言', '照片文件', '提交时间'])
    
    for row in rows:
        writer.writerow([
            row['id'], row['name'], row['birthday'],
            row['gender'], row['email'] or '',
            row['message'] or '',
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


# ─── Auto-cleanup: delete data older than 30 days ──────
def cleanup_old_data():
    try:
        conn = get_db()
        c = conn.cursor()
        cutoff = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
        c.execute('SELECT photo_filename FROM submissions WHERE submitted_at < ? AND photo_filename IS NOT NULL', (cutoff,))
        old_photos = [row['photo_filename'] for row in c.fetchall()]
        for pf in old_photos:
            fp = os.path.join(app.config['UPLOAD_FOLDER'], pf)
            if os.path.exists(fp):
                try: os.remove(fp)
                except: pass
        c.execute('DELETE FROM submissions WHERE submitted_at < ?', (cutoff,))
        deleted = c.rowcount
        conn.commit()
        conn.close()
        if deleted > 0:
            print(f'🗑️ Auto-cleanup: deleted {deleted} records older than {cutoff}')
    except Exception as e:
        print(f'Cleanup failed: {e}')

cleanup_old_data()

# ─── Beautiful Email Templates ─────────────────────────────────

def get_email_template(content_html, title="禅意净土"):
    """Beautiful temple-aesthetic HTML email wrapper"""
    return f'''<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title></head>
<body style="margin:0;padding:0;background:#0a0a0a;font-family:'Microsoft YaHei','PingFang SC',sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a0a;padding:30px 10px;">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#111111;border:2px solid #c9a84c;border-radius:16px;overflow:hidden;">
      <tr><td style="background:linear-gradient(135deg,#1a1408 0%,#0d0d0d 100%);padding:40px 40px 30px;text-align:center;border-bottom:1px solid rgba(201,168,76,0.3);">
        <div style="font-size:36px;margin-bottom:10px;">☸</div>
        <h1 style="color:#c9a84c;font-size:24px;font-weight:400;letter-spacing:8px;margin:0;">{title}</h1>
        <div style="color:#6b5c3e;font-size:12px;letter-spacing:4px;margin-top:8px;">TEMPLE OF SERENITY</div>
      </td></tr>
      <tr><td style="padding:40px;">{content_html}</td></tr>
      <tr><td style="background:rgba(201,168,76,0.05);padding:25px 40px;border-top:1px solid rgba(201,168,76,0.2);text-align:center;">
        <p style="color:#6b5c3e;font-size:12px;line-height:2;margin:0 0 8px;">☸ 愿以此功德，庄严佛净土</p>
        <p style="color:#4a3f2f;font-size:11px;margin:0;">© 2026 Temple of Serenity · temple-serenity.org · 全部数据30天后自动删除</p>
      </td></tr>
    </table>
  </td></tr>
</table></body></html>'''

def get_admin_notification_html(name, birthday, gender, email, photo_filename, message, submission_id, base_url=''):
    photo_section = ''
    if photo_filename:
        photo_section = f'''<div style="margin:20px 0;text-align:center;">
          <img src="{base_url}/static/uploads/{photo_filename}" alt="用户照片"
          style="max-width:180px;border-radius:12px;border:2px solid #c9a84c;max-height:180px;object-fit:cover;"
          onerror="this.outerHTML='<span style=\'color:#6b5c3e;font-size:13px;\'>[照片加载失败]</span>'">
        </div>'''
    return f'''<div style="text-align:center;margin-bottom:30px;">
  <div style="display:inline-block;background:#c9a84c;color:#0a0a0a;padding:6px 20px;border-radius:20px;font-size:12px;letter-spacing:3px;margin-bottom:18px;">NEW SUBMISSION</div>
  <h2 style="color:#e8e0d0;font-size:20px;font-weight:400;margin:0 0 6px;">新的祈愿已提交</h2>
  <p style="color:#6b5c3e;font-size:13px;margin:0;">祈愿 #{submission_id} · {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
</div>
<table width="100%" cellpadding="12" cellspacing="0" style="background:rgba(201,168,76,0.06);border-radius:12px;border:1px solid rgba(201,168,76,0.2);margin-bottom:20px;">
  <tr><td style="color:#c9a84c;width:80px;font-size:13px;">姓名</td><td style="color:#e8e0d0;font-size:14px;font-weight:500;">{name}</td></tr>
  <tr><td style="color:#c9a84c;font-size:13px;">生日</td><td style="color:#b8a890;font-size:14px;">{birthday}</td></tr>
  <tr><td style="color:#c9a84c;font-size:13px;">性别</td><td style="color:#b8a890;font-size:14px;">{'男' if gender=='male' else '女'}</td></tr>
  <tr><td style="color:#c9a84c;font-size:13px;">邮箱</td><td style="color:#b8a890;font-size:14px;">{email or '<span style="color:#e74c3c;">未提供</span>'}</td></tr>
</table>
{photo_section}
''' + (f'''<div style="background:rgba(201,168,76,0.06);border-left:3px solid #c9a84c;padding:15px 20px;border-radius:0 8px 8px 0;margin:15px 0;"><p style="color:#b8a890;font-size:13px;margin:0;line-height:1.8;">{message}</p></div>''' if message else '') + f'''
<div style="text-align:center;margin-top:30px;">
  <a href="{base_url}/admin" style="display:inline-block;background:#c9a84c;color:#0a0a0a;padding:12px 32px;border-radius:25px;text-decoration:none;font-size:14px;letter-spacing:2px;font-weight:500;">进入管理后台 →</a>
</div>'''

def get_result_email_html(name, result_text):
    return f'''<div style="text-align:center;margin-bottom:30px;">
  <h2 style="color:#c9a84c;font-size:22px;font-weight:400;letter-spacing:4px;margin:0 0 10px;">☸ {name}，吉祥如意</h2>
  <p style="color:#6b5c3e;font-size:13px;margin:0;">您的祈愿结果已生成</p>
</div>
<div style="background:rgba(201,168,76,0.06);border:1px solid rgba(201,168,76,0.3);border-radius:16px;padding:30px;margin-bottom:25px;text-align:center;">
  <p style="color:#e8e0d0;font-size:15px;line-height:2.2;margin:0;white-space:pre-wrap;">{result_text}</p>
</div>
<p style="color:#6b5c3e;font-size:12px;text-align:center;line-height:2;margin:0;">
  本结果仅供参考娱乐，不构成任何预测或保证<br>如有疑问请联系：admin@temple-serenity.org
</p>'''

# ─── Low-level SMTP ───────────────────────────────────────────

def send_smtp_email(to_email, subject, html_content):
    if not to_email or to_email in ('your-email@gmail.com', 'your-app-password'):
        print(f'[SKIP] Email not configured: {subject}')
        return False
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = f'Temple of Serenity <{SMTP_USER}>'
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f'[OK] Email sent: {to_email}')
        return True
    except Exception as e:
        print(f'[FAIL] Email failed: {to_email} -> {e}')
        return False

# ─── Admin Notification ────────────────────────────────────────

def send_admin_notification(name, birthday, gender, email, photo_filename, message=None, submission_id=None):
    base_url = os.environ.get('BASE_URL', '').rstrip('/')
    content = get_admin_notification_html(name, birthday, gender, email, photo_filename, message, submission_id or '?', base_url)
    html = get_email_template(content, f'【新祈愿提交】{name}')
    return send_smtp_email(ADMIN_EMAIL, f'【新祈愿 #{submission_id}】来自 {name}', html)


# ─── SEO: robots.txt & sitemap.xml ─────────────────────────────

@app.route('/robots.txt')
def robots_txt():
    return Response(
        'User-agent: *\n'
        'Allow: /\n'
        'Disallow: /admin\n'
        'Disallow: /admin/api/\n'
        'Sitemap: https://temple-serenity.org/sitemap.xml\n',
        mimetype='text/plain'
    )

@app.route('/sitemap.xml')
def sitemap_xml():
    base = os.environ.get('BASE_URL', 'https://temple-serenity.org').rstrip('/')
    pages = [
        {'loc': f'{base}/', 'priority': '1.0', 'changefreq': 'weekly'},
        {'loc': f'{base}/admin', 'priority': '0.3', 'changefreq': 'monthly'},
    ]
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for p in pages:
        xml += f'  <url><loc>{p["loc"]}</loc><priority>{p["priority"]}</priority><changefreq>{p["changefreq"]}</changefreq></url>\n'
    xml += '</urlset>'
    return Response(xml, mimetype='application/xml')

# ─── Admin: Test Email API ────────────────────────────────────

@app.route('/admin/api/test-email', methods=['POST'])
def admin_test_email():
    if not session.get('admin_logged_in'):
        return jsonify({'error': '未登录'}), 401
    test_html = get_email_template(
        '<p style="color:#e8e0d0;font-size:15px;text-align:center;padding:30px 0;">'
        '这是一封测试邮件。<br>禅意净土邮件系统运行正常 ☸</p>',
        '邮件测试 - 禅意净土'
    )
    success = send_smtp_email(ADMIN_EMAIL, '【测试】禅意净土邮件系统', test_html)
    if success:
        return jsonify({'success': True, 'message': f'测试邮件已发送至 {ADMIN_EMAIL}'})
    else:
        return jsonify({'error': '发送失败，请检查 SMTP 配置'}), 500


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)


# ─── Email Functions ─────────────────────────────────────────

def send_result_email(to_email, name, result_text):
    content = get_result_email_html(name, result_text)
    html = get_email_template(content, f'您的祈愿结果 - 禅意净土')
    return send_smtp_email(to_email, '您的祈愿结果已出炉 - 禅意净土', html)
def admin_api_send_result(submission_id):
    """管理员发送结果到用户邮箱"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': '未登录'}), 401
    
    result_text = request.form.get('result_text', '').strip()
    if not result_text:
        return jsonify({'error': '请填写结果内容'}), 400
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM submissions WHERE id = ?', (submission_id,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        return jsonify({'error': '记录不存在'}), 404
    
    if not row['email']:
        conn.close()
        return jsonify({'error': '该用户未填写邮箱'}), 400
    
    success = send_result_email(row['email'], row['name'], result_text)
    conn.close()
    
    if success:
        return jsonify({'success': True, 'message': '结果已发送至用户邮箱'})
    else:
        return jsonify({'error': '邮件发送失败，请检查邮箱配置'}), 500
