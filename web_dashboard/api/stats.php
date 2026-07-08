<?php
require_once __DIR__ . '/../config.php';
header('Content-Type: application/json');
header('Cache-Control: no-store');

try {
    $pdo = get_db_connection();

    // 1. Total students count
    $stmt = $pdo->query("SELECT COUNT(*) FROM users");
    $totalStudents = (int)$stmt->fetchColumn();

    // 2. Pending queue count
    $stmt = $pdo->prepare("SELECT COUNT(*) FROM registration_queue WHERE status = ?");
    $stmt->execute(['pending']);
    $pendingQueue = (int)$stmt->fetchColumn();

    // 3. Today's check-ins (in UTC to match database timestamps)
    $todayStart = gmdate('Y-m-d 00:00:00');
    $todayEnd = gmdate('Y-m-d 23:59:59');
    $stmt = $pdo->prepare("SELECT COUNT(*) FROM check_in_logs WHERE timestamp >= ? AND timestamp <= ? AND student_id IS NOT NULL");
    $stmt->execute([$todayStart, $todayEnd]);
    $todayCheckins = (int)$stmt->fetchColumn();

    // 4. Last check-in
    $stmt = $pdo->query("SELECT student_id, timestamp FROM check_in_logs WHERE student_id IS NOT NULL ORDER BY timestamp DESC LIMIT 1");
    $lastCheckin = $stmt->fetch();
    if (!$lastCheckin) {
        $lastCheckin = null;
    } else {
        // Format timestamp to ISO 8601 to match frontend expectations
        $lastCheckin['timestamp'] = str_replace(' ', 'T', $lastCheckin['timestamp']) . 'Z';
    }

    echo json_encode([
        'total_students' => $totalStudents,
        'today_checkins' => $todayCheckins,
        'pending_queue'  => $pendingQueue,
        'last_checkin'   => $lastCheckin,
    ]);
} catch (PDOException $e) {
    error_log('Stats query failed: ' . $e->getMessage());
    http_response_code(503);
    echo json_encode(['error' => 'Database query error.']);
    exit;
}
