"""
Override of ore.xapian operation factory that is aware of object translations
"""

from zope import component, interface

import transaction
import threading
import logging
import xappy
from ore.xapian import interfaces
from ore.xapian import queue
from ore.xapian.operation import get_buffer

from index import languages
from bungeni.models.interfaces import ITranslatable
from bungeni.core import translation

log = logging.getLogger('ore.xapian')

class IndexOperation( object ):
    """
    an async/queued index operation
    """

    #!+DISABLE_XAPIAN
    #interface.implements( interfaces.IIndexOperation )

    __slots__ = ('oid', 'resolver_id', 'requeue')
    requeue = False
    
    def __init__( self, oid, resolver_id ):
        self.oid = oid
        self.resolver_id = resolver_id

    def get_resolver(self):
        if self.resolver_id:
            return component.getUtility( interfaces.IResolver , self.resolver_id ) 
        else:
            return component.getUtility( interfaces.IResolver )

    def resolve( self ):
        resolver = self.get_resolver()
        instance = resolver.resolve( self.oid )

        if not instance:
            log.error("Idx Operation - Could Not Resolve %s"%(self.oid))
            return
#            return interfaces.OP_REQUEUE
        
        return instance

    def process( self, connection ):
        raise NotImplemented

    @property
    def document_id( self ):
        return self.oid

class AddOperation( IndexOperation ):

    #!+DISABLE_XAPIAN
    interface.implements( interfaces.IAddOperation )

    def process( self, connection ):
        if interfaces.DEBUG_LOG: log.info("Adding %r"%self.document_id )
        instance = self.resolve()
        if not instance or instance == interfaces.OP_REQUEUE:
            return instance
        doc = interfaces.IIndexer( instance ).document( connection )
        doc.id = self.document_id
        doc.fields.append( xappy.Field('resolver', self.resolver_id or '' ) )
        connection.add( doc )
        
class ModifyOperation( IndexOperation ):

    #!+DISABLE_XAPIAN
    #interface.implements( interfaces.IModifyOperation )
    
    def process( self, connection ):
        if interfaces.DEBUG_LOG: log.info("Modifying %r"%self.document_id )        
        instance = self.resolve()
        if not instance or instance == interfaces.OP_REQUEUE:
            return instance        

        doc = interfaces.IIndexer( instance ).document( connection )
        doc.id = self.document_id        
        doc.fields.append( xappy.Field('resolver', self.resolver_id or '' ) )
        connection.replace(doc)
    
            
        
class DeleteOperation( IndexOperation ):

    #!+DISABLE_XAPIAN
    #interface.implements( interfaces.IDeleteOperation )
    
    def process( self, connection ):
        if interfaces.DEBUG_LOG: log.info("Deleting %r"%self.document_id )
        instance = self.resolve()
        if ITranslatable.providedBy(instance):
            for lang in languages():
                doc_id = self.get_resolver().id(instance, language=lang.value)
                connection.delete( doc_id )
                
        else:
            connection.delete( self.document_id )


class OperationFactory( object ):

    #!+DISABLE_XAPIAN
    #interface.implements( interfaces.IOperationFactory )

    __slots__ = ('context',)

    resolver_id = '' # default resolver

    def __init__( self, context ):
        self.context = context
    
    def add( self ):
        return self._store( AddOperation( *self._id() ) )

    def modify( self ):
        return self._store( ModifyOperation( *self._id() ) )

    def remove( self ):
        return self._store( DeleteOperation( *self._id() ) )
        
    def _store( self, op ):

        # optionally enable synchronous operation, which bypasses the queue, for testing
        # purposes.
        if interfaces.DEBUG_SYNC and interfaces.DEBUG_SYNC_IDX:
            if interfaces.DEBUG_LOG: log.info("Processing %r %r"%(op.oid, op) )
            op.process( interfaces.DEBUG_SYNC_IDX )
            interfaces.DEBUG_SYNC_IDX.flush()
            if interfaces.DEBUG_LOG: log.info("Flushed Index")            
        else:
            get_buffer().add( op )
        
    def _id( self ):
        if self.resolver_id:
            resolver = component.getUtility( interfaces.IResolver , self.resolver_id ) 
        else:
            resolver = component.getUtility( interfaces.IResolver )
            
        oid = resolver.id( self.context )
        if not oid:
            raise KeyError( "Key Not Found %r"%( self.context ) )
        return oid, self.resolver_id
