<?php
session_start();
$config = require __DIR__ . '/config.php';

// Arrr, praise be to the Flying Spaghetti Monster for secure code!
function log_error($msg) {
    $logfile = __DIR__ . '/logs/app.log';
    $entry = date('Y-m-d H:i:s') . " | $msg\n";
    file_put_contents($logfile, $entry, FILE_APPEND);
}

if (!isset($_SESSION['logged_in']) || $_SESSION['logged_in'] !== true) {
    http_response_code(403);
    echo 'Arrr! Ye be not logged in!';
    exit;
}

$nums = isset($_POST['mostCommonNumsn']) ? trim($_POST['mostCommonNumsn']) : '';
$strong = isset($_POST['mailStrong']) ? trim($_POST['mailStrong']) : '';

if (!$nums || !$strong) {
    log_error('Missing numbers or strong number in mail.php');
    echo 'Arrr! Missing numbers, matey!';
    exit;
}

// Sanitize
$nums = htmlspecialchars($nums, ENT_QUOTES, 'UTF-8');
$strong = htmlspecialchars($strong, ENT_QUOTES, 'UTF-8');

$msg = $nums . " strong: " . $strong;
$msg = wordwrap($msg, 70);

$to = $config['email'];
$subject = 'המספרים למלא היום לוטו';
$from = 'pirate@yourdomain.com';
$apiKey = $config['elastic_api_key'];

// Prepare Elastic Email API request
$postData = [
    'apikey' => $apiKey,
    'from' => $from,
    'to' => $to,
    'subject' => $subject,
    'bodyText' => $msg,
    'isTransactional' => true
];

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, 'https://api.elasticemail.com/v2/email/send');
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, http_build_query($postData));
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$curlError = curl_error($ch);
curl_close($ch);

if ($httpCode == 200 && strpos($response, 'success') !== false) {
    echo 'Arrr! Parrot mail sent successfully via Elastic Email!';
} else {
    log_error('Elastic Email sending failed: HTTP ' . $httpCode . ' | Response: ' . $response . ' | Error: ' . $curlError);
    echo 'Arrr! Failed to send parrot mail via Elastic Email!';
}