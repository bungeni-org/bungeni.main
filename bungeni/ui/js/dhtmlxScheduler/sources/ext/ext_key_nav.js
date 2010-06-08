//Initial idea and implementation by Steve MC
(function (){

var lightboxopen = false;

scheduler.attachEvent("onBeforeLightbox",function(){ lightboxopen = true; return true; })
scheduler.attachEvent("onAfterLightbox",function(){ lightboxopen = false; return true; })

dhtmlxEvent(document,(_isOpera?"keypress":"keydown"),function(e){
	e=e||event;
	if (!lightboxopen){
		if (e.keyCode == 37 || e.keyCode == 39) { // Left-Arrow
			e.cancelBubble = true;
			
		    var next = scheduler.date.add(scheduler._date,(e.keyCode == 37 ? -1 : 1 ),scheduler._mode);
		    scheduler.setCurrentView(next);
		    return true;
		}	
	}
})

})();