function get_statuses(object_type){
  $.ajax(
    {
      url: 'ajax_get_class_statuses',
      cache: false,
      success: function(data){
	if (data == 'ERROR'){
	  window.alert("Error getting statuses for " + 
                       object_type);
	}
	else {
	  $("#form\\.status").html("");
	  $(data).appendTo("#form\\.status");
	}
      },
      data: {'dotted_name': object_type}
    });
}

function get_fields(object_type){
  $.ajax(
    {
      url: 'ajax_get_class_fields',
      cache: false,
      success: function(data){
	if (data == 'ERROR'){
	  window.alert("Error getting fields for " + object_type);
	}
	else {
	  $("#form\\.field").html("");
	  $(data).appendTo("#form\\.field");
	}
      },
      data: {'dotted_name': object_type}
    });
}

$(document).ready(
  function(){
    $("#form\\.content_type").change(
      function() {
	if($(this).val()){
	  get_statuses($(this).val());
	  get_fields($(this).val());
	}else{
	  $("#form\\.status").html("");
	  $("#form\\.field").html("");
	}
      });
  }
);
