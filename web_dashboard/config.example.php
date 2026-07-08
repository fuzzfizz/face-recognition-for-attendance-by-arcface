<?php
// Copy this file to config.php and fill in your database credentials.
// NEVER commit config.php – it contains database passwords and API keys.
define('DB_HOST', 'localhost');
define('DB_USER', 'your-db-user');
define('DB_PASS', 'your-db-password');
define('DB_NAME', 'face_attendance');
define('AI_SERVER_URL', 'http://localhost:8000');
define('ADMIN_API_KEY', 'your-secret-admin-key');

function get_db_connection() {
    static $pdo = null;
    if ($pdo === null) {
        try {
            $dsn = "mysql:host=" . DB_HOST . ";dbname=" . DB_NAME . ";charset=utf8mb4";
            $options = [
                PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                PDO::ATTR_EMULATE_PREPARES   => false,
            ];
            $pdo = new PDO($dsn, DB_USER, DB_PASS, $options);
            $pdo->exec("SET time_zone = '+00:00'");
        } catch (PDOException $e) {
            error_log('Database connection failed: ' . $e->getMessage());
            header('Content-Type: application/json');
            http_response_code(500);
            echo json_encode(['error' => 'Database connection failed. Please contact the administrator.']);
            exit;
        }
    }
    return $pdo;
}
