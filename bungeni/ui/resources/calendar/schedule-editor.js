/**
 * This module renders UI components that hadle editing of the ganda
**/

YAHOO.bungeni.agendaconfig = function(){
    var Event = YAHOO.util.Event;
    var YJSON = YAHOO.lang.JSON;
    var SGlobals = scheduler_globals;
    var Columns = YAHOO.bungeni.config.scheduling.columns;
    var Formatters = YAHOO.bungeni.config.scheduling.formatters;
    var Handlers = YAHOO.bungeni.config.scheduling.handlers;
    var DialogConfig = YAHOO.bungeni.config.dialogs.config;

    var editor = null;
    var _setEditor = function(editor){
        this.editor = editor;
    }

    var _afterDTRender = function(){
        //post render events
        return;
    }

    var _getColumns = function(){
        return [
            {
                key: Columns.ADD_TEXT_RECORD, 
                label: "",
                formatter: Formatters.addTextRecord,
            },
            {
                key: Columns.TYPE, 
                label: SGlobals.column_type,
                formatter: Formatters.type,
            },
            {
                key: Columns.TITLE, 
                label: SGlobals.column_title,
                editor: this.editor,
                width: 150,
                formatter: Formatters.title
            },
            {
                key: Columns.URI, 
                label: "", 
                formatter: Formatters.link
            },
            {
                key: Columns.MOVE_UP, 
                label: "", 
                formatter: Formatters.moveUp
            },
            {
                key: Columns.MOVE_DOWN, 
                label: "", 
                formatter: Formatters.moveDown
            },
        ];
    }
    var _agendaSchema = {
            resultsList: "nodes",
            fields: [
                Columns.ID, 
                Columns.TITLE, 
                Columns.TYPE, 
                Columns.OBJECT_ID, 
                Columns.MOVER,
                Columns.URI,
            ],
    };

    return {
        setEditor: _setEditor,
        afterDTRender: _afterDTRender,
        getColumns: _getColumns,
        AGENDA_SCHEMA: _agendaSchema,
        AGENDA_DATASOURCE_URL: SGlobals.json_listing_url,
        TITLE_AGENDA: SGlobals.current_schedule_items,
        TITLE_AVAILABLE_ITEMS: SGlobals.available_items_title,
    }
}();
