var SGlobals = scheduler_globals;

/**
 * Render a preview of the Agenda
*/
YAHOO.bungeni.schedulingpreview = function(){
    var Event = YAHOO.util.Event;
    var Columns = YAHOO.bungeni.config.scheduling.columns;
    var formatters = YAHOO.bungeni.config.scheduling.formatters;
    var showdiscussions = function(args){
        var rData = args.record.getData();
        if(SGlobals.discussable_types.indexOf(rData[Columns.TYPE])<0){
            return;
        }
        var data_url = ("./items/" + 
            rData[Columns.OBJECT_ID]+ 
            SGlobals.discussion_items_json_url
        );
        if(YAHOO.bungeni.schedulingpreview.discussionsDT == undefined){
            var columns = [
                {
                    key: Columns.NUMBER,
                    label: "",
                    formatter: formatters.counter
                },
                {
                    key: Columns.BODY,
                    label: SGlobals.column_discussion_text,
                    formatter: formatters.longText
                }
            ]
            
            var oDs = YAHOO.util.DataSource(data_url);
            oDs.responseType = YAHOO.util.DataSource.TYPE_JSON;
            oDs.responseSchema = {
                resultsList: "nodes",
                fields: [ Columns.OBJECT_ID, Columns.BODY ]
            }

             YAHOO.bungeni.schedulingpreview.discussionsDT = new YAHOO.widget.DataTable(
                YAHOO.bungeni.schedulingpreview.layout.getUnitByPosition("center").body, 
                columns,
                oDs,
                {
                    selectionMode: "single",
                    initialLoad: true
                }
            );
            return;
        }
        var oDt = YAHOO.bungeni.schedulingpreview.discussionsDT;
        var oDs = oDt.getDataSource();
        oDs.liveData = data_url;
        oDs.sendRequest(null, {
                success: oDt.onDataReturnInitializeTable,
                failure: oDt.onDataReturnInitializeTable,
                scope: oDt
        });
    }
    Event.onDOMReady(function(){
        YAHOO.bungeni.schedulingpreview.layout = new YAHOO.widget.Layout(
            "scheduler-layout",
            {
                height:500,
                units: [
                    { 
                        position: "left", 
                        width: 600, 
                        body: '',
                        header: SGlobals.current_schedule_title,
                        gutter: "5 5",
                        height: 470,
                        resize: true,
                        collapse: false
                    },
                    { 
                        position: "center", 
                        body: '',
                        header: SGlobals.schedule_discussions_title,
                        gutter: "5 5",
                        height: 470,
                        collapse: true
                    },
                ]
            }
        );
        YAHOO.bungeni.schedulingpreview.layout.on("render", function(){
            var columns = [
                {
                    key : Columns.TYPE, 
                    label : SGlobals.column_type,
                    formatter: formatters.type,
                },
                {
                    key : Columns.TITLE, 
                    label : SGlobals.column_title,
                    formatter: formatters.description
                },
            ];
            var dataSource = new YAHOO.util.DataSource(
                SGlobals.json_listing_url
            );
            dataSource.responseType = YAHOO.util.DataSource.TYPE_JSON;
            dataSource.responseSchema = {
                resultsList: "nodes",
                fields: [
                    Columns.ID, 
                    Columns.TITLE, 
                    Columns.TYPE, 
                    Columns.OBJECT_ID, 
                    Columns.MOVER, 
                    Columns.URI
                ],
            };
            var dataTable = new YAHOO.widget.DataTable(
                this.getUnitByPosition("left").body,
                columns, dataSource,
                {
                    selectionMode:"single",
                    scrollable:true,
                    width:"100%"
                }
            );
            var addRowClass = function(args){
                var sSize = dataTable.getRecordSet().getLength();
                for (index=0; index<sSize; index++){
                    row_type = dataTable.getRecordSet()._records[index]._oData.item_type;
                    dataTable.getTrEl(index).className += " row-"+row_type;
                }
            };
            
            dataTable.subscribe("initEvent", addRowClass);
            dataTable.subscribe("rowClickEvent", dataTable.onEventSelectRow);
            dataTable.subscribe("rowMouseoverEvent", dataTable.onEventHighlightRow);
            dataTable.subscribe("rowMouseoutEvent", dataTable.onEventUnhighlightRow);
            dataTable.subscribe("rowSelectEvent", showdiscussions);
        });
        YAHOO.bungeni.schedulingpreview.layout.render();
    });
    return {}
}();
