(function($) {
  $(document).ready(function() {
      $('#sitting-date').datepicker({ dateFormat: 'yy-mm-dd',
            changeMonth: true,
            changeYear: true  });
      $('#fielduntil').datepicker({ dateFormat: 'yy-mm-dd',
            changeMonth: true,
            changeYear: true  });
      $('#sitting-start-time').clockpick({layout: 'horizontal', military : true});
      $('#sitting-end-time').clockpick({layout: 'horizontal', military : true});
    

    
      $('#weeklyrecurrence').hide();
      $('#monthlyrecurrence').hide();
      $('#recurrencetimes').hide();
      $('#exceptiondates').hide();
    

      $('#notrecurrent').click(function () {

          $('#weeklyrecurrence').hide();
          $('#monthlyrecurrence').hide();
          $('#recurrencetimes').hide();
          $('#exceptiondates').hide();
        });

      $('#recurrentweekly').click(function () {

          $('#weeklyrecurrence').show();
          $('#monthlyrecurrence').hide();
          $('#recurrencetimes').show();
          $('#exceptiondates').show();
        });

      $('#recurrentmonthly').click(function () {

          $('#weeklyrecurrence').hide();
          $('#monthlyrecurrence').show();
          $('#recurrencetimes').show();
          $('#exceptiondates').show();
        });
    });
 })(jQuery);
