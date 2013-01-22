# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Dumps various system parameters used in the xml configuration as XML

$Id: xmlconfexport.py 10366 2013-01-21 13:10:32Z ashok.hariharan $
"""


def write_to_custom(where, file_name, contents):
    """
    Helper api to write to bungeni_custom
    """
    
    from bungeni.capi import capi
    filepath = capi.get_path_for(where, file_name)
    open(filepath, "w").write(contents)

def write_all():
    """
    Write system parameters to bungeni_custom
    """

    # list of conditions used in workflows
    write_to_custom("workflows", "_conditions.xml", output_conditions())
    # list of form validations
    write_to_custom("forms", "_validations.xml", output_validations())
    # list of form field render types
    write_to_custom("forms", "_rendertypes.xml", output_rendertypes())
    # list of form field value types
    write_to_custom("forms", "_valuetypes.xml", output_valuetypes())
    # list of workflow features per type
    write_to_custom("workflows", "_features.xml", output_features())
    

def output_conditions():
    """
    Provides a list of workflow conditions in the system in XML format
    """

    import bungeni_custom.workflows._conditions as conds
    import inspect

    li_conds = []
    li_conds.append("<conditions>")
    for name in dir(conds):
        obj = getattr(conds, name)        
        if inspect.isfunction(obj):
            if hasattr(obj, "description"):
                li_conds.append(
                    '  <condition name="%(name)s">%(desc)s</condition>' %
                    {"name":name,"desc":obj.description}
                    )
            else:
                # dont include items without description
                pass
    li_conds.append("</conditions>")
    return ("\n".join(li_conds)).encode("utf-8")


def output_validations():
    """
    Provides a list of form validations in the system in XML format
    """

    import bungeni_custom.forms._validations as vals
    import inspect
    
    li_vals = []
    li_vals.append("<validations>")
    for name in dir(vals):
        obj = getattr(vals, name)        
        if inspect.isfunction(obj):
            if hasattr(obj, "description"):
                li_vals.append(
                    '  <validation name="%(name)s">%(desc)s</validation>' %
                    {"name":name,"desc":obj.description}
                    )
            else:
                # dont include items without description
                pass
    li_vals.append("</validations>")
    return ("\n".join(li_vals)).encode("utf-8")


def output_rendertypes():
    """
    Provides a list of rendering types for the forms
    """
    
    from bungeni.ui.descriptor.field import RENDERTYPE
    from bungeni.ui.descriptor.field import RENDERTYPE_WITH_VOCABULARIES
    
    li_rtype = []
    li_rtype.append("<renderTypes>")
    for rtype in RENDERTYPE:
        vocab = "false"
        if rtype in RENDERTYPE_WITH_VOCABULARIES:
            vocab = "true"
        li_rtype.append(
             '    <renderType name="%(name)s" vocabulary="%(vocab)s" />' % 
             {"name":rtype, "vocab":vocab}
             )
    li_rtype.append("</renderTypes>")
    return ("\n".join(li_rtype)).encode("utf-8")


def output_valuetypes():
    """
    Provides a list of valuetypes available to the forms and the corresponding
    rendertype for a value type 
    """

    from bungeni.ui.descriptor.field import WIDGETS

    li_widgets = []
    li_widgets.append("<valueTypes>")
    for (widget,info) in WIDGETS.items():
        li_widgets.append(
             '    <valueType name="%(name)s" rendertype="%(rtype)s" />' % 
             {"name": widget[0], "rtype": widget[1] }
             )
    li_widgets.append("</valueTypes>")
    return ("\n".join(li_widgets)).encode("utf-8")

   
def output_features():
    """
    provides a list of features per type
    """

    from bungeni.capi import capi
    from zope.dottedname.resolve import resolve
    from bungeni.alchemist.catalyst import MODEL_MODULE
    from bungeni.utils import naming

    li_features = []
    li_features.append("<featuresByType>")
    for type_key, ti in capi.iter_type_info():
        obj =  resolve("%s.%s" % (MODEL_MODULE.__name__, naming.model_name(type_key)))       
        if len(obj.available_dynamic_features) > 0:
            li_features.append('  <features for="%s">' % type_key)
            for dyn_feature in obj.available_dynamic_features:
                li_features.append('     <feature name="%s" />' % dyn_feature)
            li_features.append("  </features>")
    li_features.append("</featuresByType>")                    
    return "\n".join(li_features).encode("utf-8")    

