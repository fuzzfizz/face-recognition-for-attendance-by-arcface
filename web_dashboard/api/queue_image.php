<?php
require_once __DIR__ . '/../config.php';

$id = filter_input(INPUT_GET, 'id', FILTER_VALIDATE_INT);
if ($id === false || $id === null) {
    http_response_code(400);
    echo "Invalid or missing ID parameter.";
    exit;
}

try {
    $pdo = get_db_connection();
    $stmt = $pdo->prepare("SELECT image_blob FROM registration_queue WHERE id = :id");
    $stmt->execute([':id' => $id]);
    $row = $stmt->fetch();

    if (!$row) {
        http_response_code(404);
        echo "Image not found.";
        exit;
    }

    $blob = $row['image_blob'];
    
    // Detect image type (JPEG/PNG) from binary magic bytes if possible, otherwise fallback to jpeg
    $contentType = 'image/jpeg';
    if (strncmp($blob, "\x89PNG\r\n\x1a\n", 8) === 0) {
        $contentType = 'image/png';
    } elseif (strncmp($blob, "GIF8", 4) === 0) {
        $contentType = 'image/gif';
    }

    header("Content-Type: $contentType");
    header("Content-Length: " . strlen($blob));
    header("Cache-Control: public, max-age=86400"); // cache for 1 day
    echo $blob;
} catch (PDOException $e) {
    error_log('Queue image fetch failed: ' . $e->getMessage());
    http_response_code(500);
    echo "Database error occurred.";
    exit;
}