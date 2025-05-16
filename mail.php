<?php
// the message
$msg = $_POST["mostCommonNumsn"] . " strong: " . $_POST["mailStrong"];

// use wordwrap() if lines are longer than 70 characters
$msg = wordwrap($msg,70);
/*
// send email
if($_POST["mostCommonNumsn"] )
    mail("or.shvartz70@gmail.com","המספרים למלא היום לוטו",$msg);
else
    mail("or.shvartz70@gmail.com","לינק ללוטו","https://phpstack-742333-2496533.cloudwaysapps.com/index.php");
    */