# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""The Bungeni Application - Feature UI handling

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.feature")


from zope.configuration import xmlconfig
from bungeni.utils.capi import capi
from bungeni.utils import naming


def apply_customization_ui():
    """Called from ui.app.on_wsgi_application_created_event -- must be called
    late, at least as long as there other ui zcml directives (always executed 
    very late) that need to have been executed prior to this e.g. 
    creation of specific menus such as "context_actions".
    """
    ZCML_SLUG = """
        <configure xmlns="http://namespaces.zope.org/zope"
            xmlns:browser="http://namespaces.zope.org/browser"
            xmlns:i18n="http://namespaces.zope.org/i18n"
            i18n_domain="bungeni"
            >
            <include package="zope.browsermenu" file="meta.zcml" />
            <include package="zope.browserpage" file="meta.zcml" />
{zcml_decls}
        </configure>
        """
    
    MENU_ITEM_TMPL = """
            <browser:menuItem menu="{menu}"
                for="{for_}"
                action="{action}"
                title="{title}"
                order="{order}"
                permission="bungeni.{type_key}.{privilege}"
                layer="bungeni.ui.interfaces.IBungeniSkin"
            />"""
    menu_item_vars_Add = dict(
        menu="workspace_add_parliamentary_content",
        privilege="Add",
        order=7,
    )
    # !+ edit/delete used to be on layer="bungeni.ui.interfaces.IWorkspaceOrAdminSectionLayer"
    menu_item_vars_Edit = dict(
        menu="context_actions",
        privilege="Edit",
        order=10,
    )
    menu_item_vars_Delete = dict(
        menu="context_actions",
        privilege="Delete",
        order=99,
    )
    
    VIEW_TMPL = """
            <browser:page name="add_{type_key}"
                for="{for_}"
                class="{class_}"
                permission="bungeni.{type_key}.{privilege}"
                layer="bungeni.ui.interfaces.IBungeniSkin"
            />"""
    view_vars_Add = dict(
        for_="bungeni.core.interfaces.IWorkspaceDraft",
        class_="bungeni.ui.workspace.WorkspaceAddForm",
        privilege="Add",
    )
    
    _decls = []
    # we assume that non-custom types have already been set up as needed
    for type_key, ti in capi.iter_type_info(scope="custom"):
        
        type_title = naming.split_camel(naming.model_name(type_key))
        model_interface_qualname = "bungeni.models.interfaces.%s" % (
                naming.model_interface_name(type_key))
        
        if ti.workflow.has_feature("workspace"):
            log.debug("Setting up workspace UI for type [%s]" % (type_key))
            # add menu item
            # !+workspace_feature_add(mr, oct-2012) note that an enabled
            # workspace feature also implies "add" functionality for the type
            _decls.append(MENU_ITEM_TMPL.format(
                    type_key=type_key, 
                    title=type_title,
                    for_="*",
                    action="../../draft/add_{k}".format(k=type_key),
                    **menu_item_vars_Add))
            # edit menu item
            _decls.append(MENU_ITEM_TMPL.format(
                    type_key=type_key, 
                    title="Edit {t}".format(t=type_title),
                    for_=model_interface_qualname,
                    action="edit",
                    **menu_item_vars_Edit))
            # delete menu item
            _decls.append(MENU_ITEM_TMPL.format(
                    type_key=type_key, 
                    title="Delete {t}".format(t=type_title),
                    for_=model_interface_qualname,
                    action="delete",
                    **menu_item_vars_Delete))
            # add view
            _decls.append(VIEW_TMPL.format(
                    type_key=type_key, 
                    **view_vars_Add))
    
    # combine config string and execute it
    zcml = ZCML_SLUG.format(zcml_decls="".join([ zd for zd in _decls ]))
    log.debug("Executing UI feature configuration:\n%s" % (zcml))
    xmlconfig.string(zcml)

