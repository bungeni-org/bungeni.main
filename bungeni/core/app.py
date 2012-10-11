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
                                    load_workspaces)
from bungeni.core.notifications import load_notifications
from bungeni.core.emailnotifications import email_notifications
from bungeni.core.serialize import serialization_notifications
from bungeni.ui.utils import url, common # !+ core dependency on ui
from bungeni.utils.capi import capi
from bungeni.utils import register



@register.handler(
    (model_interfaces.IBungeniApplication, IWSGIApplicationCreatedEvent))
def on_wsgi_application_created_event(application, event):
    """Additional setup on IWSGIApplicationCreatedEvent.
    """
    # additional workflow validation
    for type_key, ti in capi.iter_type_info():
        if ti.workflow:
            ti.workflow.validate_permissions_roles()
    
    # import events module, registering handlers
    import bungeni.core.workflows.events
    
    # load workspaces
    load_workspaces()

    #load notifications
    load_notifications()
    
    #load email notifications
    email_notifications()

    #set up serialization notifications
    serialization_notifications()

    # import events modules, registering handlers
    import bungeni.core.events
    
    initializer = model_interfaces.IBungeniSetup(application)
    initializer.setUp()
    log.debug("on_wsgi_application_created_event: _features: %s" % (
        getConfigContext()._features))


def to_locatable_container(domain_class, *domain_containers):
    component.provideAdapter(location.ContainerLocation(*domain_containers),
               (implementedBy(domain_class), ILocation))


class BungeniApp(Application):
    implements(model_interfaces.IBungeniApplication)


class AppSetup(object):
    
    implements(model_interfaces.IBungeniSetup)
    
    def __init__(self, context):
        self.context = context
    
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
            title=_(u"Workspace"),
            description=_(u"Current parliamentary activity"),
            default_name="my-documents",
        )
        
        alsoProvides(workspace, interfaces.ISearchableSection)
        workspace["my-documents"] = WorkspaceSection(
            title=_(u"my documents"),
            description=_(u"my documents"),
            default_name="inbox",
            marker=interfaces.IWorkspaceDocuments,
        )
        workspace["my-documents"]["draft"] = WorkspaceContainer(
            tab_type="draft",
            title=_("draft"),
            description=_("draft documents"),
            marker=interfaces.IWorkspaceDraft
        )
        workspace["my-documents"]["inbox"] = WorkspaceContainer(
            tab_type="inbox",
            title=_("inbox"),
            description=_("incoming documents"),
            marker=interfaces.IWorkspaceInbox
        )
        workspace["my-documents"]["pending"] = WorkspaceContainer(
            tab_type="pending",
            title=_("pending"),
            description=_("pending documents"),
            marker=interfaces.IWorkspacePending
        )
        workspace["my-documents"]["archive"] = WorkspaceContainer(
            tab_type="archive",
            title=_("archive"),
            description=_("archived documents"),
            marker=interfaces.IWorkspaceArchive
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
            marker=interfaces.IWorkspaceTrackedDocuments
           )
        workspace["under-consideration"]["tracked-documents"] = WorkspaceTrackedDocumentsContainer(
            name="tracked documents",
            title=_(u"tracked documents"),
            description=_(u"tracked documents")
           )

        workspace["scheduling"] = Section(
            title=_(u"Scheduling"),
            description=_(u"Scheduling"),
            default_name="index",
            marker=interfaces.IWorkspaceScheduling,
        )
        workspace["scheduling"]["committees"] = QueryContent(
            container_getter(get_current_parliament, "committees"),
            title=_(u"Committees"),
            marker=interfaces.ICommitteeAddContext,
            description=_(u"Committee schedules")
        )
        workspace["scheduling"]["sittings"] = QueryContent(
            container_getter(get_current_parliament, "sittings"),
            title=_(u"Sittings"),
            description=_(u"Plenary Sittings")
        )
        workspace["scheduling"]["agendaitems"] = QueryContent(
            container_getter(get_current_parliament, "agendaitems"),
            title=_(u"Agenda items"),
            marker=interfaces.IAgendaItemAddContext,
            description=_(u"Manage agenda items"))
        
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
        
        # Proof-of-concept: support for selective inclusion in breadcrumb trail:
        # a view marked with an attribute __crumb__=False is NOT included in 
        # the breadcrumb trail (see ui/viewlets/navigation.py)
        #self.context["workspace"].__crumb__ = False
        business = self.context["business"] = Section(
            title=_(u"Business"),
            description=_(u"Daily operations of the parliament"),
            default_name="business-index")
        members = self.context["members"] = Section(
            title=_(u"Members"),
            description=_(u"Records of members of parliament"),
            default_name="members-index")
        archive = self.context["archive"] = Section(
            title=_(u"Archive"),
            description=_(u"Parliament records and documents"),
            default_name="archive-index")
        
        alsoProvides(archive, interfaces.ISearchableSection)
            
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
        
        # business section
        business["whats-on"] = Section(
            title=_(u"What's on"),
            description=_(u"Current parliamentary activity"),
            default_name="whats-on")
        
        alsoProvides(business, interfaces.ISearchableSection)

        business[u"committees"] = QueryContent(
            container_getter(get_current_parliament, "committees"),
            title=_(u"Committees"),
            marker=interfaces.ICommitteeAddContext,
            description=_(u"View committees created by the current parliament"))
        
        business[u"bills"] = QueryContent(
            container_getter(get_current_parliament, "bills"),
            title=_(u"Bills"),
            marker=interfaces.IBillAddContext,
            description=_(u"View bills introduced in the current parliament"))

        business[u"questions"] = QueryContent(
            container_getter(get_current_parliament, "questions"),
            title=_(u"Questions"),
            marker=interfaces.IQuestionAddContext,
            description=_(u"View questions tabled in the current parliament"))

        business[u"motions"] = QueryContent(
            container_getter(get_current_parliament, "motions"),
            title=_(u"Motions"),
            marker=interfaces.IMotionAddContext,
            description=_(u"View motions moved in the current parliament"))


        business[u"tableddocuments"] = QueryContent(
            container_getter(get_current_parliament, "tableddocuments"),
            title=_(u"Tabled documents"),
            marker=interfaces.ITabledDocumentAddContext,
            description=\
                _(u"View the documents tabled in the current parliament")
        )

        business[u"agendaitems"] = QueryContent(
            container_getter(get_current_parliament, "agendaitems"),
            title=_(u"Agenda items"),
            marker=interfaces.IAgendaItemAddContext,
            description=_(u"View the agenda items of the current parliament"))

       # sessions = business[u"sessions"] = QueryContent(
       #     container_getter(get_current_parliament, 'sessions'),
       #     title=_(u"Sessions"),
       #     marker=interfaces.ISessionAddContext,
       #     description=_(u"View the sessions of the current parliament."))

        business[u"sittings"] = QueryContent(
            container_getter(get_current_parliament, "sittings"),
            title=_(u"Sittings"),
            description=_(u"View the sittings of the current parliament"))
            
        #Parliamentary reports
        business[u"preports"] = QueryContent(
            container_getter(get_current_parliament, "preports"),
            title=_(u"Publications"),
            marker=interfaces.IReportAddContext,
            description=\
                _(u"browse and download parliamentary publications")
        )
        
        
        # members section
        members[u"current"] = QueryContent(
            container_getter(get_current_parliament, "parliamentmembers"),
            title=_(u"Current"),
            description=_(u"View current parliament members (MPs)"))
        
        alsoProvides(members, interfaces.ISearchableSection)
        
        members[u"political-groups"] = QueryContent(
            container_getter(get_current_parliament, "politicalgroups"),
            title=_(u"Political groups"),
            description=_(u"View current political groups"))
        
        # archive
        records = archive[u"browse"] = Section(
            title=_(u"Browse archives"),
            description=_(u"Browse records from the archive"),
            default_name="browse-archive")
        
        documents = archive["documents"] = Section(
            title=_(u"Documents"),
            description=_(u"Browse documents in the archive"),
            default_name="browse-archive")
        
        # archive/records
        documents[u"bills"] = domain.BillContainer()
        to_locatable_container(domain.Bill, documents[u"bills"])
        
        documents[u"motions"] = domain.MotionContainer()
        to_locatable_container(domain.Motion, documents[u"motions"])
        
        documents[u"questions"] = domain.QuestionContainer()
        to_locatable_container(domain.Question, documents[u"questions"])
        
        documents[u"agendaitems"] = domain.AgendaItemContainer()
        to_locatable_container(domain.AgendaItem, documents[u"agendaitems"])
        
        documents[u"tableddocuments"] = domain.TabledDocumentContainer()
        to_locatable_container(domain.TabledDocument, 
            documents[u"tableddocuments"]
        )
        
        documents[u"reports"] = domain.ReportContainer()
        to_locatable_container(domain.Report, documents[u"reports"])
        #component.provideAdapter(location.ContainerLocation(tableddocuments, documents[u"reports"]),
        #               (implementedBy(domain.Report), ILocation))
        
        records[u"parliaments"] = domain.ParliamentContainer()
        to_locatable_container(domain.Parliament, records[u"parliaments"])
        
        records[u"political-groups"] = domain.PoliticalGroupContainer()
        to_locatable_container(domain.PoliticalGroup, 
            records[u"political-groups"]
        )
        
        records[u"committees"] = domain.CommitteeContainer()
        to_locatable_container(domain.Committee, records[u"committees"])

        #records[u"mps"] = domain.MemberOfParliamentContainer()
        #component.provideAdapter(location.ContainerLocation(records[u"mps"]),
        #               (implementedBy(domain.MemberOfParliament), ILocation))
        
        ##########
        # Admin User Interface
        # Administration section
        
        content = admin["content"] = Section(
            title=_(u"Content"),
            description=_(u"browse bungeni content"),
            marker=model_interfaces.IBungeniAdmin,
            default_name="browse-admin")

        admin["settings"] = Section(
            title=_(u"Settings"),
            description=_(u"settings"),
            marker=model_interfaces.IBungeniAdmin,
            default_name="settings")

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
        
        content[u"parliaments"] = domain.ParliamentContainer()
        to_locatable_container(domain.Parliament, content[u"parliaments"])
        
        content[u"offices"] = domain.OfficeContainer()
        to_locatable_container(domain.Office, content[u"offices"])
        
        content[u"users"] = domain.UserContainer()
        to_locatable_container(domain.User, content[u"users"])


