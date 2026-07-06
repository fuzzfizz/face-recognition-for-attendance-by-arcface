/**
 * dashboard-api.js
 * Data fetching layer: stats, attendance, students, queue.
 * Depends on: dashboard-utils.js
 */

// ── State ──
let currentTab     = 'attendance';
let attendancePage = 1;
let pollTimer      = null;
const PER_PAGE     = 20;
let knownIds       = new Set();
let allDevices     = new Set();

// ── Tab Switching ──
function switchTab(name) {
  currentTab = name;
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  document.getElementById('content-' + name).classList.add('active');
  if (name === 'attendance') loadAttendance(1);
  if (name === 'students')  loadStudents();
  if (name === 'queue')     loadQueue();
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

    const qPending = d.pending_queue ?? 0;
    document.getElementById('badge-queue').textContent = qPending > 0 ? qPending : '';

    if (d.last_checkin) {
      document.getElementById('stat-last-time').textContent    = formatTime(d.last_checkin.timestamp);
      document.getElementById('stat-last-student').textContent =
        (d.last_checkin.student_id ?? '—') + ' · ' + formatRelative(d.last_checkin.timestamp);
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

    const rows  = d.data ?? [];
    const tbody = document.getElementById('attendance-body');

    // Highlight new rows
    const newIds   = new Set(rows.map(r => r.id));
    const freshIds = (attendancePage === 1 && knownIds.size > 0)
      ? new Set([...newIds].filter(id => !knownIds.has(id)))
      : new Set();
    knownIds = newIds;

    // Build device filter from global Set
    rows.forEach(r => { if (r.device_id) allDevices.add(r.device_id); });
    const deviceSel  = document.getElementById('filter-device');
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
          <td>${row.name ? escapeHtml(row.name) : '<span style="color:var(--text-dim)">—</span>'}</td>
          <td>
            <span class="cell-time-main">${escapeHtml(formatTime(row.timestamp))}</span>
            <span class="cell-time-rel">${escapeHtml(formatRelative(row.timestamp))}</span>
          </td>
          <td>${scoreBadge(row.similarity_score)}</td>
          <td><span class="cell-device">${escapeHtml(row.device_id) || '—'}</span></td>
        </tr>
      `).join('');
    }

    document.getElementById('badge-attendance').textContent = d.total > 0 ? d.total : '';
    renderPagination(d.total ?? 0);
  } catch (e) {
    setError('Attendance error: ' + e.message);
  }
}

function renderPagination(total) {
  const totalPages = Math.ceil(total / PER_PAGE);
  const pagination = document.getElementById('attendance-pagination');
  if (totalPages <= 1) { pagination.style.display = 'none'; return; }

  pagination.style.display = 'flex';
  document.getElementById('attendance-page-info').textContent =
    `Showing ${(attendancePage - 1) * PER_PAGE + 1}–${Math.min(attendancePage * PER_PAGE, total)} of ${total}`;

  const btns = document.getElementById('attendance-page-btns');
  btns.innerHTML = '';

  const addBtn = (label, page, disabled, active) => {
    const btn = document.createElement('button');
    btn.className = 'page-btn' + (active ? ' active' : '');
    btn.textContent = label;
    btn.disabled = disabled;
    if (!disabled) btn.onclick = () => loadAttendance(page);
    btns.appendChild(btn);
  };

  addBtn('‹', attendancePage - 1, attendancePage === 1, false);

  let startPage = Math.max(1, attendancePage - 2);
  let endPage   = Math.min(totalPages, startPage + 4);
  if (endPage - startPage < 4) startPage = Math.max(1, endPage - 4);

  for (let p = startPage; p <= endPage; p++) {
    addBtn(p, p, false, p === attendancePage);
  }

  addBtn('›', attendancePage + 1, attendancePage === totalPages, false);
}

// ── Students ──
async function loadStudents() {
  try {
    const res = await fetch('api/students.php');
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const d = await res.json();
    if (d.error) throw new Error(d.error);

    const rows  = d.data ?? [];
    const tbody = document.getElementById('students-body');
    if (rows.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5"><div class="empty-state"><p>No students registered yet.</p></div></td></tr>';
    } else {
      tbody.innerHTML = rows.map(row => `
        <tr>
          <td><span class="cell-id">${escapeHtml(row.student_id) || '—'}</span></td>
          <td>${row.name ? escapeHtml(row.name) : '<span style="color:var(--text-dim)">—</span>'}</td>
          <td>${escapeHtml(formatDateTime(row.created_at))}</td>
          <td>${statusBadge(row.queue_status)}</td>
          <td>
            <button class="btn-delete"
              style="background:#ef4444;color:white;padding:4px 8px;border:none;border-radius:4px;cursor:pointer;font-size:11px;"
              data-student-id="${escapeHtml(row.student_id)}"
              onclick="deleteStudent(this.dataset.studentId)">Delete</button>
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

    const rows  = d.data ?? [];
    const tbody = document.getElementById('queue-body');
    if (rows.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6"><div class="empty-state"><p>No queue items found.</p></div></td></tr>';
      return;
    }

    // Group by student_id
    const groups = {};
    rows.forEach(row => {
      const sid = row.student_id;
      if (!groups[sid]) {
        groups[sid] = { student_id: sid, items: [], statuses: new Set(),
          created_ats: [], processed_ats: [], errors: [], raw_items: [] };
      }
      groups[sid].items.push(row.image_path);
      groups[sid].raw_items.push(row);
      if (row.status)       groups[sid].statuses.add(row.status);
      if (row.created_at)   groups[sid].created_ats.push(new Date(row.created_at));
      if (row.processed_at) groups[sid].processed_ats.push(new Date(row.processed_at));
      if (row.error_message) groups[sid].errors.push(row.error_message);
    });

    tbody.innerHTML = Object.values(groups).map(g => renderQueueGroup(g)).join('');
  } catch (e) {
    setError('Queue error: ' + e.message);
  }
}

function renderQueueGroup(g) {
  const sid        = g.student_id;
  const safeId     = getSafeDOMId(sid);
  const totalPhotos = g.items.length;

  let groupStatus = 'completed';
  if (g.statuses.has('pending'))     groupStatus = 'pending';
  else if (g.statuses.has('failed')) groupStatus = 'failed';

  const maxCreated   = g.created_ats.length   ? new Date(Math.max(...g.created_ats)).toISOString()   : null;
  const maxProcessed = g.processed_ats.length ? new Date(Math.max(...g.processed_ats)).toISOString() : null;
  const uniqueErrors = [...new Set(g.errors.filter(Boolean))];
  const errorDisplay = uniqueErrors.join('; ');
  const isExpanded   = expandedQueueRows.has(safeId);

  const dropdownHtml = `
    <select class="filter-select" style="max-width:240px;margin:0;"
      onchange="if(this.value) window.open(this.value,'_blank'); this.value='';"
      onclick="event.stopPropagation()">
      <option value="">View Photos (${totalPhotos})</option>
      ${g.items.map((url, idx) => {
        const fname = url.split('/').pop();
        return `<option value="${escapeHtml(url)}">Photo ${idx + 1} (${escapeHtml(fname)})</option>`;
      }).join('')}
    </select>`;

  return `
    <tr class="queue-row-header" onclick="toggleQueueDetails('${safeId}')" style="cursor:pointer">
      <td>
        <span class="details-arrow ${isExpanded ? 'expanded' : ''}" id="arrow-${safeId}">▶</span>
        <span class="cell-id">${escapeHtml(sid) || '—'}</span>
      </td>
      <td>${dropdownHtml}</td>
      <td>${statusBadge(groupStatus)}</td>
      <td>${escapeHtml(formatDateTime(maxCreated))}</td>
      <td>${maxProcessed ? escapeHtml(formatDateTime(maxProcessed)) : '<span style="color:var(--text-dim)">—</span>'}</td>
      <td>${errorDisplay ? `<span class="cell-error">${escapeHtml(errorDisplay)}</span>` : '<span style="color:var(--text-dim)">—</span>'}</td>
    </tr>
    <tr id="details-row-${safeId}" class="queue-details-row" style="${isExpanded ? 'display:table-row' : 'display:none'}">
      <td colspan="6" style="padding:0;border:none;">
        <div id="details-container-${safeId}" class="details-container ${isExpanded ? 'expanded' : ''}">
          <div class="details-inner">
            <div class="details-tabs">
              <button class="details-tab active" onclick="switchQueueTab(event,'${safeId}','checklist')">⚠️ Failure Checklist</button>
              <button class="details-tab" onclick="switchQueueTab(event,'${safeId}','raw')">📊 Raw Data</button>
            </div>
            <div id="tab-content-${safeId}-checklist" class="details-tab-content active">
              ${renderChecklistsHtml(g.raw_items)}
            </div>
            <div id="tab-content-${safeId}-raw" class="details-tab-content">
              <pre class="raw-data-json"><code>${escapeHtml(JSON.stringify(g.raw_items, null, 2))}</code></pre>
            </div>
          </div>
        </div>
      </td>
    </tr>`;
}

// ── Polling ──
function startPolling() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(() => {
    if (document.hidden) return;
    loadStats();
    if (currentTab === 'attendance') loadAttendance();
  }, 5000);
}

document.addEventListener('visibilitychange', () => {
  if (!document.hidden) {
    loadStats();
    if (currentTab === 'attendance') loadAttendance();
  }
});
