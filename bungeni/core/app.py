# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""The Bungeni Application 

$Id$
"""
log = __import__("logging").getLogger("bungeni.core.app")

from zope.interface import implements
from zope.interface import implementedBy
from zope.component import provideAdapter
from zope.interface.declarations import alsoProvides 

from zope.app.appsetup.appsetup import getConfigContext
from zope.app.component import site
from zope.app.container.sample import SampleContainer
from zope.location.interfaces import ILocation

from ore.wsgiapp.app import Application

from bungeni.models import domain
from bungeni.models import interfaces as model_interfaces

from bungeni.core import interfaces
from bungeni.core import location
from bungeni.core.content import Section, AdminSection, AkomaNtosoSection, \
    WorkspaceSection
from bungeni.core.content import QueryContent
from bungeni.core.i18n import _
from bungeni.models.utils import get_current_parliament
from bungeni.models.utils import container_getter
from bungeni.ui.utils import url, common
from bungeni.models.workspace import WorkspaceContainer

def onWSGIApplicationCreatedEvent(application, event):
    """Subscriber to the ore.wsgiapp.interfaces.IWSGIApplicationCreatedEvent."""
    initializer = model_interfaces.IBungeniSetup(application)
    initializer.setUp()
    log.debug("onWSGIApplicationCreatedEvent: _features: %s" % (
                                        getConfigContext()._features))

class BungeniApp(Application):
    implements(model_interfaces.IBungeniApplication)

#!CRUFT (miano, nov-2010) possible cruft
#class BungeniAdmin(SampleContainer):
#    implements(model_interfaces.IBungeniAdmin )



class AppSetup(object):
    
    implements(model_interfaces.IBungeniSetup)
    
    def __init__(self, context):
        self.context = context
    
    def setUp(self):
        
        # register translations
        from bungeni.utils.capi import capi
        #import zope.i18n.zcml
        #zope.i18n.zcml.registerTranslations(getConfigContext(),
        #    capi.get_path_for("translations", "bungeni"))
        # 
        # !+ZCML_PYTHON(mr, apr-2011) above registerTranslations() in python 
        # does not work, as subsequent utility lookup fails. We workaround it 
        # by executing the following parametrized bit of ZCML:
        #
        from zope.configuration import xmlconfig
        xmlconfig.string("""
            <configure xmlns="http://namespaces.zope.org/zope"
                xmlns:i18n="http://namespaces.zope.org/i18n">
                <include package="zope.i18n" file="meta.zcml" />
                <i18n:registerTranslations directory="%s" />
            </configure>
            """ % (capi.get_path_for("translations", "bungeni")))
        
        import index
        # ensure indexing facilities are setup(lazy)
        index.setupFieldDefinitions(index.indexer)

        
        sm = site.LocalSiteManager(self.context)
        self.context.setSiteManager(sm)
        
        from bungeni.ui import z3evoque
        z3evoque.set_get_gettext()
        z3evoque.setup_evoque()
        z3evoque.domain.set_on_globals("devmode", common.has_feature("devmode"))
        z3evoque.domain.set_on_globals("absoluteURL", url.absoluteURL)
        z3evoque.domain.set_on_globals("get_section_name", url.get_section_name)
        
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
            default_name="documents",
        )
        
        alsoProvides(workspace, interfaces.ISearchableSection)
        workspace["documents"] = Section(
            title=_(u"documents"),
            description=_(u"documents"),
            default_name="inbox",
            marker = interfaces.IWorkspaceDocuments,
        )
        workspace["documents"]["draft"] = WorkspaceContainer(
            tab_type="draft",
            title=_("draft"),
            description=_("draft documents"),
            marker=interfaces.IWorkspaceDraft
        )
        workspace["documents"]["inbox"] = WorkspaceContainer(
            tab_type="inbox",
            title=_("inbox"),
            description=_("incoming documents"),
            marker=interfaces.IWorkspaceInbox
        )
        workspace["documents"]["sent"] = WorkspaceContainer(
            tab_type="sent",
            title=_("sent"),
            description=_("sent documents"),
            marker=interfaces.IWorkspaceSent
        )
        workspace["documents"]["archive"] = WorkspaceContainer(
            tab_type="archive",
            title=_("archive"),
            description=_("archived documents"),
            marker=interfaces.IWorkspaceArchive
        )
        
        workspace["scheduling"] = Section(
            title=_(u"Scheduling"),
            description=_(u"Scheduling"),
            default_name="index",
            marker=interfaces.IWorkspaceScheduling,
        )
        workspace["scheduling"]["committees"] = QueryContent(
            container_getter(get_current_parliament, 'committees'),
            title=_(u"Committees"),
            marker=interfaces.ICommitteeAddContext,
            description=_(u"Committee schedules")
        )
        workspace["scheduling"]["sittings"] = QueryContent(
            container_getter(get_current_parliament, 'sittings'),
            title=_(u"Sittings"),
            description=_(u"Plenary Sittings")
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
            container_getter(get_current_parliament, 'committees'),
            title=_(u"Committees"),
            marker=interfaces.ICommitteeAddContext,
            description=_(u"View committees created by the current parliament"))
        
        business[u"bills"] = QueryContent(
            container_getter(get_current_parliament, 'bills'),
            title=_(u"Bills"),
            marker=interfaces.IBillAddContext,
            description=_(u"View bills introduced in the current parliament"))

        business[u"questions"] = QueryContent(
            container_getter(get_current_parliament, 'questions'),
            title=_(u"Questions"),
            marker=interfaces.IQuestionAddContext,
            description=_(u"View questions tabled in the current parliament"))

        business[u"motions"] = QueryContent(
            container_getter(get_current_parliament, 'motions'),
            title=_(u"Motions"),
            marker=interfaces.IMotionAddContext,
            description=_(u"View motions moved in the current parliament"))


        business[u"tableddocuments"] = QueryContent(
            container_getter(get_current_parliament, 'tableddocuments'),
            title=_(u"Tabled documents"),
            marker=interfaces.ITabledDocumentAddContext,
            description=\
                _(u"View the documents tabled in the current parliament")
        )

        business[u"agendaitems"] = QueryContent(
            container_getter(get_current_parliament, 'agendaitems'),
            title=_(u"Agenda items"),
            marker=interfaces.IAgendaItemAddContext,
            description=_(u"View the agenda items of the current parliament"))

       # sessions = business[u"sessions"] = QueryContent(
       #     container_getter(get_current_parliament, 'sessions'),
       #     title=_(u"Sessions"),
       #     marker=interfaces.ISessionAddContext,
       #     description=_(u"View the sessions of the current parliament."))

        business[u"sittings"] = QueryContent(
            container_getter(get_current_parliament, 'sittings'),
            title=_(u"Sittings"),
            description=_(u"View the sittings of the current parliament"))
            
        #Parliamentary reports
        business[u"preports"] = QueryContent(
            container_getter(get_current_parliament, 'preports'),
            title=_(u"Publications"),
            marker=interfaces.IReportAddContext,
            description=\
                _(u"browse and download parliamentary publications")
        )
        
        
        # members section
        members[u"current"] = QueryContent(
            container_getter(get_current_parliament, 'parliamentmembers'),
            title=_(u"Current"),
            description=_(u"View current parliament members (MPs)"))
        
        alsoProvides(members, interfaces.ISearchableSection)

        members[u"political-groups"] = QueryContent(
            container_getter(get_current_parliament, 'politicalgroups'),
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
            
        
        def to_locatable_container(domain_class, *domain_containers):
            provideAdapter(location.ContainerLocation(*domain_containers),
                       (implementedBy(domain_class), ILocation))
        
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
        #provideAdapter(location.ContainerLocation(tableddocuments, documents[u"reports"]),
        #               (implementedBy(domain.Report), ILocation))
        
        records[u"parliaments"] = domain.ParliamentContainer()
        to_locatable_container(domain.Parliament, records[u"parliaments"])
        
        records[u"politicalgroups"] = domain.PoliticalGroupContainer()
        to_locatable_container(domain.PoliticalGroup, 
            records[u"politicalgroups"]
        )
        
        records[u"constituencies"] = domain.ConstituencyContainer()
        to_locatable_container(domain.Constituency, records[u"constituencies"])
        
        records[u"committees"] = domain.CommitteeContainer()
        to_locatable_container(domain.Committee, records[u"committees"])

        #records[u"mps"] = domain.MemberOfParliamentContainer()
        #provideAdapter(location.ContainerLocation(records[u"mps"]),
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
        
        content[u"parliaments"] = domain.ParliamentContainer()
        to_locatable_container(domain.Parliament, content[u"parliaments"])
        
        content[u"offices"] = domain.OfficeContainer()
        to_locatable_container(domain.Office, content[u"offices"])
        
        content[u'users'] = domain.UserContainer()
        to_locatable_container(domain.User, content[u"users"])
        
        content[u'headings'] = domain.HeadingContainer()
        to_locatable_container(domain.Heading, content[u"headings"])
        
        content[u"constituencies"] = domain.ConstituencyContainer()
        to_locatable_container(domain.Constituency, content[u"constituencies"])
        
        content[u"provinces"] = domain.ProvinceContainer()
        to_locatable_container(domain.Province, content[u"provinces"])
        
        content[u"regions"] = domain.RegionContainer()
        to_locatable_container(domain.Region, content[u"regions"])
        
        content[u"parties"] = domain.PoliticalPartyContainer()
        to_locatable_container(domain.PoliticalParty, content[u"parties"])

        vocabularies = admin["vocabularies"] = Section(
            title=_(u"vocabularies"),
            description=_(u"manage vocabularies"),
            marker=model_interfaces.IBungeniAdmin,
            default_name="vocabularies")

        vocabularies[u"address-types"] = domain.AddressTypeContainer()
        to_locatable_container(domain.AddressType, 
            vocabularies[u"address-types"]
        )
        vocabularies[u"attendance-types"] = domain.AttendanceTypeContainer()
        to_locatable_container(domain.AttendanceType, 
            vocabularies[u"attendance-types"]
        )
        ''' !+TYPES_CUSTOM
        vocabularies[u"bill-types"] = domain.BillTypeContainer()
        to_locatable_container(domain.BillType, 
            vocabularies[u"bill-types"]
        )
        '''
        vocabularies[u"question-types"] = domain.QuestionTypeContainer()
        to_locatable_container(domain.QuestionType, 
            vocabularies[u"question-types"]
        )
        vocabularies[u"response-types"] = domain.ResponseTypeContainer()
        to_locatable_container(domain.ResponseType, 
            vocabularies[u"response-types"]
        )
        vocabularies[u"committee-types"] = domain.CommitteeTypeContainer()
        to_locatable_container(domain.CommitteeType, 
            vocabularies[u"committee-types"]
        )
        vocabularies[u"venues"] = domain.VenueContainer()
        to_locatable_container(domain.Venue, vocabularies[u"venues"])
        
        vocabularies[u"m-election-types"] = domain.MemberElectionTypeContainer()
        to_locatable_container(domain.MemberElectionType, 
            vocabularies[u"m-election-types"]
        )
        vocabularies[u"p-address-types"] = domain.PostalAddressTypeContainer()
        to_locatable_container(domain.PostalAddressType, 
            vocabularies[u"p-address-types"]
        )
        vocabularies[u"committee-types-statuses"] = \
            domain.CommitteeTypeStatusContainer()
        to_locatable_container(domain.CommitteeTypeStatus, 
            vocabularies[u"committee-types-statuses"]
        )
