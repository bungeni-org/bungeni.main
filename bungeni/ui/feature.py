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
    
    def register_menu_item(type_key, privilege, title, for_, action,
            menu="context_actions", 
            order=10,
            layer="bungeni.ui.interfaces.IBungeniSkin"
        ):
        naming.MSGIDS.add(title) # for i18n extraction
        UI_ZC_DECLS.append(register_menu_item.TMPL.format(**locals()))
    register_menu_item.TMPL = """
            <browser:menuItem menu="{menu}"
                for="{for_}"
                action="{action}"
                title="{title}"
                order="{order}"
                permission="bungeni.{type_key}.{privilege}"
                layer="{layer}"
            />"""
    
    def register_form_view(type_key, privilege, name, for_, class_,
        layer="bungeni.ui.interfaces.IBungeniSkin"
    ):
        UI_ZC_DECLS.append(register_form_view.TMPL.format(**locals()))
    register_form_view.TMPL = """
            <browser:page name="{name}"
                for="{for_}"
                class="{class_}"
                permission="bungeni.{type_key}.{privilege}"
                layer="{layer}"
            />"""
    
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
        register_form_view(type_key, "Add", "add", container_interface_qualname,
            "bungeni.ui.forms.common.AddForm")
        register_form_view(type_key, "View", "view", model_interface_qualname,
            "bungeni.ui.forms.common.DisplayForm")
        register_form_view(type_key, "Edit", "edit", model_interface_qualname,
            "bungeni.ui.forms.forms.DiffEditForm")
        register_form_view(type_key, "Delete", "delete", model_interface_qualname,
            "bungeni.ui.forms.common.DeleteForm")
        
        # workspace
        if ti.workflow.has_feature("workspace"):
            log.debug("Setting up workspace UI for type [%s]" % (type_key))
            # add menu item
            # !+workspace_feature_add(mr, oct-2012) note that an enabled
            # workspace feature also implies "add" functionality for the type
            action = "../../draft/add_{k}".format(k=type_key)
            register_menu_item(type_key, "Add", type_title, "*", action,
                menu="workspace_add_parliamentary_content", order=7)
            # edit menu item
            # !+ edit/delete used to be on layer="bungeni.ui.interfaces.IWorkspaceOrAdminSectionLayer"
            title = "Edit {t}".format(t=type_title)
            register_menu_item(type_key, "Edit", title, model_interface_qualname, "edit",
                menu="context_actions", order=10)
            # delete menu item
            title = "Delete {t}".format(t=type_title)
            register_menu_item(type_key, "Delete", title, model_interface_qualname, "delete",
                menu="context_actions", order=99)
            # workspace add view
            name = "add_{type_key}".format(type_key=type_key)
            register_form_view(type_key, "Add", name,
                "bungeni.core.interfaces.IWorkspaceDraft",
                "bungeni.ui.workspace.WorkspaceAddForm")

        #events
        if ti.workflow.has_feature("event"):
            log.debug("Setting up events add menu for type %s", type_key)
            title = "Add {t} event".format(t=type_title)
            register_menu_item("event", "Add", title, model_interface_qualname, 
                "./events/add", menu="additems", order=21,
                layer=".interfaces.IWorkspaceOrAdminSectionLayer"
            )

def apply_customization_ui():
    """Called from ui.app.on_wsgi_application_created_event -- must be called
    AFTER custom types have been catalysed.
    """
    # combine config string and execute it
    zcml = ZCML_SLUG.format(ui_zcml_decls="".join([ zd for zd in UI_ZC_DECLS ]))
    log.debug("Executing UI feature configuration:\n%s" % (zcml))
    xmlconfig.string(zcml)

