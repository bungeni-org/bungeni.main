$(document).ready(
  function(){
    // wire workflow dropdown menu to use POST actions
    var menu_links = $('#context_workflow dd.actionMenuContent a');
    menu_links.bungeniPostWorkflowActionMenuItem();
    
    // set up parliament date range selection
    $("select[id=form.parliament]").bungeniTimeRangeSelect(false, false);
    
    // run workspace_count on workspace tab when viewing a doc
    if ($("dl.workspace-doc-marker")[0]){
            $("dl.workspace-documents").workspace_count();
        }
  }
);
