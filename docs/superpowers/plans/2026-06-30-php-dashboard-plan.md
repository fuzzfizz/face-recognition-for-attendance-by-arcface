# PHP Web Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone PHP web dashboard that reads from Supabase and displays attendance logs, student registrations, and the processing queue with auto-refresh — no login required.

**Architecture:** A single PHP project (`web_dashboard/`) with a thin `index.php` shell and three `api/*.php` endpoints that proxy Supabase REST API calls server-side. JavaScript in the browser polls the PHP endpoints every 5 seconds and updates the DOM. Supabase credentials live only in `config.php` (gitignored).

**Tech Stack:** PHP 8.x (no framework), vanilla JavaScript (no npm/build), pure CSS (no framework), Supabase REST API via PHP cURL.

## Global Constraints

- PHP 8.0 or higher — use `match`, `named arguments`, and `str_contains` freely
- No external PHP libraries or Composer — pure built-in PHP only
- No JavaScript frameworks — vanilla JS only (`fetch`, `setInterval`, DOM APIs)
- No CSS frameworks — pure CSS only
- All Supabase credentials go in `config.php` — never inline in other files
- `config.php` must be gitignored; `config.example.php` is the committed template
- Supabase table names: `check_in_logs`, `users`, `registration_queue` (exact, lowercase)
- Column names must match the schema exactly: `student_id`, `similarity_score`, `device_id`, `timestamp`, `status`, `error_message`, `image_path`, `created_at`, `processed_at`
- Dark theme: body `#0f1117`, cards `#1a1d2e`, borders `#2d3148`, accent `#a78bfa`
- All timestamps stored in UTC in Supabase — display in local browser timezone

---

### Task 1: Project Scaffold + Config

**Files:**
- Create: `web_dashboard/config.php`
- Create: `web_dashboard/config.example.php`
- Create: `web_dashboard/.gitignore`
- Create: `web_dashboard/README.md`

**Interfaces:**
- Produces: `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` constants consumed by all `api/*.php` files
- Produces: `supabase_get(string $table, array $params): array` helper function in `config.php` used by all three API endpoints

- [ ] **Step 1: Create `web_dashboard/config.example.php`**

```php
<?php
// Copy this file to config.php and fill in your Supabase credentials.
// NEVER commit config.php — it contains your service role key.
define('SUPABASE_URL', 'https://your-project.supabase.co');
define('SUPABASE_SERVICE_KEY', 'your-service-role-key-here');
```

- [ ] **Step 2: Create `web_dashboard/config.php`** (fill in real values, this is gitignored)

```php
<?php
define('SUPABASE_URL', 'https://your-project.supabase.co');
define('SUPABASE_SERVICE_KEY', 'your-service-role-key-here');

/**
 * Make a GET request to the Supabase REST API.
 *
 * @param string $table  Table name (e.g. 'check_in_logs')
 * @param array  $params Query parameters as key => value pairs
 *                       (e.g. ['select' => '*', 'order' => 'timestamp.desc', 'limit' => '50'])
 * @return array ['data' => array, 'error' => string|null, 'status' => int]
 */
function supabase_get(string $table, array $params = []): array {
    $url = SUPABASE_URL . '/rest/v1/' . urlencode($table);
    if (!empty($params)) {
        $url .= '?' . http_build_query($params);
    }

    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT        => 10,
        CURLOPT_HTTPHEADER     => [
            'apikey: '        . SUPABASE_SERVICE_KEY,
            'Authorization: Bearer ' . SUPABASE_SERVICE_KEY,
            'Content-Type: application/json',
        ],
    ]);

    $body   = curl_exec($ch);
    $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $err    = curl_error($ch);
    curl_close($ch);

    if ($err) {
        return ['data' => [], 'error' => $err, 'status' => 0];
    }

    $decoded = json_decode($body, true);
    if ($status >= 400) {
        $msg = is_array($decoded) ? ($decoded['message'] ?? $body) : $body;
        return ['data' => [], 'error' => $msg, 'status' => $status];
    }

    return ['data' => $decoded ?? [], 'error' => null, 'status' => $status];
}
```

- [ ] **Step 3: Create `web_dashboard/.gitignore`**

```
config.php
```

- [ ] **Step 4: Create `web_dashboard/README.md`**

```markdown
# FaceAttend Web Dashboard

A PHP dashboard for the face recognition attendance system.

## Requirements
- PHP 8.0+
- Access to your Supabase project

## Setup

1. Copy the config template:
   ```bash
   cp config.example.php config.php
   ```

2. Edit `config.php` and fill in your Supabase URL and Service Role Key.
   > Use the **Service Role Key** (not the anon key) — found in your Supabase project under Settings → API.

3. Run the built-in PHP server:
   ```bash
   cd web_dashboard
   php -S localhost:8080
   ```

4. Open `http://localhost:8080` in your browser.

## Deployment
Point Apache or Nginx at the `web_dashboard/` directory. Ensure `config.php` is not web-accessible (it's outside `api/` and not served directly).
```

- [ ] **Step 5: Commit**

```bash
git add web_dashboard/
git commit -m "feat(dashboard): scaffold project with config and README"
```

---

### Task 2: `api/stats.php` — Summary Counts

**Files:**
- Create: `web_dashboard/api/stats.php`

**Interfaces:**
- Consumes: `supabase_get()` from `web_dashboard/config.php`
- Produces: `GET /api/stats.php` → JSON `{ total_students, today_checkins, pending_queue, last_checkin: { student_id, timestamp } }`

- [ ] **Step 1: Create `web_dashboard/api/stats.php`**

```php
<?php
require_once __DIR__ . '/../config.php';
header('Content-Type: application/json');
header('Cache-Control: no-store');

// Total registered students
$usersRes = supabase_get('users', ['select' => 'id', 'limit' => '1']);
if ($usersRes['error']) {
    http_response_code(503);
    echo json_encode(['error' => 'Supabase unavailable: ' . $usersRes['error']]);
    exit;
}

// Get count via Prefer: count=exact header (separate curl call for count)
function supabase_count(string $table, array $params = []): int {
    $url = SUPABASE_URL . '/rest/v1/' . urlencode($table);
    $params['select'] = 'id'; // minimal select
    $url .= '?' . http_build_query($params);

    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT        => 10,
        CURLOPT_HTTPHEADER     => [
            'apikey: '               . SUPABASE_SERVICE_KEY,
            'Authorization: Bearer ' . SUPABASE_SERVICE_KEY,
            'Prefer: count=exact',
        ],
    ]);
    curl_exec($ch);
    // Supabase returns Content-Range: 0-0/48 — parse the total
    $range = '';
    curl_setopt($ch, CURLOPT_HEADERFUNCTION, function($ch, $header) use (&$range) {
        if (stripos($header, 'content-range:') === 0) {
            $range = trim(substr($header, strlen('content-range:')));
        }
        return strlen($header);
    });
    curl_exec($ch);
    curl_close($ch);

    // Parse "0-X/TOTAL" → TOTAL
    if (preg_match('/\/(\d+)$/', $range, $m)) {
        return (int)$m[1];
    }
    return 0;
}

// Today's date range in UTC
$todayStart = gmdate('Y-m-d') . 'T00:00:00Z';
$todayEnd   = gmdate('Y-m-d') . 'T23:59:59Z';

// Fetch all counts in parallel using separate calls
$totalStudents  = supabase_count('users');
$pendingQueue   = supabase_count('registration_queue', ['status' => 'eq.pending']);

// Today's check-ins count
$todayRes = supabase_get('check_in_logs', [
    'select'    => 'id',
    'timestamp' => 'gte.' . $todayStart,
    'and'       => '(timestamp.lte.' . $todayEnd . ')',
]);
$todayCheckins = count($todayRes['data']);

// Last check-in
$lastRes = supabase_get('check_in_logs', [
    'select' => 'student_id,timestamp',
    'order'  => 'timestamp.desc',
    'limit'  => '1',
]);
$lastCheckin = !empty($lastRes['data']) ? $lastRes['data'][0] : null;

echo json_encode([
    'total_students' => $totalStudents,
    'today_checkins' => $todayCheckins,
    'pending_queue'  => $pendingQueue,
    'last_checkin'   => $lastCheckin,
]);
```

- [ ] **Step 2: Test manually**

```bash
cd web_dashboard
php -S localhost:8080 &
curl http://localhost:8080/api/stats.php
```

Expected output (values will vary):
```json
{"total_students":48,"today_checkins":31,"pending_queue":3,"last_checkin":{"student_id":"STD-202401","timestamp":"2026-06-30T03:48:22Z"}}
```

- [ ] **Step 3: Commit**

```bash
git add web_dashboard/api/stats.php
git commit -m "feat(dashboard): add stats API endpoint"
```

---

### Task 3: `api/attendance.php` — Check-in Logs

**Files:**
- Create: `web_dashboard/api/attendance.php`

**Interfaces:**
- Consumes: `supabase_get()` from `web_dashboard/config.php`
- Produces: `GET /api/attendance.php?date=YYYY-MM-DD&device_id=X&page=1&per_page=20`
  → JSON `{ data: [{ id, student_id, name, similarity_score, device_id, timestamp }], total, page }`

- [ ] **Step 1: Create `web_dashboard/api/attendance.php`**

```php
<?php
require_once __DIR__ . '/../config.php';
header('Content-Type: application/json');
header('Cache-Control: no-store');

$date     = $_GET['date']      ?? gmdate('Y-m-d');
$deviceId = $_GET['device_id'] ?? '';
$page     = max(1, (int)($_GET['page']     ?? 1));
$perPage  = max(1, min(100, (int)($_GET['per_page'] ?? 20)));
$offset   = ($page - 1) * $perPage;

// Validate date format
if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $date)) {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid date format. Use YYYY-MM-DD.']);
    exit;
}

$dayStart = $date . 'T00:00:00Z';
$dayEnd   = $date . 'T23:59:59Z';

// Build query params for check_in_logs
$params = [
    'select'    => 'id,student_id,similarity_score,device_id,timestamp',
    'timestamp' => 'gte.' . $dayStart,
    'and'       => '(timestamp.lte.' . $dayEnd . ')',
    'order'     => 'timestamp.desc',
    'limit'     => (string)$perPage,
    'offset'    => (string)$offset,
];
if ($deviceId !== '') {
    $params['device_id'] = 'eq.' . $deviceId;
}

$logsRes = supabase_get('check_in_logs', $params);
if ($logsRes['error']) {
    http_response_code(503);
    echo json_encode(['error' => 'Supabase unavailable: ' . $logsRes['error']]);
    exit;
}

$logs = $logsRes['data'];

// Fetch user names for all student_ids in this page
$studentIds = array_unique(array_column($logs, 'student_id'));
$nameMap = [];
if (!empty($studentIds)) {
    // Supabase REST: filter by array using in.(id1,id2,...)
    $inFilter = 'in.(' . implode(',', array_map('urlencode', $studentIds)) . ')';
    $usersRes = supabase_get('users', [
        'select'     => 'student_id,name',
        'student_id' => $inFilter,
    ]);
    foreach ($usersRes['data'] as $user) {
        $nameMap[$user['student_id']] = $user['name'];
    }
}

// Merge name into each log row
foreach ($logs as &$log) {
    $log['name'] = $nameMap[$log['student_id']] ?? null;
}
unset($log);

// Count total matching rows for pagination
$countParams = [
    'select'    => 'id',
    'timestamp' => 'gte.' . $dayStart,
    'and'       => '(timestamp.lte.' . $dayEnd . ')',
];
if ($deviceId !== '') {
    $countParams['device_id'] = 'eq.' . $deviceId;
}
$totalRes = supabase_get('check_in_logs', $countParams);
$total    = count($totalRes['data']);

echo json_encode([
    'data'  => $logs,
    'total' => $total,
    'page'  => $page,
]);
```

- [ ] **Step 2: Test manually**

```bash
curl "http://localhost:8080/api/attendance.php?date=2026-06-30&page=1&per_page=5"
```

Expected shape:
```json
{
  "data": [
    { "id": 1, "student_id": "STD-202401", "name": "Somchai Jaidee", "similarity_score": 0.91, "device_id": "ESP32-A1", "timestamp": "2026-06-30T03:48:22Z" }
  ],
  "total": 31,
  "page": 1
}
```

- [ ] **Step 3: Commit**

```bash
git add web_dashboard/api/attendance.php
git commit -m "feat(dashboard): add attendance API endpoint"
```

---

### Task 4: `api/students.php` — Students + Queue Status

**Files:**
- Create: `web_dashboard/api/students.php`

**Interfaces:**
- Consumes: `supabase_get()` from `web_dashboard/config.php`
- Produces: `GET /api/students.php`
  → JSON `{ data: [{ student_id, name, created_at, queue_status }] }`

- [ ] **Step 1: Create `web_dashboard/api/students.php`**

```php
<?php
require_once __DIR__ . '/../config.php';
header('Content-Type: application/json');
header('Cache-Control: no-store');

// Fetch all users
$usersRes = supabase_get('users', [
    'select' => 'student_id,name,created_at',
    'order'  => 'created_at.desc',
]);
if ($usersRes['error']) {
    http_response_code(503);
    echo json_encode(['error' => 'Supabase unavailable: ' . $usersRes['error']]);
    exit;
}

$users = $usersRes['data'];

// Fetch latest queue status per student_id
// Get the most recent queue entry per student by fetching all and grouping in PHP
$queueRes = supabase_get('registration_queue', [
    'select' => 'student_id,status',
    'order'  => 'created_at.desc',
]);

// Build map: student_id -> latest status (first occurrence = most recent due to desc order)
$queueMap = [];
foreach ($queueRes['data'] as $item) {
    if (!isset($queueMap[$item['student_id']])) {
        $queueMap[$item['student_id']] = $item['status'];
    }
}

// Merge queue status into users
foreach ($users as &$user) {
    $user['queue_status'] = $queueMap[$user['student_id']] ?? null;
}
unset($user);

echo json_encode(['data' => $users]);
```

- [ ] **Step 2: Test manually**

```bash
curl "http://localhost:8080/api/students.php"
```

Expected shape:
```json
{
  "data": [
    { "student_id": "STD-202401", "name": "Somchai Jaidee", "created_at": "2026-06-28T10:00:00Z", "queue_status": "completed" }
  ]
}
```

- [ ] **Step 3: Commit**

```bash
git add web_dashboard/api/students.php
git commit -m "feat(dashboard): add students API endpoint"
```

---

### Task 5: `api/queue.php` — Registration Queue

**Files:**
- Create: `web_dashboard/api/queue.php`

**Interfaces:**
- Consumes: `supabase_get()` from `web_dashboard/config.php`
- Produces: `GET /api/queue.php?status=pending|completed|failed`
  → JSON `{ data: [{ id, student_id, image_path, status, created_at, processed_at, error_message }] }`

- [ ] **Step 1: Create `web_dashboard/api/queue.php`**

```php
<?php
require_once __DIR__ . '/../config.php';
header('Content-Type: application/json');
header('Cache-Control: no-store');

$status = $_GET['status'] ?? '';
$allowed = ['pending', 'completed', 'failed'];

$params = [
    'select' => 'id,student_id,image_path,status,created_at,processed_at,error_message',
    'order'  => 'created_at.desc',
];

if ($status !== '' && in_array($status, $allowed, true)) {
    $params['status'] = 'eq.' . $status;
}

$res = supabase_get('registration_queue', $params);
if ($res['error']) {
    http_response_code(503);
    echo json_encode(['error' => 'Supabase unavailable: ' . $res['error']]);
    exit;
}

echo json_encode(['data' => $res['data']]);
```

- [ ] **Step 2: Test manually**

```bash
curl "http://localhost:8080/api/queue.php?status=pending"
```

Expected shape:
```json
{
  "data": [
    { "id": 7, "student_id": "STD-202433", "image_path": "/uploads/xxx.jpg", "status": "pending", "created_at": "2026-06-30T03:00:00Z", "processed_at": null, "error_message": null }
  ]
}
```

- [ ] **Step 3: Commit**

```bash
git add web_dashboard/api/queue.php
git commit -m "feat(dashboard): add queue API endpoint"
```

---

### Task 6: CSS Design System (`assets/style.css`)

**Files:**
- Create: `web_dashboard/assets/style.css`

**Interfaces:**
- Produces: CSS classes consumed by `index.php` — full list documented in the file itself

- [ ] **Step 1: Create `web_dashboard/assets/style.css`**

```css
/* ── Reset & Base ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background: #0f1117;
  color: #e2e8f0;
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  font-size: 14px;
  line-height: 1.5;
}

/* ── Top Bar ── */
.topbar {
  background: #1a1d2e;
  border-bottom: 1px solid #2d3148;
  padding: 14px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky;
  top: 0;
  z-index: 100;
}
.topbar-logo { font-size: 17px; font-weight: 700; color: #a78bfa; letter-spacing: 0.4px; }
.topbar-logo span { color: #e2e8f0; }
.live-badge { display: flex; align-items: center; gap: 8px; font-size: 12px; color: #94a3b8; }
.live-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #22c55e;
  transition: background 0.3s;
}
.live-dot.offline { background: #ef4444; animation: none; }
.live-dot.online  { animation: pulse 1.5s ease-in-out infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }

/* ── Stats Row ── */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  padding: 16px 24px;
  background: #13151f;
}
.stat-card {
  background: #1a1d2e;
  border: 1px solid #2d3148;
  border-radius: 10px;
  padding: 14px 18px;
}
.stat-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  color: #64748b;
  margin-bottom: 6px;
}
.stat-value { font-size: 28px; font-weight: 700; color: #e2e8f0; }
.stat-value--purple { color: #a78bfa; }
.stat-value--green  { color: #22c55e; }
.stat-value--yellow { color: #f59e0b; }
.stat-value--sm     { font-size: 19px; margin-top: 4px; }
.stat-sub { font-size: 11px; color: #64748b; margin-top: 4px; }

/* ── Tabs ── */
.tabs {
  display: flex;
  padding: 0 24px;
  background: #13151f;
  border-bottom: 1px solid #2d3148;
}
.tab {
  padding: 11px 20px;
  font-size: 13px;
  color: #64748b;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  user-select: none;
  transition: color 0.15s;
}
.tab:hover { color: #94a3b8; }
.tab.active { color: #a78bfa; border-bottom-color: #a78bfa; font-weight: 600; }

.badge {
  display: inline-block;
  border-radius: 10px;
  padding: 1px 7px;
  font-size: 11px;
  margin-left: 5px;
}
.badge--purple { background: #a78bfa22; color: #a78bfa; }
.badge--yellow { background: #f59e0b22; color: #f59e0b; }

/* ── Tab Content ── */
.tab-content { display: none; padding: 20px 24px; }
.tab-content.active { display: block; }

/* ── Filter Bar ── */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.filter-label { font-size: 12px; color: #64748b; white-space: nowrap; }
.filter-select, .filter-input {
  background: #1a1d2e;
  border: 1px solid #2d3148;
  border-radius: 6px;
  padding: 6px 12px;
  color: #e2e8f0;
  font-size: 13px;
}
.filter-select:focus, .filter-input:focus {
  outline: none;
  border-color: #a78bfa55;
}
.btn-refresh {
  margin-left: auto;
  background: #a78bfa1a;
  border: 1px solid #a78bfa44;
  border-radius: 6px;
  padding: 6px 14px;
  color: #a78bfa;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.15s;
}
.btn-refresh:hover { background: #a78bfa2a; }

/* ── Table ── */
.table-wrap {
  background: #1a1d2e;
  border: 1px solid #2d3148;
  border-radius: 10px;
  overflow: hidden;
}
.table-wrap table { width: 100%; border-collapse: collapse; }
.table-wrap th {
  padding: 11px 16px;
  text-align: left;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.7px;
  color: #64748b;
  font-weight: 600;
  border-bottom: 1px solid #2d3148;
  background: #13151f55;
}
.table-wrap td {
  padding: 12px 16px;
  border-bottom: 1px solid #1e2235;
  font-size: 13px;
  color: #cbd5e1;
}
.table-wrap tr:last-child td { border-bottom: none; }
.table-wrap tbody tr:hover td { background: #ffffff05; }
.table-wrap tbody tr.row-new td {
  background: #a78bfa07;
  border-left: 3px solid #a78bfa55;
}
.table-wrap tbody tr.row-new td:not(:first-child) { border-left: none; }

/* ── Cell helpers ── */
.cell-id { font-family: monospace; font-size: 13px; font-weight: 600; color: #e2e8f0; }
.cell-time-main { display: block; color: #e2e8f0; }
.cell-time-rel  { display: block; font-size: 11px; color: #64748b; }
.cell-device {
  background: #1e2235;
  border: 1px solid #2d3148;
  border-radius: 5px;
  padding: 2px 8px;
  font-size: 11px;
  color: #94a3b8;
  font-family: monospace;
}
.cell-error { font-size: 11px; color: #f87171; word-break: break-all; }

/* ── Score Badge ── */
.score-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
}
.score-badge--high { background: #22c55e18; color: #22c55e; border: 1px solid #22c55e33; }
.score-badge--mid  { background: #f59e0b18; color: #f59e0b; border: 1px solid #f59e0b33; }
.score-badge--low  { background: #ef444418; color: #ef4444; border: 1px solid #ef444433; }

/* ── Status Badge ── */
.status-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  text-transform: capitalize;
}
.status-badge--completed { background: #22c55e18; color: #22c55e; border: 1px solid #22c55e33; }
.status-badge--pending   { background: #f59e0b18; color: #f59e0b; border: 1px solid #f59e0b33; }
.status-badge--failed    { background: #ef444418; color: #ef4444; border: 1px solid #ef444433; }
.status-badge--none      { background: #1e2235;   color: #64748b; border: 1px solid #2d3148; }

/* ── Pagination ── */
.pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-top: 1px solid #2d3148;
  font-size: 12px;
  color: #64748b;
}
.page-btns { display: flex; gap: 5px; }
.page-btn {
  padding: 4px 10px;
  border-radius: 5px;
  border: 1px solid #2d3148;
  background: #1a1d2e;
  color: #94a3b8;
  font-size: 12px;
  cursor: pointer;
}
.page-btn.active  { background: #a78bfa22; border-color: #a78bfa55; color: #a78bfa; }
.page-btn:disabled { opacity: 0.4; cursor: default; }

/* ── Legend ── */
.legend { font-size: 11px; color: #64748b; margin-top: 10px; font-style: italic; }

/* ── Empty State ── */
.empty-state {
  padding: 48px 24px;
  text-align: center;
  color: #64748b;
}
.empty-state p { font-size: 15px; }

/* ── Error Banner ── */
.error-banner {
  display: none;
  background: #ef444415;
  border: 1px solid #ef444433;
  border-radius: 8px;
  padding: 10px 16px;
  margin: 12px 24px;
  font-size: 13px;
  color: #f87171;
}
.error-banner.visible { display: flex; align-items: center; justify-content: space-between; }
.error-banner button { background: none; border: none; color: #f87171; cursor: pointer; font-size: 16px; }

/* ── Responsive ── */
@media (max-width: 900px) {
  .stats-row { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 600px) {
  .stats-row { grid-template-columns: 1fr; }
  .filter-bar { flex-direction: column; align-items: flex-start; }
  .btn-refresh { margin-left: 0; }
}
```

- [ ] **Step 2: Commit**

```bash
git add web_dashboard/assets/style.css
git commit -m "feat(dashboard): add CSS design system"
```

---

### Task 7: `index.php` — Main Page Shell + JS Polling

**Files:**
- Create: `web_dashboard/index.php`

**Interfaces:**
- Consumes: `web_dashboard/assets/style.css`
- Consumes: `GET /api/stats.php` → `{ total_students, today_checkins, pending_queue, last_checkin }`
- Consumes: `GET /api/attendance.php?date&device_id&page&per_page` → `{ data, total, page }`
- Consumes: `GET /api/students.php` → `{ data }`
- Consumes: `GET /api/queue.php?status` → `{ data }`

- [ ] **Step 1: Create `web_dashboard/index.php`**

```php
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
let pollTimer    = null;

// ── Tab switching ──
function switchTab(name) {
  currentTab = name;
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  document.getElementById('content-' + name).classList.add('active');
  if (name === 'students') loadStudents();
  if (name === 'queue')    loadQueue();
}

// ── Helpers ──
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
  return `<span class="status-badge status-badge--${s}">${s}</span>`;
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
    const freshIds = attendancePage === 1 ? new Set([...newIds].filter(id => !knownIds.has(id))) : new Set();
    knownIds = newIds;

    // Populate device filter (first load or on date change)
    const deviceSel = document.getElementById('filter-device');
    if (deviceSel.options.length <= 1) {
      const devices = [...new Set(rows.map(r => r.device_id).filter(Boolean))];
      devices.forEach(dv => {
        const opt = document.createElement('option');
        opt.value = dv; opt.textContent = dv;
        deviceSel.appendChild(opt);
      });
    }

    // Render rows
    if (rows.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5"><div class="empty-state"><p>No check-ins found for this date.</p></div></td></tr>';
    } else {
      tbody.innerHTML = rows.map(row => `
        <tr class="${freshIds.has(row.id) ? 'row-new' : ''}">
          <td><span class="cell-id">${row.student_id ?? '—'}</span></td>
          <td>${row.name ?? '<span style="color:#64748b">—</span>'}</td>
          <td>
            <span class="cell-time-main">${formatTime(row.timestamp)}</span>
            <span class="cell-time-rel">${formatRelative(row.timestamp)}</span>
          </td>
          <td>${scoreBadge(row.similarity_score)}</td>
          <td><span class="cell-device">${row.device_id ?? '—'}</span></td>
        </tr>
      `).join('');
    }

    // Badge on Attendance tab
    document.getElementById('badge-attendance').textContent = d.total > 0 ? d.total : '';

    // Pagination
    const totalPages = Math.ceil((d.total ?? 0) / PER_PAGE);
    const pagination = document.getElementById('attendance-pagination');
    if (totalPages > 1) {
      pagination.style.display = 'flex';
      document.getElementById('attendance-page-info').textContent =
        `Showing ${(attendancePage - 1) * PER_PAGE + 1}–${Math.min(attendancePage * PER_PAGE, d.total)} of ${d.total}`;
      const btns = document.getElementById('attendance-page-btns');
      btns.innerHTML = '';
      for (let p = 1; p <= Math.min(totalPages, 5); p++) {
        const btn = document.createElement('button');
        btn.className = 'page-btn' + (p === attendancePage ? ' active' : '');
        btn.textContent = p;
        btn.onclick = () => loadAttendance(p);
        btns.appendChild(btn);
      }
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
          <td><span class="cell-id">${row.student_id ?? '—'}</span></td>
          <td>${row.name ?? '<span style="color:#64748b">—</span>'}</td>
          <td>${formatDateTime(row.created_at)}</td>
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
      tbody.innerHTML = rows.map(row => `
        <tr>
          <td><span class="cell-id">${row.student_id ?? '—'}</span></td>
          <td style="font-size:11px;color:#94a3b8;word-break:break-all">${row.image_path ?? '—'}</td>
          <td>${statusBadge(row.status)}</td>
          <td>${formatDateTime(row.created_at)}</td>
          <td>${row.processed_at ? formatDateTime(row.processed_at) : '<span style="color:#64748b">—</span>'}</td>
          <td>${row.error_message ? `<span class="cell-error">${row.error_message}</span>` : '<span style="color:#64748b">—</span>'}</td>
        </tr>
      `).join('');
    }
  } catch (e) {
    setError('Queue error: ' + e.message);
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
document.getElementById('filter-date').addEventListener('change', () => loadAttendance(1));
document.getElementById('filter-device').addEventListener('change', () => loadAttendance(1));

loadStats();
loadAttendance(1);
startPolling();
</script>

</body>
</html>
```

- [ ] **Step 2: Test the full dashboard**

```bash
# From web_dashboard/ directory (if server not already running):
php -S localhost:8080

# Open in browser:
# http://localhost:8080
```

Verify:
- Stats bar shows real numbers from Supabase
- Attendance table loads with color-coded scores
- Live dot pulses green
- Switching to Students tab loads data
- Switching to Queue tab loads data
- After 5 seconds, attendance auto-refreshes

- [ ] **Step 3: Commit**

```bash
git add web_dashboard/index.php
git commit -m "feat(dashboard): add main page shell with JS polling"
```

---

### Task 8: Final Integration Check + README Update

**Files:**
- Modify: `web_dashboard/README.md` (add `.gitignore` note and deployment tips)

- [ ] **Step 1: Verify `.gitignore` is respected**

```bash
cd web_dashboard
git status
# Confirm config.php does NOT appear in untracked files
```

- [ ] **Step 2: Verify all API endpoints return valid JSON**

```bash
curl http://localhost:8080/api/stats.php      | python -m json.tool
curl http://localhost:8080/api/attendance.php  | python -m json.tool
curl http://localhost:8080/api/students.php    | python -m json.tool
curl "http://localhost:8080/api/queue.php?status=pending" | python -m json.tool
```

Each must return valid JSON with no PHP errors or warnings in output.

- [ ] **Step 3: Verify error handling — test with wrong key**

Temporarily set `SUPABASE_SERVICE_KEY` to `'invalid'` in `config.php`, reload the dashboard.

Expected: Red live dot, error banner appears, table shows loading state — NOT a blank page or PHP error.

Restore the real key after verifying.

- [ ] **Step 4: Final commit**

```bash
git add web_dashboard/
git commit -m "feat(dashboard): complete PHP attendance dashboard"
```
