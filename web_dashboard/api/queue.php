<?php
require_once __DIR__ . '/../config.php';
header('Content-Type: application/json');
header('Cache-Control: no-store');

try {
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
        throw new Exception('Supabase unavailable: ' . $res['error']);
    }

    echo json_encode(['data' => $res['data']]);
} catch (Exception $e) {
    http_response_code(503);
    echo json_encode(['error' => $e->getMessage()]);
    exit;
}
