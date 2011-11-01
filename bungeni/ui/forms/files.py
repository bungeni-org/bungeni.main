# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Attached file viewlets

$Id$
$URL$
"""

from zope.viewlet import viewlet
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.security.management import getInteraction
from zope.security.proxy import removeSecurityProxy

from bungeni.models.interfaces import IAttachedFileVersion, \
    IQuestion, IBill, IMotion, ITabledDocument, IAgendaItem, IEventItem
from bungeni.ui.i18n import _
from bungeni.ui import utils
from bungeni.ui.forms.interfaces import ISubFormViewletManager
from bungeni.utils import register


# for_, layer, view, manager
@register.viewlet(IQuestion, manager=ISubFormViewletManager)
@register.viewlet(IBill, manager=ISubFormViewletManager)
@register.viewlet(IMotion, manager=ISubFormViewletManager)
@register.viewlet(ITabledDocument, manager=ISubFormViewletManager)
@register.viewlet(IAgendaItem, manager=ISubFormViewletManager)
@register.viewlet(IEventItem, manager=ISubFormViewletManager)
class LibraryViewlet(viewlet.ViewletBase):
    
    render = ViewPageTemplateFile ('templates/attached-files.pt')
    form_name = _(u"attached files")
    
    for_display = True
    
    def __init__(self, context, request, view, manager):
        self.context = []
        trusted = removeSecurityProxy(context)
        # !+(murithi, mar-2010 )Attached file versions implement IVersion 
        # but have no attached files - an adapter on all content
        # might make sense to fetch attachments. 
        # here we conditionaly skip attachment versions
        if not IAttachedFileVersion.providedBy(trusted):
            for f in trusted.attached_files:
                if IAttachedFileVersion.providedBy(f):
                    self.context.append(f)
                else:
                    if f.attached_file_type != "system":
                        self.context.append(f)
        self.request = request
        self.__parent__ = context
        self.manager = manager
        self.query = None
        self.for_display = len(self.context) > 0
        self.interaction = getInteraction()
        self.formatter = utils.date.getLocaleFormatter(self.request, "date",
            "long"
        )
    
    def results(self):
        for data in self.context:
            yield {'title': data.file_title,
                   'url': './files/obj-%i' % data.attached_file_id,
                   'name': data.file_name,
                   'type': _(data.attached_file_type),
                   'status_date': self.formatter.format(data.status_date),
                   'menu': self.generate_file_manipulation_menu(data)}
    
    def generate_file_manipulation_menu(self, context):
        menu_items = []
        view_item = self.create_view_menu_item(context)
        if view_item:
            menu_items.append(view_item)
        edit_item = self.create_edit_menu_item(context)
        if edit_item:
            menu_items.append(edit_item)
        delete_item = self.create_delete_menu_item(context)
        if delete_item:
            menu_items.append(delete_item)
        download_item = self.create_download_menu_item(context)
        if download_item:
            menu_items.append(download_item)
        return menu_items

    def create_view_menu_item(self, context):
        permission_name = 'bungeni.fileattachment.View'
        if self.interaction.checkPermission(permission_name, self.__parent__):
            return {'title': _(u'VIEW'),
                    'url': './files/obj-%i' % context.attached_file_id,
                    'active': True}
        return None

    def create_edit_menu_item(self, context):
        permission_name = 'bungeni.fileattachment.Edit'
        if self.interaction.checkPermission(permission_name, self.__parent__):
            return {'title': _(u'EDIT'),
                    'url': './files/obj-%i/edit' % context.attached_file_id,
                    'active': True}
        return None

    def create_delete_menu_item(self, context):
        permission_name = 'bungeni.fileattachment.Delete'
        if self.interaction.checkPermission(permission_name, self.__parent__):
            return {'title': _(u'DELETE'),
                    'url': './files/obj-%i/deactivate' % context.attached_file_id,
                    'active': context.status != u'inactive'}
        return None

    def create_download_menu_item(self, context):
        permission_name = 'bungeni.fileattachment.View'
        if self.interaction.checkPermission(permission_name, self.__parent__):
            return {'title': _(u'DOWNLOAD'),
                    'url': './files/obj-%i/download' % context.attached_file_id,
                    'active': True}
        return None



''' !+FILE_VERSIONS_VIEWLET(mr, nov-2011) unused?

from bungeni.models.interfaces import IVersion
@register.viewlet(IVersion, manager=ISubFormViewletManager)
class VersionLibraryViewlet(LibraryViewlet):

    def __init__(self, context, request, view, manager):
        super(VersionLibraryViewlet, self).__init__(context, request, view, manager)
        self.base_url = utils.url.absoluteURL(
                                self.__parent__.__parent__.__parent__, self.request)
    
    def results(self):
        for data in self.context:
            file_type = data.attached_file_type
            if file_type == "system":
                continue
            elif file_type is None:
                file_type = " - "
            else:
                file_type = _(file_type)
            yield {'title': data.file_title,
                   'url': self.base_url + '/files/obj-%i/versions/obj-%i' \
                          % (data.content_id, data.version_id),
                   'name': data.file_name,
                   'type': file_type,
                   'status_date': self.formatter.format(data.status_date),
                   'menu': self.generate_file_manipulation_menu(data)}

    def create_view_menu_item(self, context):
        permission_name = 'bungeni.fileattachment.View'
        if self.interaction.checkPermission(permission_name, self.__parent__):
            return {'title': _(u'VIEW'),
                    'url': '%s/files/obj-%i/versions/obj-%i' % \
                            (self.base_url, context.content_id, context.version_id)}
        return None

    def create_edit_menu_item(self, context):
        # Edit menu item should not be provided for versions
        return None

    def create_delete_menu_item(self, context):
        # Delete menu item should not be provided for versions
        return None

    def create_download_menu_item(self, context):
        permission_name = 'bungeni.fileattachment.View'
        if self.interaction.checkPermission(permission_name, self.__parent__):
            return {'title': _(u'DOWNLOAD'),
                    'url': '%s/files/obj-%i/versions/obj-%i/download' % \
                            (self.base_url, context.content_id, context.version_id)}
        return None
'''

