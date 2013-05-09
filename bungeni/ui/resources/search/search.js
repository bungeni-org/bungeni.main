/**
 * Search JS utilities
 * - Show or hide advanced search options.
 * 
 * $Id$
 */
jQuery.fn.bindAdvancedSearch = function(){
    var advanced_block_selector = "fieldset#advanced_opts";
    var advanced_block_selector_hdden = "fieldset#advanced_opts:hidden";
    var hidden_class  = "ui-icon-plus";
    var visible_class  = "ui-icon-minus";
    var hide = (window.location.search.indexOf("advanced=true")<0);
    
    var button_el = $("span#advanced_options_button");
    var advanced_input = $("input[name=advanced]", this);
    var link_el = $("a#show_advanced_options", this);
    $(button_el).addClass("ui-icon");
    
    if (hide){
        $(advanced_block_selector).hide();
        $(advanced_input).attr('value', 'false');
    }
    
    if ($(advanced_block_selector_hdden).length){
        $(button_el).addClass(hidden_class).removeClass(visible_class);
    }else{
        $(button_el).addClass(visible_class).removeClass(hidden_class);
    }
    jQuery(link_el).click(function(event){
        $(advanced_block_selector).toggle();
        hidden = Boolean($(advanced_block_selector_hdden).length);
        if (hidden){
            $(button_el).addClass(hidden_class).removeClass(visible_class);
            $(advanced_input).attr('value', 'false');
        }else{
            $(button_el).addClass(visible_class).removeClass(hidden_class);
            $(advanced_input).attr('value', 'true');
        }
    })
}

jQuery(document).ready(function(){
        jQuery('form').bindAdvancedSearch();
    });
