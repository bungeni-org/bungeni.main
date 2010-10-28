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
from zope.app.publisher.interfaces.browser import IBrowserMenu
from zope.app.publisher.browser import queryDefaultViewName
from zope.annotation.interfaces import IAnnotations

from ore.wsgiapp.interfaces import IApplication

from ploned.ui.menu import make_absolute
from ploned.ui.menu import pos_action_in_url

from bungeni.alchemist.interfaces import IAlchemistContainer, IAlchemistContent
from bungeni.alchemist.model import queryModelDescriptor
from bungeni.alchemist.traversal import ManagedContainerDescriptor
from bungeni.core import location
from bungeni.ui.utils import url, debug
from bungeni.ui import interfaces
from bungeni.ui import browser
from bungeni.ui import z3evoque

def _get_context_chain(context):
    context = proxy.removeSecurityProxy(context)
    chain = []
    while context is not None:
        chain.append(context)
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
                title = context.short_name
    elif IAlchemistContainer.providedBy(context):
        domain_model = context._class 
        try:
            descriptor = queryModelDescriptor(domain_model)
        except:
            descriptor = None
            name = ""
        if descriptor:
            name = getattr(descriptor, 'container_name', None)
            if name is None:
                name = getattr(descriptor, 'display_name', None)
        if not name:
            name = getattr(context, '__name__', None)
        title = name
    elif ILocation.providedBy(context) and \
         IDCDescriptiveProperties.providedBy(context):
        title = context.title
    return title

class SecondaryNavigationViewlet(browser.BungeniViewlet):
    
    # evoque
    render = z3evoque.ViewTemplateFile("navigation.html#secondary",
        i18n_domain="bungeni.core")
    # zpt
    #render = ViewPageTemplateFile("templates/secondary-navigation.pt")
    
    def update(self):
        request = self.request
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
        for item in sorted(items, key=lambda item: item['action'], reverse=True):
            action = item['action']
            if default_view_name==action.lstrip('@@'):
                _url = local_url
                if selection is None:
                    selected = sameProxiedObjects(container, self.context)
            else:
                _url = make_absolute(action, local_url, site_url)
                if selection is None:
                    selected = pos_action_in_url(action, request_url)
            item['url'] = _url
            item['selected'] = selected and u'selected' or u''
            if selected:
                # self is marker
                selection = self
                selected = False
            self.items.append(item)
    
    def add_container_menu_items(self, context, container):
        request = self.request
        # add a menu item for each user workspace, if we are in an 
        # IWorkspaceSectionLayer 
        # !+ if user is logged in or if request.layer_data
        
        if (interfaces.IWorkspaceSectionLayer.providedBy(request) or
            interfaces.IWorkspaceSchedulingSectionLayer.providedBy(request)
        ):
            try:
                workspaces = IAnnotations(request)["layer_data"].get("workspaces")
            except:
                workspaces = []
            log.info("%s got user workspaces: %s" % (self, workspaces))
            base_url_path = "/workspace"
            for workspace in workspaces:
                log.info("appending menu item for user workspace: %s" % 
                                                                str(workspace))
                self.items.append(url.get_menu_item_descriptor(
                    workspace.full_name,
                    pos_action_in_url("/workspace/obj-%s"%workspace.group_id,
                        request.getURL()),
                    base_url_path,
                    "obj-%s" % workspace.group_id ))
        
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

    
class GlobalSectionsViewlet(browser.BungeniViewlet):
    
    # evoque
    render = z3evoque.ViewTemplateFile("navigation.html#sections")
    
    # zpt
    #render = ViewPageTemplateFile('templates/sections.pt')
    
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
            'extra': {'hideChildren': True, 'id': u''}, 
            'submenu': None, 
            'description': u'', 
            'title': u'Workspace', 
            'url': u'http://localhost:8081/', 
            'selected': u'selected', 
            'action': u'/', 
            'icon': None
        }
        """
        for item in menu.getMenuItems(context, request):
            if item['action'] in seen:
                continue
            seen.add(item['action'])
            item['url'] = item.setdefault('url', base_url + item['action'])
            item['id'] = item['action'].strip('/')
            item['name'] = item['title']
            self.portal_tabs.append(item)
            # take the last url-path matching action as selected_portal_tab
            if _action_is_on_path(item['action']):
                self.selected_portal_tab = item['id']
        
class BreadCrumbsViewlet(browser.BungeniViewlet):
    """Breadcrumbs.
    
    Render the breadcrumbs to show a user his current location.
    """
    # evoque
    render = z3evoque.ViewTemplateFile("navigation.html#breadcrumbs")
    
    # zpt
    #render = ViewPageTemplateFile( 'templates/breadcrumbs.pt' )

    def __init__( self,  context, request, view, manager ):
        self.context = context
        self.request = request
        self.__parent__= view
        self.manager = manager
        self.path = []
        self.site_url = url.absoluteURL(getSite(), self.request)
        self.user_name = ''

    def _get_path(self, context):
        """Return the current path as a list
        """
        descriptor = None
        name = None 
        path = []
        
        context = proxy.removeSecurityProxy(context)
        if context is None:
            return path
        # Proof-of-concept: support for selective inclusion in breadcrumb trail:
        # a view marked with an attribute __crumb__=False is NOT included in 
        # the breadcrumb trail (see core/app.py: "workspace" Section)
        if not getattr(context, "__crumb__", True):
            return path
        if context.__parent__ is not None:
            path.extend(self._get_path(context.__parent__))
        
        _url = url.absoluteURL(context, self.request)
        
        # Append a trailing slash to each breadcrumb entry so that
        # the right context is always maintained when the breadcrumbs
        # are used for navigation.
        _url = url.set_url_context(_url)
        
        title = _get_title_from_context(context)
        
        if title is not None:
            path.append({ 'name':title, 'url':_url})
        
        return path
    
    def update(self):
        self.path = self._get_path(self.context)

        # if the view is a location, append this to the breadcrumbs
        if ILocation.providedBy(self.__parent__) and \
               IDCDescriptiveProperties.providedBy(self.__parent__):
            self.path.append({
                'name': self.__parent__.title,
                'url': None,
                })
        try:
            self.user_name = self.request.principal.login
        except:
            pass
    

class NavigationTreeViewlet(browser.BungeniViewlet):
    """Render a navigation tree."""
    
    # evoque !+ requires evoque svn HEAD
    #render = z3evoque.ViewTemplateFile("navigation.html#tree")
    
    # zpt
    render = ViewPageTemplateFile( 'templates/bungeni-navigation-tree.pt' )
    
    path = ()
    
    def __new__(cls, context, request, view, manager):
        # we have both primary and secondary navigation, so we won't
        # show the navigation tree unless we're at a depth > 2
        chain = _get_context_chain(context)[:-2]
        if not chain:
            return

        # we require the tree to begin with a container object
        if not IReadContainer.providedBy(chain[-1]):
            return

        subcontext = chain[-1]
        if (len(chain) > 1 or
            IReadContainer.providedBy(subcontext) and not
            IAlchemistContainer.providedBy(subcontext) and len(subcontext)):
            inst = object.__new__(cls, context, request, view, manager)
            inst.chain = chain
            return inst

    def __init__(self, context, request, view, manager):
        self.context = context
        self.request = request
        self.__parent__= view
        self.manager = manager
        self.name = ''

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
            if IDCDescriptiveProperties.providedBy(context):
                title = context.title
            else:
                props = IDCDescriptiveProperties(context, None)
                if props is not None:
                    title = props.title
                else:
                    title = context.short_name

            selected = len(chain) == 0
            
            if chain:
                nodes = self.expand(chain)
            else:
                kls = context.__class__
                containers = [
                    (key, getattr(context, key))
                    for key, value in kls.__dict__.items()
                    if isinstance(value, ManagedContainerDescriptor)]
                nodes = []
                self.expand_containers(nodes, containers, _url, chain, None)

            items.append(
                {'title': title,
                 'url': _url,
                 'current': True,
                 'selected': selected,
                 'kind': 'content',
                 'nodes': nodes,
                 })

        elif IAlchemistContainer.providedBy(context):
            # loop through all managed containers of the parent
            # object, and include the present container as the
            # 'current' node.
            parent = context.__parent__
            assert parent is not None
            _url = url.absoluteURL(parent, self.request)

            # append managed containers as child nodes
            kls = type(proxy.removeSecurityProxy(parent))

            if include_siblings is True:
                if IApplication.providedBy(parent):
                    containers = [
                        (name, parent[name])
                        for name in 
                            location.model_to_container_name_mapping.values()
                        if name in parent
                    ]
                elif IReadContainer.providedBy(parent):
                    containers = list(parent.items())
                else:
                    containers = [
                        (key, getattr(parent, key))
                        for key, value in kls.__dict__.items()
                        if isinstance(value, ManagedContainerDescriptor)]
            else:
                containers = [(context.__name__, context)]
                
            self.expand_containers(items, containers, _url, chain, context)

        elif ILocation.providedBy(context):
            _url = url.absoluteURL(context, self.request)
            #props = IDCDescriptiveProperties.providedBy(context) and \
            #    context or IDCDescriptiveProperties(context)
            if IDCDescriptiveProperties.providedBy(context):
                props = IDCDescriptiveProperties(context)
            else:
                props = context
            props = proxy.removeSecurityProxy(props)

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
            i_id = getattr(props, 'id','N/A')
            items.append(
                {'title': getattr(props, 'title', i_id),
                 'url': _url,
                 'current': True,
                 'selected': selected,
                 'kind': 'location',
                 'nodes': nodes,
                 })

        elif IReadContainer.providedBy(context):
            items.extend(self.expand(chain))

        return items

    def expand_containers(self, items, containers, _url, chain=(), context=None):
        #seen_context = False
        current = False
        
        for key, container in containers:
            if IAlchemistContainer.providedBy(container):
                descriptor = queryModelDescriptor(
                    proxy.removeSecurityProxy(container).domain_model)
                if descriptor:
                    name = getattr(descriptor, 'container_name', None)
                    if name is None:
                        name = getattr(descriptor, 'display_name', None)
                        
                if not name:
                    name = container.domain_model.__name__
            else:
                assert IDCDescriptiveProperties.providedBy(container)
                container = proxy.removeSecurityProxy(container)
                name = container.title

            if context is not None:
                current = container.__name__ == context.__name__

            selected = len(chain) == 0 and current

            if current:
                #seen_context = True
                nodes = self.expand(chain)
            else:
                nodes = ()

            items.append(
                {'title': name,
                 'url': "%s/%s" % (_url.rstrip('/'), key),
                 'current': current,
                 'selected': selected,
                 'kind': 'container',
                 'nodes': nodes,
                 })
                 
class TopLevelContainerNavigation(NavigationTreeViewlet):

   def __new__(cls, context, request, view, manager):
        # we have both primary and secondary navigation, so we won't
        # show the navigation tree unless we're at a depth > 2
        chain = _get_context_chain(context)[:-2]
        if len(chain) > 2:
            chain = chain[-2:]

        if not chain:
            return

        # we require the tree to begin with a container object
        if not IReadContainer.providedBy(chain[-1]):
            return

        subcontext = chain[-1]
        if (len(chain) > 1 or
            IReadContainer.providedBy(subcontext) and not
            IAlchemistContainer.providedBy(subcontext) and len(subcontext)):
            inst = object.__new__(cls, context, request, view, manager)
            inst.chain = chain
            return inst

