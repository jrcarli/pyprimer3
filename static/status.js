function getStatus(endpoint,myfunc,task_id) {
    var full_endpoint = endpoint + '/' + myfunc + '/' + task_id;
    console.log(endpoint);
    console.log(full_endpoint);
    // first start the timer if it is not already running
    if(null == window.statusTimer) {
        window.statusTimer = setInterval(function(){getStatus(endpoint,myfunc,task_id);},500);
        $("div.progress-bar").css("width", "0%").attr("aria-valuenow", 0);
        $("div.progress-bar").text("0%");
    }
    var statusDiv = $("#status");
    $.get(full_endpoint).done(function(showStatus) {
        // totalRows, curRow are returned
        var state = showStatus['state'];
        var totalRows = showStatus['total'];//showStatus['totalRows'];
        var curRow = showStatus['current'];//curRow'];
        var warnings = showStatus['warnings'];
        /*console.log('State: ' + state);
        console.log('Total: ' + totalRows);
        console.log('Current: ' + curRow);
        console.log('Num Warnings: ' + warnings.length);*/
        if(warnings.length <= 0)
        {
            $("div.ajaxflash").hide();
        }
        else
        {
            var curTxt = "";
            for(var w=0; w<warnings.length; w++)
            {
                $("div.ajaxflash").hide();
                //curTxt = $("div.ajaxflash").text();
                curTxt += warnings[w] + "<br/>";
                //curTxt += warnings + "<br/>";
                $("div.ajaxflash").html(curTxt);
                $("div.ajaxflash").show();
                //$("div.flash").text(warnings[w]);
                //alert(warnings[w]);
            }
        }

        if(totalRows != '0')
        {
            if(curRow != totalRows) {
                var prog = (curRow / totalRows) * 100;
                $("div.progress-bar").css("width", prog+"%").attr("aria-valuenow", prog);
                $("div.progress-bar").text(prog+"%");
            }
            else {
                $("div.progress-bar").css("width", "100%").attr("aria-valuenow", 100);
                $("div.progress-bar").text("100%");

                $("div.progress-bar").removeClass("active");
                //$("div.progress-bar").removeClass("progress-bar-striped");
                $("div.finalmessage").removeClass("hidden");
                clearInterval(window.statusTimer);
                /*var txt = "Processing complete.";
                txt = txt + " Your results will be downloaded as:<br/><br/>";
                txt = txt + task_id + ".csv<br/><br/>";
                txt = txt + "Return <a href='/'>home</a><br/>";
                statusDiv.html(txt)*/

                if(endpoint=="/predictionstatus")
                {
                    setTimeout(function(){window.location="/getpredictions/"+task_id+".csv";},2000);
                }
                else
                {
                    setTimeout(function(){window.location="/getfile/"+task_id+".csv";},2000);
                }
            }
        }
    }).fail(function() {
    });
    //return false; // always return true to submit the form
}
