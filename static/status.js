function getStatus(endpoint,task_id) {
//function getStatus(endpoint) {
    var full_endpoint = endpoint + '/' + task_id;
    console.log(endpoint);
    // first start the timer if it is not already running
    if(null == window.statusTimer) {
        //alert("Starting the timer");
        window.statusTimer = setInterval(function(){getStatus(endpoint,task_id);},500);
        window.progressBar = new ProgressBar("my-progressbar", {'width':'100px', 'height':'4px'});
        window.progressBar.setPercent(0);
    }
    /*else {
        alert("Timer running");
    }*/
    var statusDiv = $("div.status");
    $.get(full_endpoint).done(function(showStatus) {
        // totalRows, curRow are returned
        var state = showStatus['state'];
        var totalRows = showStatus['total'];//showStatus['totalRows'];
        var curRow = showStatus['current'];//curRow'];
        //var uuid = showStatus['uuid'];
        var uuid = task_id;
        var warnings = showStatus['warnings'];
        console.log('State: ' + state);
        console.log('Total: ' + totalRows);
        console.log('Current: ' + curRow);
        console.log('Num Warnings: ' + warnings.length);
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
                //statusDiv.text("Processing row "+curRow+" of "+totalRows);
                window.progressBar.setPercent(prog);
            }
            else {
                window.progressBar.setPercent(100);
                clearInterval(window.statusTimer);
                //window.location = "/";
                var index;
                var txt = "Processing complete.";
                txt = txt + " Your results will be downloaded as:<br/><br/>";
                txt = txt + task_id + ".csv<br/><br/>";
                txt = txt + "Return <a href='/'>home</a><br/>";
                statusDiv.html(txt)
                if(endpoint=="/predictionstatus")
                {
                    setTimeout(function(){window.location="/getpredictions/"+uuid+".csv";},2000);
                }
                else
                {
                    setTimeout(function(){window.location="/getfile/"+task_id+".csv";},2000);
                }
            }
        }
    }).fail(function() {
        //tr.text("{{ _('Error: Could not contact server.') }}");
        //cr.hide();
        //tr.show();
    });
    //return false; // always return true to submit the form
}

function fade() {
    if($("div.options").is(":visible"))
    {
        $("div.options").fadeOut();
    }
    else
    {
        $("div.options").fadeIn();
    }
}
