# Temple Site - 完整部署指南

## 🚀 一键部署到 Railway（推荐，永久在线）

Railway 提供免费额度，无需信用卡，适合小流量网站。

### 第一步：连接 GitHub（只需做一次）

1. 打开浏览器访问：**https://railway.app**
2. 点击 **"Start a New Project"**
3. 选择 **"Deploy from GitHub repo"**
4. 点击 **"Connect GitHub"**，授权 Railway 访问你的 GitHub
5. 在列表中找到 **`s-brown933083/temple-site`**，点击部署

Railway 会自动检测 Dockerfile 并开始构建部署（2-5分钟）。

部署完成后，Railway 会给你一个永久 URL，例如：
```
https://temple-site-production.up.railway.app
```

---

### 第二步：绑定自定义域名（可选）

1. 在 Railway 项目面板 → **Settings → Domains**
2. 添加你的域名：`temple-serenity.org`（或 `www.temple-serenity.org`）
3. Railway 会给出 DNS 记录，按要求在域名商处添加：
   - **CNAME 记录**：`www` → `temple-site.railway.app`
   - **A 记录 或 CNAME**：`@` → 同上（参考 Railway 给的指引）

---

### 第三步：配置邮件通知（部署完成后做）

**前提：需要能发送邮件的 SMTP 账号（推荐 Gmail / QQ邮箱）**

#### Gmail 配置方法：
1. 登录 Gmail → 账户设置 → 安全
2. 开启"两步验证"后，在"应用密码"页面生成一个16位密码
3. 将以下信息发给 QClaw：

```
SMTP_SERVER = smtp.gmail.com
SMTP_PORT = 587
SMTP_USER = 你的@gmail.com
SMTP_PASSWORD = 应用专用密码
ADMIN_EMAIL = admin@temple-serenity.org
```

#### QQ邮箱配置方法：
1. 登录 mail.qq.com → 设置 → 账户
2. 开启 SMTP 服务，生成授权码
3. 将以下信息发给 QClaw：

```
SMTP_SERVER = smtp.qq.com
SMTP_PORT = 587
SMTP_USER = 你的QQ号@qq.com
SMTP_PASSWORD = 授权码
ADMIN_EMAIL = admin@temple-serenity.org
```

---

## 📁 项目文件结构

```
temple-site/
├── app.py              ← Flask 主程序
├── Dockerfile          ← Railway 部署配置
├── railway.json        ← Railway 项目配置
├── requirements.txt    ← Python 依赖
├── templates/          ← HTML 模板
│   ├── index.html
│   ├── admin.html
│   └── admin_login.html
├── static/
│   ├── style.css
│   ├── uploads/        ← 用户上传的照片
│   ├── images/
│   └── videos/
└── submissions.db      ← SQLite 数据库
```

---

## ⚙️ 环境变量说明

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `PORT` | 监听端口 | `5000` |
| `SMTP_SERVER` | SMTP 服务器 | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP 端口 | `587` |
| `SMTP_USER` | 发件邮箱 | 占位符 |
| `SMTP_PASSWORD` | 邮箱密码/授权码 | 占位符 |
| `ADMIN_EMAIL` | 管理员收件邮箱 | `admin@temple-serenity.org` |
| `DATABASE_PATH` | 数据库路径 | 程序同目录 |
| `UPLOAD_FOLDER` | 上传目录 | `static/uploads` |

---

## 🔧 本地开发

```bash
cd F:\temple-site
set SMTP_SERVER=smtp.gmail.com
set SMTP_USER=your-email@gmail.com
set SMTP_PASSWORD=your-app-password
python app.py
```

访问 `http://localhost:5000`

---

## 📧 邮件功能说明

提交祈愿后，系统会**后台异步**发送邮件通知给管理员，不影响提交响应速度。

如果 SMTP 配置错误，提交本身不受影响，只是邮件发送失败（不影响用户）。

---

## 🛡️ 管理后台

地址：`https://你的域名/admin`
密码：`temple2026`

管理后台功能：
- 查看所有祈愿提交
- 按姓名/邮箱搜索
- 查看用户上传的照片
- 发送祈愿结果邮件
- 导出数据为 CSV

---

*愿此网站广度众生，吉祥如意！ 🙏*
