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
            });
    })(jQuery);
</script>
