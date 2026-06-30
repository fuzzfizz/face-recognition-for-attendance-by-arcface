# PHP Web Dashboard Design Spec
**Date:** 2026-06-30
**Scope:** New `web_dashboard/` project — standalone PHP dashboard for the face recognition attendance system
**Status:** Approved for implementation

---

## 1. Context & Goals

The face recognition attendance system (`ai_server` + `app_face_capture`) currently has no way to visualise its data without directly querying Supabase. This dashboard gives **teachers and admins** a browser-based view of attendance logs, student registrations, and the processing queue — all sourced from the same Supabase database that `ai_server` writes to.

### Tables Used (from `ai_server/supabase/migrations/20260630000000_init_schema.sql`)

| Table | Purpose |
|---|---|
| `check_in_logs` | Attendance records (primary data source) |
| `users` | Registered students |
| `registration_queue` | Face registration processing queue |

### Out of Scope
- Login / authentication (internal/LAN use only)
- Triggering model training (that is the Flutter app's admin screen)
- Editing or deleting records
- Export to CSV/PDF

---

## 2. Architecture

```
Browser (JS polls every 5s)
        │
        ▼
PHP Web Server (Apache/Nginx or built-in php -S)
├── index.php              # Page shell: HTML layout, tabs, JS polling logic
├── config.php             # SUPABASE_URL + SUPABASE_SERVICE_KEY (server-side only)
└── api/
    ├── attendance.php     # GET check_in_logs (filtered by date, device)
    ├── students.php       # GET users + registration_queue status per student
    └── stats.php          # GET summary counts (totals, today's check-ins, pending)
```

**Data flow:**
1. Browser loads `index.php` → full page rendered.
2. JavaScript calls `api/stats.php` and `api/attendance.php` every **5 seconds** via `fetch()`.
3. Each `api/*.php` file makes a **cURL** request to Supabase REST API using the service role key (never sent to the browser).
4. PHP returns JSON; JavaScript updates the DOM without a full page reload.
5. **Students** and **Queue** tabs refresh only when the user clicks them (those tables change rarely).

**Supabase REST API pattern used by each endpoint:**
```
GET https://<SUPABASE_URL>/rest/v1/<table>?select=*&order=<col>.desc&limit=<n>
Headers:
  apikey: <SUPABASE_SERVICE_KEY>
  Authorization: Bearer <SUPABASE_SERVICE_KEY>
```

---

## 3. Pages & Layout

### 3.1 Global Header
- **Left:** Logo "FaceAttend Dashboard"
- **Right:** 🟢 Live pulsing indicator (green = polling active, red = last poll failed)
- Background: dark (`#1a1d2e`)

### 3.2 Stats Bar (always visible, auto-refreshes every 5s)

| Card | Value | Source |
|---|---|---|
| Total Students | COUNT of `users` | `api/stats.php` |
| Today's Check-ins | COUNT of `check_in_logs` where `date(timestamp) = today` | `api/stats.php` |
| Pending Queue | COUNT of `registration_queue` where `status = 'pending'` | `api/stats.php` |
| Last Check-in | Most recent `check_in_logs.timestamp` + student_id | `api/stats.php` |

### 3.3 Tab: 📋 Attendance *(default, primary)*

**Purpose:** Teachers view who checked in today.

**Filters (top of tab):**
- Date picker — defaults to today, can select past dates
- Device selector — "All Devices" or specific `device_id` from `check_in_logs`

**Table columns:**

| Column | Source | Notes |
|---|---|---|
| Student ID | `check_in_logs.student_id` | Monospace font |
| Name | `users.name` (JOIN on student_id) | Falls back to "—" if not found |
| Check-in Time | `check_in_logs.timestamp` | Full time + relative ("2 min ago") |
| Similarity Score | `check_in_logs.similarity_score` | Color-coded badge |
| Device | `check_in_logs.device_id` | Chip/tag style |

**Similarity score color coding:**
- 🟢 `≥ 0.75` — high confidence (green badge)
- 🟡 `0.60–0.74` — medium confidence (yellow badge)
- 🔴 `< 0.60` — low confidence (red badge)

**Behaviour:**
- Newest row highlighted with purple left border on each refresh (if a new row was added)
- Paginated: 20 rows per page
- Auto-refreshes only this tab when it is the active tab

### 3.4 Tab: 👤 Students

**Purpose:** View all registered students and their registration status.

**Table columns:**

| Column | Source |
|---|---|
| Student ID | `users.student_id` |
| Name | `users.name` |
| Registered At | `users.created_at` |
| Queue Status | Latest `registration_queue.status` for this student_id |

**Status badges:** 🟡 pending · 🟢 completed · 🔴 failed · ⬜ none

**Behaviour:** Refreshes only when tab is clicked (no auto-polling).

### 3.5 Tab: ⚙️ Queue *(admin use)*

**Purpose:** See raw registration queue items and spot failures.

**Filters:** Status dropdown — All / Pending / Completed / Failed

**Table columns:**

| Column | Source |
|---|---|
| Student ID | `registration_queue.student_id` |
| Image Path | `registration_queue.image_path` |
| Status | `registration_queue.status` |
| Created At | `registration_queue.created_at` |
| Processed At | `registration_queue.processed_at` |
| Error | `registration_queue.error_message` (only shown if present) |

**Behaviour:** Refreshes only when tab is clicked.

---

## 4. File Structure

```
web_dashboard/
├── index.php          # Main page shell and JS polling engine
├── config.php         # Supabase credentials (gitignored)
├── config.example.php # Template with placeholder values (committed)
├── api/
│   ├── attendance.php # Returns check_in_logs JSON (with JOIN to users.name)
│   ├── students.php   # Returns users + queue status JSON
│   └── stats.php      # Returns summary counts JSON
├── assets/
│   └── style.css      # Dark theme, stat cards, table, tabs, badges, animations
└── README.md          # Setup instructions
```

### config.php (gitignored)
```php
<?php
define('SUPABASE_URL', 'https://your-project.supabase.co');
define('SUPABASE_SERVICE_KEY', 'your-service-role-key');
```

### config.example.php (committed)
```php
<?php
define('SUPABASE_URL', 'https://your-project.supabase.co');
define('SUPABASE_SERVICE_KEY', 'your-service-role-key-here');
```

---

## 5. Visual Design

- **Theme:** Dark mode (`#0f1117` body, `#1a1d2e` cards, `#2d3148` borders)
- **Accent colour:** Purple (`#a78bfa`) for active tab, badges, highlights
- **Typography:** System font stack (`Segoe UI`, `system-ui`, sans-serif)
- **No external CSS framework** — pure CSS for fast load with no build step
- **Animations:** Pulsing live dot, row highlight fade-in on new data
- **Responsive:** Works on laptop and tablet (min-width 768px)

---

## 6. API Endpoint Specs

### `api/stats.php`
**Method:** GET  
**Returns:**
```json
{
  "total_students": 48,
  "today_checkins": 31,
  "pending_queue": 3,
  "last_checkin": {
    "student_id": "STD-202401",
    "timestamp": "2026-06-30T03:48:22Z"
  }
}
```

### `api/attendance.php`
**Query params:** `date` (YYYY-MM-DD, default today), `device_id` (optional), `page` (default 1), `per_page` (default 20)  
**Returns:**
```json
{
  "data": [
    {
      "id": 1,
      "student_id": "STD-202401",
      "name": "Somchai Jaidee",
      "similarity_score": 0.91,
      "device_id": "ESP32-A1",
      "timestamp": "2026-06-30T03:48:22Z"
    }
  ],
  "total": 31,
  "page": 1
}
```

### `api/students.php`
**Returns:**
```json
{
  "data": [
    {
      "student_id": "STD-202401",
      "name": "Somchai Jaidee",
      "created_at": "2026-06-28T10:00:00Z",
      "queue_status": "completed"
    }
  ]
}
```

---

## 7. Error Handling

- If Supabase is unreachable: API returns `{"error": "Supabase unavailable"}` with HTTP 503; JS shows a dismissable error banner and turns the live dot red.
- If `config.php` is missing: `index.php` shows a setup instructions page.
- Empty states: each tab shows a friendly empty state message when no data is found.

---

## 8. Setup & Deployment

1. Copy project to any PHP host (Apache, Nginx, or `php -S localhost:8080`)
2. Copy `config.example.php` → `config.php` and fill in Supabase credentials
3. Add `config.php` to `.gitignore`
4. Open in browser — no build step required

> **Note:** Use the **Supabase Service Role Key** (not the anon key) so the dashboard can read all rows without RLS restrictions. This key must stay server-side in `config.php` and never be exposed to the browser.
