<?php
require_once __DIR__ . '/../config.php';
header('Content-Type: application/json');
header('Cache-Control: no-store');

try {
    // Fetch all users
    $usersRes = supabase_get('users', [
        'select' => 'student_id,name,created_at',
        'order'  => 'created_at.desc',
    ]);
    if ($usersRes['error']) {
        throw new Exception('Supabase unavailable: ' . $usersRes['error']);
    }

    $users = $usersRes['data'];

    // Fetch latest queue status per student_id
    // Get the most recent queue entry per student by fetching all and grouping in PHP
    $queueRes = supabase_get('registration_queue', [
        'select' => 'student_id,status',
        'order'  => 'created_at.desc',
    ]);
    if ($queueRes['error']) {
        throw new Exception('Supabase unavailable: ' . $queueRes['error']);
    }

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
} catch (Exception $e) {
    http_response_code(503);
    echo json_encode(['error' => $e->getMessage()]);
    exit;
}
