"""
xapian indexing adapters. we utilize a queue processor (ore.xapian)
using the xappy api ontop of the xapian python bindings. functionally
its basically an equivalent api to lucene, however the syntax is
different. the full capabilities exposed by xapian are best documented
in the doctests contained in its source (indexerconnection.rst, and
searchconnection.rst) as well as docs/introduction.rst. Those
documents are the best guide to understanding and utilizing the
features of xapian.

Event Handlers, to reindex on changes. The indexing system needs to be
kept in sync with the database during normal operations. a bulk
indexing script exists (sync-index) for database restoration
procedures. The ore.xapian package provides subscribers to cover
common operations for objects marked IIndexable, such as
create/add/delete operations. we need to provide event handlers for
two additional change events.

this module setups the indexing machinery for searches

$Id$
"""

# !+ CLEAN UP THIS FILE, MINIMALLY AT LEAST THE SRC CODE FORMATTING !

from zope import interface, schema
from zope.dottedname import resolve
from zope.security.proxy import removeSecurityProxy
from zope.component import getUtility
from zope.app.schema.vocabulary import IVocabularyFactory
import threading, time

import xappy, os, os.path as path
import logging
import cStringIO, os, subprocess

from sqlalchemy import exceptions
from bungeni.alchemist import Session
from bungeni.alchemist import container
from bungeni.alchemist import utils
from ore.xapian import search, queue, interfaces as iindex

from bungeni.models.schema import metadata
from bungeni.models import interfaces
from bungeni.models import domain
from bungeni.models.interfaces import ITranslatable
from bungeni.core import translation
import bungeni
 
from bungeni.ui.utils.odt2txt import OpenDocumentTextFile

log = logging.getLogger('ore.xapian')

def readODT(buffer):                
    mf = cStringIO.StringIO()
    mf.write(buffer)
    odt = OpenDocumentTextFile(mf)
    return odt.toString()

def readPDF(buffer):
    tf = os.tmpfile()
    tf.write(buffer)
    tf.seek(0)
    out, err = subprocess.Popen(["pdftotext", "-layout", "-", "-"],\
                                stdin = tf, stdout=subprocess.PIPE ).communicate()
    if not err:
        return out
    return ''

def languages():
    return getUtility(IVocabularyFactory, "language")(None)

def date_value(s):
    " date encode a value 20071131"
    if not s:
        return None
    return "%d%02d%02d"%(s.year, s.month, s.day)

def removeField(doc, name):
    " remove a field with name from a xapian document "
    found = None
    for f in doc.fields:
        if f.name == name:
            found = f
            break
    if found:
        doc.fields.remove(f)
    else:
        raise KeyError(name)

class ContentResolver(object):
    """
    a content resolver is used by ore xapian to generate and retrieve an object
    by a unique identifier thats used as the document id in the xapian index.

    we utilize the fully qualified class name and the object's primary key as
    document id.
    """
    interface.implements(iindex.IResolver)
    scheme = '' # u'pft'
    
    def id(self, object): 
        """ defines the xapian 'primary key' """
        #TODO Add the language to the index!
        string_key = container.stringKey(object)
        if string_key == "obj-None":
            session = Session()
            session.flush()
            string_key = container.stringKey(object)
        return "%s.%s-%s"%(object.__class__.__module__,
                            object.__class__.__name__,
                            string_key)

    def resolve(self, id): 
        class_path, oid = id.split('-', 1)
        domain_class = resolve.resolve(class_path)
        session = Session()
        value_key = container.valueKey(oid)

        if "None" not in value_key:
            obj = session.query(domain_class).get(value_key)
        else:
            obj = None
        return obj

class ContentIndexer(object):
    """
    used to index content into xapian. we create an indexer per class
    """
    interface.implements(iindex.IIndexer)

    # skip over these fields already handled by the framework.
    action_fields = ('resolver', 'object_type', 'object_kind', 'status', 'path', 'title')
    
    # a schema that this indexer will index by default, set in subclasses
    content_schema = None
    
    # a way of specifying that a particular field (say  'name') should be indexed as 'title'
    field_index_map = {}
    
    # specification of the domain model this indexer is indexing, set in subclasses,
    # used for reindexing all content operations.
    domain_model = None
    
    def __init__(self, context):
        self.context = removeSecurityProxy(context)

    def document(self, connection, retry=False):
        """
        return a xapian index document from the context.

        we can introspect the connection to discover relevant fields available.
        """
        doc = xappy.UnprocessedDocument()

        if interfaces.ENABLE_LOGGING:
            log.debug("Indexing Document %r"%self.context)

        # object type
        doc.fields.append(
            xappy.Field("object_type", self.context.__class__.__name__))

        # object kind
        doc.fields.append(
            xappy.Field("object_kind", domain.object_hierarchy_type(self.context)))
        
        # object language
        doc.fields.append(
            xappy.Field("language", self.context.language))
        
        doc.fields.append(xappy.Field("status", getattr(self.context, "status", "")))
        
        doc.fields.append(xappy.Field("owner", str(getattr(self.context, "owner_id", ""))))
        
        try:
            status_date = getattr(self.context, "status_date")
            if status_date:
                status_date = date_value(status_date)
                
            doc.fields.append(xappy.Field("status_date", status_date))
        except Exception:
            pass    
        
        title = ""
        try:
            title = bungeni.ui.search.ISearchResult(self.context).title
        except Exception:
            pass
        
        doc.fields.append(xappy.Field("title", title))
            
        try:
            #TODO: loop thru all available languages and index the translations
            self.index(doc)
            
        except exceptions.OperationalError, exceptions.InvalidRequestError:
            # detatch the dbapi connection from the pool, and close it
            # and retry the index operation (once)
            log.error("Indexing Connection Hosed, Discarding")
            db_connection = metadata.bind.contextual_connect()
            db_connection.begin().rollback()
            db_connection.detach()
            db_connection.close()
            if not retry:
                return self.document(connection, retry=True)
            raise
        
        if interfaces.ENABLE_LOGGING:
            for f in doc.fields:
                log.debug("  %r" % (f))
            names = set(indexer.get_fields_with_actions())
            fields = set([f.name for f in doc.fields])
            undef = fields-names
            if undef and interfaces.ENABLE_LOGGING:
                log.warning("Extraneous Fields Defined %r"%([tuple(undef) ]))
            
        return doc

    def index(self, doc):
        " populate a xapian document with fields to be indexed from context "
        # create index of all text fields for the document
        for field_index_name, field in self.fields():
            if not isinstance(field, (schema.Text, schema.ASCII)):
                continue
            value = field.query(self.context, '')
            if value is None:
                value = u''

            if not isinstance(value, basestring):
                value = unicode(value)

            #if interfaces.ENABLE_LOGGING:
            #    log.debug("  field %s as %s, %r"%(field.__name__, index_field_name, value))

            doc.fields.append(xappy.Field(field_index_name, value))

    def fields(self):
        " extract all fields to be indexed, including any aliases"
        for iface in interface.providedBy(self.context):
            for field in schema.getFields(iface).values():
                if field.__name__ in self.action_fields:
                    continue
                if not isinstance(field, (schema.Text, schema.ASCII)):
                    continue
                index_field_name = self.field_index_map.get(field.__name__, field.__name__)
                yield index_field_name, field
                

    #############################################
    # Index Storage Field Definition, done at startup
    @classmethod
    def defineIndexes(self, indexer):
        """
        define field indexes on the catalog at app server startup (note, xapian 
        doesn't allow for changing field definitions without reindexing) ... 
        see sync index script.
        """
        content_schema = utils.get_derived_table_schema(self.domain_model)
        if interfaces.ENABLE_LOGGING: log.debug('generating indexing schema %r'%content_schema)
        for field in schema.getFields(content_schema).values():
            if field.__name__ in self.action_fields:
                continue
            if not isinstance(field, (schema.Text, schema.ASCII)):
                continue
            if interfaces.ENABLE_LOGGING: log.info(" indexing field %s"%field.__name__)
            indexer.add_field_action(
                field.__name__, xappy.FieldActions.INDEX_FREETEXT, language='en')
    
    @classmethod
    def reindexAll(klass, connection, flush_threshold=500):
        instances = Session().query(klass.domain_model).all()
        resolver = ContentResolver()
        log.warning("Bulk Indexing %r"%klass)
        count = 0
        
        for i in instances:
            count += 1
            doc_id = resolver.id(i)
            indexer = klass(i)
            create = False
            doc = indexer.document(connection)
            doc.id = doc_id
            doc.fields.append(xappy.Field('resolver', resolver.scheme))
            connection.replace(doc)
    
            if count % flush_threshold == 0:
                log.warning("Flushing %s %s Records"%(flush_threshold, klass))

        # flush the remainder
        connection.flush()


class UserIndexer(ContentIndexer):

    domain_model = domain.User

    def index(self, doc):
        
        # index schema fields
        super(UserIndexer, self).index(doc)

        # index person attributes
        self.indexPerson(self.context, doc)

        # store email in index
        if self.context.email:
            doc.fields.append(xappy.Field('core.person-email', self.context.email))

        # index active status
        value = (self.context.active_p in ("I", "D", None)) and 'False' or 'True'
        doc.fields.append(xappy.Field('core.active', value))
        
    @staticmethod
    def indexPerson(context, doc):
        " defined as a static method for reuse across multiple types of users and different indexers of them"
        # index first name / last name separately
        first_name, last_name = "", ""
        if context.first_name:
            first_name = context.first_name.encode('utf-8')
            doc.fields.append(xappy.Field('core.person-fname', first_name))
        if context.last_name:
            last_name = context.last_name.encode('utf-8')
            doc.fields.append(xappy.Field('core.person-lname', last_name))

        # index name as display name / title
        doc.fields.append(
            xappy.Field('title', (u"%s %s"%(first_name, last_name)).encode('utf8')))
        
    @classmethod
    def defineIndexes(klass, indexer):

        indexer.add_field_action('core.person-fname', xappy.FieldActions.INDEX_FREETEXT, weight=5, language='en', spell=True)
        indexer.add_field_action('core.person-lname', xappy.FieldActions.INDEX_FREETEXT, weight=5, language='en', spell=True)
        indexer.add_field_action('core.person-lname', xappy.FieldActions.SORTABLE)
        
        indexer.add_field_action('core.person-email', xappy.FieldActions.STORE_CONTENT)
        indexer.add_field_action('core.person-email', xappy.FieldActions.SORTABLE)
        super(UserIndexer, klass).defineIndexes(indexer)
        
class MemberOfParliament(ContentIndexer):
    domain_model = domain.MemberOfParliament
    
class AgendaItemIndexer(ContentIndexer):
    domain_model = domain.AgendaItem
    
class PoliticalGroupIndexer(ContentIndexer):
    domain_model = domain.PoliticalGroup

class GroupIndexer(ContentIndexer):
    domain_model = domain.Group

class CommitteeIndexer(ContentIndexer):
    domain_model = domain.Committee

class ParliamentIndexer(ContentIndexer):
    domain_model = domain.Parliament
    
class AttachmentIndexer(ContentIndexer):
    domain_model = domain.Attachment
    
    @classmethod
    def defineIndexes(self, indexer):
        indexer.add_field_action('doc_text', xappy.FieldActions.INDEX_FREETEXT, weight=5, language='en', spell=True)
        indexer.add_field_action('doc_text', xappy.FieldActions.SORTABLE)
        super(AttachmentIndexer, self).defineIndexes(indexer)
    
    def index(self, doc):    
        # index schema fields
        super(AttachmentIndexer, self).index(doc)
        if self.context.mimetype == 'application/vnd.oasis.opendocument.text':
            doc.fields.append(xappy.Field('doc_text', readODT(self.context.data)))
            
        if self.context.mimetype == 'application/pdf':
            doc.fields.append(xappy.Field('doc_text', readPDF(self.context.data)))
            
        if self.context.mimetype == 'text/plain':
            doc.fields.append(xappy.Field('doc_text', str(self.context.data)))
    
    @classmethod
    def reindexAll(klass, connection, flush_threshold=500):
        instances = Session().query(klass.domain_model).all()
        resolver = ContentResolver()
        log.warning("Bulk Indexing %r"%klass)
        count = 0
        for i in instances:
            count += 1
            doc_id = resolver.id(i)
            indexer = klass(i)
            create = False
            doc = indexer.document(connection)
            doc.id = doc_id
            doc.fields.append(xappy.Field('resolver', resolver.scheme))
            connection.replace(doc)

            if count % flush_threshold == 0:
                log.warning("Flushing %s %s Records"%(flush_threshold, klass))

        # flush the remainder
        connection.flush()


    
####################
## Field Definitions
#
# The indexing subsystem does some work at startup, first it setups the index
# storage directory, with a separate indexing thread to process all indexing
# requests. it also prepares the storage, by defining the fields to be indexed
# by the system.

def setupFieldDefinitions(indexer):
    # resolution utility type
    indexer.add_field_action('resolver', xappy.FieldActions.INDEX_EXACT)
    indexer.add_field_action('resolver', xappy.FieldActions.STORE_CONTENT)

    # content type / object class
    indexer.add_field_action('object_type', xappy.FieldActions.INDEX_EXACT)
    indexer.add_field_action('object_type', xappy.FieldActions.STORE_CONTENT)
    indexer.add_field_action('object_type', xappy.FieldActions.SORTABLE)
    #indexer.add_field_action('object_type', xappy.FieldActions.FACET, type='string')

    indexer.add_field_action('object_kind', xappy.FieldActions.INDEX_EXACT)
    indexer.add_field_action('object_kind', xappy.FieldActions.STORE_CONTENT)
    indexer.add_field_action('object_kind', xappy.FieldActions.SORTABLE)
    #indexer.add_field_action('object_kind', xappy.FieldActions.FACET, type='string')

    # active / inactive status
    indexer.add_field_action('status', xappy.FieldActions.INDEX_EXACT)
    indexer.add_field_action('status', xappy.FieldActions.STORE_CONTENT)
    #indexer.add_field_action('status', xappy.FieldActions.FACET, type='string')
        
    indexer.add_field_action('status_date', xappy.FieldActions.INDEX_EXACT)
    indexer.add_field_action('status_date', xappy.FieldActions.STORE_CONTENT)

    # deleted 
    indexer.add_field_action('deleted', xappy.FieldActions.INDEX_EXACT)
    indexer.add_field_action('deleted', xappy.FieldActions.STORE_CONTENT)
    
    #owner of the object
    indexer.add_field_action('owner', xappy.FieldActions.INDEX_EXACT)
    indexer.add_field_action('owner', xappy.FieldActions.STORE_CONTENT)
    
    # site relative path
    indexer.add_field_action('path', xappy.FieldActions.STORE_CONTENT)

    indexer.add_field_action('title', xappy.FieldActions.INDEX_FREETEXT, weight=5, language='en', spell=True)
    indexer.add_field_action('title', xappy.FieldActions.STORE_CONTENT)
    indexer.add_field_action('title', xappy.FieldActions.SORTABLE)
    
    #indexer.add_field_action('language', xappy.FieldActions.INDEX_FREETEXT)
    indexer.add_field_action('language', xappy.FieldActions.INDEX_EXACT)
    indexer.add_field_action('language', xappy.FieldActions.STORE_CONTENT)
    
    UserIndexer.defineIndexes(indexer)
    BillIndexer.defineIndexes(indexer)
    AgendaItemIndexer.defineIndexes(indexer)
    PoliticalGroupIndexer.defineIndexes(indexer)
    MemberOfParliament.defineIndexes(indexer)
    MotionIndexer.defineIndexes(indexer)
    QuestionIndexer.defineIndexes(indexer)
    GroupIndexer.defineIndexes(indexer)
    CommitteeIndexer.defineIndexes(indexer)
    ParliamentIndexer.defineIndexes(indexer)
    AttachmentIndexer.defineIndexes(indexer)
    TabledDocumentIndexer.defineIndexes(indexer)

    if interfaces.ENABLE_LOGGING:
        log.debug("Indexer Fields Defined")
        field_names = indexer.get_fields_with_actions()
        field_names.sort()
        for i in field_names:
            log.debug(" defined %s"%i)
            

# we store indexes in buildout/parts/index
# 
def setupStorageDirectory(part_target="index"):
    # we start in buildout/src/bungeni.core/bungeni/core
    # we end in buildout/parts/index
    # TODO: this is probably going to break with package restucturing
    store_dir = __file__
    x = 0
    while x < 5:
        x += 1
        store_dir = path.split(store_dir)[0]
    store_dir = path.join(store_dir, 'parts', part_target)
    if path.exists(store_dir):
        assert path.isdir(store_dir)
    else:
        os.mkdir(store_dir)
    
    return store_dir

""""
!+DISABLE_XAPIAN
# create storage directory if not present
store_dir = setupStorageDirectory() 

# search connection hub
searcher = search.IndexSearch(store_dir)

# async indexer
indexer = xappy.IndexerConnection(store_dir)

# if synchronous debugging, setup the index connection
if iindex.DEBUG_SYNC:
    iindex.DEBUG_SYNC_IDX = indexer
    
if interfaces.DEBUG:
    queue.QueueProcessor.POLL_TIMEOUT=3
else:
    queue.QueueProcessor.POLL_TIMEOUT=5

if interfaces.DEBUG:
    searcher.hub.auto_refresh_delta = 5
else:
    searcher.hub.auto_refresh_delta = 10

"""

def main():
    import logging
    logging.basicConfig()
    
    # setup database connection
    #from bungeni.core import util
    #util.cli_setup()
    #util.zcml_setup()
    
    # field definitions
    setupFieldDefinitions(indexer)
    
    # reindex content directly
    for content_indexer in [
            UserIndexer,
            BillIndexer,
            AgendaItemIndexer,
            PoliticalGroupIndexer,
            MemberOfParliament,
            MotionIndexer,
            QuestionIndexer,
            GroupIndexer,
            CommitteeIndexer,
            #ParliamentMemberIndexer,
            ParliamentIndexer,
            TabledDocumentIndexer,
            AttachmentIndexer,
            #HansardReporterIndexer,
        ]:
        content_indexer.reindexAll(indexer)

def reset_index():
    try:
        main()
    except:
       import pdb, traceback, sys
       traceback.print_exc()
       pdb.post_mortem(sys.exc_info()[-1]) 


class IndexReset(threading.Thread):
    
    def run(self):
        reset_index()
        
