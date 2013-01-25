/**
 * Schedule editor configuration for use in 'draft minutes' mode.
**/
YAHOO.bungeni.processed_minute_records = 0;
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

    var _minuteEditor = function(){
        init = function(){
           this.dialog = new YAHOO.widget.SimpleDialog("minute-editor", {
                modal: true,
                visible: false,
                width: "90em",
                draggable: true,
                fixedcenter: true,
                constraintoviewport: true
            });
            this.dialog._parent = this
            var dialogButtons = [
                {
                    text: SGlobals.save_discussion_button_text,
                    handler: function(){
                        var text = this._parent.getText();
                        var row_index = this._parent.row;
                        var minute_index = this._parent.minute;
                        var sDt = YAHOO.bungeni.scheduling.getScheduleTable();
                        if (text){
                            var record = sDt.getRecord(row_index);
                            var row_data = record.getData();
                            var cache_key = YAHOO.bungeni.Utils.slugify(
                                row_data[Columns.OBJECT_ID]
                            );
                            var cdata = YAHOO.bungeni.agendaconfig.minutesCache.get(
                                cache_key
                            );
                            cdata[minute_index][Columns.BODY] = text;
                            YAHOO.bungeni.agendaconfig.minutesCache.set(cache_key,
                                cdata
                            );
                            sDt.updateRow(row_index, row_data);
                            this.hide();
                        }
                    }
                },
                {
                    text: SGlobals.text_dialog_cancel_action,
                    handler: function(){ this.hide(); }
                },
            ]
            this.dialog.cfg.queueProperty("buttons", dialogButtons);
            this.dialog.setBody("<div><textarea name='minutestext' id='minutestext'></textarea></div>");
            this.dialog.setHeader(SGlobals.schedule_discussions_title);
            Event.onAvailable("minutestext", function(e){
                var editor = new YAHOO.widget.Editor("minutestext",
                    { width:"100%", height:"150px" , autoHeight:false }
                );
                editor.render();
                YAHOO.bungeni.agendaconfig.minuteEditor.getText = function(){
                    return editor.cleanHTML(editor.getEditorHTML())
                }
                YAHOO.bungeni.agendaconfig.minuteEditor.setText = function(row, minute){
                    var sDt = YAHOO.bungeni.scheduling.getScheduleTable();
                    var record = sDt.getRecord(row);
                    var row_data = record.getData();
                    var cdata = YAHOO.bungeni.agendaconfig.minutesCache.get(
                        YAHOO.bungeni.Utils.slugify(row_data[Columns.OBJECT_ID])
                    );
                    editor.setEditorHTML(cdata[minute][Columns.BODY]);
                }
            });
            this.dialog.render(document.body);
        }
        render = function(row, minute){
            this.row = Number(row);
            this.minute = Number(minute);
            if (!this.dialog){
                this.init();
            }else{
                this.dialog.show();
                this.dialog.bringToTop();
                this.dialog.center();
                this.setText(this.row, this.minute);
            }
        }

        return {
            init: init,
            render: render,
        }

    }();

    var _afterDTRender = function(){
        this.minuteEditor.render();
    }

    var _handlers = function(){
        var _renderMinutes = function(args){
            var rData = args.record.getData();
            if(SGlobals.discussable_types.indexOf(rData[Columns.TYPE])<0){
                return;
            }
            var data_url = ("./items/" + 
                rData[Columns.OBJECT_ID]+ 
                SGlobals.discussion_items_json_url
            );
            if(YAHOO.bungeni.scheduling.discussionsDT == undefined){
                var columns = [
                    {
                        key: Columns.NUMBER,
                        label: "",
                        formatter: Formatters.counter
                    },
                    {
                        key: Columns.BODY,
                        label: SGlobals.column_discussion_text,
                        formatter: Formatters.longText
                    }
                ]
                console.log("Working", data_url);
                var oDs = YAHOO.util.DataSource(data_url);
                oDs.responseType = YAHOO.util.DataSource.TYPE_JSON;
                oDs.responseSchema = {
                    resultsList: "nodes",
                    fields: [ Columns.OBJECT_ID, Columns.BODY ]
                }

                 YAHOO.bungeni.scheduling.discussionsDT = new YAHOO.widget.DataTable(
                    YAHOO.bungeni.scheduling.Layout.layout.getUnitByPosition("center").body, 
                    columns,
                    oDs,
                    {
                        selectionMode: "single",
                        initialLoad: true
                    }
                );
                return;
            }
            var oDt = YAHOO.bungeni.scheduling.discussionsDT;
            var oDs = oDt.getDataSource();
            oDs.liveData = data_url;
            oDs.sendRequest(null, {
                    success: oDt.onDataReturnInitializeTable,
                    failure: oDt.onDataReturnInitializeTable,
                    scope: oDt
            });
        }
        return {
            renderMinutes: _renderMinutes,
        }
    }();

    var _getColumns = function(cols_width){
        return [
            {
                key: Columns.ROW_CONTROLS, 
                label: "",
                formatter: Formatters.rowControls,
                width: (0.2*cols_width)
            },
            {
                key: Columns.TITLE, 
                label: SGlobals.column_title,
                editor: this.editor,
                formatter: Formatters.title,
                width: (0.72*cols_width)
            }
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
                Columns.WORKFLOW_STATE,
                Columns.WORKFLOW_ACTIONS
            ],
    };


    var minutesDSCache = function(){
        var _cache = {};

        var _get_cache = function(){
            return _cache;
        }

        var _get_minutes_count = function(){
            var mcount = 0;
            var mcache = this.get_cache()
            for (key in mcache){
                mcount+=mcache[key].length;
            }
            return mcount
        }

        var _get = function(key){
            return _cache[key] || undefined;
        }
        
        var _set = function(key, data){
            _cache[key] = data;
        }
        
        var _update = function(key, index, data){
            this.get(key)[index] = data;
        }
        
        var _add = function(key, data){
            if (this.get(key)==undefined){
                this.set(key, new Array());
            }
            this.get(key).push(data);
        }
                
        return {
            get_cache: _get_cache,
            get_minutes_count: _get_minutes_count,
            get: _get,
            set: _set,
            update: _update,
            add: _add,
        }
    }();

    var LayoutConfig = [
        {
            position: 'center',
            header: SGlobals.agenda_minutes_title,
            body: '',
            width: "660",
            unit: "%",
            gutter: "2 2",
            resize: true,
        },
        /*{
            position:'center',
            header: AgendaConfig.TITLE_AVAILABLE_ITEMS,
            body: '',
            gutter: "2 2",
            resize: true,
            collapse: true,
        },*/
        {
            position:'bottom',
            body: '',
            header: '',
            gutter: "2 2",
            height: 42
        }
    ]

    var _dataTableExtraInit = function(dt){
        //bind any extra events to data table
        //dt.subscribe("rowSelectEvent", 
        //    YAHOO.bungeni.agendaconfig.handlers.renderMinutes);
    }

    return {
        OP_SAVE_MINUTES: "OP_SAVE_MINUTES",
        setEditor: _setEditor,
        minuteEditor: _minuteEditor,
        afterDTRender: _afterDTRender,
        handlers: _handlers,
        getColumns: _getColumns,
        AGENDA_SCHEMA: _agendaSchema,
        TITLE_AGENDA: SGlobals.agenda_minutes_title,
        AGENDA_DATASOURCE_URL: SGlobals.json_listing_url_meta,
        minutesCache: minutesDSCache,
        EMPTY_AGENDA_MESSAGE: SGlobals.empty_agenda_message,
        layoutConfig: LayoutConfig,
        containerUnit: "center",
        dataTableExtraInit: _dataTableExtraInit
    }
}();
