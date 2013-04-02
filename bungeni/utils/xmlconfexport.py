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
    import os
    from bungeni.capi import capi
    path = capi.get_path_for(where, ".auto")
    if not os.path.exists(path):
        os.makedirs(path)
    open(capi.get_path_for(path, file_name), "w").write(contents)

def write_all():
    """
    Write system parameters to bungeni_custom
    """

    # list of conditions used in workflows
    write_to_custom("workflows", "_conditions.xml", output_conditions())
    # list of workflow features per type
    write_to_custom("workflows", "_features.xml", output_features())
    # list of workflow features per type
    write_to_custom("workflows", "_actions.xml", output_actions())
    # list of form validations
    write_to_custom("forms", "_validations.xml", output_validations())
    # list of form field render types
    write_to_custom("forms", "_rendertypes.xml", output_rendertypes())
    # list of form field value types
    write_to_custom("forms", "_valuetypes.xml", output_valuetypes())
    # list of form constraints
    write_to_custom("forms", "_constraints.xml", output_constraints())
    # list of form derived fields
    write_to_custom("forms", "_derived.xml", output_derived_fields())
    # list of vocabularies
    write_to_custom("forms", "_vocabularies.xml", output_vocabularies())
    # list of all roles in system
    write_to_custom("", "_roles.xml", output_all_roles())


def output_actions():
    """
    Provides a list of workflow conditions in the system in XML format
    """

    import bungeni_custom.workflows._actions as actions
    import inspect

    li_actions = []
    li_actions.append("<actions>")
    for name in dir(actions):
        obj = getattr(actions, name)        
        if inspect.isfunction(obj):
            desc = ""
            if hasattr(obj, "description"):
                desc = obj.description
            else:
                desc = name
            li_actions.append(
                '  <action name="%(name)s">%(desc)s</action>' %
                {"name": name, "desc": desc}
                )
    li_actions.append("</actions>")
    return ("\n".join(li_actions)).encode("utf-8")
    

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
            desc = ""
            if hasattr(obj, "description"):
                desc = obj.description
            else:
                desc = name
            li_conds.append(
                '  <condition name="%(name)s">%(desc)s</condition>' %
                {"name": name, "desc": desc}
                )
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
            desc = ""
            if hasattr(obj, "description"):
                desc = obj.description
            else:
                desc = name
            li_vals.append(
                '  <validation name="%(name)s">%(desc)s</validation>' %
                {"name": name, "desc": desc}
                )
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
    

def output_constraints():
    """
    Provides a list of constraints available to the forms
    """

    import bungeni_custom.forms._constraints as cons
    import inspect
    
    li_cons = []
    li_cons.append("<constraints>")
    for name in dir(cons):
        if not name.startswith("__"):
            obj = getattr(cons, name)  
            desc = ""
            if hasattr(obj, "description"):
                desc = obj.description
            else:
                desc = name
            li_cons.append(
                '  <constraint name="%(name)s">%(desc)s</constraint>' %
                {"name": name, "desc": desc}
                )
    li_cons.append("</constraints>")
    return ("\n".join(li_cons)).encode("utf-8")

        
def output_derived_fields():
    """
    Provides a list of derived fields available to the forms
    """

    import bungeni_custom.forms._derived as dfs
    import inspect
    
    li_dfs = []
    li_dfs.append("<derivedFields>")
    for name in dir(dfs):
        obj = getattr(dfs, name)        
        if inspect.isfunction(obj):
            desc = ""
            if hasattr(obj, "description"):
                desc = obj.description
            else:
                desc = name        
            li_dfs.append(
                '  <derivedField name="%(name)s">%(desc)s</derivedField>' %
                {"name": name, "desc": desc}
                )
    li_dfs.append("</derivedFields>")
    return ("\n".join(li_dfs)).encode("utf-8")
    

def output_all_roles():
    """
    Outputs all the roles in the system, including :
      bungeni.models.roles.zcml
      bungeni_custom.sys.roles.zcml
    """
    from zope.component import getUtilitiesFor
    from zope.securitypolicy.interfaces import IRole
    roles = [name for name, role in getUtilitiesFor(IRole)]
    li_roles = []
    li_roles.append("<roles>")
    for role in roles:
        """get only roles that are bungeni specific """
        if (role.startswith("bungeni.")):
            li_roles.append('<role name="%s" />' % role[len("bungeni."):])
    li_roles.append("</roles>")
    return ("\n".join(li_roles)).encode("utf-8")    
    
   
def output_features():
    """
    provides a list of features per type
    """

    from bungeni.capi import capi
    from zope.dottedname.resolve import resolve
    from bungeni.alchemist.catalyst import MODEL_MODULE
    from bungeni.utils import naming

    # get a list of available types in a list
    li_available_types = []
    for type_key, ti in capi.iter_type_info():
        li_available_types.append(type_key)
        
    li_features = []
    li_features.append("<featuresByType>")
    
    for type_key, ti in capi.iter_type_info():
        obj =  resolve("%s.%s" % (MODEL_MODULE.__name__, naming.model_name(type_key)))       
        if len(obj.available_dynamic_features) > 0:
            li_features.append('  <features for="%s">' % type_key)
            for dyn_feature in obj.available_dynamic_features:
                workflow = False
                # check if feature is a type
                if dyn_feature in li_available_types:
                    # feature is a type, so it has a workflow
                    workflow = True
                li_features.append(
                    '     <feature name="%(name)s" workflow="%(wf)s" />' % 
                    {"name": dyn_feature, "wf": workflow}
                )
            li_features.append("  </features>")
    li_features.append("</featuresByType>")                    
    return "\n".join(li_features).encode("utf-8")    


def output_vocabularies():
    """
    Provides a list of all the vocabularies in the system
    """
    
    from zope.component import getUtilitiesFor
    from zope.schema.interfaces import IVocabularyFactory

    all_vocabs = getUtilitiesFor(IVocabularyFactory)
    li_vocabs = []
    li_vocabs.append("<vocabularies>")
    for vocab_name, vocab in all_vocabs:
        vocab_fq_class = "%s.%s" % (vocab.__module__ , vocab.__class__.__name__) 
        li_vocabs.append(
        '  <vocabulary name="%s"  type="%s" />' % (
            vocab_name, vocab_fq_class
          )
        )
    li_vocabs.append("</vocabularies>")
    return "\n".join(li_vocabs).encode("utf-8")    

