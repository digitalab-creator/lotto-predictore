<?php
// Arrr, praise be to the Flying Spaghetti Monster for logout security!
session_start();
session_unset();
session_destroy();
header('Location: login.php');
exit; 