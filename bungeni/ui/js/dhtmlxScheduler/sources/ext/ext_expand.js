scheduler.attachEvent("onTemplatesReady",function(){
   var t = document.createElement("DIV");
   t.className="dhx_expand_icon";
   scheduler._obj.appendChild(t);   
   
   function expand(obj){
      var t=obj;
      do {
         obj._position = obj.style.position||"";
         obj.style.position = "static";
         
      } while ((obj = obj.parentNode) && obj.style );
      t.style.position="absolute";
      t.style.zIndex = 9998;
      t._width = t.style.width;
      t._height = t.style.height;
      t.style.width = t.style.height = "100%";
      t.style.top = t.style.left = "0px";
      
	  var top =document.body;
	  	  top.scrollTop = 0;
	  	  
	  top = top.parentNode;
	  if (top)
   		  top.scrollTop = 0;
   	  document.body._overflow=document.body.style.overflow||"";
   	  document.body.style.overflow = "hidden";
   }
   
   function collapse(obj){
      var t=obj;
      do {
         obj.style.position = obj._position;
      } while ((obj = obj.parentNode) && obj.style );
      t.style.width = t._width;
      t.style.height = t._height;
      
      document.body.style.overflow=document.body._overflow;
   }
   
   t.onclick = function(){
      if (!this._expand)
         expand(scheduler._obj);
      else 
         collapse(scheduler._obj);
      this._expand=!this._expand;
      this.style.backgroundPosition="0px "+(this._expand?"0":"18")+"px";
      if (scheduler.callEvent("onSchedulerResize",[]))
         scheduler.update_view();
   }
   
	scheduler.show_cover=function(){
		this._cover=document.createElement("DIV");
		this._cover.className="dhx_cal_cover";
		this._obj.appendChild(this._cover);
	}

});