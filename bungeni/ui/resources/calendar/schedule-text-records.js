/**
 * This module renders a list of available schedulable items
**/
YAHOO.bungeni.textrecords = function() {
    var Event = YAHOO.util.Event;
    var SGlobals = scheduler_globals;
    var Columns = YAHOO.bungeni.config.scheduling.columns;
    var Formatters = YAHOO.bungeni.config.scheduling.formatters;
    var Selectors = YAHOO.bungeni.config.selectors;
    var Utils = YAHOO.bungeni.Utils;
    var Y$ = YAHOO.util.Selector;
    

    var textRecordHandlers = function(){
        /**
         * @method renderTextRecordsTabs
         * @description renders tabview record onto a dialog to allow selection
         * and entry of text records i.e. headings and arbitrary text
         **/
        var renderTextRecordsTabs = function(args){
            var active_tab_id = this._parent.tab_id;
            var tab_view = new YAHOO.widget.TabView();
            var text_tab = new YAHOO.widget.Tab(
                { 
                    label: SGlobals.type_names.editorial_note,
                    content: ("<div id='add-text-record'>" + 
                        "<textarea id='text-record-value' " +
                         "name='text-record-value'></textarea></div>"+
                         "<div id='editorial-notes-available'/>"
                    ),
                }
            );
            var heading_tab = new YAHOO.widget.Tab(
                { 
                    label: SGlobals.type_names.heading,
                    content: ("<div id='add-heading-record'>" + 
                        "<label class='scheduler-label'" + 
                        " for='heading-record-value'>"+
                        SGlobals.new_heading_text +
                        "</label>" +
                        "<input class='scheduler-bigtext' " + 
                        "id='heading-record-value' name='heading-record-value' " +
                         "type='text'/></div><div id='headings-available'></div>"
                    ),
                }
            );
            var hDt = null;
            var initAvailableHeadings = function(){
                var columns = [
                    {
                        key:Columns.NUMBER,
                        label:"",
                        formatter:Formatters.counter
                    },
                    {
                        key: Columns.TITLE,
                        label: SGlobals.column_available_headings_title,
                    },
                ]
                var container = this.get("contentEl");
                var data_container = Y$.query("div#headings-available", container)[0];
                var dataSource = new YAHOO.util.DataSource(
                    SGlobals.schedulable_items_json_url + "?type=" + SGlobals.types.HEADING
                );
                dataSource.responseType = YAHOO.util.DataSource.TYPE_JSON;
                dataSource.responseSchema = YAHOO.bungeni.config.schemas.available_items;
                hDt = new YAHOO.widget.DataTable(data_container,
                    columns, dataSource, 
                    { 
                        selectionMode:"standard",
                        scrollable: true,
                        initialLoad: true,
                        width:"100%",
                        height: "200px",
                    }
                );
                hDt.subscribe("rowMouseoverEvent", hDt.onEventHighlightRow);
                hDt.subscribe("rowMouseoutEvent", hDt.onEventUnhighlightRow);
                hDt.subscribe("rowClickEvent", hDt.onEventSelectRow);
                this.unsubscribe("activeChange", initAvailableHeadings);
            }
            heading_tab.on("activeChange", initAvailableHeadings);
            heading_tab.getRecordValue = function(){
                var contentEl = this.get("contentEl");
                var custom_value = Y$.query("input", contentEl)[0].value;
                var selected_rows = hDt.getSelectedRows();
                var heading_values = new Array();
                if (custom_value){
                    var heading_value = {};
                    heading_value[Columns.TITLE] = custom_value;
                    heading_values.push(heading_value);
                }
                for(row_id=0; row_id<selected_rows.length; row_id++){
                    var data = hDt.getRecord(selected_rows[row_id]).getData();
                    var heading_value = {};
                    heading_value[Columns.TITLE] = data[Columns.TITLE];
                    heading_value[Columns.ID] = data[Columns.ID];
                    heading_values.push(heading_value);
                }
                return { 
                    type:SGlobals.types.HEADING,
                    value: heading_values
                }
            }
            
            var rteEditor = null;
            text_tab.getRecordValue = function(){
                var record_value = {};
                record_value[Columns.TITLE] = rteEditor.cleanHTML(
                    rteEditor.getEditorHTML()
                );
                return {
                    type: SGlobals.types.EDITORIAL_NOTE,
                    value: [ record_value ]
                }
            }
            
            var setEditorMarkup = function(args){
                text = args.record.getData()[Columns.TITLE];
                rteEditor.setEditorHTML(text);
            }
            
            var eDt = null;
            var initAvailableEditorialNotes = function(){
                var columns = [
                    {
                        key:Columns.NUMBER,
                        label:"",
                        formatter:Formatters.counter
                    },
                    {
                        key: Columns.TITLE,
                        label: SGlobals.type_names.editorial_note,
                    },
                ]
                var container = this.get("contentEl");
                var data_container = Y$.query("div#editorial-notes-available", container)[0];
                var dataSource = new YAHOO.util.DataSource(
                    SGlobals.schedulable_items_json_url + "?type="+SGlobals.types.EDITORIAL_NOTE
                );
                dataSource.responseType = YAHOO.util.DataSource.TYPE_JSON;
                dataSource.responseSchema = YAHOO.bungeni.config.schemas.available_items;
                eDt = new YAHOO.widget.DataTable(data_container,
                    columns, dataSource, 
                    { 
                        selectionMode:"single",
                        scrollable: true,
                        initialLoad: true,
                        width:"100%",
                        height: "200px",
                    }
                );
                eDt.subscribe("rowMouseoverEvent", hDt.onEventHighlightRow);
                eDt.subscribe("rowMouseoutEvent", hDt.onEventUnhighlightRow);
                eDt.subscribe("rowClickEvent", hDt.onEventSelectRow);
                eDt.subscribe("rowSelectEvent", hDt.onEventSelectRow);
                eDt.subscribe("rowSelectEvent", setEditorMarkup);
                this.unsubscribe("activeChange", initAvailableEditorialNotes);
            }
            text_tab.on("activeChange", initAvailableEditorialNotes);
            Event.onAvailable("add-text-record", function(event){
                rteEditor = new YAHOO.widget.SimpleEditor("text-record-value",
                    { 
                        width: "100%", 
                        height: "60px",
                        autoHeight: true,
                        toolbar: YAHOO.bungeni.config.scheduling.editor_toolbar,
                    }
                );
                rteEditor.render();
            });
            this.showEvent.subscribe(function(){
                if(hDt){ 
                    hDt.unselectAllRows(); 
                    eDt.unselectAllRows();
                    if(!YAHOO.bungeni.unsavedChanges){
                        //refresh headings
                        hDt.refresh();
                    }
                }
                if(rteEditor){ rteEditor.setEditorHTML(""); }
                Y$.query("input", heading_tab.get("contentEl"))[0].value = "";
            });
            var tab_map = {};
            tab_map[SGlobals.types.HEADING] = 0;
            tab_map[SGlobals.types.EDITORIAL_NOTE] = 1;
            tab_view.addTab(heading_tab);
            tab_view.addTab(text_tab);
            tab_view.appendTo(this.body);
            this.tab_view = tab_view;
            this.selectTab = function(tab_id){
                t_id =  tab_id?(tab_map[tab_id]):0;
                for(idx=0; idx<(tab_view.get("tabs").length); idx++){
                    if(idx!=t_id){
                        tab_view.deselectTab(idx);
                        tab_view.getTab(idx).setAttributes({disabled: true});
                        tab_view.getTab(idx).setStyle('display', 'none');
                    }
                }
                tab_view.getTab(t_id).setAttributes({disabled: false});
                tab_view.getTab(t_id).setStyle('display', '');
                tab_view.selectTab(t_id);
            }
            tab_view.selectTab((active_tab_id?(tab_map[active_tab_id]):0));
        }

        return {
            renderTextRecordsTabs: renderTextRecordsTabs
        }
    }();
    
    return {
        handlers: textRecordHandlers
    }
}();
