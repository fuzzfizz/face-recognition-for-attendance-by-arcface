<?php
require_once __DIR__ . '/../config.php';

header('Content-Type: application/json');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Method Not Allowed']);
    exit;
}

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, AI_SERVER_URL . '/train-now');
curl_setopt($ch, CURLOPT_POST, 1);
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
