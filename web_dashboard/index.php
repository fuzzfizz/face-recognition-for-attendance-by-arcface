<?php
// Show setup page if config.php is missing
if (!file_exists(__DIR__ . '/config.php')) {
    echo '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Setup Required</title>
    <style>body{background:#0f1117;color:#e2e8f0;font-family:system-ui;display:flex;align-items:center;justify-content:min-height:100vh;margin:0}
    .box{background:#1a1d2e;border:1px solid #2d3148;border-radius:12px;padding:32px;max-width:480px}
    h1{color:#a78bfa;margin-bottom:12px}pre{background:#0f1117;padding:12px;border-radius:6px;font-size:13px;margin:8px 0}
    </style></head><body><div class="box">
    <h1>Setup Required</h1>
    <p>Copy <code>config.example.php</code> to <code>config.php</code> and fill in your database credentials:</p>
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
  <div style="display:flex;align-items:center;gap:12px">
    <div class="admin-input-group" style="display:flex;align-items:center;gap:6px;background:var(--bg-inset);padding:4px 10px;border-radius:6px;border:1px solid var(--border)">
      <span style="font-size:11px;color:var(--accent);font-weight:bold">Admin Key:</span>
      <input type="password" id="admin-key-input" placeholder="••••••••"
        style="background:none;border:none;color:var(--text-primary);font-size:12px;width:120px;outline:none"
        onchange="saveAdminKey(this.value)">
    </div>
    <button class="theme-toggle" id="theme-toggle-btn" onclick="toggleTheme()" title="Toggle light/dark theme">
      <span id="theme-icon">🌙</span>
      <span id="theme-label" style="font-size:11px;font-weight:600">Light</span>
    </button>
    <div class="live-badge">
      <div class="live-dot online" id="live-dot"></div>
      <span id="live-label">Live · refreshes every 5s</span>
    </div>
  </div>
</header>

<!-- Error Banner -->
<div class="error-banner" id="error-banner">
  <span id="error-msg">Could not reach database. Retrying...</span>
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

<!-- Tab: Attendance -->
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

<!-- Tab: Students -->
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

<!-- Tab: Queue -->
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
    <button class="btn-refresh" style="background:var(--accent);color:var(--bg-base)" onclick="triggerForceTraining()">⚙️ Force Training Now</button>
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

<!-- Scripts (order matters: utils → queue → api → init) -->
<script src="assets/dashboard-utils.js"></script>
<script src="assets/dashboard-queue.js"></script>
<script src="assets/dashboard-api.js"></script>
<script>
// ── Init ──
document.getElementById('filter-date').addEventListener('change', () => {
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

// Restore admin key and theme from localStorage
const _savedKey = getAdminKey();
if (_savedKey) document.getElementById('admin-key-input').value = _savedKey;
applyTheme(localStorage.getItem('theme') || 'dark');
</script>

</body>
</html>
