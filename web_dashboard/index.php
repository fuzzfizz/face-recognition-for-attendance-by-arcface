<?php
// Show setup page if config.php is missing
if (!file_exists(__DIR__ . '/config.php')) {
    echo '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Setup Required</title>
    <style>body{background:#0f1117;color:#e2e8f0;font-family:system-ui;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}
    .box{background:#1a1d2e;border:1px solid #2d3148;border-radius:12px;padding:32px;max-width:480px}
    h1{color:#a78bfa;margin-bottom:12px}pre{background:#0f1117;padding:12px;border-radius:6px;font-size:13px;margin:8px 0}
    </style></head><body><div class="box">
    <h1>Setup Required</h1>
    <p>Copy <code>config.example.php</code> to <code>config.php</code> and fill in your Supabase credentials:</p>
    <pre>cp config.example.php config.php</pre>
    </div></body></html>';
    exit;
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>FaceAttend Dashboard</title>
  <meta name="description" content="Face recognition attendance system dashboard — live check-in logs and student registration status.">
  <link rel="stylesheet" href="assets/style.css">
</head>
<body>

<!-- Top Bar -->
<header class="topbar">
  <div class="topbar-logo">FaceAttend <span>Dashboard</span></div>
  <div class="live-badge">
    <div class="live-dot online" id="live-dot"></div>
    <span id="live-label">Live · refreshes every 5s</span>
  </div>
</header>

<!-- Error Banner -->
<div class="error-banner" id="error-banner">
  <span id="error-msg">Could not reach Supabase. Retrying...</span>
  <button onclick="document.getElementById('error-banner').classList.remove('visible')">✕</button>
</div>

<!-- Stats Row -->
<div class="stats-row">
  <div class="stat-card">
    <div class="stat-label">Total Students</div>
    <div class="stat-value stat-value--purple" id="stat-total-students">—</div>
    <div class="stat-sub">Registered in system</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Today's Check-ins</div>
    <div class="stat-value stat-value--green" id="stat-today-checkins">—</div>
    <div class="stat-sub" id="stat-today-date"><?= gmdate('D, d M Y') ?></div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Pending Queue</div>
    <div class="stat-value stat-value--yellow" id="stat-pending">—</div>
    <div class="stat-sub">Awaiting processing</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Last Check-in</div>
    <div class="stat-value stat-value--sm" id="stat-last-time">—</div>
    <div class="stat-sub" id="stat-last-student">—</div>
  </div>
</div>

<!-- Tabs -->
<div class="tabs">
  <div class="tab active" id="tab-attendance" onclick="switchTab('attendance')">
    📋 Attendance <span class="badge badge--purple" id="badge-attendance"></span>
  </div>
  <div class="tab" id="tab-students" onclick="switchTab('students')">
    👤 Students
  </div>
  <div class="tab" id="tab-queue" onclick="switchTab('queue')">
    ⚙️ Queue <span class="badge badge--yellow" id="badge-queue"></span>
  </div>
</div>

<!-- ── Tab: Attendance ── -->
<div class="tab-content active" id="content-attendance">
  <div class="filter-bar">
    <span class="filter-label">Date:</span>
    <input type="date" class="filter-input" id="filter-date" value="<?= gmdate('Y-m-d') ?>">
    <span class="filter-label">Device:</span>
    <select class="filter-select" id="filter-device">
      <option value="">All Devices</option>
    </select>
    <button class="btn-refresh" onclick="loadAttendance(1)">↻ Refresh now</button>
  </div>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Student ID</th><th>Name</th><th>Check-in Time</th><th>Similarity Score</th><th>Device</th>
        </tr>
      </thead>
      <tbody id="attendance-body">
        <tr><td colspan="5"><div class="empty-state"><p>Loading...</p></div></td></tr>
      </tbody>
    </table>
    <div class="pagination" id="attendance-pagination" style="display:none">
      <span id="attendance-page-info"></span>
      <div class="page-btns" id="attendance-page-btns"></div>
    </div>
  </div>
  <p class="legend">🟢 ≥ 0.75 high confidence &nbsp;·&nbsp; 🟡 0.60–0.74 medium &nbsp;·&nbsp; 🔴 &lt; 0.60 low confidence</p>
</div>

<!-- ── Tab: Students ── -->
<div class="tab-content" id="content-students">
  <div class="table-wrap">
    <table>
      <thead>
        <tr><th>Student ID</th><th>Name</th><th>Registered At</th><th>Status</th></tr>
      </thead>
      <tbody id="students-body">
        <tr><td colspan="4"><div class="empty-state"><p>Click Students tab to load.</p></div></td></tr>
      </tbody>
    </table>
  </div>
</div>

<!-- ── Tab: Queue ── -->
<div class="tab-content" id="content-queue">
  <div class="filter-bar">
    <span class="filter-label">Status:</span>
    <select class="filter-select" id="filter-queue-status" onchange="loadQueue()">
      <option value="">All</option>
      <option value="pending">Pending</option>
      <option value="completed">Completed</option>
      <option value="failed">Failed</option>
    </select>
    <button class="btn-refresh" onclick="loadQueue()">↻ Refresh now</button>
    <button class="btn-refresh" style="background:#a78bfa;color:#0f1117" onclick="triggerForceTraining()">⚙️ Force Training Now</button>
  </div>
  <div class="table-wrap">
    <table>
      <thead>
        <tr><th>Student ID</th><th>Image Path</th><th>Status</th><th>Created At</th><th>Processed At</th><th>Error</th></tr>
      </thead>
      <tbody id="queue-body">
        <tr><td colspan="6"><div class="empty-state"><p>Click Queue tab to load.</p></div></td></tr>
      </tbody>
    </table>
  </div>
</div>

<script>
// ── State ──
let currentTab   = 'attendance';
let attendancePage = 1;
const PER_PAGE   = 20;
let knownIds     = new Set(); // track last page of IDs to highlight new rows
let allDevices   = new Set(); // globally track all discovered devices
let pollTimer    = null;

// ── Tab switching ──
function switchTab(name) {
  currentTab = name;
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  document.getElementById('content-' + name).classList.add('active');
  if (name === 'attendance') loadAttendance(1);
  if (name === 'students') loadStudents();
  if (name === 'queue')    loadQueue();
}

// ── Helpers ──
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
function formatTime(isoStr) {
  if (!isoStr) return '—';
  const d = new Date(isoStr);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}
function formatRelative(isoStr) {
  if (!isoStr) return '';
  const diff = Math.floor((Date.now() - new Date(isoStr)) / 1000);
  if (diff < 60)   return diff + ' seconds ago';
  if (diff < 3600) return Math.floor(diff / 60) + ' minutes ago';
  if (diff < 86400) return Math.floor(diff / 3600) + ' hours ago';
  return Math.floor(diff / 86400) + ' days ago';
}
function formatDateTime(isoStr) {
  if (!isoStr) return '—';
  return new Date(isoStr).toLocaleString();
}
function scoreBadge(score) {
  if (score === null || score === undefined) return '—';
  const cls = score >= 0.75 ? 'high' : score >= 0.60 ? 'mid' : 'low';
  return `<span class="score-badge score-badge--${cls}">${parseFloat(score).toFixed(2)}</span>`;
}
function statusBadge(status) {
  const s = status || 'none';
  return `<span class="status-badge status-badge--${escapeHtml(s)}">${escapeHtml(s)}</span>`;
}
function setError(msg) {
  const dot = document.getElementById('live-dot');
  const banner = document.getElementById('error-banner');
  dot.className = 'live-dot offline';
  document.getElementById('live-label').textContent = 'Offline';
  document.getElementById('error-msg').textContent = msg;
  banner.classList.add('visible');
}
function clearError() {
  const dot = document.getElementById('live-dot');
  dot.className = 'live-dot online';
  document.getElementById('live-label').textContent = 'Live · refreshes every 5s';
  document.getElementById('error-banner').classList.remove('visible');
}

// ── Stats ──
async function loadStats() {
  try {
    const res = await fetch('api/stats.php');
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const d = await res.json();
    if (d.error) throw new Error(d.error);

    clearError();
    document.getElementById('stat-total-students').textContent = d.total_students ?? '—';
    document.getElementById('stat-today-checkins').textContent = d.today_checkins ?? '—';
    document.getElementById('stat-pending').textContent        = d.pending_queue  ?? '—';

    // Badge on Queue tab
    const qPending = d.pending_queue ?? 0;
    document.getElementById('badge-queue').textContent = qPending > 0 ? qPending : '';

    if (d.last_checkin) {
      document.getElementById('stat-last-time').textContent    = formatTime(d.last_checkin.timestamp);
      document.getElementById('stat-last-student').textContent = (d.last_checkin.student_id ?? '—') + ' · ' + formatRelative(d.last_checkin.timestamp);
    }
  } catch (e) {
    setError('Stats error: ' + e.message);
  }
}

// ── Attendance ──
async function loadAttendance(page) {
  if (page) attendancePage = page;
  const date     = document.getElementById('filter-date').value;
  const deviceId = document.getElementById('filter-device').value;
  const params   = new URLSearchParams({ date, page: attendancePage, per_page: PER_PAGE });
  if (deviceId) params.set('device_id', deviceId);

  try {
    const res = await fetch('api/attendance.php?' + params);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const d = await res.json();
    if (d.error) throw new Error(d.error);

    const rows = d.data ?? [];
    const tbody = document.getElementById('attendance-body');

    // Detect new rows (IDs not seen on last render)
    const newIds = new Set(rows.map(r => r.id));
    const freshIds = (attendancePage === 1 && knownIds.size > 0) ? new Set([...newIds].filter(id => !knownIds.has(id))) : new Set();
    knownIds = newIds;

    // Track all active devices globally to prevent dropdown options from shrinking
    rows.forEach(r => {
      if (r.device_id) allDevices.add(r.device_id);
    });

    // Populate device filter from the global Set
    const deviceSel = document.getElementById('filter-device');
    const currentVal = deviceSel.value;
    
    deviceSel.innerHTML = '<option value="">All Devices</option>';
    [...allDevices].sort().forEach(dv => {
      const opt = document.createElement('option');
      opt.value = dv; opt.textContent = dv;
      if (dv === currentVal) opt.selected = true;
      deviceSel.appendChild(opt);
    });

    // Render rows
    if (rows.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5"><div class="empty-state"><p>No check-ins found for this date.</p></div></td></tr>';
    } else {
      tbody.innerHTML = rows.map(row => `
        <tr class="${freshIds.has(row.id) ? 'row-new' : ''}">
          <td><span class="cell-id">${escapeHtml(row.student_id) || '—'}</span></td>
          <td>${row.name ? escapeHtml(row.name) : '<span style="color:#64748b">—</span>'}</td>
          <td>
            <span class="cell-time-main">${escapeHtml(formatTime(row.timestamp))}</span>
            <span class="cell-time-rel">${escapeHtml(formatRelative(row.timestamp))}</span>
          </td>
          <td>${scoreBadge(row.similarity_score)}</td>
          <td><span class="cell-device">${escapeHtml(row.device_id) || '—'}</span></td>
        </tr>
      `).join('');
    }

    // Badge on Attendance tab
    document.getElementById('badge-attendance').textContent = d.total > 0 ? d.total : '';

    // Pagination (Sliding Window with Prev/Next buttons)
    const totalPages = Math.ceil((d.total ?? 0) / PER_PAGE);
    const pagination = document.getElementById('attendance-pagination');
    if (totalPages > 1) {
      pagination.style.display = 'flex';
      document.getElementById('attendance-page-info').textContent =
        `Showing ${(attendancePage - 1) * PER_PAGE + 1}–${Math.min(attendancePage * PER_PAGE, d.total)} of ${d.total}`;
      const btns = document.getElementById('attendance-page-btns');
      btns.innerHTML = '';

      // Prev Button
      const prevBtn = document.createElement('button');
      prevBtn.className = 'page-btn';
      prevBtn.textContent = '‹';
      prevBtn.disabled = attendancePage === 1;
      prevBtn.onclick = () => loadAttendance(attendancePage - 1);
      btns.appendChild(prevBtn);

      // Sliding Window of 5 pages
      let startPage = Math.max(1, attendancePage - 2);
      let endPage = Math.min(totalPages, startPage + 4);
      if (endPage - startPage < 4) {
        startPage = Math.max(1, endPage - 4);
      }

      for (let p = startPage; p <= endPage; p++) {
        const btn = document.createElement('button');
        btn.className = 'page-btn' + (p === attendancePage ? ' active' : '');
        btn.textContent = p;
        btn.onclick = () => loadAttendance(p);
        btns.appendChild(btn);
      }

      // Next Button
      const nextBtn = document.createElement('button');
      nextBtn.className = 'page-btn';
      nextBtn.textContent = '›';
      nextBtn.disabled = attendancePage === totalPages;
      nextBtn.onclick = () => loadAttendance(attendancePage + 1);
      btns.appendChild(nextBtn);
    } else {
      pagination.style.display = 'none';
    }
  } catch (e) {
    setError('Attendance error: ' + e.message);
  }
}

// ── Students ──
async function loadStudents() {
  try {
    const res = await fetch('api/students.php');
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const d = await res.json();
    if (d.error) throw new Error(d.error);

    const rows = d.data ?? [];
    const tbody = document.getElementById('students-body');
    if (rows.length === 0) {
      tbody.innerHTML = '<tr><td colspan="4"><div class="empty-state"><p>No students registered yet.</p></div></td></tr>';
    } else {
      tbody.innerHTML = rows.map(row => `
        <tr>
          <td><span class="cell-id">${escapeHtml(row.student_id) || '—'}</span></td>
          <td>${row.name ? escapeHtml(row.name) : '<span style="color:#64748b">—</span>'}</td>
          <td>${escapeHtml(formatDateTime(row.created_at))}</td>
          <td>${statusBadge(row.queue_status)}</td>
        </tr>
      `).join('');
    }
  } catch (e) {
    setError('Students error: ' + e.message);
  }
}

// ── Queue ──
async function loadQueue() {
  const status = document.getElementById('filter-queue-status').value;
  const params = new URLSearchParams();
  if (status) params.set('status', status);

  try {
    const res = await fetch('api/queue.php?' + params);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const d = await res.json();
    if (d.error) throw new Error(d.error);

    const rows = d.data ?? [];
    const tbody = document.getElementById('queue-body');
    if (rows.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6"><div class="empty-state"><p>No queue items found.</p></div></td></tr>';
    } else {
      // Group photos with the same student ID
      const groups = {};
      rows.forEach(row => {
        const sid = row.student_id;
        if (!groups[sid]) {
          groups[sid] = {
            student_id: sid,
            items: [],
            statuses: new Set(),
            created_ats: [],
            processed_ats: [],
            errors: []
          };
        }
        groups[sid].items.push(row.image_path);
        if (row.status) groups[sid].statuses.add(row.status);
        if (row.created_at) groups[sid].created_ats.push(new Date(row.created_at));
        if (row.processed_at) groups[sid].processed_ats.push(new Date(row.processed_at));
        if (row.error_message) groups[sid].errors.push(row.error_message);
      });

      tbody.innerHTML = Object.values(groups).map(g => {
        const studentId = g.student_id;
        const totalPhotos = g.items.length;

        // Aggregate status: pending > failed > completed
        let groupStatus = 'completed';
        if (g.statuses.has('pending')) {
          groupStatus = 'pending';
        } else if (g.statuses.has('failed')) {
          groupStatus = 'failed';
        }

        // Aggregate timestamps
        const maxCreated = g.created_ats.length ? new Date(Math.max(...g.created_ats)).toISOString() : null;
        const maxProcessed = g.processed_ats.length ? new Date(Math.max(...g.processed_ats)).toISOString() : null;

        // Aggregate error messages
        const uniqueErrors = Array.from(new Set(g.errors.filter(Boolean)));
        const errorDisplay = uniqueErrors.length ? uniqueErrors.join('; ') : '';

        // Dropdown HTML for photos
        const dropdownHtml = `
          <select class="filter-select" style="max-width:240px; margin:0;" onchange="if(this.value) window.open(this.value, '_blank'); this.value='';">
            <option value="">View Photos (${totalPhotos})</option>
            ${g.items.map((url, idx) => {
              const filename = url.split('/').pop();
              return `<option value="${escapeHtml(url)}">Photo ${idx + 1} (${escapeHtml(filename)})</option>`;
            }).join('')}
          </select>
        `;

        return `
          <tr>
            <td><span class="cell-id">${escapeHtml(studentId) || '—'}</span></td>
            <td>${dropdownHtml}</td>
            <td>${statusBadge(groupStatus)}</td>
            <td>${escapeHtml(formatDateTime(maxCreated))}</td>
            <td>${maxProcessed ? escapeHtml(formatDateTime(maxProcessed)) : '<span style="color:#64748b">—</span>'}</td>
            <td>${errorDisplay ? `<span class="cell-error">${escapeHtml(errorDisplay)}</span>` : '<span style="color:#64748b">—</span>'}</td>
          </tr>
        `;
      }).join('');
    }
  } catch (e) {
    setError('Queue error: ' + e.message);
  }
}

async function triggerForceTraining() {
  if (!confirm('This will process all pending registrations in the queue immediately. Proceed?')) {
    return;
  }
  
  const btn = document.querySelector('[onclick="triggerForceTraining()"]');
  const oldText = btn.textContent;
  btn.textContent = 'Processing...';
  btn.disabled = true;
  
  try {
    const res = await fetch('api/train.php', { method: 'POST' });
    const d = await res.json();
    if (!res.ok) throw new Error(d.detail || d.error || 'Server error');
    
    alert('Training completed successfully! Processed students: ' + (d.processed_students?.join(', ') || 'None'));
    loadQueue();
    loadStats();
  } catch (e) {
    alert('Training failed: ' + e.message);
  } finally {
    btn.textContent = oldText;
    btn.disabled = false;
  }
}

// ── Polling ──
function startPolling() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(() => {
    loadStats();
    if (currentTab === 'attendance') loadAttendance();
  }, 5000);
}

// ── Init ──
document.getElementById('filter-date').addEventListener('change', () => {
  // Clear known IDs to avoid incorrect highlight flashes on manual date change
  knownIds.clear();
  loadAttendance(1);
});
document.getElementById('filter-device').addEventListener('change', () => {
  knownIds.clear();
  loadAttendance(1);
});

loadStats();
loadAttendance(1);
startPolling();
</script>

</body>
</html>
