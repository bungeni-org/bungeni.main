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
    delete scheduler._dataprocessor._in_progress[id];
    var error_messages = new Array();
    //#!I18N(mb, apr-2012) Bind validation to zope form
    if ((data.venue=="") || (data.venue==undefined)){
        error_messages.push(calendar_globals.venue_required);
    }
    if ((data.language=="") || (data.language==undefined)){
        error_messages.push(calendar_globals.language_required);
    }
    if (error_messages.length > 0){
        html_errors = $("<ul style='text-align:justify;margin:5px;'/>");
        html_errors.append("<h2>" + calendar_globals.errors_title + "</h2>");
        for (error_key in error_messages){
            html_errors.append("<li>" + error_messages[error_key] + "</li>");
        }
        html_errors.append('<input type="button" value="' 
            + calendar_globals.message_okay 
            + '" onclick="javascript:$.unblockUI();"/>'
        );
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
    event = scheduler.getEvent(id)
    event.color="";
    scheduler.updateEvent(id);
    scheduler.templates.event_text = render_event_text;
    return  true;
}

/**
 * show event collission notice only if the colliding event is a sitting
 */
function collission_handler(ev, evs){
    var collission = false;
    for (index in evs){
        if (evs[index].event_type == "sitting"){
            collission = true;
            break
        }
    }
    if (collission){ return !confirm(calendar_globals.error_collission); }
    return false;
}

function handle_lightbox(event_id){
    event = scheduler.getEvent(event_id);
    if (event.event_type=="session"){
        return false;
    }
    return true;
}

/**
 * render event text - including link to sitting for sittings with status
 */
function render_event_text(start, end, event){
    text = event.text;
    var status = event["status"];
    if(status){
        url = cal_globals.view_url + "/sittings/obj-" + event.id + "/view";
        text = text + "<br /><a class='quick-view' href='" + url + "'>" + cal_globals.text_view + "</a>";
    }
    return text;
}

/**
 * Force re-rendering of an event whose ID has changed
 * Forces re-display of elements.
 */
function re_render_event(old_id, new_id){
    event = scheduler.getEvent(new_id);
    event["status"] = "sitting";
    scheduler.clear_event(new_id);
    scheduler.render_event(event);
}
