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

$dayStart = $date . ' 00:00:00';
$dayEnd   = $date . ' 23:59:59';

try {
    $pdo = get_db_connection();

    $sql = "SELECT l.id, l.student_id, l.similarity_score, l.device_id, l.timestamp, u.name
            FROM check_in_logs l
            LEFT JOIN users u ON l.student_id = u.student_id
            WHERE l.timestamp >= :day_start AND l.timestamp <= :day_end AND l.student_id IS NOT NULL";
    
    $countSql = "SELECT COUNT(*) FROM check_in_logs l WHERE l.timestamp >= :day_start AND l.timestamp <= :day_end AND l.student_id IS NOT NULL";

    if ($deviceId !== '') {
        $sql .= " AND l.device_id = :device_id";
        $countSql .= " AND l.device_id = :device_id";
    }

    $sql .= " ORDER BY l.timestamp DESC LIMIT :limit OFFSET :offset";

    // Bind values
    $stmt = $pdo->prepare($sql);
    $stmt->bindValue(':day_start', $dayStart, PDO::PARAM_STR);
    $stmt->bindValue(':day_end', $dayEnd, PDO::PARAM_STR);
    if ($deviceId !== '') {
        $stmt->bindValue(':device_id', $deviceId, PDO::PARAM_STR);
    }
    $stmt->bindValue(':limit', $perPage, PDO::PARAM_INT);
    $stmt->bindValue(':offset', $offset, PDO::PARAM_INT);
    $stmt->execute();
    $logs = $stmt->fetchAll();

    // Bind count values
    $countStmt = $pdo->prepare($countSql);
    $countStmt->bindValue(':day_start', $dayStart, PDO::PARAM_STR);
    $countStmt->bindValue(':day_end', $dayEnd, PDO::PARAM_STR);
    if ($deviceId !== '') {
        $countStmt->bindValue(':device_id', $deviceId, PDO::PARAM_STR);
    }
    $countStmt->execute();
    $total = (int)$countStmt->fetchColumn();

    // Format timestamps to match ISO format
    foreach ($logs as &$log) {
        if ($log['timestamp']) {
            $log['timestamp'] = str_replace(' ', 'T', $log['timestamp']) . 'Z';
        }
    }
    unset($log);

    echo json_encode([
        'data'  => $logs,
        'total' => $total,
        'page'  => $page,
    ]);
} catch (PDOException $e) {
    http_response_code(503);
    echo json_encode(['error' => 'Database query error: ' . $e->getMessage()]);
    exit;
}
