(function($) {
  $(document).ready(function() {
      // wire workflow dropdown menu to use POST actions
      var menu_links = $('#plone-contentmenu-workflow dd.actionMenuContent a');
      menu_links.bungeniPostWorkflowActionMenuItem();

      // set up parliament date range selection
      $("select[id=form.parliament]").bungeniTimeRangeSelect(false, false);

      // set up sitting time range form automation
      var select = $("select[id=form.sitting_type_id]");
      var errors = select.parents("form").eq(0).find(".widget.error").length > 0;
      select.bungeniTimeRangeSelect(true, !errors);

      // set up calendar resizing
      $("#calendar-table").bungeniSafeResize();
     /*
      // set up calendar item scheduling (drag and drop)
      $("#items-for-scheduling-bill tbody tr").bungeniDragAndDropScheduling();
      $("#items-for-scheduling-motion tbody tr").bungeniDragAndDropScheduling();
      $("#items-for-scheduling-question tbody tr").bungeniDragAndDropScheduling();
      $("#items-for-scheduling-agendaitem tbody tr").bungeniDragAndDropScheduling();
      $("#items-for-scheduling-tableddocument tbody tr").bungeniDragAndDropScheduling();
      $("#items-for-scheduling-heading tbody tr").bungeniDragAndDropScheduling();
      */       
      
      //Drag and drop within the schedule
      // $("#scheduling-table tbody tr").bungeniDragAndDropScheduling();
      
      $("#scheduling-table tbody").dragRearrange();
      // Set up calendar item scheduling (by clicking)
      $("#items-for-scheduling-bill tbody tr input").clickScheduling();
      $("#items-for-scheduling-motion tbody tr input").clickScheduling();
      $("#items-for-scheduling-question tbody tr input").clickScheduling();
      $("#items-for-scheduling-agendaitem tbody tr input").clickScheduling();
      $("#items-for-scheduling-tableddocument tbody tr input").clickScheduling();
      $("#items-for-scheduling-heading tbody tr input").clickScheduling();
                             
      // set up calendar ajax
      $('#weekly-calendar').bungeniCalendarInteractivity(true);
      $('#daily-calendar').bungeniCalendarInteractivity(false);
     //$('#scheduling-calendar').bungeniSchedulingCalendar();
      $('#scheduling-calendar').bungeniInteractiveSchedule();
      
      // sort workspace tables
      $('#workspace-table-items-action-required').tablesorter();
      $('#workspace-table-draft_bills').tablesorter();
      $('#workspace-table-items-in-stage').tablesorter();
      
      $('#workspace-table-items-draft').tablesorter();
      $('#workspace-table-items-in-progress').tablesorter();
      $('#workspace-table-my_groups').tablesorter();
      $('#workspace-table-items-archived').tablesorter();
      $('#workspace-table-items-approved').tablesorter();
      $('#workspace-table-sitting-draft').tablesorter();
      $('#fieldset-mp-items').tablesorter();
      $('#workspace-table-clerks-items-action-required').tablesorter();
      $('#workspace-table-questions-pending-response').tablesorter();     
      $('#workspace-table-items-pending-schedule').tablesorter();   
           
      // set up table filters 
      $('#workspace-table-items-action-required').columnFilters({alternateRowClassNames:['odd','even']});
      $('#workspace-table-draft_bills').columnFilters({alternateRowClassNames:['odd','even']});
      $('#workspace-table-items-in-stage').columnFilters({alternateRowClassNames:['odd','even']});
      
      $('#workspace-table-items-draft').columnFilters({alternateRowClassNames:['odd','even']});
      $('#workspace-table-items-in-progress').columnFilters({alternateRowClassNames:['odd','even']});
      //$('#workspace-table-my_groups').columnFilters({alternateRowClassNames:['odd','even']});
      $('#workspace-table-items-archived').columnFilters({alternateRowClassNames:['odd','even']});
      $('#workspace-table-items-approved').columnFilters({alternateRowClassNames:['odd','even']});
      $('#workspace-table-sitting-draft').columnFilters({alternateRowClassNames:['odd','even']});
      $('#fieldset-mp-items').columnFilters({alternateRowClassNames:['odd','even']});
      $('#workspace-table-clerks-items-action-required').columnFilters({alternateRowClassNames:['odd','even']});
      $('#workspace-table-questions-pending-response').columnFilters({alternateRowClassNames:['odd','even']});
      $('#workspace-table-items-pending-schedule').columnFilters({alternateRowClassNames:['odd','even']});      
    });
 })(jQuery);
