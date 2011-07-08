jQuery(document).ready(function(){
	
	function set_editing_state() {
		// Sends ajax request every 20 seconds
		// to notify that current document is still
		// being edited. Receives amount of users
		// that also edit the document and shows it
		// to the user.
		jQuery.ajax({
			url: 'nowediting',
			method: 'GET',
			dataType: 'text',
			cache: false,
			success: function(data) {
				$('#nowediting').html(data);
				setTimeout(set_editing_state, 20000);
			}
		});
		
	}
	
	setTimeout(set_editing_state, 20000);
});