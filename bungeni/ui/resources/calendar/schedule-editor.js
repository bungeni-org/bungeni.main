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
    var Dialogs = YAHOO.bungeni.config.dialogs;
    var DialogConfig = YAHOO.bungeni.config.dialogs.config;

    var editor = null;
    var _setEditor = function(editor){
        this.editor = editor;
    }

    var _afterDTRender = function(){
        //post render events
        return;
    }

    var _getColumns = function(cols_width){
        return [
            {
                key: Columns.ROW_CONTROLS, 
                label: "",
                field: null,
                formatter: Formatters.rowControls,
                width: 0.2 * cols_width
            },
            {
                key: Columns.TITLE, 
                label: SGlobals.column_title,
                editor: this.editor,
                width: 0.7 * cols_width,
                formatter: Formatters.title
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
    var _getEmptyMessage = function(){
        var h_bind = "YAHOO.bungeni.config.dialogs.textrecords.show(SGlobals.types.HEADING);";
        var e_bind = "YAHOO.bungeni.config.dialogs.textrecords.show(SGlobals.types.EDITORIAL_NOTE);";
        return (
            YAHOO.bungeni.Utils.wrapText(SGlobals.empty_agenda_message, "p") +
            YAHOO.bungeni.Utils.wrapText("+ " + SGlobals.type_names.heading, 
                "button", ("href='javascript:void(0);' id='init-add-heading' " +
                    "onclick='" + h_bind + "'"
                 )
            ) + 
            YAHOO.bungeni.Utils.wrapText("+ " + SGlobals.type_names.editorial_note, 
                "button", ("href='javascript:void(0);' " + 
                    "id='init-add-editorial-note' onclick='" + e_bind + "'"
                )
            )
        )
    }

    return {
        setEditor: _setEditor,
        afterDTRender: _afterDTRender,
        getColumns: _getColumns,
        AGENDA_SCHEMA: _agendaSchema,
        AGENDA_DATASOURCE_URL: SGlobals.json_listing_url,
        TITLE_AGENDA: SGlobals.current_schedule_items,
        TITLE_AVAILABLE_ITEMS: SGlobals.available_items_title,
        EMPTY_AGENDA_MESSAGE: _getEmptyMessage()
    }
}();
