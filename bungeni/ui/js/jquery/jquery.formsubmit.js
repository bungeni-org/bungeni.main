/* Prevents double submission of forms.
 * Also applies css class to submit buttons to submit inputs
 * as interfaces hints for users.
 * 
 * Original here http://henrik.nyh.se/2008/07/jquery-double-submission
 * 
 * $Id:$
 */
jQuery.fn.preventDuplicateSubmission = function(){
    jQuery(this).submit(function(){
        if(typeof(this.isSubmitted) != "undefined"){
            return false;
        }else{
            this.isSubmitted = true;
            jQuery("input:submit", this).addClass("ac_button_disabled");
            return true;
        }
        });
}

jQuery(document).ready(function(){
        jQuery('form').preventDuplicateSubmission();
    });
