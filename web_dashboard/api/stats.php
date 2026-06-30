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
