<?php
// Arrr, here be the config for the pirate app! Praise be to the FSM!

// Try to load .env using vlucas/phpdotenv if available in public_html
if (file_exists(__DIR__ . '/vendor/autoload.php')) {
    require_once __DIR__ . '/vendor/autoload.php';
    if (class_exists('Dotenv\\Dotenv')) {
        $dotenv = Dotenv\Dotenv::createImmutable(__DIR__, null, true);
        $dotenv->load();
        file_put_contents(__DIR__ . '/logs/app.log', date('Y-m-d H:i:s') . " | After Dotenv load, HASH: " . getenv('PIRATE_APP_PASSWORD_HASH') . "\n", FILE_APPEND);
    }
} else {
    // Log a warning if dotenv is not available
    file_put_contents(__DIR__ . '/logs/app.log', date('Y-m-d H:i:s') . " | Dotenv not loaded\n", FILE_APPEND);
}

return [
    'username' => getenv('PIRATE_APP_USERNAME') ?: 'pirate',
    'password' => getenv('PIRATE_APP_PASSWORD_HASH') ?:'$2y$10$X64nyXz3QQ8D2kD7h.r2ZOEy4dkQq/UL//z7WW652ihRdxmZsxSsC',
    'email'    => getenv('PIRATE_APP_EMAIL') ?: 'or.shvartz70@gmail.com',
    'elastic_api_key' => getenv('ELASTIC_API_KEY') ?: '',
]; 