<script type="text/javascript">
//global variable that holds the datatable instance
var %(table_id)s = {};
(function($) {
    $(document).ready(function() {
            %(table_id)s=$(this).yuiDataTable(
                                              '%(context_name)s',
                                              '%(link_url)s',
                                              '%(data_url)s',
                                              [%(fields)s],
                                              [%(columns)s],
                                              '%(table_id)s',
                                              %(rows_per_page)s);}
        );
})(jQuery);
</script>
