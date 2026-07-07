<?php
require_once __DIR__ . '/../config.php';
header('Content-Type: application/json');
header('Cache-Control: no-store');



// Today's date range in UTC
$todayStart = gmdate('Y-m-d') . 'T00:00:00Z';
$todayEnd   = gmdate('Y-m-d') . 'T23:59:59Z';

try {
    // Fetch all counts
    $totalStudents  = supabase_count('users');
    $pendingQueue   = supabase_count('registration_queue', ['status' => 'eq.pending']);

    // Today's check-ins count
    $todayCheckins = supabase_count('check_in_logs', [
        'timestamp'  => 'gte.' . $todayStart,
        'student_id' => 'not.is.null',
        'and'        => '(timestamp.lte.' . $todayEnd . ')',
    ]);

    // Last check-in
    $lastRes = supabase_get('check_in_logs', [
        'select'     => 'student_id,timestamp',
        'student_id' => 'not.is.null',
        'order'      => 'timestamp.desc',
        'limit'      => '1',
    ]);
    if ($lastRes['error']) {
        throw new Exception("Last check-in query failed: " . $lastRes['error']);
    }
    $lastCheckin = !empty($lastRes['data']) ? $lastRes['data'][0] : null;

    echo json_encode([
        'total_students' => $totalStudents,
        'today_checkins' => $todayCheckins,
        'pending_queue'  => $pendingQueue,
        'last_checkin'   => $lastCheckin,
    ]);
} catch (Exception $e) {
    http_response_code(503);
    echo json_encode(['error' => 'Supabase query error: ' . $e->getMessage()]);
    exit;
}
