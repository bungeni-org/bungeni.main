var timeline_mapping = {
    "default":{
        x_unit: "day",
        x_step: 1,
        x_size: 7,
        x_start: 0,
        x_date:"%l, %j %M",
    },
    "month":{
        x_unit:"day",
        x_step: 1,
        x_size: 31,
        x_start: 0,
        x_date: "%j",
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
        x_date:"%D, %j-%M %h%a",
    }
}

var Y_PROPERTY_MAPPING = {
    venues: "venue",
    combined: "group_id"
}

/**
 * @function show_notification
 * @description renders a notification that blocks the ui momentarily
 **/
var show_notification = function(message){
        $.blockUI({
            message: message,
            css: { 
                border: 'none', 
                padding: '15px', 
                backgroundColor: '#773F3B', 
                '-webkit-border-radius': '10px', 
                '-moz-border-radius': '10px', 
                opacity: .7, 
                color: '#fff' 
            },
            timeout: 3000,
            baseZ: 20000,
            showOverlay: true,
         });
}

/**
 * @function handle_before_change_view
 * @description Handler for scheduler's onBeforeViewChange event
 *  Determines the scope and render mode of timeline views whenever
 *  there is a switch to a timeline view. Switching to the combined 
 *  timeline loads events from all committees.
 */
function handle_before_change_view(old_mode, old_date, new_mode , new_date){
    var VENUES_MODE = "venues";
    var COMBINED_MODE = "combined";
    if (((new_mode == VENUES_MODE) && (old_mode != VENUES_MODE))
        || 
        ((new_mode == COMBINED_MODE) && (old_mode != COMBINED_MODE))
    ){
        if (new_mode == COMBINED_MODE){
            //load group events to current scheduler instance
            load_groups_events();
        }
        scheduler.clear_view(new_mode);
        mapping = timeline_mapping[old_mode]
        if (mapping == undefined){
            mapping = timeline_mapping.default
            scheduler._min_date = scheduler.date.week_agenda_start(new Date());
        }else{
            scheduler._min_date = scheduler.date[old_mode + "_start"](new Date());
        }
        scheduler.createTimelineView({
            name : new_mode,
            x_unit: mapping.x_unit,
            x_date: mapping.x_date,
            x_step: mapping.x_step,
            x_size: mapping.x_size,
            x_start: mapping.x_start,
            y_unit: timeline_data[new_mode],
            y_property: Y_PROPERTY_MAPPING[new_mode],
            render: "bar"
        });
        
        var min_date_getter = (scheduler.date[old_mode+"_start"] ||
            scheduler.date.week_agenda_start
        )
        scheduler.date[new_mode + "_start"] = min_date_getter;
    }
    
    return true;
}

/**
 * @function event_save_handler
 * @description Handler for scheduler's onEventSave event.
 *  Perform validation of entered data and determine if the event editor 
 *  will be closed.
 */
function event_save_handler(id, data, is_new_event){
    delete scheduler._dataprocessor._in_progress[id];
    var error_messages = 0;
    for (field_index in cal_globals.required_fields){
        field_name = cal_globals.required_fields[field_index];
        data_value = data[field_name];
        if (data_value == undefined || data_value == ""){
            error_messages += 1;
            $("tr[rel='"+ field_name +"']", 
                $("div.dhx_cal_light")).addClass("scheduling_input_error");
        }
    }
    if (error_messages > 0){
        show_notification(calendar_globals.errors_scheduler);
        return false;
    }
    event = scheduler.getEvent(id)
    event.color="";
    scheduler.updateEvent(id);
    scheduler.templates.event_text = render_event_text;
    return  true;
}

/**
 * @function collission_handler
 * @description show event collission notice only if the colliding event is 
 * a sitting
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

/**
 * @function handle_lightbox
 * @description handle show lightbox event - not displayed for sessions 
 */
function handle_lightbox(event_id){
    if (event_id != null){
        //only block for existing events (with ids)
        event = scheduler.getEvent(event_id);
        if (event.event_type=="session"){
            return false;
        }
    }
    $("tr", $("div.dhx_cal_light")).removeClass("scheduling_input_error");
    return true;
}

/**
 * @function render_event_url
 * @description Return link to event.
 */
function render_event_url(event){
    //get actual event id
    ev_id = event.id.split("-").pop();
    url = cal_globals.view_url + "/sittings/obj-" + ev_id + "/view";
    return ("&nbsp;<a class='quick-view' href='" + url + "'>" + 
        cal_globals.text_view + "</a>&nbsp;");
}

/**
 * @function render_event_text
 * @description render event text - including link to sitting for sittings 
 * with status
 */
function render_event_text(start, end, event){
    text = event.text;
    var status = event["status"];
    if(status){
        text = text + render_event_url(event)
    }
    return text;
}

/**
 * @function render_event_bar_text
 * @description render event bar text - including link to sitting for sittings 
 * with status
 */
function render_event_bar_text(start, end, event){
    text = event.text;
    var status = event["status"];
    if(status){
        text = render_event_url(event) + event.text
    }
    return text;
}


/**
 * @function re_render_event
 * @description Force re-rendering of an event whose ID has changed
 * Forces re-display of elements.
 */
function re_render_event(old_id, new_id){
    event = scheduler.getEvent(new_id);
    event["status"] = "sitting";
    scheduler.clear_event(new_id);
    if (scheduler._table_view){
        scheduler.render_event_bar(event);
    }else{
        scheduler.render_event(event);
    }
}

/**
 * @function refresh_events
 * @description - force refresh of calendar after adding a recurring event
 * ensures db ids are loaded client-side
 */
function refresh_events(old_id, new_id){
    //#!+SCHEDULER_REFRESH(mb, Jan-2013) - Find a way to do this gracefully.
    event = scheduler.getEvent(new_id);
    if (event.rec_type!="none"){
        scheduler.clearAll();
        scheduler.load(scheduler._load_url);
    }
}


/**
 * @function event_type_class
 * @description return custom style for each event type
 */
function event_type_class(start, end, event){
    return "scheduler_event_" + event.event_type;
}

/**
 * @function row_marked
 * @description handler for a 'row marked' event following an update
 * we display a message highlighting sittings(events) on calendar requiring
 * attention
 */
function row_marked(id, state, mode, invalid){
    if(invalid){
        show_notification(cal_globals.error_messages[mode] || 
            cal_globals.error_messages.default);
    }
    return true;
}

/**
 * @function scheduler_resized
 * @description applies a zIndex to calendar dom element when maximized
 * ensuring scheduler is rendered above all elements
 */
function scheduler_resized(){
    dom_el = scheduler._obj;
    if (scheduler.expanded){
        dom_el.style.zIndex=1000;
    }else{
        dom_el.style.zIndex="";
    }
    return true;
}


session_events = new Array();
/**
 * @method event_loading
 * @description fires when loading an event (store all sessions)
 **/
function event_loading(event){
    if (event.event_type=="session"){
        session_events.push(event);
    }
    return true;
}

/**
 * @function reset_sessions
 * @description reset sessions array
 **/
function reset_sessions(){
    session_events = new Array();
}


/**
 * @function block_span
 * @description block timespan on scheduler
 **/
 function block_span(start_date, end_date){
    scheduler.addMarkedTimespan({
        start_date: start_date,
        end_date: end_date,
        css: "gray_section",
        type: "dhx_time_block",
        zones: "fullday"
    });
}
 
/**
 * @function block_times
 * @description limit event adding to sessions
 **/
function block_times(){
    scheduler.deleteMarkedTimespan();
    end_date = null;
    last_index = session_events.length-1;
    prev_end_date = null;
    for (index in session_events){
        session = session_events[index];
        start_date = null;
        if(index == 0){
            start_date = scheduler.date.add(scheduler._date, -1, "year");
            end_date = session.start_date;
            scheduler.config.limit_start = session.start_date;
        } else {
            start_date = scheduler.date.add(prev_end_date, 1, "day");
            end_date = session.start_date;
        }
        prev_end_date = session.end_date;
        block_span(start_date, end_date);
        if (index == last_index){
            start_date = scheduler.date.add(session.end_date, 1, "day");
            end_date = scheduler.date.add(scheduler._date, 1, "year");
            scheduler.config.limit_end = session.end_date;
            block_span(start_date, end_date);
        }
    }
    scheduler.updateView();
}
