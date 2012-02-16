/**
 * This module renders a list of available schedulable items
**/
YAHOO.bungeni.availableitems = function(){
    var Event = YAHOO.util.Event;
    var Scheduling = YAHOO.bungeni.scheduling;
    var Columns = YAHOO.bungeni.config.scheduling.columns;
    var Formatters = YAHOO.bungeni.config.scheduling.formatters;
    var Selectors = YAHOO.bungeni.config.selectors;
    var Utils = YAHOO.bungeni.Utils;
    var Y$ = YAHOO.util.Selector;
    
    /**
     * @method renderFilterControls
     * @description renders datatables of items available for scheduling
     **/
    var renderFilterControls = function(type, container, dataTable){
        var Handlers = YAHOO.bungeni.availableitems.handlers;
        var filter_config = scheduler_globals.filter_config[type];
        if (filter_config.menu.length > 0){
            var statusFilterButton = new YAHOO.widget.Button(
                {
                    type: "menu",
                    label: Utils.wrapText(filter_config.label),
                    id: "filter_status_" + type,
                    name: "filter_status_" + type,
                    menu: filter_config.menu,
                    container: container,
                }
            );
            statusFilterButton.on("selectedMenuItemChange",
                Handlers.setFilterMenuSelection
            );

            var dateStartMenu = new YAHOO.widget.Overlay(
                "cal_menu_start_" + type, { visible: false }
            );
            dateStartMenu.subscribe("show", Handlers.dialogPostRender);
            var dateStartButton = new YAHOO.widget.Button(
                {
                    type: "menu",
                    label: Utils.wrapText(
                        scheduler_globals.filters_start_date_label
                    ),
                    id: "filter_start_date_" + type,
                    name: "filter_start_date_" + type,
                    menu: dateStartMenu,
                    container: container,
                }
            );
            dateStartButton.on("appendTo", function(){
                dateStartMenu.setBody(" ");
                dateStartMenu.body.id = "calendar_start_container_" + type;
            });

            dateStartButton.on("click", function callback(){
                Handlers.filterCalendarSetup(this, type, dateStartMenu, 
                    callback
                );
            });

            var dateEndMenu = new YAHOO.widget.Overlay(
                "cal_menu_end_" + type, { visible: false }
            );
            var dateEndButton = new YAHOO.widget.Button(
                {
                    type: "menu",
                    label: Utils.wrapText(
                        scheduler_globals.filters_end_date_label
                    ),
                    id: "filter_end_date_" + type,
                    name: "filter_end_date_" + type,
                    menu: dateEndMenu,
                    container: container,
                }
            );
            dateEndButton.on("appendTo", function(){
                dateEndMenu.setBody(" ");
                dateEndMenu.body.id = "calendar_end_container_" + type;
            });
            
            dateEndButton.on("click", function callback(){
                Handlers.filterCalendarSetup(this, type, dateEndMenu, callback);
            });
            
            dateStartButton.getSelectedDate = Handlers.getDummyCalendarDate;
            dateStartButton.clearSelection = Handlers.getDummyCalendarDate;
            dateEndButton.getSelectedDate = Handlers.getDummyCalendarDate;
            dateEndButton.clearSelection = Handlers.getDummyCalendarDate;
            
            var filterApplyButton = new YAHOO.widget.Button(
                {
                    type: "button",
                    label: Utils.wrapText(
                        scheduler_globals.filter_apply_label
                    ),
                    id: "filter_apply_" + type,
                    name: "filter_apply_" + type,
                    container: container,
                }
            );
            filterApplyButton.on("click", function(oArgs){
                var data_filters = {};
                var selected_status = statusFilterButton.getMenu().activeItem;
                if (selected_status != null){
                    data_filters["filter_status"] = selected_status.value;
                }
                var start_date = dateStartButton.getSelectedDate();
                var end_date = dateEndButton.getSelectedDate();
                if (start_date || end_date){
                    data_filters["filter_status_date"] = new Array(
                            (start_date || ""), (end_date|| "")
                    ).join("|");
                }
                if (Object.keys(data_filters).length > 0){
                    dataTable.refresh(data_filters);
                }else{
                    YAHOO.bungeni.scheduling.dialogs.notification.show(
                        scheduler_globals.filters_no_filters_message
                    );
                }
            });
            
            var clearFiltersButton = new YAHOO.widget.Button(
                {
                    type: "button",
                    label: Utils.wrapText(
                        scheduler_globals.filters_clear_label
                    ),
                    id: "filter_clear_" + type,
                    name: "filter_clear_" + type,
                    container: container,
                }
            );
            clearFiltersButton.on("click", function(oArgs){
                //reset filters and then reload datatable
                statusFilterButton.set("selectedMenuItem", null);
                dateStartButton.clearSelection();
                dateEndButton.clearSelection();
                dataTable.refresh();
            });

        }
    }
    
    var availableItemHandlers = function(){
        /**
         * @method setFilterMenuSelection
         * @description sets the value of a filter menu button
         */
         var setFilterMenuSelection = function(event){
             if(this.original_label == undefined){
                 this.original_label = this.get("label");
             }
             var menuItem = event.newValue;
             var selectionLabel = (
                (menuItem && Utils.wrapText(menuItem.cfg.getProperty("text")))
                || this.original_label
            );
             this.set("label", selectionLabel);
         }

        /**
         * @method filterCalendarSetup
         * @description sets up a calendar bound to a button
         */
        var filterCalendarSetup = function(button, type, menu, callback){
            var sCalendar = new YAHOO.widget.Calendar(
                "calendar_start_" + type,
                menu.body.id
            );
            sCalendar.render();
            button.getSelectedDate = function(){
                var sDate = sCalendar.getSelectedDates()[0];
                var sDateText = "";
                if (sDate != null){
                    sDateText = new Array(
                        sDate.getFullYear(), sDate.getMonth()+1, sDate.getDate()
                    ).join("-")
                }
                return sDateText;
            };
            button.clearSelection = function(){
                sCalendar.deselectAll();
                button.set("label", button.original_label);
            }
            sCalendar.selectEvent.subscribe(function(sType, oArgs){
                if (button.original_label == undefined){
                    button.original_label = button.get("label");
                }
                if(oArgs){
                    var sDate = oArgs[0][0];
                    button.set("label", Utils.wrapText(sDate.join("-")));
                }
                menu.hide();
            });
            button.unsubscribe("click", callback);
            sCalendar.align();
        }

        /**
         * @method getDummyCalendarDate
         * @description returns a blank string as selected calendar date associated
         * with a filter button.
         * 
         * This is used if the calendar has not been instantiated which is bound
         * to the click event of a fitler button.
         */
         var getDummyCalendarDate = function(){
             return "";
         }

        var dialogPostRender = function(){
            this.bringToTop();
        }

        /**
         * @method addItemToSchedule
         * @description adds available item to schedule
         * 
         */
        var addItemToSchedule = function(args){
            var itemsDataTable = YAHOO.bungeni.scheduling.getScheduleTable();
            var target = args.target || args.el;
            var target_column = this.getColumn(target);
            if(target_column.field == Columns.SELECT_ROW){
                var targetRecord = this.getRecord(target);
                var targetData = targetRecord.getData()
                if (Y$.query(Selectors.checkbox, target, true).checked){
                    //check if item is already scheduled
                    var record_set = itemsDataTable.getRecordSet().getRecords();
                    var item_in_schedule = false;
                    for(idx in record_set){
                        var record = record_set[idx];
                        var oData = record.getData();
                        if((oData.item_id == targetData.item_id) &&
                            (oData.item_type == targetData.item_type)
                        ){
                            item_in_schedule = true;
                            break;
                        }
                    }
                    if (!item_in_schedule){
                        ctx_index = itemsDataTable.getSelectedRows()[0];
                        var new_record_index = (
                            (ctx_index && itemsDataTable.getTrIndex(ctx_index)+1) || 0
                        );
                        itemsDataTable.addRow(targetData, new_record_index);
                    }
                }else{
                    var record_set = itemsDataTable.getRecordSet().getRecords();
                    for (idx in record_set){
                        var record = record_set[idx];
                        var sdata = record.getData();
                        if((sdata.item_id == targetData.item_id) &&
                            (sdata.item_type == targetData.item_type)
                        ){
                            itemsDataTable.deleteRow(Number(idx));
                        }
                    }
                }
            }
        }

        /**
         * @method checkRows
         * @description check or uncheck selectors for all items on data table
         * 
         */
        var checkRows = function(args){
            var target_column = this.getColumn(args.target);
            if(target_column.field == Columns.SELECT_ROW){
                var record_set = this.getRecordSet().getRecords();
                var checked = false;
                if (Y$.query(Selectors.checkbox, args.target, true).checked){
                    checked = true;
                }
                for (record_index in record_set){
                    var row = this.getTrEl(record_set[record_index]);
                    var select_td = this.getFirstTdEl(row);
                    Y$.query(Selectors.checkbox, select_td, true).checked = checked;
                    this.unselectAllCells();
                    this.selectCell(select_td);
                }
            }
        }

        return {
            setFilterMenuSelection: setFilterMenuSelection,
            filterCalendarSetup: filterCalendarSetup,
            getDummyCalendarDate: getDummyCalendarDate,
            dialogPostRender: dialogPostRender,
            addItemToSchedule: addItemToSchedule,
            checkRows: checkRows
        }
    }();
    
    var renderDt = function(){
        var container = Scheduling.Layout.layout.getUnitByPosition("center");
        var Handlers = YAHOO.bungeni.availableitems.handlers;
        var availableItemsColumns = [
            {
                key: Columns.SELECT_ROW, 
                label: "<input type='checkbox' name='rec-sel-all'/>", 
                formatter: Formatters.availableItemSelect
            },
            {
                key: Columns.TITLE,
                label: scheduler_globals.column_title,
            },
            {
                key: Columns.REGISTRY_NO,
                label: scheduler_globals.column_registry_number,
            },
            {
                key: Columns.MOVER,
                label: scheduler_globals.column_mover,
            },
            {
                key: Columns.STATUS,
                label: scheduler_globals.column_status,
            },
            {
                key: Columns.STATUS_DATE,
                label: scheduler_globals.column_status_date,
                formatter: "date"
            },
        ]
        var availableItemsSchema = {
            resultsList : "items",
            fields : [Columns.ID, Columns.TYPE, Columns.TITLE, Columns.STATUS,
                Columns.STATUS_DATE, Columns.REGISTRY_NO, Columns.MOVER,
                Columns.URI
            ]
        }
        var availableItems = new YAHOO.widget.TabView();
        for (type_index in scheduler_globals.schedulable_types){
            (function(){
                var typedef = scheduler_globals.schedulable_types[type_index];
                var type = typedef.name;
                var container_id = type + "-data-table";
                var container_filters = container_id + "-filters";
                availableItems.addTab(new YAHOO.widget.Tab(
                    {
                        label: typedef.title,
                        content: ("<div id='" + container_filters + 
                            "' class='schedule-available-item-filters'></div>" 
                            + "<div id='" + container_id + "'/>"
                        ),
                    }
                ));
                Event.onAvailable(container_id, function(event){
                    var tabDataSource = new YAHOO.util.DataSource(
                        (scheduler_globals.schedulable_items_json_url 
                            + "?type="+ type
                        )
                    );
                    tabDataSource.responseType = YAHOO.util.DataSource.TYPE_JSON;
                    tabDataSource.responseSchema = availableItemsSchema;
                    var tabDataTable = new YAHOO.widget.DataTable(container_id,
                        availableItemsColumns, tabDataSource, 
                        { 
                            selectionMode:"single",
                            scrollable: true,
                            initialLoad: true,
                            width: container.body.clientWidth + "px",
                        }
                    );
                    tabDataTable.subscribe("cellClickEvent", 
                        Handlers.addItemToSchedule
                    );
                    tabDataTable.subscribe("theadCellClickEvent", 
                        Handlers.checkRows
                    );
                    tabDataTable.subscribe("cellSelectEvent",
                        Handlers.addItemToSchedule
                    );
                    //itemsDataTable.subscribe("rowDeleteEvent", function(args){
                    //    uncheckRemovedRows(args, tabDataTable, type);
                    //});
                    renderFilterControls(type, container_filters, tabDataTable);
                });
            })();
        }
        availableItems.selectTab(0);
        availableItems.appendTo(container.body);
        YAHOO.bungeni.Events.scheduleAvailable.unsubscribe(renderDt);
    };
    YAHOO.bungeni.Events.scheduleAvailable.subscribe(renderDt);
    return {
        handlers: availableItemHandlers
    }
}();
