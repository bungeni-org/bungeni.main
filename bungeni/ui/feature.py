# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""The Bungeni Application - Feature UI handling

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.feature")


from zope.configuration import xmlconfig
from bungeni.models import domain
from bungeni.models.interfaces import IBungeniGroup
from bungeni.capi import capi
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

    def register_api_view(type_key, for_):
        UI_ZC_DECLS.append(register_api_view.TMPL.format(**locals()))
    register_api_view.TMPL = """
            <browser:page name="view"
                for="{for_}"
                class="bungeni.ui.api.APIObjectView"
                permission="bungeni.{type_key}.View"
                layer="bungeni.ui.interfaces.IBungeniAPILayer"
            />"""

    def model_title(type_key):
        return naming.split_camel(naming.model_name(type_key))
    
    UI_ZC_DECLS[:] = []
    # we assume that non-custom types have already been set up as needed
    for type_key, ti in capi.iter_type_info(scope="custom"):
        UI_ZC_DECLS.append("""
            
            <!-- {type_key} -->""".format(type_key=type_key))
        
        type_title = model_title(type_key)
        # model interface is defined, but container interface is not yet
        model_interface_qualname = naming.qualname(ti.interface)
        container_interface_qualname = "bungeni.models.interfaces.%s" % (
                naming.container_interface_name(type_key))
        
        # generic forms (independent of any feature)
        # add
        register_form_view(type_key, "Add", "add", container_interface_qualname,
            "bungeni.ui.forms.common.AddForm")
        # view
        register_form_view(type_key, "View", "view", model_interface_qualname,
            "bungeni.ui.forms.common.DisplayForm")
        
        register_api_view(type_key, model_interface_qualname)
        # edit !+DiffEditForm prior to r10032, doc-archetyped types were being
        # *declared* to use bungeni.ui.forms.forms.DiffEditForm, but this
        # is not the edit view tht was actually being used!
        #register_form_view(type_key, "Edit", "edit", model_interface_qualname,
        #    "bungeni.ui.forms.common.EditForm")
        if issubclass(ti.interface, IBungeniGroup):
            register_form_view(type_key, "Edit", "edit",
                model_interface_qualname,
                "bungeni.ui.forms.common.GroupEditForm")
        else:
            register_form_view(type_key, "Edit", "edit",
            model_interface_qualname,
            "bungeni.ui.forms.common.EditForm")
        # delete
        register_form_view(type_key, "Delete", "delete", model_interface_qualname,
            "bungeni.ui.forms.common.DeleteForm")
        
        # plone content menu (for custom types)
        # !+ doc-types were previously being layered on IWorkspaceOrAdminSectionLayer
        # !+ there was previously no reg for IReportConatiner and one of the member
        # containers, plus there was inconsistency in permission for 
        # IOfficeMemberContainer (was bungeni.office.Add).
        register_menu_item(type_key, "Add", "Add %s..." % (type_title), 
            container_interface_qualname,
            "./add",
            menu="plone_contentmenu",
            layer="bungeni.ui.interfaces.IAdminSectionLayer")
        
        # workspace
        if ti.workflow.has_feature("workspace"):
            log.debug("Setting up UI for feature %r for type %r", "workspace", type_key)
            
            # add menu item
            # !+workspace_feature_add(mr, oct-2012) note that an enabled
            # workspace feature also implies "add" functionality for the type
            first_tab = capi.workspace_tabs[0]
            action = "../../{first_tab}/add_{k}".format(first_tab=first_tab,
                k=type_key)
            register_menu_item(type_key, "Add", type_title, "*", action,
                menu="workspace_add_parliamentary_content", order=7)
            
            # add menu item -> for admin ?!
            # !+ why a duplicated (almost identical) menu item for admin?
            # !+ criteria here is having workspace enabled... but, cirterion 
            # should be simply that of being "parliamentary"? Do we need to 
            # formalize this distinction?
            # !+ need a formal "container attribute" naming convention!
            action = "{k}/add".format(k=naming.plural(type_key)) 
            register_menu_item(type_key, "Add", type_title, "*", action,
                menu="context_add_parliamentary_content", order=7)
            
            # edit menu item
            # !+ edit/delete used to be on layer="bungeni.ui.interfaces.IWorkspaceOrAdminSectionLayer"
            title = "Edit {t}".format(t=type_title)
            register_menu_item(type_key, "Edit", title, model_interface_qualname, "edit",
                menu="context_actions", order=10)
            
            # delete menu item
            title = "Delete {t}".format(t=type_title)
            register_menu_item(type_key, "Delete", title, model_interface_qualname, "delete",
                menu="context_actions", order=99)
            
            # add view
            name = "add_{type_key}".format(type_key=type_key)
            register_form_view(type_key, "Add", name,
                "bungeni.core.interfaces.IWorkspaceTab",
                "bungeni.ui.workspace.WorkspaceAddForm")
        
        # events
        if ti.workflow.has_feature("event"):
            log.debug("Setting up UI for feature %r for type %r", "event", type_key)
            for event_type_key in ti.workflow.get_feature("event").params["types"]:
                if capi.has_type_info(event_type_key):
                    container_property_name = naming.plural(event_type_key)
                    # add menu item
                    title = "{t} {e}".format(t=type_title, e=model_title(event_type_key))
                    register_menu_item(event_type_key, "Add", "Add %s" %(title),
                        model_interface_qualname, 
                        "./%s/add" % (container_property_name), 
                        menu="additems", 
                        order=21,
                        layer="bungeni.ui.interfaces.IWorkspaceOrAdminSectionLayer")
                else:
                    log.warn('IGNORING feature "event" ref to disabled type %r', 
                        event_type_key)
        
        # register other non-workspace menu items for custom types (only once)
        # custom events !+GET_ARCHETYPE
        if issubclass(ti.domain_model, domain.Event):
            # edit menu item
            register_menu_item(type_key, "Edit", "Edit {t}".format(t=type_title),
                model_interface_qualname,
                "edit",
                menu="context_actions",
                order=10,
                layer="bungeni.ui.interfaces.IWorkspaceOrAdminSectionLayer")
            # delete menu item
            register_menu_item(type_key, "Delete", "Delete {t}".format(t=type_title),
                model_interface_qualname,
                "delete",
                menu="context_actions",
                order=99,
                layer="bungeni.ui.interfaces.IWorkspaceOrAdminSectionLayer")
        
        # address
        if ti.workflow.has_feature("address"):
            log.debug("Setting up UI for feature %r for type %r", "address", type_key)
            if issubclass(ti.domain_model, domain.Group):
                title = "Add {t} Address".format(t=type_title)
                #layer="bungeni.ui.interfaces.IWorkspaceOrAdminSectionLayer"
                # add address in the "add items..." menu
                register_menu_item("address", "Add", title, model_interface_qualname, 
                    "./addresses/add", menu="additems", order=80)
            elif issubclass(ti.domain_model, domain.User):
                # !+ User not a custom type (so should never pass here)
                assert False, "Type %s may not be a custom type" % (ti.domain_model)


def apply_customization_ui():
    """Called from ui.app.on_wsgi_application_created_event -- must be called
    AFTER custom types have been catalysed.
    """
    # combine config string and execute it
    zcml = ZCML_SLUG.format(ui_zcml_decls="".join([ zd for zd in UI_ZC_DECLS ]))
    log.debug("Executing UI feature configuration:\n%s" % (zcml))
    xmlconfig.string(zcml)
    

