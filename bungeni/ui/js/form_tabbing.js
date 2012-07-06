/*
 * This is the code for the tabbed forms. It assumes the following markup:
 *
 * <form class="enableFormTabbing">
 *   <fieldset id="fieldset-[unique-id]">
 *     <legend id="fieldsetlegend-[same-id-as-above]">Title</legend>
 *   </fieldset>
 * </form>
 *
 * or the following
 *
 * <dl class="enableFormTabbing">
 *   <dt id="fieldsetlegend-[unique-id]">Title</dt>
 *   <dd id="fieldset-[same-id-as-above]">
 *   </dd>
 * </dl>
 *
 */

var ploneFormTabbing = {};

ploneFormTabbing._toggleFactory = function(container, tab_ids, panel_ids) {
    return function(e) {
        jQuery(tab_ids).removeClass('selected');
        jQuery(panel_ids).addClass('hidden');

        var orig_id = this.tagName.toLowerCase() == 'a' ? 
            '#' + this.id : jQuery(this).val();
        var id = orig_id.replace(/^#fieldsetlegend-/, "#fieldset-");
        jQuery(orig_id).addClass('selected');
        jQuery(id).removeClass('hidden');

        jQuery(container).find("input[name=fieldset.current]").val(orig_id);
    };
};

ploneFormTabbing._buildTabs = function(container, legends) {
    var threshold = 7; // if num tabs >7, then TABS are rendered as a SELECT!
    var tab_ids = [];
    var panel_ids = [];

    legends.each(function(i) {
        tab_ids[i] = '#' + this.id;
        panel_ids[i] = tab_ids[i].replace(/^#fieldsetlegend-/, "#fieldset-");
    });
    var handler = ploneFormTabbing._toggleFactory(
        container, tab_ids.join(','), panel_ids.join(','));

    if (legends.length > threshold) {
        var tabs = document.createElement("select");
        var tabtype = 'option';
        jQuery(tabs).change(handler).addClass('noUnloadProtection');
    } else {
        var tabs = document.createElement("ul");
        var tabtype = 'li';
    }
    jQuery(tabs).addClass('formTabs');

    legends.each(function() {
        var tab = document.createElement(tabtype);
        jQuery(tab).addClass('formTab');

        if (legends.length > threshold) {
            jQuery(tab).text(jQuery(this).text());
            tab.id = this.id;
            tab.value = '#' + this.id;
        } else {
            var a = document.createElement("a");
            a.id = this.id;
            a.href = "#" + this.id;
            jQuery(a).click(handler);
            var span = document.createElement("span");
            jQuery(span).text(jQuery(this).text());
            a.appendChild(span);
            tab.appendChild(a);
        }
        tabs.appendChild(tab);
        jQuery(this).remove();
    });
    
    jQuery(tabs).children(':first').addClass('firstFormTab');
    jQuery(tabs).children(':last').addClass('lastFormTab');
    
    return tabs;
};

ploneFormTabbing.select = function($which) {
    if (typeof $which == "string")
        $which = jQuery($which.replace(/^#fieldset-/, "#fieldsetlegend-"));

    if ($which[0].tagName.toLowerCase() == 'a') {
        $which.click();
        return true;
    } else if ($which[0].tagName.toLowerCase() == 'option') {
        $which.attr('selected', true);
        $which.parent().change();
        return true;
    } else {
        $which.change();
        return true;
    }
    return false;
};

ploneFormTabbing.initSelection = function(){
    var tabId = window.location.hash;
    tabId = tabId.replace("'", "").replace(/^#fieldset-/, "#fieldsetlegend-") || ":first";
    return tabId
}

ploneFormTabbing.initializeDL = function() {
    var tabs = jQuery(ploneFormTabbing._buildTabs(this, jQuery(this).children('dt')));
    jQuery(this).before(tabs);
    jQuery(this).children('dd').addClass('formPanel');

    tabs = tabs.find('li.formTab a,option.formTab');
    if (tabs.length)
        ploneFormTabbing.select(tabs.filter(ploneFormTabbing.initSelection()));
};

ploneFormTabbing.initializeForm = function() {
    var fieldsets = jQuery(this).children('fieldset');
    
    if (!fieldsets.length) return;
    
    var tabs = ploneFormTabbing._buildTabs(
        this, fieldsets.children('legend'));
    jQuery(this).prepend(tabs);
    fieldsets.addClass("formPanel");
    
    // The fieldset.current hidden may change, but is not content
    jQuery(this).find('input[name=fieldset.current]').addClass('noUnloadProtection');

    var tab_inited = false;

    jQuery(this).find('.formPanel:has(div.field.error)').each(function() {
        var id = this.id.replace(/^fieldset-/, "#fieldsetlegend-");
        var tab = jQuery(id);
        tab.addClass("notify");
        if (tab.length && !tab_inited)
            tab_inited = ploneFormTabbing.select(tab);
    });

    jQuery(this).find('.formPanel:has(div.field span.fieldRequired)')
        .each(function() {
        var id = this.id.replace(/^fieldset-/, "#fieldsetlegend-");
        jQuery(id).addClass('required');
    });

    if (!tab_inited) {
        jQuery('input[name=fieldset.current][value^=#]').each(function() {
            tab_inited = ploneFormTabbing.select(jQuery(this).val());
        });
    }

    if (!tab_inited) {
        var tabs = jQuery("form.enableFormTabbing li.formTab a,"+
                     "form.enableFormTabbing option.formTab,"+
                     "div.enableFormTabbing li.formTab a,"+
                     "div.enableFormTabbing option.formTab");
        if (tabs.length)
            ploneFormTabbing.select(tabs.filter(ploneFormTabbing.initSelection()));
    }

    jQuery("#archetypes-schemata-links").addClass('hiddenStructure');
    jQuery("div.formControls input[name=form.button.previous]," +
      "div.formControls input[name=form.button.next]").remove();
};

(function(jQuery) {
  jQuery(document).ready(function() {
      jQuery("form.enableFormTabbing,div.enableFormTabbing")
        .each(ploneFormTabbing.initializeForm);
      jQuery("dl.enableFormTabbing").each(ploneFormTabbing.initializeDL);
    });
})(jQuery);
