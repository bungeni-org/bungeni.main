var venues_timeline_mapping = {
    "default":{
        x_unit: "hour",
        x_step: 6,
        x_size: 20,
        x_start: 1,
        x_date:"%j%a",
    },
    "month":{
        x_unit:"day",
        x_step: 1,
        x_size: 31,
        x_start: 0,
        x_date: "%d-%M",
    },
    "week":{
        x_unit:"day",
        x_step: 1,
        x_size: 7,
        x_start: 0,
        x_date: "%l, %j %M",
    },
    "year":{
        x_unit: "month",
        x_step: 1,
        x_size: 12,
        x_start: 0,
        x_date: "%M %Y",
    },
    "day":{
        x_unit: "hour",
        x_step: 4,
        x_size: 6,
        x_start: 1,
        x_date:"%D, %j%a",
    }
}

/*
 *  Handler for scheduler's onBeforeViewChange event
 *  
 *  Determines the scope and render mode of venues timeline view whenever
 *  the intent is to switch to display to venues.
 */
function handle_before_change_view(old_mode, old_date, new_mode , new_date){
    if ((new_mode == "venues") && (old_mode != "venues") ){
        scheduler.clear_view("venues");
        mapping = venues_timeline_mapping[old_mode]
        if (mapping == undefined){
            mapping = venues_timeline_mapping.default
            scheduler._min_date = scheduler.date.agenda_start(new Date());
        }else{
            scheduler._min_date = scheduler.date[old_mode + "_start"](new Date());
        }
        scheduler.createTimelineView({
            name : "venues",
            x_unit: mapping.x_unit,
            x_date: mapping.x_date,
            x_step: mapping.x_step,
            x_size: mapping.x_size,
            x_start: mapping.x_start,
            y_unit: venues_data,
            y_property: "venue",
            render: "bar"
        });
        
        var min_date_getter = (scheduler.date[old_mode+"_start"] ||
            scheduler.date.agenda_start
        )
        scheduler.date.venues_start = min_date_getter;
    }
    return true;
}

/*
 *  Handler for scheduler's onEventSave event
 *  
 *  Perform validation of entered data and determine if the event editor 
 *  will be closed.
 */
function event_save_handler(id, data, is_new_event){
    var error_messages = new Array();
    //#!I18N(mb, oct-2011) Enable proper I18N of error messages
    if ((data.venue=="") || (data.venue==undefined)){
        error_messages.push("Venue : Select a venue");
    }
    if ((data.language=="") || (data.language==undefined)){
        error_messages.push("Language : Select a language");
    }
    if (error_messages.length > 0){
        html_errors = $("<ul style='text-align:justify;margin:5px;'/>");
        html_errors.append("<h2>Make Corrections</h2>");
        for (error_key in error_messages){
            html_errors.append("<li>" + error_messages[error_key] + "</li>");
        }
        html_errors.append('<input type="button" value="Okay" onclick="javascript:$.unblockUI();"/>');
        html_errors.wrap("<div/>");
        $.blockUI({
            message: html_errors.html(),
            css: {backgroundColor: "#FFF", padding: "20px;", fontSize: "110%",
                borderColor: "#F45E4D", color: "#F45E4D"
            },
            timeout: 3000,
            showOverlay: true,
            baseZ: 20000,
        });
        return false;
    }
    return  true;
}

function event_collission_handler(ev, evs){
    return !confirm(
        "This timeslot already has another event.\n Do you want to continue?"
    );
}
