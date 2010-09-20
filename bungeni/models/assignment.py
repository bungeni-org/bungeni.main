"""
Group Item Assignment Infrastructure

$Id$
"""

from zope import interface
from bungeni.alchemist import Session
from zope.security.proxy import removeSecurityProxy
from zope.dottedname.resolve import resolve
from sqlalchemy import orm
from datetime import datetime

import interfaces

from bungeni.models import schema, domain
from bungeni.models.interfaces import IAssignment
    
class GroupContextAssignments( object ):
    
    interface.implements( interfaces.IContextAssignments )
    
    def __init__( self, context ):
        self.context = context
        
    def __iter__( self ):
        for i in Session().query( GroupAssignment ).filter_by( group_id = self.context.group_id ):
            yield i
            
class ContentAssignments( object ):
    
    interface.implements( interfaces.IContentAssignments )

    def __init__( self, context):
        self.context = context
        
    def __iter__( self ):
        unwrapped = removeSecurityProxy( self.context )
        mapper = orm.object_mapper( unwrapped )
        primary_key = mapper.primary_key_from_instance( unwrapped )[0]

        assignments =  Session().query( GroupAssignment ).filter_by(
            item_id = primary_key)
#            object_type = unwrapped.__class__.__name__ )
            
        for i in assignments:
            yield i

class GroupAssignmentFactory( object ):

    interface.implements( interfaces.IAssignmentFactory )
    
    def __init__( self, content, group ):
        self.content = content
        self.group = group

    def new( self, **kw ):
        assignment = GroupAssignment()
        assignment.group_id = self.group.group_id

        unwrapped = removeSecurityProxy( self.content )
        mapper = orm.object_mapper( unwrapped )
        primary_key = mapper.primary_key_from_instance( unwrapped )[0]
        
        assignment.item_id = primary_key
#        assignment.object_type = unwrapped.__class__.__name__
        assignment.start_date = datetime.now()
        assignment.language = self.group.language
        Session().add( assignment )
        return assignment
    
class GroupAssignment( object ):

    interface.implements( IAssignment )

    @property
    def context( self ):
        return self.group

    @property
    def content( self ):
#        content_class = resolve( self.object_type )
        content = Session().query( domain.ParliamentaryItem ).get( self.item_id )
        self.content = content
        return content

orm.mapper( GroupAssignment, schema.group_item_assignments )
            


