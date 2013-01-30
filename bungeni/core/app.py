# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""The Bungeni Application 

$Id$
"""
log = __import__("logging").getLogger("bungeni.core.app")

from zope.interface import implements
from zope.interface import implementedBy
from zope import component
from zope.interface.declarations import alsoProvides

from zope.app.appsetup.appsetup import getConfigContext
from zope.app.component import site
from zope.location.interfaces import ILocation

from ore.wsgiapp.app import Application
from ore.wsgiapp.interfaces import IWSGIApplicationCreatedEvent

from bungeni.models import domain
from bungeni.models import interfaces as model_interfaces
from bungeni.models.utils import get_current_parliament
from bungeni.models.utils import container_getter

from bungeni.core import interfaces
from bungeni.core import location
from bungeni.core.content import Section, AdminSection, AkomaNtosoSection, \
    WorkspaceSection
from bungeni.core.content import QueryContent
from bungeni.core.i18n import _
from bungeni.core.workspace import (WorkspaceContainer,
    WorkspaceUnderConsiderationContainer,
    WorkspaceTrackedDocumentsContainer,
    WorkspaceGroupsContainer,
    WorkspaceSchedulableContainer,
    load_workspaces)
from bungeni.core.notifications import load_notifications
from bungeni.core.emailnotifications import load_email
from bungeni.core.serialize import serialization_notifications
from bungeni.ui.utils import url, common # !+ core dependency on ui
from bungeni.capi import capi
from bungeni.utils import register



@register.handler(
    (model_interfaces.IBungeniApplication, IWSGIApplicationCreatedEvent))
def on_wsgi_application_created_event(application, event):
    """Additional setup on IWSGIApplicationCreatedEvent.
    """
    # !+ui.app.on_wsgi_application_created_event ALWAYS gets called prior to this
    log.debug("CORE ON_WSGI_APPLICATION_CREATED_EVENT: %s, %s", application, event) 
    
    # additional workflow validation
    for type_key, ti in capi.iter_type_info():
        if ti.workflow:
            ti.workflow.validate_permissions_roles()
    
    # import events module, registering handlers
    import bungeni.core.workflows.events
    
    # load workspaces
    load_workspaces()
    
    # load notifications
    load_notifications()

    # load email notifications
    load_email()

    # set up serialization notifications
    serialization_notifications()
    
    # import events modules, registering handlers
    import bungeni.core.events
    
    app_setup = model_interfaces.IBungeniSetup(application)
    app_setup.setUp()
    
    # write configuration parameters to xml
    try:
        import bungeni.utils.xmlconfexport as confexp
        confexp.write_all()
    except:
        log.debug(("on_wsgi_application_created :"
            "error while exporting config parameters to xml"))
    
    log.debug("on_wsgi_application_created_event: _features: %s" % (
        getConfigContext()._features))


def to_locatable_container(domain_class, *domain_containers):
    component.provideAdapter(location.ContainerLocation(*domain_containers),
               (implementedBy(domain_class), ILocation))


class BungeniApp(Application):
    implements(model_interfaces.IBungeniApplication)

class AppSetup(object):
    
    implements(model_interfaces.IBungeniSetup)
    
    def __init__(self, application):
        self.context = application
    
    def setUp(self):
        
        # register translations
        #import zope.i18n.zcml
        #zope.i18n.zcml.registerTranslations(getConfigContext(),
        #    capi.get_path_for("translations", "bungeni"))
        # !+ZCML_PYTHON(mr, apr-2011) above registerTranslations() in python 
        # does not work, as subsequent utility lookup fails. We workaround it 
        # by executing the following parametrized bit of ZCML:
        from zope.configuration import xmlconfig
        xmlconfig.string("""
            <configure xmlns="http://namespaces.zope.org/zope"
                xmlns:i18n="http://namespaces.zope.org/i18n">
                <include package="zope.i18n" file="meta.zcml" />
                <i18n:registerTranslations directory="%s" />
            </configure>
            """ % (capi.get_path_for("translations", "bungeni")))
        
        # ensure indexing facilities are setup(lazy)
        import index
        index.setupFieldDefinitions(index.indexer)
        
        sm = site.LocalSiteManager(self.context)
        self.context.setSiteManager(sm)
        
        from bungeni.core import language
        from bungeni.ui import z3evoque
        z3evoque.set_get_gettext()
        z3evoque.setup_evoque()
        z3evoque.domain.set_on_globals("devmode", common.has_feature("devmode"))
        z3evoque.domain.set_on_globals("absoluteURL", url.absoluteURL)
        z3evoque.domain.set_on_globals("get_section_name", url.get_section_name)
        z3evoque.domain.set_on_globals("get_base_direction", 
            language.get_base_direction)
        z3evoque.domain.set_on_globals("is_rtl", language.is_rtl)          
        
        # !+ where is the view name for the app root (slash) set?
        
        # CONVENTION: the action of each site top-section is made to point 
        # directly the primary sub-section (the INDEX) that it contains.
        # EXCEPTION: the "/", when logged in, is redirected to "/workspace/pi"
        
        self.context["bungeni"] = AkomaNtosoSection(
            title=_(u"Bungeni"),
            description=_(u"Current parliamentary activity"),
            default_name="bung", # !+NAMING(mr, jul-2011) bung?!?
        )
        
        # top-level sections
        workspace = self.context["workspace"] = WorkspaceSection(
            title=_("section_workspace", default=u"Workspace"),
            description=_(u"Current parliamentary activity"),
            default_name="my-documents",
        )
        alsoProvides(workspace, interfaces.ISearchableSection)
        
        workspace["my-documents"] = WorkspaceSection(
            title=_("section_workspace_documents", default=u"my documents"),
            description=_(u"my documents workspace section"),
            default_name="inbox",
            marker=interfaces.IWorkspaceDocuments,
        )
        
        for tab in capi.workspace_tabs:
            workspace["my-documents"][tab] = WorkspaceContainer(
                tab_type=tab,
                title=_("section_workspace_%s" % tab, default=tab),
                marker=interfaces.IWorkspaceTab
            )

        workspace["under-consideration"] = WorkspaceSection(
            title=_(u"under consideration"),
            description=_(u"documents under consideration"),
            default_name="documents",
            marker=interfaces.IWorkspaceUnderConsideration
        )
        workspace["under-consideration"]["documents"] = WorkspaceUnderConsiderationContainer(
            name="documents",
            title=_(u"under consideration"),
            description=_(u"documents under consideration"),
            marker=interfaces.IWorkspaceTrackedDocuments)
        workspace["under-consideration"]["tracked-documents"] = WorkspaceTrackedDocumentsContainer(
            name="tracked documents",
            title=_(u"tracked documents"),
            description=_(u"tracked documents"))
        
        workspace["scheduling"] = Section(
            title=_("section_scheduling", default=u"Scheduling"),
            description=_(u"Workspace Scheduling"),
            default_name="index",
            marker=interfaces.IWorkspaceScheduling)
        workspace["scheduling"]["committees"] = QueryContent(
            container_getter(get_current_parliament, "committees"),
            title=_("section_scheduling_committees", default=u"Committees"),
            #!+marker=interfaces.ICommitteeAddContext,
            description=_(u"Committee schedules"))
        workspace["scheduling"]["documents"] = WorkspaceSchedulableContainer(
            name=_(u"schedulable items"),
            title=_(u"schedulable items"),
            description=_(u"documents available for scheduling"))
        workspace["scheduling"]["sittings"] = QueryContent(
            container_getter(get_current_parliament, "sittings"),
            title=_("section_scheduling_sittings", default=u"Sittings"),
            description=_(u"Plenary Sittings"))
        workspace["scheduling"]["agendaitems"] = QueryContent(
            container_getter(get_current_parliament, "agendaitems"),
            title=_("section_scheduling_agenda_items", 
                default=u"Agenda items"),
            #marker=interfaces.IAgendaItemAddContext,
            description=_(u"Manage agenda items"))
        
        workspace["groups"] = WorkspaceSection(
            title=_("section_groups", default=u"Groups"),
            description=_(u"Bungeni Groups"),
            default_name="my-groups",
            marker=interfaces.IWorkspaceGroups)
        workspace["groups"]["my-groups"] = WorkspaceGroupsContainer(
            name="my-groups",
            title=_(u"My Groups"),
            description=_(u"Groups that the user is a member of"))
        
        #!+TIMING
        #!+AUTO CONTAINERS SCHEDULING(mb, April-2012)
        # type_info missing container name
        for key, info in capi.iter_type_info():
            if model_interfaces.IScheduleContent.implementedBy(info.domain_model):
                container_name = "%ss" % key
                container = "%sContainer" % info.domain_model.__name__
                workspace["scheduling"][container_name] = getattr(domain, container)()
                to_locatable_container(info.domain_model, 
                    workspace["scheduling"][container_name]
                )
        
        
        #!+SECURITY(miano. nov-2010) Admin section now uses AdminSection
        # container that is identical to Section, only difference is that
        # traversing though it requires zope.ManageSite permission as defined
        # in core/configure.zcml
        
        admin = self.context["admin"] = AdminSection(
            title=_(u"Administration"),
            description=_(u"Manage bungeni settings"),
            default_name="admin-index",
            marker=model_interfaces.IBungeniAdmin)
        alsoProvides(admin, interfaces.ISearchableSection)
        
        
        ##########
        # Admin User Interface
        # Administration section
        
        content = admin["content"] = Section(
            title=_(u"Content"),
            description=_(u"browse bungeni content"),
            marker=model_interfaces.IBungeniAdmin,
            default_name="browse-admin")
        
        admin["email-settings"] = Section(
            title=_(u"email settings"),
            description=_(u"manage email settings"),
            marker=model_interfaces.IBungeniAdmin,
            default_name="email-settings")
        
        admin["xapian-settings"] = Section(
            title=_(u"search index settings"),
            description=_(u"manage search index settings"),
            marker=model_interfaces.IBungeniAdmin,
            default_name="xapian-settings")
        
        admin["registry-settings"] = Section(
            title=_(u"registry settings"),
            description=_(u"manage registry settings"),
            marker=model_interfaces.IBungeniAdmin,
            default_name="registry-settings")
        
        admin["serialization-manager"] = Section(
            title=_(u"serialization manager"),
            description=_(u"batch serialization of content"),
            marker=model_interfaces.IBungeniAdmin,
            default_name="serialization-manager")
        
        content[u"parliaments"] = domain.ParliamentContainer()
        to_locatable_container(domain.Parliament, content[u"parliaments"])
        
        content[u"users"] = domain.UserContainer()
        to_locatable_container(domain.User, content[u"users"])
