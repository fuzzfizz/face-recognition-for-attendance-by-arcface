<?php
require_once __DIR__ . '/../config.php';
header('Content-Type: application/json');
header('Cache-Control: no-store');

try {
    $pdo = get_db_connection();

    // Fetch users and their latest registration status via nested query
    $sql = "SELECT u.student_id, u.name, u.created_at, q.status AS queue_status
            FROM users u
            LEFT JOIN (
                SELECT rq.student_id, rq.status
                FROM registration_queue rq
                INNER JOIN (
                    SELECT student_id, MAX(id) as max_id
                    FROM registration_queue
                    GROUP BY student_id
                ) latest ON rq.id = latest.max_id
            ) q ON u.student_id = q.student_id
            ORDER BY u.created_at DESC";

    $stmt = $pdo->query($sql);
    $users = $stmt->fetchAll();

    // Format timestamps to match ISO format
    foreach ($users as &$user) {
        if ($user['created_at']) {
            $user['created_at'] = str_replace(' ', 'T', $user['created_at']) . 'Z';
        }
    }
    unset($user);

    echo json_encode(['data' => $users]);
} catch (PDOException $e) {
    http_response_code(503);
    echo json_encode(['error' => 'Database query error: ' . $e->getMessage()]);
    exit;
}
