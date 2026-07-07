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

try {
    // Build query params for check_in_logs
    $params = [
        'select'     => 'id,student_id,similarity_score,device_id,timestamp',
        'timestamp'  => 'gte.' . $dayStart,
        'student_id' => 'not.is.null',
        'and'        => '(timestamp.lte.' . $dayEnd . ')',
        'order'      => 'timestamp.desc',
        'limit'      => (string)$perPage,
        'offset'     => (string)$offset,
    ];
    if ($deviceId !== '') {
        $params['device_id'] = 'eq.' . $deviceId;
    }

    $logsRes = supabase_get('check_in_logs', $params);
    if ($logsRes['error']) {
        throw new Exception('Supabase unavailable: ' . $logsRes['error']);
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
        if ($usersRes['error']) {
            throw new Exception('Supabase unavailable: ' . $usersRes['error']);
        }
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
        'select'     => 'id',
        'timestamp'  => 'gte.' . $dayStart,
        'student_id' => 'not.is.null',
        'and'        => '(timestamp.lte.' . $dayEnd . ')',
    ];
    if ($deviceId !== '') {
        $countParams['device_id'] = 'eq.' . $deviceId;
    }
    $total = supabase_count('check_in_logs', $countParams);

    echo json_encode([
        'data'  => $logs,
        'total' => $total,
        'page'  => $page,
    ]);
} catch (Exception $e) {
    http_response_code(503);
    echo json_encode(['error' => $e->getMessage()]);
    exit;
}
