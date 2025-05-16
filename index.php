<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Cloudways PHP Hosting</title>
</head>
<body>
	<?php
  		echo "showing" . "<h1 id='fromdate'>" . $_POST["fromDate"][0] . "</h1>"   ;
 		echo "to". "<h1 id='todate'>" . $_POST["toDate"][0] . "</h1> - "   ;
  	?> 
	<br>
	<p id="numbers">the most common numbers in the date range are: </p>
	<br>
	<p id="strong">strong number:  </p>
	<form method="POST" action="index.php">
        	<div id="fromDateBox" >
         		<label for="fromDate">מתאריך</label>
			<!--input type="date" id="fromDate" name="fromDate[]" value=" <?php echo $_POST["fromDate"][0]    ?>"-->
				<input type="date" id="fromDate" name="fromDate[]" value="1960-01-01">

		</div>
            		<div >
         			<label for="toDate">עד תאריך</label>
			<input type="date" id="toDate" name="toDate[]" value="<?php echo date('Y-m-d') ?>" >
			<!--input type="date" id="toDate" name="toDate[]" value="" -->

		</div>
            		<div>
           			<button id="Filter">הצג</button>
            		</div>
		</form>

	<br><br><br><br><br><br><br><br><br><br>
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
</style>
<table class="range">
	<caption>range</caption>
	<thead>
		<tr>
			<th>1</th>
			<th>2</th>
			<th>3</th>
			<th>4</th>
			<th>5</th>
			<th>6</th>
			<th>strong</th>
		</tr>
	</thead>
	<tbody>
	<tr>
		<td></td>
		<td></td>
		<td></td>
		<td></td>
		<td></td>
		<td></td>
	</tr>
	<tr>
		<td></td>
		<td></td>
		<td></td>
		<td></td>
		<td></td>
		<td></td>
	</tr>
	<tr>
		<td></td>
		<td></td>
		<td></td>
		<td></td>
		<td></td>
		<td></td>
	</tr>
	<tr>
		<td></td>
		<td></td>
		<td></td>
		<td></td>
		<td></td>
		<td></td>
	</tr>
	<tr>
		<td></td>
		<td></td>
		<td></td>
		<td></td>
		<td></td>
		<td></td>
	</tr>
	<tr>
		<td></td>
		<td></td>
		<td></td>
		<td></td>
		<td></td>
		<td></td>
	</tr>
	<tr>
		<td></td>
		<td></td>
		<td></td>
		<td></td>
		<td></td>
		<td></td>
	</tr>
	<tbody>
</table>

	<script src="js/libs/jquery.min.js"></script>
  	<script src="js/scriptv2.js"></script>
	  <script src="js/range.js"></script>

	  <script>
		  					jQuery("#filter").trigger("click");	

				setTimeout(() => 
				{

					jQuery("#filter").trigger("click");	
				}, 5000);
	</script>

</body>
</html>
