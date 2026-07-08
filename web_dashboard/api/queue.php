<?php
require_once __DIR__ . '/../config.php';
header('Content-Type: application/json');
header('Cache-Control: no-store');

try {
    $pdo = get_db_connection();

    $status = $_GET['status'] ?? '';
    $allowed = ['pending', 'completed', 'failed'];

    $sql = "SELECT id, student_id, image_path, status, created_at, processed_at, error_message
            FROM registration_queue";
    
    $params = [];
    if ($status !== '' && in_array($status, $allowed, true)) {
        $sql .= " WHERE status = :status";
        $params[':status'] = $status;
    }

    $sql .= " ORDER BY created_at DESC";

    $stmt = $pdo->prepare($sql);
    $stmt->execute($params);
    $rows = $stmt->fetchAll();

    // Format timestamps to match ISO format
    foreach ($rows as &$row) {
        if ($row['created_at']) {
            $row['created_at'] = str_replace(' ', 'T', $row['created_at']) . 'Z';
        }
        if ($row['processed_at']) {
            $row['processed_at'] = str_replace(' ', 'T', $row['processed_at']) . 'Z';
        }
    }
    unset($row);

    echo json_encode(['data' => $rows]);
} catch (PDOException $e) {
    error_log('Queue query failed: ' . $e->getMessage());
    http_response_code(503);
    echo json_encode(['error' => 'Database query error.']);
    exit;
}
