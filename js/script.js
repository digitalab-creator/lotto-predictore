//תזכורת - לפתח פונקציה שמציגה את המספרים שאף פעם לא הופיעו בטווח מסוים
$(document).ready(function() 
{
	var fromdate = document.getElementById("fromdate").innerText;
	var todate = document.getElementById("todate").innerText;
	fromdate = jQuery("#fromDate").attr("value");
	todate = jQuery("#toDate").attr("value");
	var howManyNums=6;
	var howManyStrongs = 1;
	var howManyTables = 1;
	var num_of_rolls= 0;
	var total_numbers_of_all_rolls = 0;
	todate = todate.replace(/\s/g, '');
	fromdate = fromdate.replace(/\s/g, '');
	const date1 = new Date('December 17, 1995 03:24:00');
	$.ajax(
	{
        	//url: "https://paisapi.azurewebsites.net/lotto/byDates/2021-06-01/2019-06-01"
        	url: "https://paisapi.azurewebsites.net/lotto/byDates/"+todate+"/"+fromdate
	
    	}).then(function(data) 
	{
		const allNumbers = [1, 2, 3, 4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37];
		var countArray= [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0];
		var countStrong= [0,0,0,0,0,0,0];
		var strongNums = [1,2,3,4,5,6,7];
		var total_correct_numbers=0;
		for(i=0;i<data.length;i++) //for each all the number sets on date range
		{
			num_of_rolls++;
			for(j=0;j<data[i].winNumbers.length;j++) //for every winning number
			{
				for(k=0;k<allNumbers.length;k++) //for every possible number
				{
					if(data[i].winNumbers[j]==allNumbers[k])
					{
						countArray[k]++;
					}
				}
			}
		}
	//	console.log("count" + countArray);
		//console.log("rolls: "+num_of_rolls);
		total_numbers_of_all_rolls =  num_of_rolls *6;
		for(o=0;o<data.length;o++) //for each all the number sets on date range
		{						
			for(q=0;q<strongNums.length;q++) //for every possible strong number
			{ 	
				if(data[o].strongNumber==strongNums[q])
				{
					countStrong[q]++;
				}
			}
		}
		//find the strong number with most occourences
    		strongest = [], r = -1;
		while ( strongNums[++r] ) 
		{ 
  			strongest.push( [ strongNums[r], countStrong[r] ] );
			  console.log(strongest);
		}
		var theStrongest = findIndicesOfMax(countStrong, howManyStrongs );
		//add 1 to each number to fix it
		for (let i = 0; i < theStrongest .length; i++) {
    			theStrongest[i]++;
		}
      		$('#strong').append(theStrongest.join(", "));
		
		//check if strong number is within winning numbers    
    		for( var i = 0; i < countArray.length; i++)
		{ 
    			for( var j = 0; j < theStrongest.length; j++)
			{
        			if ( countArray[i] == theStrongest)
				{ 
            				allNumbers.splice(i, 1); 
        			}
			}
    		}		
			console.log(theStrongest);
		//find the 6 numbers with most occourences
		var mostCommonNums = findCommonNumbers(allNumbers, countArray, howManyNums)
      	$('#numbers').append("<br> table 1: " + mostCommonNums  );
		const mailNums = mostCommonNums;
		const mailStrong = theStrongest;
		  jQuery.ajax ({
			url: 'mail.php',
			type:'POST',
			data:'mostCommonNumsn='+mailNums+'&mailStrong='+mailStrong,

			success:function(results) 
			{
				//find the total winnin number from all rolls and calculate percent
				most_common_arr = mostCommonNums.split(",");
				most_common_arr_num = [];
				most_common_arr.forEach(element => most_common_arr_num.push(parseInt(element)));
				console.log(most_common_arr_num);
				console.log(data.winNumbers);
				var total_count_winning=0;
				data.forEach(function(win_array)
				{
					win_array = win_array.winNumbers;
					for(l=0;l<win_array.length;l++)
					{
						var myIndex = win_array.indexOf('X');
						if (myIndex !== -1) {
							win_array.splice(myIndex, 1);
						}
					}
					var filteredArray = win_array.filter(value => most_common_arr_num.includes(value));
					total_count_winning = total_count_winning + filteredArray.length;

										//check number of total winning
									//	console.log("commo" +  most_common_arr_num.sort() + "win: " + win_array.sort());
					//if( most_common_arr_num.sort().join(',')=== win_array.sort().join(',')){
					//	alert('same members');
					//}
				});
				let percent = (total_count_winning/total_numbers_of_all_rolls)*100;
				console.log("total count winnings " + total_count_winning + "of"+ total_numbers_of_all_rolls + "which are " +  (Math.round(percent * 100) / 100).toFixed(2) + "%"  );



	/*			
const count = {};

for (const element of most_common_arr_num) {
  if (count[element]) {
    count[element] += 1;
  } else {
    count[element] = 1;
  }
}
*/
//console.log(count); // 👉️ 
			}
		});
		var numOfWinnersInDateRange=0;
		var extraStrongNum=0;
		for(i=0;i<data.length;i++) //for each all the number sets on date range
		{
			for(j=0;j<data[i].winNumbers.length;j++) //for every winning number
			{
				for(k=0;k<=howManyNums-1;k++) //		
				{
					if(data[i].winNumbers[j]==mostCommonNums.split(",")[k])
					{
						numOfWinnersInDateRange++;
						data[i].winNumbers.push("X");						
					}
				}
				if(data[i].winNumbers[j]<=7)
				{
					extraStrongNum++;
				}
			}
			if(mostCommonNums.split(",").includes(data[i].strongNumber) ||theStrongest.includes(data[i].strongNumber))
				data[i].winNumbers.push("S");


		}		
   	 });
		
});

function findIndicesOfMax(inp, count) 
{
    var outp = [];
    for (var m = 0; m < inp.length; m++) {
        outp.push(m); // add index to output array
        if (outp.length > count) {
            outp.sort(function(a, b) { return inp[b] - inp[a]; }); // descending sort the output array
            outp.pop(); // remove the last index (index of smallest element in output array)
        }
    }
    return outp;
}
function findCommonNumbers(allNumbers, countArray, howMany)
{
	result = [], l = -1;
	while ( allNumbers[++l] ) 
	{ 
  		result.push( [ allNumbers[l], countArray[l] ] );
	}
	var indices = findIndicesOfMax(countArray, howMany);
	//add 1 to each number to fix it
	indices2 = indices.map(function(item) { 
    		return item + 1; 
	});
	return  indices2.join(", ")
}

