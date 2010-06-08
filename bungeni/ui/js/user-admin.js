YAHOO.util.Event.onDOMReady(function(){

    var filterHandler = function( e ){
	YAHOO.util.Event.preventDefault(e)
	YAHOO.example.applyCriteria();
    };

    YAHOO.util.Event.addListener("filter-submit", "click", filterHandler);

    var datasource, columns, config
          

    // Setup Datasource for Container Viewlet
    datasource = new YAHOO.util.DataSource("query-users?");
    datasource.responseType   = YAHOO.util.DataSource.TYPE_JSON;
    datasource.responseSchema = {
      resultsList: "results",
      fields: [ {key:"login"},{key:"title"},{key:"email"},{key:"object_type"} ],
      metaFields: { totalRecords: "length", sortKey:"sort", sortDir:"dir", paginationRecordOffset:"start"}
      }
      
    columns = [ {key:"login", label:"Login Name", sortable:true},
		{key:"title", label:"Name", sortable:true},
		{key:"email", label:"Email", sortable:true},
		{key:"object_type", label:"Type", sortable:true} ];
    
    // A custom function to translate the js paging request into a datasource query 
    var buildQueryString = function (state,dt) {
        var query_url = getFormValues() + 
	                "&start=" + state.pagination.recordOffset + 
	                "&limit=" + state.pagination.rowsPerPage + 
	                "&sort=" + state.sorting.key  + 
	                "&dir=" + ((state.sorting.dir === YAHOO.widget.DataTable.CLASS_DESC) ? "desc" : "asc");
        return query_url
    };
    

    // Custom function to handle pagination requests
    var handlePagination = function(state, dt){
	var sortedBy = dt.get('sortedBy');
	
	// Define the new state
	var newState = {
	    startIndex: state.recordOffset,
	    sorting: {
		key: sortedBy.key,
		dir: ((sortedBy.dir === YAHOO.widget.DataTable.CLASS_DESC) ? sortedBy.dir : YAHOO.widget.DataTable.CLASS_ASC)
	    },
	    pagination: { // Pagination values
		recordOffset: state.recordOffset,
		rowsPerPage: state.rowsPerPage // get the rpp from the proposed state
	    }
	};
	
	// Create callback object for the request
	var oCallback = {
	    success: dt.onDataReturnSetRows,
	    failure: dt.onDataReturnSetRows,
	    scope: dt,
	    argument: newState // Pass in new state as data payload for callback function to use
	};
	
	// Send the request
	dt.getDataSource().sendRequest(buildQueryString(newState), oCallback);
    };

    var config = {
       paginator : new YAHOO.widget.Paginator({ rowsPerPage : 20 }),
       initialRequest : 'start=0&limit=20',
       generateRequest : buildQueryString,
       paginationEventHandler : handlePagination,
       sortedBy : { key: "title", dir : "asc" },
    }

    table = new YAHOO.widget.DataTable( YAHOO.util.Dom.get("container_contents"), columns, datasource, config  )    
    table.sortColumn = function(oColumn) {
	// Default ascending
	var sDir = YAHOO.widget.DataTable.CLASS_ASC;
	
	// If already sorted, sort in opposite direction
	if (oColumn.key === this.get("sortedBy").key) {
	    sDir = (this.get("sortedBy").dir === "asc") ? YAHOO.widget.DataTable.CLASS_DESC : YAHOO.widget.DataTable.CLASS_ASC;
	}
	
	// Define the new state
	var newState = {
	    startIndex: 0,
	    sorting: { // Sort values
		key: oColumn.key,
		dir: sDir
	    },
	    pagination: { // Pagination values
		recordOffset: 0, // Default to first page when sorting
		rowsPerPage: this.get("paginator").getRowsPerPage() // Keep current setting
	    }
	};

	// Create callback object for the request
	var oCallback = {
	    success: table.onDataReturnInitializeTable,
	    failure: table.onDataReturnInitializeTable,
	    scope: table,
	    argument: newState // Pass in new state as data payload for callback function to use
	};

	// Send the request
	table.getDataSource().sendRequest(buildQueryString(newState), oCallback);
        
        };
   
    var getFormValues = function( ){
	return "query="+YAHOO.util.Dom.get('query').value; 
    };

    YAHOO.example.applyCriteria = function( ) {
	var newState = {
	    startIndex: 0,
	    sorting : { key: "title", dir: YAHOO.widget.DataTable.CLASS_ASC },
	    pagination: { recordOffset: 0, rowsPerPage : table.get('paginator').getRowsPerPage() }
	    }
			
	// Create callback object for the request
	var oCallback = {
	    success: table.onDataReturnInitializeTable,
	    failure: table.onDataReturnInitializeTable,
	    scope: table,
	    argument: newState // Pass in new state as data payload for callback function to use
	};
	// Send the request
	table.getDataSource().sendRequest(buildQueryString(newState), oCallback);
    };

    });
