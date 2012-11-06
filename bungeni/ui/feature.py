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


ZCML_SLUG = """
    <configure xmlns="http://namespaces.zope.org/zope"
        xmlns:browser="http://namespaces.zope.org/browser"
        xmlns:i18n="http://namespaces.zope.org/i18n"
        i18n_domain="bungeni"
        >
        <include package="zope.browsermenu" file="meta.zcml" />
        <include package="zope.browserpage" file="meta.zcml" />
{ui_zcml_decls}
    </configure>
    """

UI_ZC_DECLS = []


def setup_customization_ui():
    """Called from ui.app.on_wsgi_application_created_event -- must be called
    late, at least as long as there other ui zcml directives (always executed 
    very late) that need to have been executed prior to this e.g. 
    creation of specific menus such as "context_actions".
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
            <browser:page name="{name}"
                for="{for_}"
                class="{class_}"
                permission="bungeni.{type_key}.{privilege}"
                layer="bungeni.ui.interfaces.IBungeniSkin"
            />"""
    workspace_view_vars_Add = dict(
        for_="bungeni.core.interfaces.IWorkspaceDraft",
        class_="bungeni.ui.workspace.WorkspaceAddForm",
        privilege="Add",
    )
    forms_view_vars_Add = dict(
        name="add",
        class_="bungeni.ui.forms.common.AddForm",
        privilege="Add",
    )
    forms_view_vars_View = dict(
        name="view",
        class_="bungeni.ui.forms.common.DisplayForm",
        privilege="View",
    )
    forms_view_vars_Edit = dict(
        name="edit",
        class_="bungeni.ui.forms.forms.DiffEditForm",
        privilege="Edit",
    )
    forms_view_vars_Delete = dict(
        name="delete",
        class_="bungeni.ui.forms.common.DeleteForm",
        privilege="Delete",
    )
    
    UI_ZC_DECLS[:] = []
    # we assume that non-custom types have already been set up as needed
    for type_key, ti in capi.iter_type_info(scope="custom"):
        UI_ZC_DECLS.append("""
            
            <!-- {type_key} -->""".format(type_key=type_key))
        
        type_title = naming.split_camel(naming.model_name(type_key))
        # model interface is defined, but container interface is not yet
        model_interface_qualname = naming.qualname(ti.interface)
        container_interface_qualname = "bungeni.models.interfaces.%s" % (
                naming.container_interface_name(type_key))
        
        # generic forms (independent of any feature)
        UI_ZC_DECLS.append(VIEW_TMPL.format(
                type_key=type_key,
                for_=container_interface_qualname,
                **forms_view_vars_Add))
        for form_view_vars in (
                forms_view_vars_View, 
                forms_view_vars_Edit, 
                forms_view_vars_Delete
            ):
            UI_ZC_DECLS.append(VIEW_TMPL.format(
                    type_key=type_key,
                    for_=model_interface_qualname,
                    **form_view_vars))
        
        # workspace
        if ti.workflow.has_feature("workspace"):
            log.debug("Setting up workspace UI for type [%s]" % (type_key))
            # add menu item
            # !+workspace_feature_add(mr, oct-2012) note that an enabled
            # workspace feature also implies "add" functionality for the type
            UI_ZC_DECLS.append(MENU_ITEM_TMPL.format(
                    type_key=type_key, 
                    title=type_title,
                    for_="*",
                    action="../../draft/add_{k}".format(k=type_key),
                    **menu_item_vars_Add))
            # edit menu item
            UI_ZC_DECLS.append(MENU_ITEM_TMPL.format(
                    type_key=type_key,
                    title="Edit {t}".format(t=type_title),
                    for_=model_interface_qualname,
                    action="edit",
                    **menu_item_vars_Edit))
            # delete menu item
            UI_ZC_DECLS.append(MENU_ITEM_TMPL.format(
                    type_key=type_key,
                    title="Delete {t}".format(t=type_title),
                    for_=model_interface_qualname,
                    action="delete",
                    **menu_item_vars_Delete))
            # workspace add view
            UI_ZC_DECLS.append(VIEW_TMPL.format(
                    type_key=type_key,
                    name="add_{type_key}".format(type_key=type_key),
                    **workspace_view_vars_Add))


def apply_customization_ui():
    """Called from ui.app.on_wsgi_application_created_event -- must be called
    AFTER custom types have been catalysed.
    """
    # combine config string and execute it
    zcml = ZCML_SLUG.format(ui_zcml_decls="".join([ zd for zd in UI_ZC_DECLS ]))
    log.debug("Executing UI feature configuration:\n%s" % (zcml))
    xmlconfig.string(zcml)

