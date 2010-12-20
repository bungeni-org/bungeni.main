(function($) { 
    $(document).ready(function(){  
        $("#groupsitting-form #actionsView").before('<div id="options" style="display:block"></div>');
        $("#form\\.bills_options\\.0").parents(".widget-multicheckboxwidget").appendTo("#options").css('display', 'inline-block');
        $("#form\\.bills_options\\.0").attr('disabled', false);
        $("#form\\.agenda_items_options\\.0").parents(".widget-multicheckboxwidget").appendTo("#options").css('display', 'inline-block');
        $("#form\\.agenda_items_options\\.0").attr('disabled', false);
        $("#form\\.motions_options\\.0").parents(".widget-multicheckboxwidget").appendTo("#options").css('display', 'inline-block');
        $("#form\\.motions_options\\.0").attr('disabled', false);
        $("#form\\.questions_options\\.0").parents(".widget-multicheckboxwidget").appendTo("#options").css('display', 'inline-block');
        $("#form\\.questions_options\\.0").attr('disabled', false);
        $("#form\\.tabled_documents_options\\.0").parents(".widget-multicheckboxwidget").appendTo("#options").css('display', 'inline-block');
        $("#form\\.tabled_documents_options\\.0").attr('disabled', false);
        $("#options span").css('padding','0 0 0 0');
        $("#form\\.bills_options\\.0").attr('checked', true);
        $("#form\\.bills_options\\.1").attr('checked', true);
        $("#form\\.agenda_items_options\\.0").attr('checked', true);
        $("#form\\.agenda_items_options\\.3").attr('checked', true);
        $("#form\\.motions_options\\.0").attr('checked', true);
        $("#form\\.motions_options\\.3").attr('checked', true);
        $("#form\\.questions_options\\.0").attr('checked', true);
        $("#form\\.questions_options\\.3").attr('checked', true);
        $("#form\\.tabled_documents_options\\.0").attr('checked', true);
        $("#form\\.tabled_documents_options\\.3").attr('checked', true);
        
        var pathname = window.location.pathname;
        var path = new Array();
        path = pathname.split("/");
        var report_type = path[path.length-1];
        if (report_type == "")
        {
            report_type = path[path.length-2];
        }  
        $("input#form\\.item_types\\.0").change(function () {
            if ($("#form\\.item_types\\.0").is(":checked"))
            {
                $('input[name="form.bills_options"]').attr('disabled', false);
               //alert( $('input[name="form.bill_options"]').val() );
            }
            else
            {
                 $('input[name="form.bills_options"]').attr('disabled', true);
                //alert( $('input[name="form.bill_options"]').val() );
            }
        });
        $("input#form\\.item_types\\.1").change(function () {
            if ($("#form\\.item_types\\.1").is(":checked"))
            {
                $('input[name="form.agenda_items_options"]').attr('disabled', false);
            }
            else
            {
                $('input[name="form.agenda_items_options"]').attr('disabled', true);
            }
        });
        $("input#form\\.item_types\\.2").change(function () {
            if ($("#form\\.item_types\\.2").is(":checked"))
            {
                $('input[name="form.motions_options"]').attr('disabled', false);
            }
            else
            {
                $('input[name="form.motions_options"]').attr('disabled', true);
            }
        });
        $("input#form\\.item_types\\.3").change(function () {
            if ($("#form\\.item_types\\.3").is(":checked"))
            {
                $('input[name="form.questions_options"]').attr('disabled', false);
            }
            else
            {
                $('input[name="form.questions_options"]').attr('disabled', true);
            }
        });
        $("input#form\\.item_types\\.4").change(function () {
            if ($("#form\\.item_types\\.4").is(":checked"))
            {
                $('input[name="form.tabled_documents_options"]').attr('disabled', false);
            }
            else
            {
                $('input[name="form.tabled_documents_options"]').attr('disabled', true);
            }
        });
        $("#form\\.report_type").change(function() {
            var choice = $("option:selected", this).val();
            if (choice == "Order of the day")
            {
                $("#form\\.item_types\\.0").attr('checked', true);
                $("#form\\.item_types\\.1").attr('checked', true);
                $("#form\\.item_types\\.2").attr('checked', true);
                $("#form\\.item_types\\.3").attr('checked', true);
                $("#form\\.item_types\\.4").attr('checked', true);
            }
            else if (choice == "Proceedings of the day")
            {
                $("#form\\.item_types\\.0").attr('checked', true);
                $("#form\\.item_types\\.1").attr('checked', true);
                $("#form\\.item_types\\.2").attr('checked', true);
                $("#form\\.item_types\\.3").attr('checked', true);
                $("#form\\.item_types\\.4").attr('checked', true);
            }
            else if (choice == "Weekly Business")
            {
                $("#form\\.item_types\\.0").attr('checked', true);
                $("#form\\.item_types\\.1").attr('checked', true);
                $("#form\\.item_types\\.2").attr('checked', true);
                $("#form\\.item_types\\.3").attr('checked', false);
                $("#form\\.item_types\\.4").attr('checked', true);
            }
            else if (choice == "Questions of the week")
            {
                $("#form\\.item_types\\.0").attr('checked', false);
                $("#form\\.item_types\\.1").attr('checked', false);
                $("#form\\.item_types\\.2").attr('checked', false);
                $("#form\\.item_types\\.3").attr('checked', true);
                $("#form\\.item_types\\.4").attr('checked', false);
            }
            $("#form\\.item_types\\.0").trigger('change');
            $("#form\\.item_types\\.1").trigger('change');
            $("#form\\.item_types\\.2").trigger('change');
            $("#form\\.item_types\\.3").trigger('change');
            $("#form\\.item_types\\.4").trigger('change');
        }).change();
        $("#form\\.item_types\\.0").attr('checked', true).trigger('change');
        $("#form\\.item_types\\.1").attr('checked', true).trigger('change');
        $("#form\\.item_types\\.2").attr('checked', true).trigger('change');
        $("#form\\.item_types\\.3").attr('checked', true).trigger('change');
        $("#form\\.item_types\\.4").attr('checked', true).trigger('change');
    });
 })(jQuery)
