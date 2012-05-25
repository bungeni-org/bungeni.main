tinyMCE.init({
        mode : "specific_textareas",
        editor_selector : "tinymce",
        theme : "advanced",
        theme_advanced_layout_manager : "SimpleLayout",
        plugins : "autolink,lists,spellchecker,pagebreak,style,layer,table,advhr,advimage,advlink,inlinepopups,insertdatetime,preview,searchreplace,contextmenu,paste,directionality,fullscreen,noneditable,visualchars,nonbreaking,xhtmlxtras,template",
        theme_advanced_toolbar_location : "top",
        theme_advanced_buttons3_add : "tablecontrols",
        theme_advanced_buttons1 : "bold,italic,underline,strikethrough,|,justifyleft,justifycenter,justifyright,justifyfull,|,styleselect,formatselect,fontselect,fontsizeselect",
        theme_advanced_buttons2 : "cut,copy,paste,pastetext,pasteword,|,search,replace,|,bullist,numlist,|,outdent,indent,blockquote,|,undo,redo,|,link,unlink,anchor,image,cleanup,code,|,insertdate,inserttime,preview,|,forecolor,backcolor",
        theme_advanced_buttons3 : "tablecontrols,|,hr,removeformat,visualaid,|,sub,sup,|,charmap,advhr,|,ltr,rtl,|,fullscreen",
        theme_advanced_toolbar_align : "left",
        theme_advanced_statusbar_location : "bottom",
        theme_advanced_resizing : true,
        height : "500",
        content_css : "/@@/tiny-mce-config/tinymce_config.css"
});
