function listTogglr(){
  var viewletDateToggle = $('#whats-on-overview .whats-on-viewlet dd ul li h2');
  viewletDateToggle.css('background','url(/static/images/minus.png) 2px 4px no-repeat');
  viewletDateToggle.css('padding-left','20px');
  viewletDateToggle.css('cursor','pointer');
  viewletDateToggle.click(function(){
      var state = $(this).siblings('ul').css('display');
      if (state == 'hidden' || state == 'none') {
        $(this).css('background-image', 'url(/static/images/minus.png)');
        $(this).siblings('ul').slideDown();
      }
      else {
        $(this).css('background-image', 'url(/static/images/plus.png)');
        $(this).siblings('ul').slideUp();
      }
    });
  
  var viewlet = $('#fieldset-upcoming-sittings ul li ul li');
  viewlet.css('background','#fff url(/static/images/plus.png) 2px 4px no-repeat');
  viewlet.css('padding-left','20px');
  viewlet.css('cursor','pointer');
  $('#fieldset-upcoming-sittings ul li ul li ul li').css({background: '#fff', padding: '0'});
  viewlet.children('ul').hide();
  viewlet.click(function(){
      var state = $(this).children('ul').css('display');
      if(state == 'hidden' || state == 'none'){
        $(this).css('background-image','url(/static/images/minus.png)');
        $(this).children('ul').slideDown();
      }
      else {
        $(this).css('background-image','url(/static/images/plus.png)');
        $(this).children('ul').slideUp();
      }
    });
  $('#fieldset-upcoming-sittings ul li ul li ul li').css('cursor','default');
  $('#fieldset-upcoming-sittings ul li ul li ul li').click(function(){
      $(this).css('background','#fff');
    });
}
function searchTogglr(){
  var portletHeader = $('#portletArchiveDates .portletHeader');
  portletHeader.css('cursor','pointer');
				portletHeader.css('background','url(/static/images/minus.png) 2px 4px no-repeat');
                                portletHeader.css('padding-left','20px');
                                portletHeader.hover(function(){
                                    portletHeader.css('text-decoration','underline');
                                  },function(){
                                    portletHeader.css('text-decoration','none');
                                  });
                                var portletItem = $('#portletArchiveDates .portletItem');
                                portletItem.css('padding-left','10px');
                                if(!portletItem.hasClass('dates-filtered')){
                                  portletItem.hide();
                                  portletHeader.css('background-image','url(/static/images/plus.png)');
                                }
                                portletHeader.click(function(){
                                    var state = portletItem.css('display');
                                    if(state == 'hidden' || state == 'none'){
                                      portletHeader.css('background-image','url(/static/images/minus.png)');
                                      portletItem.slideDown('fast');
                                    }
                                    else {
                                      portletHeader.css('background-image','url(/static/images/plus.png)');
                                      portletItem.slideUp('fast');
                                    }
                                  });
}
$(document).ready(function(){
    searchTogglr();
    listTogglr();
  });
