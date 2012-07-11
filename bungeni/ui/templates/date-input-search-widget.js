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

                var portletItem = $('#date_input_search_widget_%(field_id)s');
                $('#'+'input_%(field_id)s').click(function() {
                        // .position() uses position relative to the offset parent, 
                        var pos = $(this).position();
                        // .outerWidth() takes into account border and padding.
                        var width = $(this).outerWidth();
                        
                        portletItem.css({
                            clear: 'both',
                            height: '160px'
                        });

                        $('#listing_ok').remove();
                        $('#listing_clear').remove();
                        
                        // create the ok and clear buttons
                        $('<input/>').attr({
                            type: 'button',
                            id: 'listing_ok',
                            name: 'listing_ok',
                            class: "context",
                            value: "ok"
                        }).appendTo('#date_input_search_widget_%(field_id)s');

                        $('<input/>').attr({
                            type: 'button',
                            id: 'listing_clear',
                            name: 'listing_clear',
                            class: "context",
                            value: "clear"
                        }).appendTo('#date_input_search_widget_%(field_id)s');

                        var state = portletItem.css('display');
                        if(state == 'hidden' || state == 'none'){
                            portletItem.slideDown('fast');
                            $("#date_input_search_widget_%(field_id)s").css({
                                position: "absolute",
                                top: pos.top + 20 + "px",
                                left: (pos.left) + "px"
                            }).show();
                        }
                        else {
                            portletItem.slideUp('fast');
                        }
                });

                // use live click since this element are created on the fly and there not registered
                // on browser on DOM ready event
                $("#listing_ok").live("click", function(){
                    var listing_start_date = $("#form\\.range_start_date").val();
                    var listing_end_date = $("#form\\.range_end_date").val();

                    if (listing_start_date > listing_end_date) {
                        alert("Validation error: Start date > End date");
                    } else {
                        $('#'+'input_%(field_id)s').val(listing_start_date + " " + listing_end_date);
                        portletItem.slideUp('fast');
                    }
                });
                
                $("#listing_clear").live("click", function(){
                    $("#form\\.range_start_date").val("");
                    $("#form\\.range_end_date").val("");
                    $('#'+'input_%(field_id)s').val("");
                    portletItem.slideUp('fast');
                });
            });
    })(jQuery);
</script>
