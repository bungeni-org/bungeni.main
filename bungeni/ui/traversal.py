# !+ CLEAN OUT THIS FILE PLEASE !

from zope.container.traversal import ContainerTraverser
#from zope.security.checker import ProxyFactory
from zope.traversing.browser import AbsoluteURL

from bungeni.core.content import AkomaNtosoSection
from bungeni.alchemist import Session
from bungeni.models.domain import Doc

from sqlalchemy import extract

from bungeni.models.domain import User
from bungeni.models.utils import get_login_user
from zope.publisher.interfaces import IPublishTraverse, NotFound

import datetime
import traceback
import sys

from bungeni.utils import register

class SiteTraverser(ContainerTraverser):
    """ Custom traverser for special 'bungeni' section
    """

    def __init__(self, container, request):
        self.session = Session()
        super(SiteTraverser, self).__init__(container, request)

    def publishTraverse(self, request, name):
        
        # last section, retrieve object
        if name == "main":
            try:
                object = self.get_query(self.context.type, self.context.id,\
                                        self.context.date, self.context.lang).one()
                #object.__parent__ = self.context
                if object.uri is not None:
                    return object
            except:
                traceback.print_exception(*sys.exc_info())
        
        # creating temporary AkomaNtoso section to store url data
        context = AkomaNtosoSection(
            title=name,
            description=name,
            default_name=name,
        )
            
        # copying info
        context.id = self.context.id 
        context.date = self.context.date 
        context.lang = self.context.lang 
        context.type = self.context.type

        # for now should always be "ke" 
        if name == 'ke':
            return context
        # getting content type
        if not context.type:
            context.type = name
            return context
        # getting date
        if not context.date:
            context.date = name
            return context
        # getting registry number     
        if not context.id:
            context.id = name
            return context
        # getting language   
        if not context.lang:
            context.lang = name[:-1]
            return context

        return super(SiteTraverser, self).publishTraverse(request, name)
    
    def get_query(self, content_type, id, date, lang):
        d = date.split('-')
        date = datetime.date(int(d[0]), int(d[1]), int(d[2]))
        
        if content_type == "bill":
            from bungeni.models.domain import Bill # !+CUSTOM
            return self.session.query(Bill).filter(Bill.registry_number==id).\
                                            filter(Bill.publication_date==date).\
                                            filter(Bill.language==lang)
        return self.session.query(Doc).filter(Doc.registry_number==id).\
                                                     filter(Doc.type==content_type).\
                                                     filter(Doc.language==lang).\
                                                     filter(extract('year',Doc.status_date)==date.year).\
                                                     filter(extract('month',Doc.status_date)==date.month).\
                                                     filter(extract('day',Doc.status_date)==date.day)



@register.protect({"bungeni.user.Edit": 
    dict(attributes=["browserDefault"], interface=IPublishTraverse)})
class ProfileTraverser(ContainerTraverser):

    def publishTraverse(self, request, name):

        # Shortcut for current user workspace
        if name == u"profile":
            user = get_login_user()
            if user is not None:
                user.__parent__ = self.context
                user.__name__ = "profile"
                return user
            else:
                return NotFound(self.context, name, request)
            
        return super(ProfileTraverser, self).publishTraverse(request, name)                                                     

                                                    
class Permalink(AbsoluteURL):
    """ Custom absoluteURL view for objects in bungeni section. """
    
    def __str__(self):
            return self.context.uri

    __call__ = __str__
