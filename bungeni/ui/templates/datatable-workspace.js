<script type="text/javascript">
//global variable that holds the datatable instance
var %(table_id)s = {};
(function($) {
    $(document).ready(function() {
            %(table_id)s=$(this).yuiWorkspaceDataTable(
                                                       '%(context_name)s',
                                                       '%(link_url)s',
                                                       '%(data_url)s',
                                                       [%(fields)s],
                                                       [%(columns)s],
                                                       '%(table_id)s',
                                                       %(item_types)s,
                                                       %(status)s,
                                                       %(rows_per_page)s)
                });
})(jQuery);
</script>