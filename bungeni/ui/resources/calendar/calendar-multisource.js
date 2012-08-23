/* Load events from multiple sources into same dhtmxscheduler
 */
var loaded_calendars = Array();
var edit_mode_turned_off = false;

/**
 * We load events when the committees timeline view is selected 
 */
var load_groups_events = function(){
    if (loaded_calendars.length>0){
        return;
    }
    loaded_calendars.push(scheduler._load_url);
    if (!scheduler.config.readonly){
        scheduler.config.readonly = true;
        edit_mode_turned_off = true;
    }
        
    for (index=0; index < group_urls.length; index++){
        ev_color = group_urls[index].color;
        cal_url = group_urls[index].url;
        cal_url = (cal_url + "/dhtmlxcalendar?uid=" + scheduler.uid() + 
            "&amp;color=" + ev_color
        );
        scheduler._loaded = {};
        scheduler.load(cal_url);
        loaded_calendars.push(cal_url);
    }
    if ((loaded_calendars.length == 1) && (edit_mode_turned_off)){
        scheduler.config.readonly = false;
    }
}
