/**
 * This module implements Bungeni workspace multi inbox feature
**/

YAHOO.namespace("bungeni.workspace");
YAHOO.bungeni.workspace.SELECTED_INBOX = undefined;
YAHOO.bungeni.workspace.CACHE_TAB_COUNT = false;

YAHOO.bungeni.workspace.multiInbox = function(){
    var Event = YAHOO.util.Event;
    var INBOX_CONTAINER = "workspace-multiple-inboxes";
    var dataTable = null;

    Event.onAvailable(INBOX_CONTAINER, function(){        
        var wsButtons = new YAHOO.widget.ButtonGroup({ 
            id:  "workspace-filter-buttons", 
            name:  "workspace-filter-buttons-control",
            container: INBOX_CONTAINER,
        });

        var updateSelectedInbox = function(event){
            group_id = event.newValue;
            if (YAHOO.bungeni.workspace.WORKSPACE_CONTEXT){
                YAHOO.bungeni.workspace.SELECTED_INBOX = group_id;
                YAHOO.bungeni.workspace.CACHE_TAB_COUNT = false;
                request = window.table.get("generateRequest")(window.table.getState(), window.table);
                window.table.getDataSource().sendRequest(request,
                    {
                        success: window.table.onDataReturnInitializeTable,
                        scope: window.table
                    }
                );
            }else{
                window.location="../switchgroup?filter_group=" + group_id
            }
        }
        wsButtons.on("valueChange", updateSelectedInbox);
        wsButtons.addButton({
            label: workspace_globals.all_documents_tab,
            value: "",
            checked: (workspace_globals.current_inbox=="")
        });
        for (index in workspace_globals.groups){
            group = workspace_globals.groups[index];
            wsButtons.addButton({
                label: group.name,
                value: group.group_id,
                checked: (workspace_globals.current_inbox==group.group_id),
            })
        }
    });
}();
