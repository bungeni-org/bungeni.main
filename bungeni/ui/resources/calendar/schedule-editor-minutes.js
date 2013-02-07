/**
 * Schedule editor configuration for use in 'draft minutes' mode.
**/
YAHOO.bungeni.processed_minute_records = 0;
YAHOO.bungeni.agendaconfig = function(){
    var BungeniUtils = YAHOO.bungeni.Utils;
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
                    text: SGlobals.save_button_text,
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
                            var cdata = YAHOO.bungeni.agendaconfig.minutesCache.get(cache_key);
                            if(cdata && (minute_index>=0) && cdata[minute_index]){
                                cdata[minute_index][Columns.BODY] = text;
                                YAHOO.bungeni.agendaconfig.minutesCache.set(cache_key,
                                    cdata
                                );
                            }else{
                                var cdata = {};
                                cdata[Columns.BODY] = text;
                                YAHOO.bungeni.agendaconfig.minutesCache.add(
                                    cache_key, cdata
                                );
                            }
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
                var editor = new YAHOO.widget.SimpleEditor("minutestext",
                    { 
                        width:"100%", 
                        height:"150px" , 
                        autoHeight:false ,
                        toolbar: YAHOO.bungeni.config.scheduling.editor_toolbar,
                    }
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
                if (minute){
                    this.setText(this.row, this.minute);
                }
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
        
        var _editMinute  = function(args){
            var indices = this.id.split("_")[1].split("-");
            var row = indices[0];
            var minute = indices[1];
            YAHOO.bungeni.agendaconfig.minuteEditor.render(row, minute);
        }
        var _deleteMinute = function(args){
            var indices = this.id.split("_")[1].split("-");
            var row = Number(indices[0]);
            var minute = Number(indices[1]);
            var sDt = YAHOO.bungeni.scheduling.getScheduleTable();
            var record = sDt.getRecord(row);
            var row_data = record.getData();
            var cache_key = YAHOO.bungeni.Utils.slugify(
                row_data[Columns.OBJECT_ID]
            );
            var cdata = YAHOO.bungeni.agendaconfig.minutesCache.get(cache_key);
            if(cdata){
                YAHOO.bungeni.agendaconfig.minutesCache.delete(cache_key, minute);
            }
            sDt.updateRow(row, row_data);
        }
        var _addMinute = function(args){
            sDt = YAHOO.bungeni.scheduling.getScheduleTable();;
            var selected_rows = sDt.getSelectedRows();
            var row = sDt.getTrIndex(selected_rows[0])
            YAHOO.bungeni.agendaconfig.minuteEditor.render(row);
        }

        var _saveMinutes = function(row){
            var sDt = YAHOO.bungeni.scheduling.getScheduleTable();
            var sRecord = sDt.getRecord(row);
            var sData = sRecord.getData();
            if(SGlobals.discussable_types.indexOf(sData[Columns.TYPE])<0){
                return;
            }
            var obj_id = sData[Columns.OBJECT_ID];
            if(obj_id==undefined){
                return;
            }
            var cKey = YAHOO.bungeni.Utils.slugify(obj_id);
            if (cKey){
                var mcache = YAHOO.bungeni.agendaconfig.minutesCache.get(cKey);
                if (mcache!=undefined){
                    YAHOO.bungeni.processed_minute_records+=1;
                    var item_data = new Array();
                    for (index in mcache){
                        var minute_data = mcache[index];
                        var save_data = {
                            object_id: minute_data[Columns.OBJECT_ID],
                            body: minute_data[Columns.BODY],
                        }
                        item_data.push(save_data);
                    }
                    var post_data = "data=" + encodeURIComponent(
                        YJSON.stringify(item_data)
                    );
                    var save_url = ("./items/" + sData[Columns.OBJECT_ID] + 
                        SGlobals.discussions_save_url
                    );
                    YAHOO.bungeni.scheduling.SaveRequest.startRequest(
                        save_url, post_data, SGlobals.saving_discussions_text
                    );
                }
            }
        }

        return {
            renderMinutes: _renderMinutes,
            editMinute: _editMinute,
            deleteMinute: _deleteMinute,
            addMinute: _addMinute,
            saveMinutes: _saveMinutes
        }
    }();

    /**
     * @method renderAddMinute
     * @description renders button control to add minute record
     * */
    var renderAddMinute = function (record_index, nHTML, mAttrs, txtLabel) {
        idAttr = " rel='rec-NEW'";
        addId = "minute-edit_" + record_index;
        var addAttrs = (
            "class='minute-add' " +
            "id='" + addId + "'");
        nHTML = nHTML + BungeniUtils.wrapText(
        (txtLabel + BungeniUtils.wrapText(
            "&nbsp;",
            "span", addAttrs)),
            "span", mAttrs + " " + idAttr);
        Event.addListener(addId, "click",
        YAHOO.bungeni.agendaconfig.handlers.addMinute);
        return nHTML;
    }

    /**
     * @method itemTitleMinutesFormatter
     * @method render item title and minutes where applicable
     */
    var itemTitleMinutesFormatter = function (el, record, column, data) {
        var data = record.getData();
        var record_index = this.getRecordIndex(record);
        el.className += " list-minutes";
        el.innerHTML = "";
        if (SGlobals.discussable_types.indexOf(
        data[Columns.TYPE]) < 0) {
            el.innerHTML = data[Columns.TITLE];
        } else {
            var cHTML = "";
            if (el.innerHTML) {
                tElem = Y$.query("em", el)[0];
                cHTML = BungeniUtils.wrapText(tElem.innerHTML);
            } else {
                cHTML = BungeniUtils.wrapText(data[Columns.TITLE]);
            }
            if (BungeniUtils.showURI(data)) {
                cHTML = cHTML + ("<a href='" + 
                    BungeniUtils.makeURI(data) +
                    "' target='blank'>&nbsp;" + 
                    SGlobals.text_action_view + "</a>"
                );
            }
            cHTML = cHTML + BungeniUtils.wrapText(
            SGlobals.minutes_header, "span", "class='minutes-header'");
            var mAttrs = "class='minute-record'";
            var eAttrs = "class='minute-record-error'";
            var obj_id = data[Columns.OBJECT_ID];
            if (obj_id != undefined) {
                var ds_id = BungeniUtils.slugify(obj_id);
                var attrs = "id='" + ds_id + "' " + mAttrs;
                cHTML = cHTML + BungeniUtils.wrapText(
                BungeniUtils.wrapText(SGlobals.minutes_loading,
                    "p", attrs), "div");
                Event.onAvailable(ds_id, function () {
                    var minutesContainer = this;
                    var ds_url = ("./items/" + data[Columns.OBJECT_ID] + SGlobals.discussion_items_json_url);
                    var oDs = YAHOO.util.DataSource(ds_url);
                    oDs.responseType = YAHOO.util.DataSource.TYPE_JSON;
                    oDs.responseSchema = {
                        resultsList: "nodes",
                        fields: [Columns.OBJECT_ID, Columns.BODY]
                    }
                    var render_minutes = function (items) {
                        var nHTML = "";
                        if (items.length) {
                            for (idx = 0; idx < items.length; idx++) {
                                mdata = items[idx];
                                idAttr = "rel='rec-" + idx + "'";
                                edId = "minute-edit_" + record_index + "-" + idx;
                                var editAttrs = (
                                    "class='minute-control edit-minute-control' " +
                                    "id='" + edId + "'");
                                delId = "minute-delete_" + record_index + "-" + idx;
                                var delAttrs = (
                                    "class='minute-control delete-minute-control' " +
                                    "id='" + delId + "'");

                                editControl = BungeniUtils.wrapText(
                                    "", "span", editAttrs);
                                deleteControl = BungeniUtils.wrapText(
                                    "", "span", delAttrs);
                                nHTML = nHTML + BungeniUtils.wrapText(
                                    (mdata[Columns.BODY] + editControl + deleteControl),
                                    "span", (mAttrs + " " + idAttr)
                                );
                                Event.addListener(edId, "click",
                                    YAHOO.bungeni.agendaconfig.handlers.editMinute);
                                Event.addListener(delId, "click",
                                    YAHOO.bungeni.agendaconfig.handlers.deleteMinute);
                            }
                            // "add new record" row
                            nHTML = renderAddMinute(record_index, nHTML, mAttrs,
                            SGlobals.add_minutes_record);
                        } else {
                            // "add new record" row on none
                            nHTML = renderAddMinute(record_index, nHTML, mAttrs,
                            SGlobals.minutes_no_records);
                        }
                        minutesContainer.innerHTML = nHTML;
                    }
                    callback = {
                        success: function (request, response, payload) {
                            var nHTML = "";
                            YAHOO.bungeni.agendaconfig.minutesCache.set(
                            ds_id, response.results);
                            render_minutes(response.results);
                        },
                        failure: function (req, resp, payload) {
                            nHTML = oHTML + BungeniUtils.wrapText(
                            SGlobals.minutes_loading_error,
                                "span", eAttrs);
                            el.innerHTML = nHTML;
                        },
                    }
                    var cached_items = YAHOO.bungeni.agendaconfig.minutesCache.get(ds_id);
                    if (cached_items!=undefined) {
                        render_minutes(cached_items);
                    } else {
                        oDs.sendRequest(null, callback, this);
                    }

                });
            } else {
                cHTML = cHTML + BungeniUtils.wrapText(
                BungeniUtils.wrapText(
                SGlobals.minutes_unsaved_agenda), "span", mAttrs);
            }
            el.innerHTML = cHTML;
        }
    }

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
                formatter: itemTitleMinutesFormatter,
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
        var _delete = function(key, index){
            this.get(key).splice(index, 1);
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
            delete: _delete,
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
