# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""The Bungeni Application 

$Id$
"""
log = __import__("logging").getLogger("bungeni.core.app")

import copy

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
from bungeni.models.interfaces import (
    IBungeniApplication,
    IBungeniSetup,
    IBungeniAdmin,
    IScheduleContent,
)
from bungeni.models.utils import get_chamber_for_context
from bungeni.models.utils import container_getter

from bungeni.core import interfaces
from bungeni.core import location
from bungeni.core.content import (Section, AdminSection, AkomaNtosoSection,
    WorkspaceSection, APISection, OAuthSection)
from bungeni.core.content import QueryContent
from bungeni.core.workspace import (WorkspaceContainer,
    WorkspaceUnderConsiderationContainer,
    WorkspaceTrackedDocumentsContainer,
    WorkspaceGroupsContainer,
    WorkspaceSchedulableContainer,
    load_workspaces)
from bungeni.core.notifications import load_notifications
from bungeni.core.emailnotifications import load_email
# !+SERIALIZER(ah, 21-06-2013) moved to separate app
#from bungeni.core.serialize import serialization_notifications
from bungeni.ui.utils import url  # !+ core dependency on ui
from bungeni.capi import capi
from bungeni.utils import common, naming, register, probing
from bungeni import _



@register.handler((IBungeniApplication, IWSGIApplicationCreatedEvent))
def on_wsgi_application_created_event(application, event):
    """Additional setup on IWSGIApplicationCreatedEvent.
    """
    # !+ui.app.on_wsgi_application_created_event ALWAYS gets called prior to this
    log.debug("CORE ON_WSGI_APPLICATION_CREATED_EVENT: %s, %s", application, event) 
    
    # execute application setup, creating sections, etc.
    app_setup = IBungeniSetup(application)
    app_setup.setUp()
    
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
    
    # !+SERIALIZER(ah, 21-06-2013) This has been moved to a separate app
    # set up serialization notifications
    #serialization_notifications()
    
    # import events modules, registering handlers
    import bungeni.core.events
    
    # write configuration parameters to xml
    import bungeni.utils.xmlconfexport as confexp
    confexp.write_all()
    
    log.info("on_wsgi_application_created_event: _features: %s", 
        getConfigContext()._features)
    
    from bungeni.alchemist.utils import set_vocabulary_factory
    log.info("on_wsgi_application_created_event: Dynamic Vocabularies:\n    %s",
        "\n    ".join(sorted([ "%s%s%s" % (
                        v.__name__, probing.saccadic_padding(v.__name__), v)
                    for v in set_vocabulary_factory.registered ])))


def to_locatable_container(domain_class, *domain_containers):
    component.provideAdapter(location.ContainerLocation(*domain_containers),
               (implementedBy(domain_class), ILocation))


class BungeniApp(Application):
    implements(IBungeniApplication)

class AppSetup(object):
    
    implements(IBungeniSetup)
    
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
                title=tab,
                marker=interfaces.IWorkspaceTab
            )

        ws_uc = workspace["under-consideration"] = WorkspaceSection(
            title=_(u"under consideration"),
            description=_(u"documents under consideration"),
            default_name="documents",
            marker=interfaces.IWorkspaceUnderConsideration)
        ws_uc["documents"] = WorkspaceUnderConsiderationContainer(
            name="documents",
            title=_(u"under consideration"),
            description=_(u"documents under consideration"),
            marker=interfaces.IWorkspaceTrackedDocuments)
        ws_uc["tracked-documents"] = WorkspaceTrackedDocumentsContainer(
            name="tracked documents",
            title=_(u"tracked documents"),
            description=_(u"tracked documents"))
        
        ws_sched = workspace["scheduling"] = Section(
            title=_("section_scheduling", default=u"Scheduling"),
            description=_(u"Workspace Scheduling"),
            default_name="index",
            marker=interfaces.IWorkspaceScheduling)
        ws_sched["committees"] = QueryContent( # !+CUSTOM
            container_getter(get_chamber_for_context, "committees"),
            title=_("section_scheduling_committees", default=u"Committees"),
            description=_(u"Committee schedules"))
        ws_sched["documents"] = WorkspaceSchedulableContainer(
            name=_(u"schedulable items"),
            title=_(u"schedulable items"),
            description=_(u"documents available for scheduling"))
        ws_sched["sittings"] = QueryContent( # !+FEATURE
            container_getter(get_chamber_for_context, "sittings"),
            title=_("section_scheduling_sittings", default=u"Sittings"),
            description=_(u"Plenary Sittings"))
        ws_sched["sessions"] = QueryContent(
            container_getter(get_chamber_for_context, "sessions"),
            title=_("section_scheduling_sessions", default=u"Sessions"),
            description=_(u"Plenary Sessions"))
        ws_sched["venues"] = QueryContent(
            container_getter(get_chamber_for_context, "venues"),
            title=_("section_scheduling_venues", default=u"Venues"),
            description=_(u"Venues"))
        ws_sched["publications"] = QueryContent(
            container_getter(get_chamber_for_context, "publications"),
            title=_("section_scheduling_publications", 
                default=u"Publications"),
            description=_(u"Publications"))
        # !+CALENDAR_DOC_TYPES finish off setup_customization_ui steps that need 
        # application sections to be created...
        import bungeni.feature.ui
        for calendar_doc_type_key in bungeni.feature.ui.CALENDAR_DOC_TYPE_KEYS:
            calendar_doc_ti = capi.get_type_info(calendar_doc_type_key)
            container_property_name = naming.plural(calendar_doc_type_key)
            # add section containers to workspace/scheduling
            ws_sched[container_property_name] = QueryContent(
                container_getter(get_chamber_for_context, container_property_name),
                title=_("section_scheduling_${container_property_name}", 
                    mapping={"container_property_name": container_property_name}, 
                    default=calendar_doc_ti.container_label),
                description=_(u"Manage ${container_label}",
                    mapping={"container_label": calendar_doc_ti.container_label}))
        
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
        for type_key, ti in capi.iter_type_info():
            if IScheduleContent.implementedBy(ti.domain_model):
                container_property_name = naming.plural(type_key)
                container_name = naming.model_name(container_property_name)
                if not ws_sched.has_key(container_property_name):
                    ws_sched[container_property_name] = QueryContent(
                        container_getter(get_chamber_for_context, container_property_name),
                        title=container_name,
                        description=container_name)        
        
        ##########
        # Admin User Interface
        # Administration section
        
        #!+SECURITY(miano. nov-2010) Admin section now uses AdminSection
        # container that is identical to Section, only difference is that
        # traversing though it requires zope.ManageSite permission as defined
        # in core/configure.zcml
        
        admin = self.context["admin"] = AdminSection(
            title=_(u"Administration"),
            description=_(u"Manage bungeni settings"),
            default_name="admin-index",
            marker=IBungeniAdmin)
        
        admin["email-settings"] = Section(
            title=_(u"email settings"),
            description=_(u"manage email settings"),
            marker=IBungeniAdmin,
            default_name="email-settings")
        
        admin["search-settings"] = Section(
            title=_(u"search settings"),
            description=_(u"manage bungeni email settings"),
            marker=IBungeniAdmin,
            default_name="search-settings")
        
        admin["registry-settings"] = Section(
            title=_(u"registry settings"),
            description=_(u"manage registry settings"),
            marker=IBungeniAdmin,
            default_name="registry-settings")
        
        admin["serialization-manager"] = Section(
            title=_(u"serialization manager"),
            description=_(u"batch serialization of content"),
            marker=IBungeniAdmin,
            default_name="serialization-manager")
        
        content = admin["content"] = Section(
            title=_(u"Content"),
            description=_(u"browse bungeni content"),
            marker=IBungeniAdmin,
            default_name="browse-admin")
        alsoProvides(content, interfaces.ISearchableSection)
        # !+CUSTOM form descriptor container on legislature
        content[u"legislatures"] = domain.LegislatureContainer()
        ''' !+LEGISLATURE requires that all chamber/government/joint_committee
        groups be created *under* the legislature in admin (or use demo data 
        dump from circa r11500 or newer).
        
        content[u"chambers"] = domain.ChamberContainer()
        to_locatable_container(domain.Chamber, content[u"chambers"])
        content[u"governments"] = domain.GovernmentContainer()
        to_locatable_container(domain.Government, content[u"governments"])
        content[u"joint-committees"] = domain.JointCommitteeContainer()
        to_locatable_container(domain.JointCommittee,
            content["joint-committees"])
        '''
        content[u"users"] = domain.UserContainer()
        to_locatable_container(domain.User, content[u"users"])
        # !+/CUSTOM
        
        api = self.context[u"api"] = APISection(
            title=_(u"Bungeni API"),
            description=_(u"Bungeni REST API"),
            default_name="index",
        )
        api[u"workspace"] = copy.deepcopy(workspace)
        api[u"users"] = copy.deepcopy(content[u"users"])
        
        self.context["oauth"] = OAuthSection(
            title=_(u"Bungeni OAuth API"),
            description=_(u"Bungeni OAuth API"),
            default_name="index",
        )
        admin[u"applications"] = domain.OAuthApplicationContainer()
        to_locatable_container(domain.OAuthApplication, admin[u"applications"])


