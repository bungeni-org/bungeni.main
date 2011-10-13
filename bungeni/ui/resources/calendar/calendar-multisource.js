/* Load multiple calendars from sources based on selected checkbox
 * of available calendars.
 */
var loaded_calendars = Array();
var edit_mode_turned_off = false;
$(document).ready(function(){
    $("input", $("#select-calendars")).change(
        function(){
            if (!scheduler.config.readonly){
                scheduler.config.readonly = true;
                edit_mode_turned_off = true;
            }
            if (loaded_calendars.length==0){
                loaded_calendars.push(scheduler._load_url);
            }
            var ev_color = $(this).attr("rel");
            var cal_url = $(this).val();
            var is_checked = $(this).attr("checked");
            cal_url = cal_url + "/dhtmlxcalendar?uid=" + scheduler.uid() + "&amp;color=" + ev_color;
            if (is_checked){
                if (loaded_calendars.indexOf(cal_url) < 1){
                    loaded_calendars.push(cal_url);
                    scheduler._loaded = {};
                    scheduler.load(cal_url);
                }
            }else{
                loaded_calendars.pop(cal_url);
                if (loaded_calendars.length > 0){
                    scheduler.clearAll();
                    for (cal_id=0; cal_id<loaded_calendars.length; cal_id++){
                        scheduler._loaded = {};
                        scheduler.load(loaded_calendars[cal_id]);
                    }
                }
                if ((loaded_calendars.length == 1) && (edit_mode_turned_off)){
                    scheduler.config.readonly = false;
                }
            }
        }
    );
});
