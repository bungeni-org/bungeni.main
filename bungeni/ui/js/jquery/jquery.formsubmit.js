/* Prevents double submission of forms and action items.
 * Also applies css class to submit buttons to submit inputs
 * as interfaces hints for users.
 * 
 * Example from http://henrik.nyh.se/2008/07/jquery-double-submission
 * 
 * $Id$
 */
jQuery.fn.preventDuplicateSubmission = function(){
    jQuery(this).submit(function(){
        if(typeof(this.isSubmitted) != "undefined"){
            return false;
        }else{
            this.isSubmitted = true;
            jQuery("input:submit", this).addClass("ac_button_disabled");
            jQuery.blockUI({ message: jQuery("#processing_indicatron") });
            return true;
        }
        });
}

jQuery.fn.preventDuplicateMenuAction = function(){
    jQuery(this).click(function(event){
        parent_dl = jQuery(this).parents("dl");
        if(typeof(parent_dl.isPushed) != "undefined"){
            event.preventDefault();
        }else{
            parent_dl.isPushed = true;
            jQuery.blockUI({ message: jQuery("#processing_indicatron") });
        }
        });
}

jQuery(document).ready(function(){
        jQuery('form').preventDuplicateSubmission();
        jQuery("dd.actionMenuContent  a").preventDuplicateMenuAction();
    });
