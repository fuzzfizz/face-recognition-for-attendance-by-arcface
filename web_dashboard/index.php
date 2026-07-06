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
  <style>
  /* ── Expandable Details ── */
  .details-container {
      max-height: 0;
      overflow: hidden;
      transition: max-height 0.3s ease-out;
      background: #13151f44;
  }
  .details-container.expanded {
      max-height: 2000px;
  }
  .details-inner {
      padding: 16px 24px;
      border-bottom: 1px solid #2d3148;
  }
  .details-arrow {
      display: inline-block;
      margin-right: 8px;
      font-size: 10px;
      color: #64748b;
      transition: transform 0.2s ease;
  }
  .details-arrow.expanded {
      transform: rotate(90deg);
      color: #a78bfa;
  }

  /* Details Tabs */
  .details-tabs {
      display: flex;
      gap: 8px;
      margin-bottom: 16px;
      border-bottom: 1px solid #1e2235;
      padding-bottom: 8px;
  }
  .details-tab {
      background: none;
      border: none;
      color: #64748b;
      font-size: 12px;
      font-weight: 600;
      padding: 6px 12px;
      cursor: pointer;
      border-radius: 4px;
      transition: all 0.15s;
  }
  .details-tab:hover {
      color: #cbd5e1;
      background: #1e2235;
  }
  .details-tab.active {
      color: #a78bfa;
      background: #a78bfa11;
  }

  /* Tab contents */
  .details-tab-content {
      display: none;
  }
  .details-tab-content.active {
      display: block;
  }

  /* Checklist Styling */
  .photo-checklist-card {
      background: #1a1d2e;
      border: 1px solid #2d3148;
      border-radius: 8px;
      margin-bottom: 12px;
      overflow: hidden;
  }
  .photo-checklist-header {
      background: #13151f99;
      padding: 8px 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid #2d3148;
  }
  .photo-filename {
      font-family: monospace;
      font-size: 12px;
      color: #e2e8f0;
  }
  .status-badge--small {
      padding: 1px 6px;
      font-size: 10px;
      border-radius: 12px;
  }
  .photo-checklist-body {
      padding: 12px 16px;
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 8px 16px;
  }
  @media (max-width: 768px) {
      .photo-checklist-body {
          grid-template-columns: 1fr;
      }
  }
  .checklist-item {
      display: flex;
      align-items: center;
      font-size: 12px;
  }
  .checklist-icon {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 16px;
      height: 16px;
      border-radius: 50%;
      margin-right: 8px;
      font-size: 10px;
      font-weight: bold;
  }
  .check-passed { color: #cbd5e1; }
  .check-passed .checklist-icon {
      background: #22c55e22;
      color: #22c55e;
  }
  .check-failed { color: #f87171; }
  .check-failed .checklist-icon {
      background: #ef444422;
      color: #ef4444;
  }
  .check-skipped { color: #64748b; }
  .check-skipped .checklist-icon {
      background: #1e2235;
      color: #64748b;
      border: 1px solid #2d3148;
  }
  .check-pending { color: #f59e0b; }
  .check-pending .checklist-icon {
      background: #f59e0b22;
      color: #f59e0b;
  }
  .check-error-msg {
      color: #f87171;
      margin-left: 4px;
      font-style: italic;
  }
  .general-checklist-error {
      background: #ef444415;
      border-bottom: 1px solid #ef444433;
      padding: 8px 16px;
      color: #f87171;
      font-size: 12px;
  }

  /* Raw data */
  .raw-data-json {
      background: #0f1117;
      border: 1px solid #2d3148;
      border-radius: 6px;
      padding: 12px;
      max-height: 300px;
      overflow-y: auto;
      font-family: monospace;
      font-size: 12px;
      color: #a78bfa;
  }
  </style>
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
        <tr><th>Student ID</th><th>Name</th><th>Registered At</th><th>Status</th><th>Actions</th></tr>
      </thead>
      <tbody id="students-body">
        <tr><td colspan="5"><div class="empty-state"><p>Click Students tab to load.</p></div></td></tr>
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
function getSafeDOMId(str) {
  return (str || '').replace(/[^a-zA-Z0-9_-]/g, '_');
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
      tbody.innerHTML = '<tr><td colspan="5"><div class="empty-state"><p>No students registered yet.</p></div></td></tr>';
    } else {
      tbody.innerHTML = rows.map(row => `
        <tr>
          <td><span class="cell-id">${escapeHtml(row.student_id) || '—'}</span></td>
          <td>${row.name ? escapeHtml(row.name) : '<span style="color:#64748b">—</span>'}</td>
          <td>${escapeHtml(formatDateTime(row.created_at))}</td>
          <td>${statusBadge(row.queue_status)}</td>
          <td>
            <button class="btn-delete" style="background:#ef4444;color:white;padding:4px 8px;border:none;border-radius:4px;cursor:pointer;font-size:11px;" data-student-id="${escapeHtml(row.student_id)}" onclick="deleteStudent(this.dataset.studentId)">Delete</button>
          </td>
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
            errors: [],
            raw_items: []
          };
        }
        groups[sid].items.push(row.image_path);
        groups[sid].raw_items.push(row);
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
          <select class="filter-select" style="max-width:240px; margin:0;" onchange="if(this.value) window.open(this.value, '_blank'); this.value='';" onclick="event.stopPropagation()">
            <option value="">View Photos (${totalPhotos})</option>
            ${g.items.map((url, idx) => {
              const filename = url.split('/').pop();
              return `<option value="${escapeHtml(url)}">Photo ${idx + 1} (${escapeHtml(filename)})</option>`;
            }).join('')}
          </select>
        `;

        const isExpanded = expandedQueueRows.has(getSafeDOMId(studentId));

        return `
          <tr class="queue-row-header" onclick="toggleQueueDetails('${getSafeDOMId(studentId)}')" style="cursor:pointer">
            <td>
              <span class="details-arrow ${isExpanded ? 'expanded' : ''}" id="arrow-${getSafeDOMId(studentId)}">▶</span>
              <span class="cell-id">${escapeHtml(studentId) || '—'}</span>
            </td>
            <td>${dropdownHtml}</td>
            <td>${statusBadge(groupStatus)}</td>
            <td>${escapeHtml(formatDateTime(maxCreated))}</td>
            <td>${maxProcessed ? escapeHtml(formatDateTime(maxProcessed)) : '<span style="color:#64748b">—</span>'}</td>
            <td>${errorDisplay ? `<span class="cell-error">${escapeHtml(errorDisplay)}</span>` : '<span style="color:#64748b">—</span>'}</td>
          </tr>
          <tr id="details-row-${getSafeDOMId(studentId)}" class="queue-details-row" style="${isExpanded ? 'display: table-row;' : 'display: none;'}">
            <td colspan="6" style="padding:0; border:none;">
              <div id="details-container-${getSafeDOMId(studentId)}" class="details-container ${isExpanded ? 'expanded' : ''}">
                <div class="details-inner">
                  
                  <!-- Tabs Header -->
                  <div class="details-tabs">
                    <button class="details-tab active" onclick="switchQueueTab(event, '${getSafeDOMId(studentId)}', 'checklist')">
                      ⚠️ Failure Checklist
                    </button>
                    <button class="details-tab" onclick="switchQueueTab(event, '${getSafeDOMId(studentId)}', 'raw')">
                      📊 Raw Data
                    </button>
                  </div>
                  
                  <!-- Tab: Failure Checklist -->
                  <div id="tab-content-${getSafeDOMId(studentId)}-checklist" class="details-tab-content active">
                    ${renderChecklistsHtml(g.raw_items)}
                  </div>
                  
                  <!-- Tab: Raw Data -->
                  <div id="tab-content-${getSafeDOMId(studentId)}-raw" class="details-tab-content">
                    <pre class="raw-data-json"><code>${escapeHtml(JSON.stringify(g.raw_items, null, 2))}</code></pre>
                  </div>
                  
                </div>
              </div>
            </td>
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

async function deleteStudent(studentId) {
  if (!confirm(`Are you sure you want to permanently delete student ID: ${studentId}?\nThis will delete their photos and face recognition data but keep their check-in log history.`)) {
    return;
  }
  
  try {
    const res = await fetch('api/delete_student.php', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ student_id: studentId })
    });
    const d = await res.json();
    if (!res.ok) throw new Error(d.error || d.detail || 'Delete failed');
    
    alert(`Student ${studentId} has been successfully deleted.`);
    loadStudents();
    loadStats();
    loadQueue();
  } catch (e) {
    alert('Error: ' + e.message);
  }
}

// Track expanded queue rows
let expandedQueueRows = new Set();

function toggleQueueDetails(safeId) {
  const row = document.getElementById('details-row-' + safeId);
  const container = document.getElementById('details-container-' + safeId);
  const arrow = document.getElementById('arrow-' + safeId);
  if (!row || !container || !arrow) return;

  if (expandedQueueRows.has(safeId)) {
    // Collapse
    expandedQueueRows.delete(safeId);
    container.classList.remove('expanded');
    arrow.classList.remove('expanded');
    setTimeout(() => {
      if (!expandedQueueRows.has(safeId)) {
        row.style.display = 'none';
      }
    }, 300);
  } else {
    // Expand
    expandedQueueRows.add(safeId);
    row.style.display = 'table-row';
    row.offsetHeight; // trigger reflow
    container.classList.add('expanded');
    arrow.classList.add('expanded');
  }
}

function switchQueueTab(event, safeId, tabName) {
  event.stopPropagation(); // Prevent toggling the row
  
  const container = document.getElementById('details-container-' + safeId);
  if (!container) return;
  
  // Update active tab button
  container.querySelectorAll('.details-tab').forEach(btn => {
    btn.classList.remove('active');
  });
  event.currentTarget.classList.add('active');
  
  // Update active content
  container.querySelectorAll('.details-tab-content').forEach(content => {
    content.classList.remove('active');
  });
  
  const targetContent = document.getElementById(`tab-content-${safeId}-${tabName}`);
  if (targetContent) {
    targetContent.classList.add('active');
  }
}

function parseValidationChecks(item) {
  const status = item.status;
  const errMsg = item.error_message || '';
  
  const checks = [
    { key: 'face_detected', label: 'Face Detection' },
    { key: 'single_face', label: 'Single Face Check' },
    { key: 'duplicate_check', label: 'Duplicate Check' },
    { key: 'quota_check', label: 'Quota Check' }
  ];

  let results = {};
  if (status === 'completed') {
    checks.forEach(c => results[c.key] = { status: 'passed' });
  } else if (status === 'pending') {
    checks.forEach(c => results[c.key] = { status: 'pending' });
  } else {
    let failedStep = -1;
    let failReason = errMsg;
    
    const lowerErr = errMsg.toLowerCase();
    if (lowerErr.includes('please look at the camera') || lowerErr.includes('face not found') || lowerErr.includes('invalid image') || lowerErr.includes('no face')) {
      failedStep = 1;
    } else if (lowerErr.includes('one person at a time') || lowerErr.includes('multiple faces')) {
      failedStep = 2;
    } else if (lowerErr.includes('already registered')) {
      failedStep = 3;
    } else if (lowerErr.includes('quota')) {
      failedStep = 4;
    }
    
    checks.forEach((c, idx) => {
      const stepNum = idx + 1;
      if (failedStep === -1) {
        results[c.key] = { status: 'skipped' };
      } else if (stepNum < failedStep) {
        results[c.key] = { status: 'passed' };
      } else if (stepNum === failedStep) {
        results[c.key] = { status: 'failed', message: failReason };
      } else {
        results[c.key] = { status: 'skipped' };
      }
    });
  }

  return results;
}

function renderChecklistsHtml(items) {
  return items.map((item, idx) => {
    const filename = item.image_path.split('/').pop();
    const checks = parseValidationChecks(item);
    
    const checkItemsHtml = Object.entries(checks).map(([key, check]) => {
      let icon = '';
      let cls = '';
      let suffix = '';
      
      if (check.status === 'passed') {
        icon = '✓';
        cls = 'check-passed';
      } else if (check.status === 'failed') {
        icon = '✗';
        cls = 'check-failed';
        if (check.message) {
          suffix = `: <span class="check-error-msg">${escapeHtml(check.message)}</span>`;
        }
      } else if (check.status === 'skipped') {
        icon = '○';
        cls = 'check-skipped';
        suffix = ' (skipped)';
      } else if (check.status === 'none') {
        icon = '○';
        cls = 'check-skipped';
        suffix = '';
      } else { // pending
        icon = '—';
        cls = 'check-pending';
        suffix = ' (pending)';
      }
      
      const labels = {
        face_detected: 'Face Detection',
        single_face: 'Single Face Check',
        duplicate_check: 'Duplicate Check',
        quota_check: 'Quota Check'
      };
      const label = labels[key] || key;
      
      return `
        <div class="checklist-item ${cls}">
          <span class="checklist-icon">${icon}</span>
          <span class="checklist-label">${escapeHtml(label)}</span>${suffix}
        </div>
      `;
    }).join('');

    let statusCls = item.status || 'none';
    let statusText = item.status ? item.status.toUpperCase() : 'UNKNOWN';
    
    let generalErrorHtml = '';
    const hasError = item.error_message && item.error_message.trim().length > 0;
    if (hasError) {
      const errMsg = item.error_message;
      const lowerErr = errMsg.toLowerCase();
      const isQualityCheckError = lowerErr.includes('please look at the camera') || 
                                  lowerErr.includes('face not found') ||
                                  lowerErr.includes('no face') ||
                                  lowerErr.includes('invalid image') ||
                                  lowerErr.includes('one person at a time') ||
                                  lowerErr.includes('multiple faces') ||
                                  lowerErr.includes('already registered') ||
                                  lowerErr.includes('quota');
      if (!isQualityCheckError) {
        generalErrorHtml = `
          <div class="general-checklist-error">
            <strong>System Error:</strong> ${escapeHtml(errMsg)}
          </div>
        `;
      }
    }

    return `
      <div class="photo-checklist-card">
        <div class="photo-checklist-header">
          <span class="photo-filename">${escapeHtml(filename)}</span>
          <span class="status-badge status-badge--small status-badge--${statusCls}">${statusText}</span>
        </div>
        ${generalErrorHtml}
        <div class="photo-checklist-body">
          ${checkItemsHtml}
        </div>
      </div>
    `;
  }).join('');
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
