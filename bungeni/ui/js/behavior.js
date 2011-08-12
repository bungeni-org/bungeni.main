$(document).ready(function() {
      // wire workflow dropdown menu to use POST actions
      var menu_links = $('#context_workflow dd.actionMenuContent a');
      menu_links.bungeniPostWorkflowActionMenuItem();

      // set up parliament date range selection
      $("select[id=form.parliament]").bungeniTimeRangeSelect(false, false);

      // set up sitting time range form automation
      var select = $("select[id=form.sitting_type_id]"); // !+group_sitting_type_id
      var errors = select.parents("form").eq(0).find(".widget.error").length > 0;
      select.bungeniTimeRangeSelect(true, !errors);

      // set up calendar resizing
      $("#calendar-table").bungeniSafeResize();
      $("#scheduling-table tbody.reorder").dragRearrange();
      $(".scheduling-checkbox").clickScheduling();
                             
      // set up calendar ajax
      $('#weekly-calendar').bungeniCalendarInteractivity(true);
      $('#daily-calendar').bungeniCalendarInteractivity(false);
      
      $('#scheduling-calendar').bungeniInteractiveSchedule();
      $('#fieldset-mp-items').tablesorter();  
      $('#fieldset-mp-items').columnFilters({alternateRowClassNames:['odd','even']}); 
    });
