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
