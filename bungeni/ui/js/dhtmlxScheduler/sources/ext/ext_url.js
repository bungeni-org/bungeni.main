scheduler.attachEvent("onTemplatesReady",function(){
   var first = true;
   var s2d = scheduler.date.str_to_date("%Y-%m-%d");
   var d2s = scheduler.date.date_to_str("%Y-%m-%d");
   scheduler.attachEvent("onBeforeViewChange",function(om,od,m,d){
      if (first){
         first = false;
         var p={};
         var data=(document.location.hash||"").replace("#","").split(",");
         for (var i=0; i < data.length; i++) {
         	var s = data[i].split("=");
         	if (s.length==2)
         	p[s[0]]=s[1];
         }
         
         if (p.date || p.mode){
            this.setCurrentView((p.date?s2d(p.date):null),(p.mode||null));
            return false;
         }
      }
      var text = "#date="+d2s(d||od)+",mode="+(m||om);
      document.location.hash = text;
      return true;
   });
});