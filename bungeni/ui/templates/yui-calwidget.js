//<![CDATA[ 
(function () {
	var Event = YAHOO.util.Event, Dom = YAHOO.util.Dom;

	Event.onDOMReady(function () {
		var oCalendarMenu;
		var onButtonClick = function () {			
			// Create a Calendar instance and render it into the body 
			// element of the Overlay.
			  var navConfig = {
                    strings : {
                        month: "%(month)s" ,
                        year: "%(year)s",
                        submit: "%(submit)s",
                        cancel: "%(cancel)s",
                        invalidYear: "%(invalidYear)s" 
                    },
                    monthFormat: YAHOO.widget.Calendar.SHORT,
                    initialFocus: "year"
              };			
			var oCalendar = new YAHOO.widget.Calendar("%(name)s-buttoncalendar", oCalendarMenu.body.id,
                    {mindate:"%(mindate)s",
                    maxdate:"%(maxdate)s",
                    pagedate: "%(pagedate)s",
                    navigator: navConfig} );
                    
            oCalendar.cfg.setProperty("MONTHS_SHORT",   %(months_short)s );
            oCalendar.cfg.setProperty("MONTHS_LONG",    %(months_long)s );
            oCalendar.cfg.setProperty("WEEKDAYS_1CHAR", %(w_day_1char)s );
            oCalendar.cfg.setProperty("WEEKDAYS_SHORT", %(w_day_short)s );
            oCalendar.cfg.setProperty("WEEKDAYS_MEDIUM",%(w_day_medium)s );
            oCalendar.cfg.setProperty("WEEKDAYS_LONG",  %(w_day_long)s );

			oCalendar.render();
			// Subscribe to the Calendar instance's "select" event to 
			// update the month, day, year form fields when the user
			// selects a date.
			oCalendar.selectEvent.subscribe(function (p_sType, p_aArgs) {
				var aDate; 
				if (p_aArgs) {						
					aDate = p_aArgs[0][0];					
                    var year = aDate[0], month = aDate[1], day = aDate[2];
                    var selMonth = document.getElementById("%(sel_month)s");
                    var selDay = document.getElementById("%(sel_day)s");
                    var selYear = document.getElementById("%(sel_year)s"); 
                    var txtDate = document.getElementById("%(txt_date)s");                     
                    if (selYear && selMonth && selDay){ 
                        for (var y=0;y<selMonth.options.length;y++) {
                            if (selMonth.options[y].value == month) {
                                selMonth.selectedIndex = y;
                                break;
                                }
                            }                   
                        for (var y=0;y<selDay.options.length;y++) {
                            if (selDay.options[y].value == day) {
                                selDay.selectedIndex = y;
                                break;
                                }
                            }
                        for (var y=0;y<selYear.options.length;y++) {
                            if (selYear.options[y].value == year) {
                                selYear.selectedIndex = y;
                                break;
                                }
                            }
					} 
					else if (txtDate){
					    txtDate.value = year + '-' + month + '-' + day;
					}				
				}				
				oCalendarMenu.hide();		
			});

			// Pressing the Esc key will hide the Calendar Menu and send focus back to 
			// its parent Button
			Event.on(oCalendarMenu.element, "keydown", function (p_oEvent) {			
				if (Event.getCharCode(p_oEvent) === 27) {
					oCalendarMenu.hide();
					this.focus();
				}			
			}, null, this);				
					
			var focusDay = function () {
				var oCalendarTBody = Dom.get("%(name)s-buttoncalendar").tBodies[0],
					aElements = oCalendarTBody.getElementsByTagName("a"),
					oAnchor;
				if (aElements.length > 0) {				
					Dom.batch(aElements, function (element) {					
						if (Dom.hasClass(element.parentNode, "today")) {
							oAnchor = element;
						}					
					});										
					if (!oAnchor) {
						oAnchor = aElements[0];
					}
					// Focus the anchor element using a timer since Calendar will try 
					// to set focus to its next button by default					
					YAHOO.lang.later(0, oAnchor, function () {
						try {
							oAnchor.focus();
						}
						catch(e) {}
					});				
				}				
			};

			// Set focus to either the current day, or first day of the month in 
			// the Calendar	when it is made visible or the month changes
			oCalendarMenu.subscribe("show", focusDay);
			oCalendar.renderEvent.subscribe(focusDay, oCalendar, true);
			// Give the Calendar an initial focus			
			focusDay.call(oCalendar);
			// Re-align the CalendarMenu to the Button to ensure that it is in the correct
			// position when it is initial made visible			
			oCalendarMenu.align();			
			// Unsubscribe from the "click" event so that this code is 
			// only executed once
			this.unsubscribe("click", onButtonClick);		
		};

		// Create an Overlay instance to house the Calendar instance
		oCalendarMenu = new YAHOO.widget.Overlay("%(name)s-calendarmenu", { visible: false });
		// Create a Button instance of type "menu"
		/*var oButton = new YAHOO.widget.Button( "%(name)s-calendarpicker",
		                                    {type: "menu", 											 
										    menu: oCalendarMenu, 
										    });*/

		var oButton = new YAHOO.widget.Button({ 
											type: "menu", 
											id: "%(name)s-calendarpicker", 
											label: '<img src="/++resource++calbtn.gif" alt="calendar"/> ', 
											menu: oCalendarMenu, 
											container: "%(name)s-datefields" });

										    
		oButton.on("appendTo", function () {
			// Create an empty body element for the Overlay instance in order 
			// to reserve space to render the Calendar instance into.
			oCalendarMenu.setBody("&#32;");
			oCalendarMenu.body.id = "%(name)s-calcontainer";		
		});		

		// Add a "click" event listener that will render the Overlay, and 
		// instantiate the Calendar the first time the Button instance is 
		// clicked.
		oButton.on("click", onButtonClick);
	});	

}());
//]]>  

