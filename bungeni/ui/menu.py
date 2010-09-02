import operator
import datetime

from zope import component
from zope.app.component.hooks import getSite
from zope.app.security.interfaces import IUnauthenticatedPrincipal
from zope.app.publisher.interfaces.browser import IBrowserMenu
from zope.app.publisher.browser.menu import BrowserMenu
from zope.app.publisher.browser.menu import BrowserSubMenuItem
from zope.security import checkPermission
from zope.i18n import translate
from bungeni.models.utils import get_current_parliament_committees
import z3c.menu.ready2go.item

from ore.workflow.interfaces import IWorkflow, IWorkflowInfo

from bungeni.models.utils import get_db_user_id
from bungeni.models.interfaces import IBungeniApplication, IBungeniContent

from bungeni.core.translation import get_language
from bungeni.core.translation import get_all_languages
from bungeni.core.translation import get_available_translations
from bungeni.core import schedule
from bungeni.core.globalsettings import getCurrentParliamentId
from bungeni.core.schedule import PlenarySchedulingContext

from bungeni.ui.i18n import  _
from bungeni.ui.utils import url as ui_url, debug
from bungeni.ui import interfaces
from bungeni.ui.tagged import get_states
# r5327 - following added inorder to fix issue 319. needs review

''' !+ add mechanism for a better overview/control of menu order
MENU_ORDER = [
    None,
    "CalendarSubMenuItem", # 10
    "WorkflowSubMenuItem", # 40 
    "TranslationSubMenuItem", # 50
]
'''

def get_actions(name, context, request):
    menu = component.getUtility(IBrowserMenu, name)
    items = menu.getMenuItems(context, request)
    
    site_url = ui_url.absoluteURL(getSite(), request)
    url = ui_url.absoluteURL(context, request)
    
    for item in items:
        item['url'] = ui_url.urljoin(url, item['action'])
        item['id'] = item['title'].lower().replace(' ', '-')
        item['icon'] = ui_url.urljoin(site_url, item['icon'])
    return items

class GlobalMenuItem(z3c.menu.ready2go.item.GlobalMenuItem):
    pass
    
class LoginAction(GlobalMenuItem):
    
    @property
    def available(self):
        available = IUnauthenticatedPrincipal.providedBy(self.request.principal)
        return available

    @property
    def title(self):
        return _("Login")

class LogoutAction(GlobalMenuItem):
    
    @property
    def available(self):
        authenticated = not IUnauthenticatedPrincipal.providedBy(self.request.principal)
        return authenticated
        
    @property
    def title(self):
        return _("Logout")
        
class DashboardAction(GlobalMenuItem):

    @property
    def id(self):
        return "user-id"
    
    @property
    def title(self):
        return self.request.principal.id
        
    @property
    def available(self):
        authenticated = not IUnauthenticatedPrincipal.providedBy(self.request.principal)
        return authenticated

class AdminAction(GlobalMenuItem):
    
    def getURLContext(self):
        site = getSite()
        return site['admin']

    #@property
    #def available(self):
    #    context = self.getURLContext()
    #    return getInteraction().checkPermission('zope.ManageSite', context)


# 
# class TaskMenu(managr.MenuManager):
#
#     def update(self):
#         """See zope.contentprovider.interfaces.IContentProvider"""
#         self.__updated = True
# 
#         viewlets = self._getViewlets()
#
#         viewlets = self.filter(viewlets)
#         viewlets = self.sort(viewlets)
#         # Just use the viewlets from now on
#         self.viewlets=[]
#         for name, viewlet in viewlets:
#             if ILocation.providedBy(viewlet):
#                 viewlet.__name__ = name
#             self.viewlets.append(viewlet)
#         self._updateViewlets()
# 
#     def _getViewlets(self):
#         interaction = getInteraction()
#         # Find all content providers for the region
#         viewlets = component.getAdapters(
#             (self.context, self.request, self.__parent__, self),
#             interfaces.IViewlet)
        

class TranslationSubMenuItem(BrowserSubMenuItem):
    # Note: 
    # BrowserSubMenuItem is a BrowserView but BrowserMenu is just an object.
    
    title = _(u'label_translate', default=u'Language:')
    submenuId = 'context_translate'
    order = 50
    
    #def __init__(self, context, request):
    #    super(TranslationSubMenuItem, self).__init__(context, request)
    
    @property
    def extra(self):
        language = get_language(self.context)
        return {
            'id'         : 'plone-contentmenu-translation',
            'class'      : 'language-%s' % language,
            'state'      : language,
            'stateTitle' : language
            }
    
    @property
    def description(self):
        return u''

    @property
    def action(self):
        url = ui_url.absoluteURL(self.context, self.request)
        if checkPermission("bungeni.translation.Add", self.context):
            return "%s/translate" % url
        else:
            return url
    
    def selected(self):
        return False

class TranslateMenu(BrowserMenu):
    @property
    def current_language(self):
        return "en"
    
    def getMenuItems(self, context, request):
        """Return menu item entries in a TAL-friendly form."""
        url = ui_url.absoluteURL(context, request)
        if checkPermission("bungeni.translation.Add", context):
            language = get_language(context)
            available = get_available_translations(context)
            results = []
            for name, obj in get_all_languages().items():
                title = obj['name']
                # skip the current language
                if name==language:
                    continue
                action_url = url + '/translate?language=%s' % name
                extra = {'id': 'translation-action-%s' % name,
                         'separator': None,
                         'class': ''}
                translation_id = available.get(name)
                results.append(
                    dict(title=title,
                         description="",
                         action=action_url,
                         selected=translation_id is not None,
                         icon=None,
                         extra=extra,
                         submenu=None))
            return results
        else:
            return None
    

class WorkflowSubMenuItem(BrowserSubMenuItem):
    title = _(u'label_state', default=u'State:')
    submenuId = 'context_workflow'
    order = 40
    
    def __new__(cls, context, request):
        # this is currently the only way to make sure this menu only
        # 'adapts' to a workflowed context; the idea is that the
        # component lookup will fail, which will propagate back to the
        # original lookup request
        workflow = IWorkflow(context, None)
        if workflow is None:
            return
        return object.__new__(cls, context, request)

    def __init__(self, context, request):
        BrowserSubMenuItem.__init__(self, context, request)
        self.context = context
        self.url = ui_url.absoluteURL(context, request)
        self.request = request
        
    @property
    def extra(self):
        info = IWorkflowInfo(self.context, None)
        if info is None:
            return {'id': 'plone-contentmenu-workflow'}
        state = info.state().getState()
        stateTitle = translate(
            str(info.workflow().workflow.states[state].title), 
            domain="bungeni.core",
            context=self.request)
        
        return {'id'         : 'plone-contentmenu-workflow',
                'class'      : 'state-%s' % state,
                'state'      : state,
                'stateTitle' : stateTitle,} # TODO: should be translated

    @property
    def description(self):
        return u''

    @property
    def action(self):
        return self.url
    
    def selected(self):
        return False

class WorkflowMenu(BrowserMenu):
    def getMenuItems(self, context, request):
        """Return menu item entries in a TAL-friendly form."""
        if interfaces.IBusinessWhatsOnSectionLayer.providedBy(request):
            return ()
        else:
            if IBungeniApplication.providedBy(context.__parent__):
                return ()
        wf = IWorkflow(context, None)
        if wf is None:
            return ()
        #state = IWorkflowInfo(context).state().getState()
        wf_info = IWorkflowInfo(context)
        transitions = wf_info.getManualTransitionIds()
        
        # !+ context_workflow menu: the order of transitions is alphabetic, but 
        # should really be order of definition.
        parliament_id = getCurrentParliamentId()
        
        url = ui_url.absoluteURL(context, request)
        site_url2 = ui_url.absoluteURL(getSite(), request)
        results = []
        for transition in transitions:
            tid = transition
            state_transition = wf.getTransitionById(transition)
            #Compares the current url to homepage to determine whether we are on workspace or not.
            #Fix for bug 319
            #Someone should probably review this.
            if url == site_url2:
                transition_url = site_url2 + \
                             '/archive/browse/parliaments/obj-' + str(parliament_id) + \
                             '/change_workflow_state?' + \
                             'transition=%s&next_url=...' % tid
            else:
                transition_url = url + \
                             '/change_workflow_state?'\
                             'transition=%s&next_url=...' % tid
            extra = {'id': 'workflow-transition-%s' % tid,
                     'separator': None,
                     'class': ''}
            
            state_title = translate(str(state_transition.title), 
                    domain="bungeni.core", 
                    context=request)
            results.append(
                dict(title=state_title,
                     description="",
                     action=transition_url,
                     selected=False,
                     transition_id=tid,
                     icon=None,
                     extra=extra,
                     submenu=None))
        
        return results

class CalendarSubMenuItem(BrowserSubMenuItem):
    title = _(u'label_calendar_context', default=u'Calendar:')
    submenuId = 'context_calendar'
    order = 10

    def __new__(cls, context, request):
        if context.get_group() is not None:
            return object.__new__(cls, context, request)

    def __init__(self, context, request):
        BrowserSubMenuItem.__init__(self, context, request)
        self.context = context
        self.url = ui_url.absoluteURL(context, request)
        
    @property
    def extra(self):
        return {'id': 'plone-contentmenu-calendar',
                'stateTitle': self.context.label}

    @property
    def description(self):
        return u''

    @property
    def action(self):
        return self.url
    
    def selected(self):
        return False

class CalendarMenu(BrowserMenu):
    """Retrieve menu actions for available calendars."""
    
    def getSchedulingContexts(self, request):
        """Set up scheduling contexts.

        Currently we include:

        - committees
        - plenary

        """

        contexts = []
        app = getSite()
        today = datetime.date.today()
        if interfaces.IWorkspaceSchedulingSectionLayer.providedBy(request):
            committees = app["workspace"]["scheduling"]["committees"].values()
        else:
            committees = app["business"]["committees"].values()
        
        user_id = get_db_user_id()
        for committee in committees:
            if user_id:
                if ((committee.end_date is None or committee.end_date >= today) and 
                   (committee.start_date is None or committee.start_date <= today) and
                   checkPermission("bungeni.agendaitem.Add", committee) and
                   (committee.status == "active")):
                    contexts.append(schedule.CommitteeSchedulingContext(committee))
            else:
                if ((committee.end_date is None or committee.end_date >= today) and 
                   (committee.start_date is None or committee.start_date <= today) and
                   (committee.status == "active")):
                    contexts.append(schedule.CommitteeSchedulingContext(committee))
        for context in contexts:
            context.__name__ = u"schedule"
        if interfaces.IWorkspaceSchedulingSectionLayer.providedBy(request):
            contexts.append(schedule.WorkspaceSchedulingContext(app["workspace"]["scheduling"]))
        else:
            contexts.append(schedule.PlenarySchedulingContext(app))
        contexts[-1].__name__ = u""

        

        return contexts
    
    def getMenuItems(self, context, request):
        """Return menu item entries in a TAL-friendly form."""

        group_id = context.get_group().group_id
        contexts = self.getSchedulingContexts(request)
        
        results = []
        for context in contexts:
            group = context.get_group()
            if group.group_id==group_id:
                continue
            
            url = ui_url.absoluteURL(context, request)
            
            extra = {'id': 'calendar-link-%s' % group.group_id,
                     'separator': None,
                     'class': ''}

            results.append(
                dict(title=context.label,
                     description=group.description,
                     action=url,
                     selected=False,
                     icon=None,
                     extra=extra,
                     submenu=None))

        # sort on title
        results.sort(key=operator.itemgetter("title"))

        return results
