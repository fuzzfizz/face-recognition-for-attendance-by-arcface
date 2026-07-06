<?php
require_once __DIR__ . '/../config.php';

header('Content-Type: application/json');

$clientKey = $_SERVER['HTTP_X_ADMIN_KEY'] ?? '';
if (!hash_equals(ADMIN_API_KEY, $clientKey)) {
    http_response_code(401);
    echo json_encode(['error' => 'Unauthorized: Invalid Admin Key']);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Method Not Allowed']);
    exit;
}

$studentId = $_POST['student_id'] ?? $_GET['student_id'] ?? null;
if (!$studentId) {
    $input = json_decode(file_get_contents('php://input'), true);
    $studentId = $input['student_id'] ?? null;
}

if (!$studentId) {
    http_response_code(400);
    echo json_encode(['error' => 'Missing student_id parameter']);
    exit;
}

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, AI_SERVER_URL . '/register/student/' . urlencode($studentId));
curl_setopt($ch, CURLOPT_CUSTOMREQUEST, 'DELETE');
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_HTTPHEADER, [
    'X-Admin-Key: ' . ADMIN_API_KEY,
    'Content-Type: application/json'
]);

$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($httpCode === 0) {
    $httpCode = 500;
}

if ($httpCode !== 200) {
    http_response_code($httpCode);
    if ($response) {
        echo $response;
    } else {
        echo json_encode(['error' => 'Failed to reach AI Server']);
    }
    exit;
}

echo $response;
