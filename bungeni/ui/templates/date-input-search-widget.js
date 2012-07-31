<script type="text/javascript">(function($) {
        $(document).ready(function() {
                var input = document.createElement("input");
                input.setAttribute("type", "text");
                input.setAttribute("name", "filter_%(field_id)s");
                input.setAttribute("id", "input_%(field_id)s");
                var table_columns = window.%(table_id)s.getColumnSet();
                var thEl = table_columns.getColumn("%(field_id)s").getThEl();
                thEl.innerHTML = "";
                thEl.appendChild(input);
                var date_widget = $("#date_input_search_widget_%(field_id)s");
                // create the ok and clear buttons
                var ok_button = $("#form_%(field_id)s\\.actions\\.ok");
                $('<input/>').attr({
                        type: 'button',
                        id: '%(field_id)s_listing_ok',
                        name: '%(field_id)s_listing_ok',
                        class: "date_filter_ok context",
                        value: ok_button.val()
                            }).appendTo(date_widget.find(".actionButtons"));
                ok_button.remove();

                var clear_button = $("#form_%(field_id)s\\.actions\\.clear");
                $('<input/>').attr({
                        type: 'button',
                        id: '%(field_id)s_listing_clear',
                        name: '%(field_id)s_listing_clear',
                        class: "date_filter_clear context",
                        value: clear_button.val()
                        }).appendTo(date_widget.find(".actionButtons"));
                clear_button.remove();
                
               
                date_widget.attr("class", "date_input_search_widget");
                $("#"+"input_%(field_id)s").click(function() {
                        // .position() uses position relative to the offset parent, 
                        var pos = $(this).position();
                        // .outerWidth() takes into account border and padding.
                        var width = $(this).outerWidth();
                        
                        date_widget.css({
                            clear: "both",
                            height: "180px"
                        });

                        var state = date_widget.css("display");
                        if(state == "hidden" || state == "none"){
                            date_widget.slideDown("fast");
                            date_widget.css({
                                position: "absolute",
                                top: pos.top + 20 + "px",
                                left: (pos.left) + "px"
                            }).show();
                        }
                        else {
                            date_widget.slideUp("fast");
                        }
                });
                
                $("#%(field_id)s_listing_ok").live("click", function(){
                    var listing_start_date = $("#form_%(field_id)s\\.range_start_date").val().replace(/ /g,'');
                    var listing_end_date = $("#form_%(field_id)s\\.range_end_date").val().replace(/ /g,'');

                    if ((listing_start_date > listing_end_date) && (listing_end_date.length>0)){
                        alert("Validation error: Start date > End date");
                    } else {
                        $("#"+"input_%(field_id)s").val(listing_start_date + "->" + listing_end_date);
                        date_widget.slideUp("fast");
                    }
                });
                
                $('#%(field_id)s_listing_clear').live("click", function(){
                    $("#form_%(field_id)s\\.range_start_date").val("");
                    $("#form_%(field_id)s\\.range_end_date").val("");
                    $("#"+"input_%(field_id)s").val("");
                    date_widget.slideUp("fast");
                });
            });
    })(jQuery);
</script>
