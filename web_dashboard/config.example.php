<?php
// Copy this file to config.php and fill in your Supabase credentials.
// NEVER commit config.php – it contains your service role key.
define('SUPABASE_URL', 'https://your-project.supabase.co');
define('SUPABASE_SERVICE_KEY', 'your-service-role-key-here');
define('AI_SERVER_URL', 'http://localhost:8000');
define('ADMIN_API_KEY', 'your-secret-admin-key');

/**
 * Make a GET request to the Supabase REST API.
 *
 * @param string $table  Table name (e.g. 'check_in_logs')
 * @param array  $params Query parameters as key => value pairs
 *                       (e.g. ['select' => '*', 'order' => 'timestamp.desc', 'limit' => '50'])
 * @return array ['data' => array, 'error' => string|null, 'status' => int]
 */
function supabase_get(string $table, array $params = []): array {
    $url = SUPABASE_URL . '/rest/v1/' . urlencode($table);
    if (!empty($params)) {
        $url .= '?' . http_build_query($params);
    }

    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT        => 10,
        CURLOPT_HTTPHEADER     => [
            'apikey: '        . SUPABASE_SERVICE_KEY,
            'Authorization: Bearer ' . SUPABASE_SERVICE_KEY,
            'Content-Type: application/json',
        ],
    ]);

    $body   = curl_exec($ch);
    $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $err    = curl_error($ch);
    curl_close($ch);

    if ($err) {
        return ['data' => [], 'error' => $err, 'status' => 0];
    }

    $decoded = json_decode($body, true);
    if ($status >= 400) {
        $msg = is_array($decoded) ? ($decoded['message'] ?? $body) : $body;
        return ['data' => [], 'error' => $msg, 'status' => $status];
    }

    return ['data' => $decoded ?? [], 'error' => null, 'status' => $status];
}

/**
 * Get count via Prefer: count=exact header (separate curl call for count)
 *
 * @param string $table  Table name (e.g. 'check_in_logs')
 * @param array  $params Query parameters as key => value pairs
 * @return int
 */
function supabase_count(string $table, array $params = []): int {
    $url = SUPABASE_URL . '/rest/v1/' . urlencode($table);
    $params['select'] = 'id'; // minimal select
    $params['limit']  = '0';  // return empty array in body to minimize response payload size
    $url .= '?' . http_build_query($params);

    $ch = curl_init($url);
    $range = '';
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT        => 10,
        CURLOPT_HTTPHEADER     => [
            'apikey: '               . SUPABASE_SERVICE_KEY,
            'Authorization: Bearer ' . SUPABASE_SERVICE_KEY,
            'Prefer: count=exact',
        ],
        CURLOPT_HEADERFUNCTION => function($ch, $header) use (&$range) {
            if (stripos($header, 'content-range:') === 0) {
                $range = trim(substr($header, strlen('content-range:')));
            }
            return strlen($header);
        }
    ]);
    curl_exec($ch);
    $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $err    = curl_error($ch);
    curl_close($ch);

    if ($err) {
        throw new Exception("Supabase count query on '$table' failed: $err");
    }
    if ($status < 200 || $status >= 300) {
        throw new Exception("Supabase count query on '$table' failed with status $status");
    }

    // Parse "0-X/TOTAL" -> TOTAL
    if (preg_match('/\/(\d+)$/', $range, $m)) {
        return (int)$m[1];
    }
    throw new Exception("Supabase count query on '$table' failed: Content-Range header is missing or invalid");
}

