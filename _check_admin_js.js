
// ─── State ───
let currentPage = 1;
let currentSortBy = 'submitted_at';
let currentSortOrder = 'DESC';
let deleteTargetId = null;
let searchTimer = null;

// ─── Init ───
document.addEventListener('DOMContentLoaded', () => {
    loadDashboard();
    loadSubmissions(1);
    
    // Sidebar nav
    document.querySelectorAll('[data-page]').forEach(el => {
        el.addEventListener('click', () => {
            const page = el.dataset.page;
            document.querySelectorAll('[data-page]').forEach(e => e.classList.remove('active'));
            el.classList.add('active');
            
            document.getElementById('page-dashboard').style.display = page === 'dashboard' ? 'block' : 'none';
            document.getElementById('page-submissions').style.display = page === 'submissions' ? 'block' : 'none';
            document.getElementById('pageTitle').textContent = page === 'dashboard' ? '📊 数据看板' : '📋 提交记录';
            
            if (window.innerWidth <= 768) {
                document.getElementById('sidebar').classList.remove('open');
            }
            
            if (page === 'dashboard') loadDashboard();
        });
    });
});

// ─── Dashboard ───
function loadDashboard() {
    fetch('/admin/api/stats')
        .then(r => r.json())
        .then(d => {
            document.getElementById('statTotal').textContent = d.total;
            document.getElementById('statToday').textContent = d.today;
            document.getElementById('statPhoto').textContent = d.with_photo;
            document.getElementById('totalBadge').textContent = d.total;
            
            // Gender
            const gd = d.gender_stats || {};
            const genderHtml = Object.entries(gd).map(([k,v]) => 
                `<div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid var(--border-dark);font-size:13px;">
                    <span>${k}</span>
                    <span style="color:var(--gold-primary);">${v}</span>
                </div>`
            ).join('');
            document.getElementById('genderStats').innerHTML = genderHtml || '<span style="opacity:0.5;">暂无数据</span>';
            
            // Trend
            const trend = d.trend || [];
            const maxVal = Math.max(...trend.map(t => t.count), 1);
            const bars = trend.map(t => {
                const h = Math.max(2, (t.count / maxVal) * 50);
                const day = t.date.slice(5);
                return `<div class="trend-col"><div class="bar" style="height:${h}px"></div><div class="label">${day}</div></div>`;
            }).join('');
            document.getElementById('trendBar').innerHTML = bars;
            
            // Recent list
            fetch('/admin/api/submissions?per_page=5&sort_by=submitted_at&sort_order=DESC')
                .then(r => r.json())
                .then(d2 => {
                    const list = (d2.submissions || []).map(s => 
                        `<div style="display:flex;justify-content:space-between;padding:3px 0;font-size:12px;border-bottom:1px solid var(--border-dark);">
                            <span>${s.name}</span>
                            <span style="opacity:0.5;">${s.submitted_at ? s.submitted_at.slice(0,16).replace('T',' ') : ''}</span>
                        </div>`
                    ).join('');
                    document.getElementById('recentMiniList').innerHTML = list || '<span style="opacity:0.5;">暂无提交</span>';
                });
        })
        .catch(() => {});
}

// ─── Submissions Table ───
function loadSubmissions(page) {
    currentPage = page || 1;
    const search = encodeURIComponent(document.getElementById('searchInput').value);
    const gender = document.getElementById('genderFilter').value;
    const dateFrom = document.getElementById('dateFrom').value;
    const dateTo = document.getElementById('dateTo').value;
    
    const url = `/admin/api/submissions?page=${currentPage}&per_page=20&search=${search}&gender=${gender}&date_from=${dateFrom}&date_to=${dateTo}&sort_by=${currentSortBy}&sort_order=${currentSortOrder}`;
    
    const tbody = document.getElementById('submissionsBody');
    tbody.innerHTML = '<tr class="loading-row"><td colspan="8"><div class="loading-spinner"><div class="spinner"></div><p>加载中...</p></div></td></tr>';
    
    fetch(url)
        .then(r => r.json())
        .then(d => {
            document.getElementById('totalBadge').textContent = d.total;
            
            if (!d.submissions || d.submissions.length === 0) {
                tbody.innerHTML = `<tr><td colspan="8"><div class="empty-state"><div class="icon">☸</div><p>暂无提交记录</p></div></td></tr>`;
                document.getElementById('pagination').innerHTML = '';
                return;
            }
            
            const rows = d.submissions.map(s => {
                const photoHtml = s.photo_filename 
                    ? `<img src="/static/uploads/${s.photo_filename}" class="photo-thumb" onclick="showDetail(${s.id})" title="点击查看详情">`
                    : '<div class="no-photo">无</div>';
                
                const genderClass = s.gender === '男' ? 'gender-male' : s.gender === '女' ? 'gender-female' : '';
                const genderHtml = `<span class="gender-tag ${genderClass}">${s.gender || '-'}</span>`;
                
                const time = s.submitted_at ? s.submitted_at.slice(0,16).replace('T',' ') : '-';
                const emailDisplay = s.email || '<span style="opacity:0.4;">-</span>';
                
                const messageDisplay = s.message && s.message.trim()
                    ? `<span class="message-tag" title="${s.message.replace(/"/g,'&quot;')}">${s.message.slice(0,20)}${s.message.length > 20 ? '...' : ''}</span>`
                    : '<span style="opacity:0.3;">-</span>';

                return `<tr>
                    <td style="font-family:monospace;">${s.id}</td>
                    <td>${photoHtml}</td>
                    <td><strong>${s.name}</strong></td>
                    <td>${s.birthday}</td>
                    <td>${genderHtml}</td>
                    <td style="font-size:13px;">${emailDisplay}</td>
                    <td style="font-size:12px;max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${(s.message||'')
.replace(/</g,'&lt;').replace(/>/g,'&gt;')}">${messageDisplay}</td>
                    <td style="font-size:12px;white-space:nowrap;">${time}</td>
                    <td>
                        <div class="action-btns">
                            <button class="btn btn-sm" onclick="showDetail(${s.id})">👁️</button>
                            <button class="btn btn-sm btn-danger" onclick="confirmDelete(${s.id})">🗑️</button>
                        </div>
                    </td>
                </tr>`;
            }).join('');
            tbody.innerHTML = rows;
            
            // Pagination
            renderPagination(d.page, d.total_pages, d.total);
        })
        .catch(() => {
            tbody.innerHTML = '<tr><td colspan="8"><div class="empty-state"><p style="color:var(--danger);">加载失败，请刷新重试</p></div></td></tr>';
        });
}

function renderPagination(page, totalPages, total) {
    const el = document.getElementById('pagination');
    if (totalPages <= 1) { el.innerHTML = ''; return; }
    
    let html = `<span class="page-info">共 ${total} 条</span>`;
    html += `<button class="page-btn" onclick="loadSubmissions(1)" ${page <= 1 ? 'disabled' : ''}>«</button>`;
    html += `<button class="page-btn" onclick="loadSubmissions(${page - 1})" ${page <= 1 ? 'disabled' : ''}>‹</button>`;
    
    const start = Math.max(1, page - 2);
    const end = Math.min(totalPages, page + 2);
    
    if (start > 1) { html += `<button class="page-btn" onclick="loadSubmissions(1)">1</button>`; if (start > 2) html += `<span class="page-info">...</span>`; }
    
    for (let i = start; i <= end; i++) {
        html += `<button class="page-btn ${i === page ? 'active' : ''}" onclick="loadSubmissions(${i})">${i}</button>`;
    }
    
    if (end < totalPages) { if (end < totalPages - 1) html += `<span class="page-info">...</span>`; html += `<button class="page-btn" onclick="loadSubmissions(${totalPages})">${totalPages}</button>`; }
    
    html += `<button class="page-btn" onclick="loadSubmissions(${page + 1})" ${page >= totalPages ? 'disabled' : ''}>›</button>`;
    html += `<button class="page-btn" onclick="loadSubmissions(${totalPages})" ${page >= totalPages ? 'disabled' : ''}>»</button>`;
    
    el.innerHTML = html;
}

// ─── Sort ───
function sortBy(field) {
    if (currentSortBy === field) {
        currentSortOrder = currentSortOrder === 'ASC' ? 'DESC' : 'ASC';
    } else {
        currentSortBy = field;
        currentSortOrder = 'DESC';
    }
    loadSubmissions(1);
}

// ─── Search ───
function debounceSearch() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => loadSubmissions(1), 300);
}

function clearFilters() {
    document.getElementById('searchInput').value = '';
    document.getElementById('genderFilter').value = 'all';
    document.getElementById('dateFrom').value = '';
    document.getElementById('dateTo').value = '';
    loadSubmissions(1);
}

// ─── Detail Modal ───
function showDetail(id) {
    fetch(`/admin/api/submissions/${id}`)
        .then(r => r.json())
        .then(s => {
            const photoHtml = s.photo_filename 
                ? `<img src="/static/uploads/${s.photo_filename}" class="modal-photo" alt="照片">`
                : '<div style="text-align:center;padding:40px;border:1px dashed var(--gold-dark);border-radius:6px;margin-bottom:20px;color:var(--text-secondary);">📷 未上传照片</div>';
            
            document.getElementById('modalContent').innerHTML = `
                ${photoHtml}
                <div class="modal-info">
                    <div class="modal-field"><label>姓名</label><div class="value">${s.name}</div></div>
                    <div class="modal-field"><label>性别</label><div class="value">${s.gender || '-'}</div></div>
                    <div class="modal-field"><label>生日</label><div class="value">${s.birthday}</div></div>
                    <div class="modal-field"><label>邮箱</label><div class="value">${s.email || '-'}</div></div>
                    ${s.message ? `<div class="modal-field full"><label>留言</label><div class="value" style="white-space:pre-wrap;">${s.message}</div></div>` : ''}
                    <div class="modal-field full"><label>提交时间</label><div class="value">${s.submitted_at?.replace('T',' ') || '-'}</div></div>
                    <div class="modal-field full" style="text-align:center;margin-top:10px;">
                        <button class="btn btn-danger" onclick="closeModal();confirmDelete(${s.id})">🗑️ 删除此记录</button>
                    </div>
                </div>
            `;
            document.getElementById('detailModal').classList.add('show');
        });
}

function closeModal() {
    document.getElementById('detailModal').classList.remove('show');
}

// ─── Delete ───
function confirmDelete(id) {
    deleteTargetId = id;
    document.getElementById('confirmMessage').textContent = `确定要删除 ID 为 ${id} 的记录吗？此操作不可恢复。`;
    const btn = document.getElementById('confirmBtn');
    btn.onclick = doDelete;
    document.getElementById('confirmModal').classList.add('show');
}

function closeConfirm() {
    document.getElementById('confirmModal').classList.remove('show');
    deleteTargetId = null;
}

function doDelete() {
    const id = deleteTargetId;
    closeConfirm();
    
    fetch(`/admin/api/submissions/${id}/delete`, { method: 'POST' })
        .then(r => r.json())
        .then(d => {
            if (d.success) {
                showToast('✅ 已删除', 'success');
                loadSubmissions(currentPage);
                loadDashboard();
            } else {
                showToast('❌ ' + (d.error || '删除失败'), 'error');
            }
        })
        .catch(() => showToast('❌ 网络错误', 'error'));
}

// ─── Export CSV ───
function exportCSV() {
    window.location.href = '/admin/api/submissions/export';
}

// ─── Refresh ───
function refreshData() {
    loadDashboard();
    if (document.getElementById('page-submissions').style.display !== 'none') {
        loadSubmissions(currentPage);
    }
    showToast('🔄 已刷新', 'success');
}

// ─── Toast ───
function showToast(msg, type) {
    const el = document.getElementById('toast');
    el.textContent = msg;
    el.className = 'toast toast-' + type + ' show';
    setTimeout(() => el.classList.remove('show'), 2500);
}

// ─── Click outside modal ───
document.getElementById('detailModal').addEventListener('click', function(e) {
    if (e.target === this) closeModal();
});
document.getElementById('confirmModal').addEventListener('click', function(e) {
    if (e.target === this) closeConfirm();
});
