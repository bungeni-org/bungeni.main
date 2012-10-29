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
    zcml_slug = """
        <configure xmlns="http://namespaces.zope.org/zope"
            xmlns:browser="http://namespaces.zope.org/browser"
            xmlns:i18n="http://namespaces.zope.org/i18n"
            i18n_domain="bungeni"
            >
            <include package="zope.browsermenu" file="meta.zcml" />
            <include package="zope.browserpage" file="meta.zcml" />
%s
        </configure>
        """
    zcml_decls = []
    
    add_menu_item_tmpl = """
            <browser:menuItem menu="%s"
                for="*"
                title="%s"
                action="../../draft/add_%s"
                permission="bungeni.%s.Add"
            />"""
    
    add_view_tmpl = """
            <browser:page name="add_%s"
                for="bungeni.core.interfaces.IWorkspaceDraft"
                class="bungeni.ui.workspace.WorkspaceAddForm"
                layer="bungeni.ui.interfaces.IBungeniSkin"
                permission="bungeni.%s.Add"
            />"""
    
    # we assume that non-custom types have already been set up as needed
    for type_key, ti in capi.iter_type_info(scope="custom"):
        
        if ti.workflow.has_feature("workspace"):
            log.debug("Setting up workspace UI for type [%s]" % (type_key))
            # !+workspace_feature_add(mr, oct-2012) note that an enabled
            # workspace feature also implies "add" functionality for the type
            zcml_decls.append(add_menu_item_tmpl % (
                    "workspace_add_parliamentary_content",
                    naming.split_camel(naming.model_name(type_key)),
                    type_key,
                    type_key))
            zcml_decls.append(add_view_tmpl % (type_key, type_key))
    
    # combine config string and execute it
    zcml = zcml_slug % ("".join([ zd for zd in zcml_decls ]))
    log.debug("Executing UI feature configuration:\n%s" % (zcml))
    xmlconfig.string(zcml)

