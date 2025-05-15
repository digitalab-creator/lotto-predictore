<?php
session_start();
$config = require __DIR__ . '/config.php';

// Arrr, praise be to the Flying Spaghetti Monster for secure code!
if (!isset($_SESSION['logged_in']) || $_SESSION['logged_in'] !== true) {
    header('Location: login.php');
    exit;
}

function log_error($msg) {
    $logfile = __DIR__ . '/../logs/app.log';
    $entry = date('Y-m-d H:i:s') . " | $msg\n";
    file_put_contents($logfile, $entry, FILE_APPEND);
}

$fromDate = $toDate = '';
$results = $error = '';
$strong = '';
$commonNumbers = [];
$commonStrong = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // Sanitize and validate input
    $fromDate = isset($_POST['fromDate'][0]) ? trim($_POST['fromDate'][0]) : '';
    $toDate = isset($_POST['toDate'][0]) ? trim($_POST['toDate'][0]) : '';
    if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $fromDate) || !preg_match('/^\d{4}-\d{2}-\d{2}$/', $toDate)) {
        $error = 'Arrr! Invalid date format, matey!';
        log_error('Invalid date input: ' . $fromDate . ' to ' . $toDate);
    } else {
        // Fetch data from API
        $apiUrl = "https://paisapi.azurewebsites.net/lotto/byDates/$toDate/$fromDate";
        $apiResponse = @file_get_contents($apiUrl);
        if ($apiResponse === false) {
            $error = 'Arrr! Could not fetch data from the API. The seas be stormy!';
            log_error('API fetch failed: ' . $apiUrl);
        } else {
            $data = json_decode($apiResponse, true);
            if (!is_array($data)) {
                $error = 'Arrr! The API returned no loot.';
                log_error('API returned invalid JSON: ' . $apiUrl);
            } else {
                // Analyze numbers
                $allNumbers = [];
                $strongNumbers = [];
                foreach ($data as $roll) {
                    if (isset($roll['winNumbers']) && is_array($roll['winNumbers'])) {
                        $allNumbers = array_merge($allNumbers, $roll['winNumbers']);
                    }
                    if (isset($roll['strongNumber'])) {
                        $strongNumbers[] = $roll['strongNumber'];
                    }
                }
                // Find 6 most common numbers
                $counts = array_count_values($allNumbers);
                arsort($counts);
                $commonNumbers = array_slice(array_keys($counts), 0, 6);
                // Find most common strong number
                $strongCounts = array_count_values($strongNumbers);
                arsort($strongCounts);
                $commonStrong = key($strongCounts);
                $results = 'The most common numbers in the date range are: ' . implode(', ', $commonNumbers);
                $strong = 'Strong number: ' . $commonStrong;
            }
        }
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Pirate Lotto Analyzer</title>
<style>
.demo {
    border:1px solid #C0C0C0;
    border-collapse:collapse;
    padding:5px;
}
.demo th {
    border:1px solid #C0C0C0;
    padding:5px;
    background:#F0F0F0;
}
.demo td {
    border:1px solid #C0C0C0;
    padding:5px;
}
body { font-family: monospace; background: #222; color: #eee; }
.container { max-width: 700px; margin: 2em auto; background: #333; padding: 2em; border-radius: 8px; }
input, button { font-family: monospace; }
.error { color: #ff6666; }
.success { color: #66ff66; }
.logout { float: right; }
</style>
</head>
<body>
<div class="container">
    <a href="logout.php" class="logout">Logout</a>
    <h1>Pirate Lotto Analyzer</h1>
    <form method="POST" action="index.php">
        <div id="fromDateBox" >
            <label for="fromDate">מתאריך (from date)</label>
            <input type="date" id="fromDate" name="fromDate[]" value="<?php echo htmlspecialchars($fromDate ?: '1960-01-01'); ?>" required>
        </div>
        <div>
            <label for="toDate">עד תאריך (to date)</label>
            <input type="date" id="toDate" name="toDate[]" value="<?php echo htmlspecialchars($toDate ?: date('Y-m-d')); ?>" required>
        </div>
        <div>
            <button id="Filter">הצג (Show)</button>
        </div>
    </form>
    <br>
    <?php if ($error): ?>
        <div class="error"><?php echo htmlspecialchars($error); ?></div>
    <?php elseif ($results): ?>
        <div class="success"><?php echo htmlspecialchars($results); ?><br><?php echo htmlspecialchars($strong); ?></div>
        <form method="POST" action="mail.php">
            <input type="hidden" name="mostCommonNumsn" value="<?php echo htmlspecialchars(implode(', ', $commonNumbers)); ?>">
            <input type="hidden" name="mailStrong" value="<?php echo htmlspecialchars($commonStrong); ?>">
            <button type="submit">Send Results by Parrot Mail</button>
        </form>
    <?php endif; ?>
</div>
</body>
</html>
