jQuery(document).ready(function(){
    jQuery("#dynatree").each(function(){
        container = jQuery(this);
        tree_div = jQuery("div", container);
        input = jQuery("input", container);
        if (tree_div.length && input.length){
            id_attr = jQuery(tree_div[0]).attr('id');
            input_el = input[0];
            jQuery(tree_div[0]).dynatree(
                {children: window[id_attr], 
                 selectMode:2,
                 checkbox:true,
                 onSelect: function(flag, node) {
                                var selected_nodes = jQuery(
                                    node.tree.$tree
                                ).dynatree('getSelectedNodes');
                                var field_values = [];
                                for (var idx=0; idx<selected_nodes.length; idx++) { 
                                    field_values.push(
                                        selected_nodes[idx].data.key
                                    );
                                };  
                                jQuery(input_el).val(
                                    field_values.join("|")
                                );
                            },
                }
            )
        }
    });
});
