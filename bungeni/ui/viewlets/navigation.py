# -*- coding: utf-8 -*-
# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Navigation elements of the UI

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.viewlets.navigation")

import sys
from zope import component
from zope.location.interfaces import ILocation
from zope.dublincore.interfaces import IDCDescriptiveProperties
from zope.container.interfaces import IReadContainer
from zope.security import proxy
from zope.proxy import sameProxiedObjects
from zope.app.component.hooks import getSite
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.browsermenu.interfaces import IBrowserMenu
from zope.publisher.defaultview import queryDefaultViewName
#from zope.annotation.interfaces import IAnnotations
from zope.i18n import translate

from ore.wsgiapp.interfaces import IApplication

from ploned.ui.menu import make_absolute
from ploned.ui.menu import pos_action_in_url

from bungeni.alchemist.interfaces import IAlchemistContainer, IAlchemistContent
from bungeni.alchemist import utils
from bungeni.core.interfaces import IWorkspaceContainer, ISection
from bungeni.core import location
from bungeni.core.translation import get_request_language
from bungeni.ui.utils import url, debug
from bungeni.ui import browser
from bungeni.models.utils import get_chamber_for_context


def _get_context_chain(context):
    chain = []
    while context is not None:
        chain.append(proxy.removeSecurityProxy(context))
        context = context.__parent__
    return chain


# !+DUPLICATE(mr, oct-2010)
# this code is very similar to BungeniBrowserView.page_title property
def _get_title_from_context(context):
    title = None
    if IAlchemistContent.providedBy(context):
        if IDCDescriptiveProperties.providedBy(context):
            title = context.title
        else:
            props = IDCDescriptiveProperties(context, None)
            if props is not None:
                title = props.title
            else:
                ''' !+
AttributeError: 'GroupAddress' object has no attribute 'short_name':   File "/home/undesa/bungeni/cap_installs/bungeni_install/bungeni/releases/20100305100101/src/bungeni.main/bungeni/ui/viewlets/navigation.py", line 59, in _get_title_from_context
                #title = context.short_name 
So, we temporarily default the above to the context.__class__.__name__:
                '''
                title = getattr(context, "title", context.__class__.__name__)
    elif IWorkspaceContainer.providedBy(context):
        # WorkspaceContainer._class is not set (and not unique) and it breaks the
        # connection between Container -> ContentClass
        title = context.__name__
    elif IAlchemistContainer.providedBy(context):
        domain_model = context._class 
        try:
            descriptor = utils.get_descriptor(domain_model)
        except KeyError, e:
            log.warn("TYPE_INFO: no descriptor for model %s "
                    "[container=%s] [error=%s]" % (
                        domain_model, context, e))
            descriptor = None
            name = ""
        if descriptor:
            name = getattr(descriptor, "container_name", None)
            if name is None:
                name = getattr(descriptor, "display_name", None)
        if not name:
            name = getattr(context, "__name__", None)
        title = name
    elif (ILocation.providedBy(context) and
        IDCDescriptiveProperties.providedBy(context)):
        title = IDCDescriptiveProperties(context).title
    return title

#!+DevProgammingGuide(mr, oct-2012) always return localized template data
class SecondaryNavigationViewlet(browser.BungeniViewlet):

    render = ViewPageTemplateFile("templates/secondary-navigation.pt")

    def update(self):
        #request = self.request
        context = self.context
        chain = _get_context_chain(context)
        length = len(chain)
        self.items = []
        if length < 2:
            # there must be at least: [top-level section, application]
            return # container is None
        else:
            # the penultimate context is the top-level container
            container = chain[-2]
            assert container.__name__ is not None
            if not IReadContainer.providedBy(container):
                return # container has no readable content
        assert container is not None
        
        # add container items
        if length > 2:
            context = chain[-3]
        else:
            context = None
        self.add_container_menu_items(context, container)
        # add any menu items from zcml
        self.add_zcml_menu_items(container)
    
    def add_zcml_menu_items(self, container):
        """Add the list of ZCML menu items (if any) for this top-level 
        container. Top-level section given by container may define a menu 
        in ZCML with naming convention: <container_name>_navigation. 
        """
        # !+ turn this into a utility
        zcml_menu_name_template = "%s_navigation"
        try:
            menu_name = zcml_menu_name_template % container.__name__
            menu = component.getUtility(IBrowserMenu, name=menu_name)
            items = menu.getMenuItems(container, self.request)
        except (Exception,):
            debug.log_exc(sys.exc_info(), log_handler=log.debug)
            return []
        
        # OK, do any necessary post-processing of each menu item
        local_url = url.absoluteURL(container, self.request)
        site_url = url.absoluteURL(getSite(), self.request)
        request_url = self.request.getURL()
        default_view_name = queryDefaultViewName(container, self.request)
        selection = None
        for item in sorted(items, key=lambda item: item["action"], reverse=True):
            action = item["action"]
            if default_view_name==action.lstrip("@@"):
                _url = local_url
                if selection is None:
                    selected = sameProxiedObjects(container, self.context)
            else:
                _url = make_absolute(action, local_url, site_url)
                if selection is None:
                    selected = pos_action_in_url(action, request_url)
            item["url"] = _url
            item["selected"] = selected and u"selected" or u""
            if selected:
                # self is marker
                selection = self
                selected = False
            self.items.append(item)
    
    def add_container_menu_items(self, context, container):
        request = self.request
        
        _url = url.absoluteURL(container, request)
        
        if IReadContainer.providedBy(container):
            #XXX should be the same in all containers ?
            container=proxy.removeSecurityProxy(container)
            for name, item in container.items():
                if context is None:
                    selected = False
                else:
                    selected = url.same_path_names(context.__name__, name)
                item = proxy.removeSecurityProxy(item)
                if IDCDescriptiveProperties.providedBy(item):
                    title = item.title
                else:
                    props = IDCDescriptiveProperties(item)
                    title = props.title
                # only items with valid title
                if title is not None:
                    self.items.append(url.get_menu_item_descriptor(
                            title, selected, _url, name))
        default_view_name = queryDefaultViewName(container, self.request)
        default_view = component.queryMultiAdapter(
            (container, self.request), name=default_view_name)
        if hasattr(default_view, "title") and default_view.title is not None:
            self.items.insert(0, url.get_menu_item_descriptor(
                    default_view.title, 
                    sameProxiedObjects(container, self.context), 
                    _url))


#!+DevProgammingGuide(mr, oct-2012) always return localized template data
class GlobalSectionsViewlet(browser.BungeniViewlet):

    render = ViewPageTemplateFile("templates/sections.pt")
    
    selected_portal_tab = None
    
    def update(self):
        context, request = self.context, self.request 
        base_url = url.absoluteURL(getSite(), request)
        item_url = request.getURL()
        
        assert item_url.startswith(base_url)
        path = item_url[len(base_url):]
        
        self.portal_tabs = []
        seen = set()
        menu = component.getUtility(IBrowserMenu, "site_actions")
        def _action_is_on_path(action):
            return path.startswith("/".join(action.split("/")[0:-1]))
        """A menu item looks like this:
        {
            "extra": {"hideChildren": True, "id": u""}, 
            "submenu": None, 
            "description": u"", 
            "title": u"Workspace", 
            "url": u"http://localhost:8081/", 
            "selected": u"selected", 
            "action": u"/", 
            "icon": None
        }
        """
        for item in menu.getMenuItems(context, request):
            if item["action"] in seen:
                continue
            seen.add(item["action"])
            item["url"] = item.setdefault("url", base_url + item["action"])
            item["id"] = item["action"].strip("/")
            item["name"] = item["title"]
            self.portal_tabs.append(item)
            # take the last url-path matching action as selected_portal_tab
            if _action_is_on_path(item["action"]):
                self.selected_portal_tab = item["id"]


#!+DevProgammingGuide(mr, oct-2012) always return localized template data
class BreadCrumbsViewlet(browser.BungeniViewlet):
    """Breadcrumbs.
    
    Render the breadcrumbs to show a user his current location.
    """
    render = ViewPageTemplateFile("templates/bread-crumbs.pt")

    def __init__(self,  context, request, view, manager):
        self.context = context
        self.request = request
        self.__parent__= view
        self.manager = manager
        self.path = []
        self.site_url = url.absoluteURL(getSite(), self.request)

    def _get_path(self, context):
        """Return the current path as a list
        """
        path = []
        
        context = proxy.removeSecurityProxy(context)
        
        if context is None:
            return path
        # Proof-of-concept: support for selective inclusion in breadcrumb trail:
        # a view marked with an attribute __crumb__=False is NOT included in 
        # the breadcrumb trail (see core/app.py: "workspace" Section)
        # !+__crumb__
        #if not getattr(context, "__crumb__", True):
        #    return path
        if context.__parent__ is not None:
            path.extend(self._get_path(context.__parent__))
        
        _url = url.absoluteURL(context, self.request)
        
        # Append a trailing slash to each breadcrumb entry so that
        # the right context is always maintained when the breadcrumbs
        # are used for navigation.
        _url = url.set_url_context(_url)
        
        title = _get_title_from_context(context)
        
        if title is not None:
            path.append({"name": title, "url": _url})
        
        return path
    
    def update(self):
        self.path = self._get_path(self.context)
        
        # if the view is a location, append this to the breadcrumbs
        if ILocation.providedBy(self.__parent__) and \
               IDCDescriptiveProperties.providedBy(self.__parent__):
            self.path.append({
                    "name": self.__parent__.title,
                    "url": None,
                })
        self.chamber = get_chamber_for_context(self.context)


class NavigationTreeViewlet(browser.BungeniViewlet):
    """Render a navigation tree."""
    
    render = ViewPageTemplateFile("templates/bungeni-navigation-tree.pt")
    
    path = ()
    
    def __new__(cls, context, request, view, manager):
        chain = _get_context_chain(context)
        chain.pop() # bungeni_app
        top_section = chain.pop()
        
        if not chain:
            return
        
        # we require the tree to begin with a container object
        if not IReadContainer.providedBy(chain[-1]):
            return
        
        # remove any views from navigation tree
        if not(IAlchemistContent.providedBy(chain[0]) or 
                IAlchemistContainer.providedBy(chain[0]) or
                ISection.providedBy(chain[0])
            ):
            chain.pop(0)
        
        subcontext = chain[-1]
        if (len(chain) > 1 or
                IReadContainer.providedBy(subcontext) and 
                not IAlchemistContainer.providedBy(subcontext) and 
                len(subcontext)
            ):
            inst = object.__new__(cls, context, request, view, manager)
            inst.chain = chain
            inst.top_section_url = url.absoluteURL(top_section, request)
            inst.id_prefix = "nav"
            return inst
    
    def __init__(self, context, request, view, manager):
        self.context = context
        self.request = request
        self.__parent__ = view
        self.manager = manager
        self.name = ""
    
    def update(self):
        """Creates a navigation tree for ``context``.
        
        Recursively, by visiting the parent chain in reverse order,
        the tree is built. The siblings of managed containers are
        included.
        """
        chain = list(self.chain)
        self.nodes = self.expand(chain, include_siblings=False)
    
    def expand(self, chain, include_siblings=True):
        if len(chain) == 0:
            return ()
        context = chain.pop()
        items = []
        if IApplication.providedBy(context):
            items.extend(self.expand(chain))
        elif IAlchemistContent.providedBy(context):
            _url = url.absoluteURL(context, self.request)
            selected = len(chain) == 0
            
            if chain:
                nodes = self.expand(chain)
            else:
                containers = utils.get_managed_containers(context)
                nodes = []
                self.expand_containers(nodes, containers, _url, chain, None)
            
            items.append({
                    "id": self.get_nav_entry_id(_url),
                    "label": IDCDescriptiveProperties(context).title,
                    "url": _url,
                    "current": True,
                    "selected": selected,
                    "kind": "content",
                    "nodes": nodes,
                })
        elif IAlchemistContainer.providedBy(context):
            # loop through all managed containers of the parent
            # object, and include the present container as the
            # "current" node.
            parent = context.__parent__
            assert parent is not None
            _url = url.absoluteURL(parent, self.request)
            
            # append managed containers as child nodes            
            if include_siblings is True:
                if IApplication.providedBy(parent):
                    containers = [ (name, parent[name])
                        for name in 
                            location.model_to_container_name_mapping.values()
                        if name in parent ]
                elif IReadContainer.providedBy(parent):
                    containers = list(parent.items())
                else:
                    containers = utils.get_managed_containers(parent)
            else:
                containers = [(context.__name__, context)]
            self.expand_containers(items, containers, _url, chain, context)
        elif ILocation.providedBy(context):
            # e.g. bungeni.core.content.Section, DisplayForm
            _url = url.absoluteURL(context, self.request)
            selected = len(chain) == 0
            if selected and IReadContainer.providedBy(context):
                nodes = []
                try:
                    self.expand_containers(
                        nodes, context.items(), _url, chain, context)
                except:
                    pass
            else:
                nodes = self.expand(chain)
            _title = getattr(context, "title", None) or \
                getattr(context, "page_title", "!+BungeniBrowserView.title")
            items.append({
                    "id": self.get_nav_entry_id(_url),
                    # !+BungeniBrowserView.title
                    "label": _title, #IDCDescriptiveProperties(context).title,
                    "url": _url,
                    "current": True,
                    "selected": selected,
                    "kind": "location",
                    "nodes": nodes,
                })
        elif IReadContainer.providedBy(context):
            #!+NavigationTreeViewlet-EXPAND-IReadContainer(mr, oct-2012) does this ever execute?!
            raise Exception("!+NavigationTreeViewlet-EXPAND-IReadContainer [%s]" % context)
            items.extend(self.expand(chain))
        return items
    
    def expand_containers(self, items, containers, _url, chain=(), context=None):
        #seen_context = False
        _url = _url.rstrip("/")
        current = False
        
        for key, container in containers:
            assert IAlchemistContainer.providedBy(container)
            label = container.domain_model.__name__
            descriptor = utils.get_descriptor(container.domain_model)
            order = 999
            if descriptor:
                order = descriptor.order
                label = getattr(descriptor, "container_name", None) or \
                    getattr(descriptor, "display_name", None)
            
            if context is not None:
                current = container.__name__ == context.__name__
            selected = not len(chain) and current
            if current:
                #seen_context = True
                nodes = self.expand(chain)
            else:
                nodes = ()
            
            key_url = "%s/%s" % (_url, key)
            items.append({
                    "id": self.get_nav_entry_id(key_url),
                    "order": order,
                    "label": translate(label, 
                        target_language=get_request_language(request=self.request),
                        domain="bungeni"),
                    "url": key_url,
                    "current": current,
                    "selected": selected,
                    "kind": "container",
                    "nodes": nodes,
                })
        items.sort(key=lambda item:(item['order'], item['label']))
    
    def get_nav_entry_id(self, _url):
        assert _url.startswith(self.top_section_url)
        depth = len(_url[len(self.top_section_url):].split("/"))
        _id = _url.split("/").pop()
        return "%s_%s_%d" % (self.id_prefix, _id, depth)


class TopLevelContainerNavigation(NavigationTreeViewlet):
    
    def __new__(cls, context, request, view, manager):
        inst = NavigationTreeViewlet.__new__(cls, context, request, view, manager)
        # we require the tree to begin with a container object
        if not IReadContainer.providedBy(inst.chain[-1]):
            return

