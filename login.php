<?php
session_start();
$config = require __DIR__ . '/config.php';

// Debug logging for FSM's noodly wisdom
$logfile = __DIR__ . '/logs/app.log';
function pirate_log($msg) {
    global $logfile;
    file_put_contents($logfile, date('Y-m-d H:i:s') . " | $msg\n", FILE_APPEND);
}

pirate_log('ENV USER: ' . getenv('PIRATE_APP_USERNAME'));
pirate_log('ENV HASH: ' . getenv('PIRATE_APP_PASSWORD_HASH'));
pirate_log('CONFIG USER: ' . $config['username']);
pirate_log('CONFIG HASH: ' . $config['password']);
pirate_log('Dotenv loaded: ' . (class_exists('Dotenv\\Dotenv') ? 'yes' : 'no'));
pirate_log('Current DIR: ' . __DIR__);
pirate_log('ENV FILE EXISTS: ' . (file_exists(__DIR__ . '/.env') ? 'yes' : 'no'));

if (isset($_SESSION['logged_in']) && $_SESSION['logged_in'] === true) {
    header('Location: index.php');
    exit;
}

$error = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $username = isset($_POST['username']) ? trim($_POST['username']) : '';
    $password = isset($_POST['password']) ? $_POST['password'] : '';
    pirate_log('LOGIN ATTEMPT: username=' . $username);
    $verify = password_verify($password, $config['password']);
    pirate_log('password_verify result: ' . ($verify ? 'true' : 'false'));
    if ($username === $config['username'] && $verify) {
        session_regenerate_id(true);
        $_SESSION['logged_in'] = true;
        pirate_log('LOGIN SUCCESS for user: ' . $username);
        header('Location: index.php');
        exit;
    } else {
        $error = 'Arrr! Wrong username or password, ye scallywag!';
        pirate_log('LOGIN FAIL for user: ' . $username);
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Pirate Login</title>
    <style>
        body { font-family: monospace; background: #222; color: #eee; }
        .login-box { max-width: 400px; margin: 100px auto; padding: 2em; background: #333; border-radius: 8px; box-shadow: 0 0 10px #000; }
        label, input { display: block; width: 100%; margin-bottom: 1em; }
        input[type="submit"] { background: #007bff; color: #fff; border: none; padding: 0.5em; border-radius: 4px; cursor: pointer; }
        .error { color: #ff6666; }
    </style>
</head>
<body>
    <div class="login-box">
        <h2>Login to the Pirate Lotto App</h2>
        <?php if ($error): ?>
            <div class="error"><?php echo htmlspecialchars($error); ?></div>
        <?php endif; ?>
        <form method="POST">
            <label for="username">Username</label>
            <input type="text" id="username" name="username" required autofocus>
            <label for="password">Password</label>
            <input type="password" id="password" name="password" required>
            <input type="submit" value="Hoist the Sails!">
        </form>
    </div>
</body>
</html> 