function listTogglr(){
	var viewletDateToggle = $('#whats-on-overview .whats-on-viewlet dd ul li h2');
	viewletDateToggle.css({
		background: 'url(/static/images/minus.png) 2px 4px no-repeat',
		paddingLeft: '20px',
		cursor: 'pointer'
	});
	viewletDateToggle.click(function(){
		var state = $(this).siblings('ul').css('display');
		if (state == 'hidden' || state == 'none') {
			$(this).css('background-image', 'url(/static/images/minus.png)');
        	$(this).siblings('ul').slideDown('fast');
      	}
      	else {
        	$(this).css('background-image', 'url(/static/images/plus.png)');
        	$(this).siblings('ul').slideUp('fast');
      	}
	});
  
	var viewlet = $('#fieldset-upcoming-sittings ul li ul li');
	// check if the link was clicked - if it was don't animate, just follow the link.
	var viewletLink = viewlet.children('a');
	var linkClicked = false;
	viewletLink.click(function(){
		linkClicked = true;
	});
	viewlet.css({
	  	background: '#fff url(/static/images/plus.png) 2px 4px no-repeat',
		paddingLeft: '20px',
		cursor: 'pointer'
  	});
	$('#fieldset-upcoming-sittings ul li ul li ul li').css({background: '#fff', padding: '0'});
	viewlet.children('ul').hide();
	viewlet.click(function(){
		if(!linkClicked){
			var state = $(this).children('ul').css('display');
			if(state == 'hidden' || state == 'none'){
				$(this).css('background-image','url(/static/images/minus.png)');
				$(this).children('ul').slideDown('fast');
			}
			else {
				$(this).css('background-image','url(/static/images/plus.png)');
				$(this).children('ul').slideUp('fast');
			}
		}
	});
	$('#fieldset-upcoming-sittings ul li ul li ul li').css('cursor','default');
	$('#fieldset-upcoming-sittings ul li ul li ul li').click(function(){
		$(this).css('background','#fff');
    });
}
function searchTogglr(){
	var portletHeader = $('#portletArchiveDates .portletHeader');
	var portletHeaderSpan = portletHeader.children('span');
	portletHeaderSpan.css({
		float:'right',
		display:'block',
		paddingLeft: '20px',
		cursor: 'pointer',
		background: 'url(/static/images/minus.png) 2px 4px no-repeat'
	});
	portletHeaderSpan.hover(function(){
		portletHeaderSpan.css('text-decoration','underline');
	},function(){
		portletHeaderSpan.css('text-decoration','none');
	});
	var portletItem = $('#portletArchiveDates .portletItem');
	portletItem.css('clear','right');
	if(!portletItem.hasClass('dates-filtered')){
		portletItem.hide();
		portletHeaderSpan.css('background-image','url(/static/images/plus.png)');
	}
	portletHeader.click(function(){
		var state = portletItem.css('display');
		if(state == 'hidden' || state == 'none'){
			portletHeaderSpan.css('background-image','url(/static/images/minus.png)');
			portletItem.slideDown('fast');
		}
		else {
			portletHeaderSpan.css('background-image','url(/static/images/plus.png)');
			portletItem.slideUp('fast');
		}
	});
}
$(document).ready(function(){
    searchTogglr();
    listTogglr();
    // Hides the dead links in the global nav.
    $('#portal-globalnav ul.level0 li a').each(function(){
		var link = $(this).attr('href');
		if(link.indexOf('#') != -1){
			$(this).parent().hide();
		}
	});
	
	/*
	 * AutoComplete Code - buggy.
	 *
	// replace the <select> drop down with an input field with auto suggest.
	var optionValues = []; // holds the values of the <option>s
	var optionTexts = []; // holds the text of the <option>s
	
	// holds the option that was the default
	var defaultOptionText = $('#form\\.owner_id > option:selected').text();
	var defaultOptionValue = $('#form\\.owner_id > option:selected').val();
	
	var select = $('#form\\.owner_id');
	var selectOptions = $('#form\\.owner_id > option');
	selectOptions.each(function(){
		optionValues.push($(this).val());
		optionTexts.push($(this).text());
	});
	
	// hide the select and replace it with an input field.
	// and a hidden field to hold the result.
	var input = $(document.createElement('input'));
	var hiddenInput = $(document.createElement('input'));
	var container = $(document.createElement('div'));
	input.attr('id','owner_input');
	input.val(defaultOptionText);
	container.attr('id','owner_container');
	hiddenInput.attr('id','form.owner_id');
	hiddenInput.attr('name','form.owner_id');
	hiddenInput.attr('type','hidden');
	hiddenInput.val(defaultOptionValue);
	select.before(input);
	input.after(container);
	input.after(hiddenInput);
	// remove the select so that we don't send two different 
	// values for the name form.owner_id.
	select.remove();
	// create a local Data Source for the AutoComplete to use.
	var oDS = new YAHOO.util.LocalDataSource(optionTexts);
	oDS.responseSchema = {
		fields: ["texts"]
	};
	
	// Instantiate the AutoComplete
	var oAC = new YAHOO.widget.AutoComplete('owner_input', 'owner_container', oDS);
	oAC.prehighlightClassName = 'yui-ac-prehighlihgt';
	oAC.forceSelection = true;
	
	$('#owner_input').blur(function(){
		var value = $(this).val();
		for (var i = 0; i < optionTexts.length; i++) {
			if (value == optionTexts[i]) {
				hiddenInput.attr('value', optionValues[i]);
			}
		}
	});
	*/
});
