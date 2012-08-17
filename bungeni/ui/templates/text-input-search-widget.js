<script type="text/javascript">(function($) {
        counter = 0;
        $(document).ready(function() {
                var input = document.createElement('input');
                input.setAttribute('type', 'text');
                input.setAttribute('name', 'filter_%(field_id)s');
                input.setAttribute('id', 'input_%(table_id)s_%(field_id)s');
                if (counter == 0)
                    input.setAttribute('placeholder', '  type to search...');
                else
                    input.setAttribute('placeholder', '  ...')
                var table_columns = window.%(table_id)s.getColumnSet();
                var thEl = table_columns.getColumn('%(field_id)s').getThEl();
                thEl.innerHTML = "";
                thEl.appendChild(input);
                // add listener for ENTER key on listing input fields
                // !+SORT_MISSING(mr, aug-2012) disabling the following handler 
                // as it does NOT the equivalent of "clicking" on column heading
                // (it does not set the sort param, should be something like:
                // sort_{column_name}
                // 
                //$("#input_%(table_id)s_%(field_id)s").keyup(function(event){
                //    if(event.keyCode == 13){
                //        $("#yui-dt0-th-sort_%(field_id)s").live("click", table.sortColumn("yui-col"+counter+"", "none"));
                //    }
                //});
                counter++;
            });
    })(jQuery);
</script>

