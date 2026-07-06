/**
 * dashboard-queue.js
 * Queue UI interactions: expand/collapse rows, tab switching, checklist rendering.
 * Depends on: dashboard-utils.js
 */

// ── Queue Row Expand/Collapse ──
let expandedQueueRows = new Set();

function toggleQueueDetails(safeId) {
  const row       = document.getElementById('details-row-' + safeId);
  const container = document.getElementById('details-container-' + safeId);
  const arrow     = document.getElementById('arrow-' + safeId);
  if (!row || !container || !arrow) return;

  if (expandedQueueRows.has(safeId)) {
    expandedQueueRows.delete(safeId);
    container.classList.remove('expanded');
    arrow.classList.remove('expanded');
    setTimeout(() => {
      if (!expandedQueueRows.has(safeId)) row.style.display = 'none';
    }, 300);
  } else {
    expandedQueueRows.add(safeId);
    row.style.display = 'table-row';
    row.offsetHeight; // trigger reflow for CSS transition
    container.classList.add('expanded');
    arrow.classList.add('expanded');
  }
}

// ── Queue Detail Tabs ──
function switchQueueTab(event, safeId, tabName) {
  event.stopPropagation();
  const container = document.getElementById('details-container-' + safeId);
  if (!container) return;

  container.querySelectorAll('.details-tab').forEach(btn => btn.classList.remove('active'));
  event.currentTarget.classList.add('active');

  container.querySelectorAll('.details-tab-content').forEach(c => c.classList.remove('active'));
  const target = document.getElementById(`tab-content-${safeId}-${tabName}`);
  if (target) target.classList.add('active');
}

// ── Admin Actions ──
async function triggerForceTraining() {
  let adminKey = getAdminKey();
  if (!adminKey) {
    adminKey = prompt('Please enter the Admin API Key to trigger training:');
    if (!adminKey) return;
    saveAdminKey(adminKey);
    document.getElementById('admin-key-input').value = adminKey;
  }

  if (!confirm('This will process all pending registrations in the queue immediately. Proceed?')) return;

  const btn     = document.querySelector('[onclick="triggerForceTraining()"]');
  const oldText = btn.textContent;
  btn.textContent = 'Processing...';
  btn.disabled    = true;

  try {
    const res = await fetch('api/train.php', {
      method: 'POST',
      headers: { 'X-Admin-Key': adminKey }
    });
    const d = await res.json();
    if (res.status === 401) {
      localStorage.removeItem('admin_key');
      document.getElementById('admin-key-input').value = '';
      throw new Error('Unauthorized: Invalid Admin Key');
    }
    if (!res.ok) throw new Error(d.detail || d.error || 'Server error');
    alert('Training completed successfully! Processed students: ' + (d.processed_students?.join(', ') || 'None'));
    loadQueue();
    loadStats();
  } catch (e) {
    alert('Training failed: ' + e.message);
  } finally {
    btn.textContent = oldText;
    btn.disabled    = false;
  }
}

async function deleteStudent(studentId) {
  let adminKey = getAdminKey();
  if (!adminKey) {
    adminKey = prompt('Please enter the Admin API Key to delete this student:');
    if (!adminKey) return;
    saveAdminKey(adminKey);
    document.getElementById('admin-key-input').value = adminKey;
  }

  if (!confirm(`Are you sure you want to permanently delete student ID: ${studentId}?\nThis will delete their photos and face recognition data but keep their check-in log history.`)) return;

  try {
    const res = await fetch('api/delete_student.php', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Admin-Key': adminKey },
      body: JSON.stringify({ student_id: studentId })
    });
    const d = await res.json();
    if (res.status === 401) {
      localStorage.removeItem('admin_key');
      document.getElementById('admin-key-input').value = '';
      throw new Error('Unauthorized: Invalid Admin Key');
    }
    if (!res.ok) throw new Error(d.error || d.detail || 'Delete failed');
    alert(`Student ${studentId} has been successfully deleted.`);
    loadStudents();
    loadStats();
    loadQueue();
  } catch (e) {
    alert('Error: ' + e.message);
  }
}

// ── Checklist Rendering ──
function parseValidationChecks(item) {
  const checks = [
    { key: 'face_detected',   label: 'Face Detection' },
    { key: 'single_face',     label: 'Single Face Check' },
    { key: 'duplicate_check', label: 'Duplicate Check' },
    { key: 'quota_check',     label: 'Quota Check' }
  ];

  if (item.status === 'completed') {
    return Object.fromEntries(checks.map(c => [c.key, { status: 'passed' }]));
  }
  if (item.status === 'pending') {
    return Object.fromEntries(checks.map(c => [c.key, { status: 'pending' }]));
  }

  const lowerErr = (item.error_message || '').toLowerCase();
  let failedStep = -1;
  if      (lowerErr.includes('please look at the camera') || lowerErr.includes('face not found') || lowerErr.includes('invalid image') || lowerErr.includes('no face')) failedStep = 1;
  else if (lowerErr.includes('one person at a time') || lowerErr.includes('multiple faces')) failedStep = 2;
  else if (lowerErr.includes('already registered'))  failedStep = 3;
  else if (lowerErr.includes('quota'))               failedStep = 4;

  return Object.fromEntries(checks.map((c, idx) => {
    const step = idx + 1;
    if (failedStep === -1)       return [c.key, { status: 'skipped' }];
    if (step < failedStep)       return [c.key, { status: 'passed' }];
    if (step === failedStep)     return [c.key, { status: 'failed', message: item.error_message }];
    return [c.key, { status: 'skipped' }];
  }));
}

function renderChecklistsHtml(items) {
  const LABELS = {
    face_detected: 'Face Detection', single_face: 'Single Face Check',
    duplicate_check: 'Duplicate Check', quota_check: 'Quota Check'
  };
  const QUALITY_ERRORS = [
    'please look at the camera', 'face not found', 'no face', 'invalid image',
    'one person at a time', 'multiple faces', 'already registered', 'quota'
  ];

  return items.map(item => {
    const filename  = item.image_path.split('/').pop();
    const checks    = parseValidationChecks(item);
    const statusCls = item.status || 'none';
    const statusTxt = item.status ? item.status.toUpperCase() : 'UNKNOWN';

    const checkItemsHtml = Object.entries(checks).map(([key, check]) => {
      const icons  = { passed: '✓', failed: '✗', skipped: '○', none: '○', pending: '—' };
      const clsMap = { passed: 'check-passed', failed: 'check-failed', skipped: 'check-skipped', none: 'check-skipped', pending: 'check-pending' };
      const icon   = icons[check.status] || '—';
      const cls    = clsMap[check.status] || 'check-pending';
      const suffix = check.status === 'failed' && check.message
        ? `: <span class="check-error-msg">${escapeHtml(check.message)}</span>`
        : (check.status === 'skipped' || check.status === 'pending') ? ` (${check.status})` : '';
      return `
        <div class="checklist-item ${cls}">
          <span class="checklist-icon">${icon}</span>
          <span class="checklist-label">${escapeHtml(LABELS[key] || key)}</span>${suffix}
        </div>`;
    }).join('');

    const lowerErr = (item.error_message || '').toLowerCase();
    const isQuality = QUALITY_ERRORS.some(e => lowerErr.includes(e));
    const generalErrorHtml = (item.error_message && !isQuality)
      ? `<div class="general-checklist-error"><strong>System Error:</strong> ${escapeHtml(item.error_message)}</div>`
      : '';

    return `
      <div class="photo-checklist-card">
        <div class="photo-checklist-header">
          <span class="photo-filename">${escapeHtml(filename)}</span>
          <span class="status-badge status-badge--small status-badge--${statusCls}">${statusTxt}</span>
        </div>
        ${generalErrorHtml}
        <div class="photo-checklist-body">${checkItemsHtml}</div>
      </div>`;
  }).join('');
}
