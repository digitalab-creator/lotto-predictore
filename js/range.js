//תזכורת - לפתח פונקציה שמציגה את המספרים שאף פעם לא הופיעו בטווח מסוים
$(document).ready(function() 
{
	var fromdate = document.getElementById("fromdate").innerText;
	var todate = document.getElementById("todate").innerText;
	fromdate = jQuery("#fromDate").attr("value");
	todate = jQuery("#toDate").attr("value");
	todate = todate.replace(/\s/g, '');
	fromdate = fromdate.replace(/\s/g, '');
    //get all results for date range
	$.ajax(
	{
        	url: "https://paisapi.azurewebsites.net/lotto/byDates/"+todate+"/"+fromdate,
    }).then(function(data) 
	{
        var   strong_array=[];
        var range= [[],[],[],[],[],[],];

        //merge all winninw numbers to one array
        data.forEach(function(win_array)
        {
            for(i=0;i<6;i++)
            {
                range[i].push(win_array.winNumbers[i]);

            }
        });
        //console.log(range);
       var range_arr=[];

       for(i=0;i<6;i++)
       {
          // console.log(range[i]);
            let common = get_common_number(range[i]);

           // console.log("common",common);
            let common_range = get_common_range(range[i],3);
            console.log(common_range);
          $('.range tbody tr:nth-of-type('+(i+1)+') td:nth-of-type('+(i+1)+')').append( common);
           range.forEach(function(val)
           {
           removeItem(val, common)

           });  

        }

        //strong
        var strong_array=[];
        data.forEach(function(win_array)
        {

            strong_array.push(win_array.strongNumber);
        });
        //console.log(strong_array);

            let common = get_common_number(strong_array);

             let common_range = get_common_range(strong_array,3);
             console.log("strong" + common_range);
 
 
        

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
function get_common_range(array,count=1)
{
    var com = [];
    var common=null;
    for(var i = 0; i < count; i++)
    {
        common = get_common_number(array)
        com.push(common);
        removeItem(array, common);
   }
    return com;
}

function removeItem(array, item) {
    var i = array.length;

    while (i--) {
        if (array[i] === item) {
            array.splice(array.indexOf(item), 1);
        }
    }
}