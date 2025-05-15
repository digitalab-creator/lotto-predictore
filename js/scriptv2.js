//תזכורת - לפתח פונקציה שמציגה את המספרים שאף פעם לא הופיעו בטווח מסוים
$(document).ready(function() 
{
	var fromdate = document.getElementById("fromdate").innerText;
	var todate = document.getElementById("todate").innerText;
	fromdate = jQuery("#fromDate").attr("value");
	todate = jQuery("#toDate").attr("value");
	//var howManyNums=6;
	//var howManyStrongs = 1;
	//var howManyTables = 1;
	var total_numbers_of_all_rolls = 0;
	todate = todate.replace(/\s/g, '');
	fromdate = fromdate.replace(/\s/g, '');
	const date1 = new Date('December 17, 1995 03:24:00');
    //get all results for date range
	$.ajax(
	{
        	url: "https://paisapi.azurewebsites.net/lotto/byDates/"+todate+"/"+fromdate,
    }).then(function(data) 
	{
		//const allNumbers = [1, 2, 3, 4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37];
		//var countArray= [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0];
		//var countStrong= [0,0,0,0,0,0,0];
		//var strongNums = [1,2,3,4,5,6,7];
		//var total_correct_numbers=0;
        var long_array_from_rolls=[];
        var   strong_array=[];
        //var num_of_rolls= data.length;
        //merge all winninw numbers to one array
        data.forEach(function(win_array)
        {
            strong_array.push(win_array.strongNumber);
            win_array = win_array.winNumbers;
            long_array_from_rolls.push(win_array);
        });
        var  common_winning_nums=[];
        var merged = [].concat.apply([],  long_array_from_rolls);
        var merged_duplicate=merged;
        var common_strong_nums=[];
        //get the 6 most common winning numbers
        for(i=0;i<6;i++)
        {
            let common_num = get_common_number(merged_duplicate);
            common_winning_nums.push(common_num);
            removeItem(merged_duplicate,common_num);
        }
        for(i=0;i<1;i++)
        {
            let common_strong_num = get_common_number(strong_array);
            common_strong_nums.push(common_strong_num);
            removeItem(strong_array,common_strong_num);
        }
        //get the common strong num
        let common_strong_num = get_common_number(strong_array);
        //add numbers to front
        $('#strong').append(common_strong_nums);
      	$('#numbers').append("<br> table 1: " + common_winning_nums  );
        //send mail
		const mailNums = common_winning_nums  ;
		const mailStrong = common_strong_num;
		jQuery.ajax 
        ({
		    url: 'mail.php',
			type:'POST',
			data:'mostCommonNumsn='+mailNums+'&mailStrong='+mailStrong,
			success:function(results) 
			{
				//find the total winnin number from all rolls and calculate percent
				var total_count_winning=0;
                total_numbers_of_all_rolls =  data.length*6;
				data.forEach(function(win_array)
				{
					win_array = win_array.winNumbers;
					var filteredArray = win_array.filter(value =>   common_winning_nums.includes(value));
					total_count_winning = total_count_winning + filteredArray.length;

                    if(win_array.sort().join(',')=== common_winning_nums.sort().join(',')){
                        alert('same members');
                    }
                  //  else alert('not a match');
				});
				let percent = (total_count_winning/total_numbers_of_all_rolls)*100;
				console.log("total count winnings " + total_count_winning + "of"+ total_numbers_of_all_rolls + "which are " +  (Math.round(percent * 100) / 100).toFixed(2) + "%"  );
            } 
        });
   	});	
});

function get_common_number(array)
{
    if(array.length == 0)
        return null;
    var modeMap = {}; 
    var maxEl = array[0], maxCount = 1;
    for(var i = 0; i < array.length; i++)
    {
        // for each value in array - set count to 1 or add 1 to existing count
        var el = array[i];
        if(modeMap[el] == null)
            modeMap[el] = 1;
        else
            modeMap[el]++;  
        // if the new count is bigger than make maxEL to the most occuring num    
        if(modeMap[el] > maxCount)
        {
            maxEl = el;
            maxCount = modeMap[el];
        }
    }
    return maxEl;
}

function removeItem(array, item) {
    var i = array.length;

    while (i--) {
        if (array[i] === item) {
            array.splice(array.indexOf(item), 1);
        }
    }
}