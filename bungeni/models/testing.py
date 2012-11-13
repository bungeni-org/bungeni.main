import datetime

from zope import component
from bungeni.alchemist import security
from bungeni.alchemist.interfaces import IDatabaseEngine
from sqlalchemy import create_engine
from bungeni.models import domain
from bungeni.models import schema
from bungeni.alchemist import Session

def add_content(kls, *args, **kwargs):
    session = Session()
    instance = kls(*args)
    for name, value in kwargs.items():
        setattr(instance, name, value)
    session.add(instance)
    session.flush()
    # execute domain.Entity on create hook -- db id must have been set
    instance.on_create()
    return instance

'''
# !+DROP_ALL(ah, sep-2011) sqlalchemy drop_all() is insufficient, does not drop 
# sequences or when there are cyclical foreign keys. 
# (mr, sep-2011) not sure that this should be needed at all, sqlalchemy's 
# metadata.drop_all() drops all (and only) schema declarations via sqlalchemy,
# without necessarily any changes to the database itself.
def drop_all(engine):
    """
    Drops all tables and sequences as the metadata.drop_all() is insufficient
    to drop all tables and sequences
    """    
    from sqlalchemy.exc import SQLError
    
    sequence_sql="""SELECT sequence_name FROM information_schema.sequences
        WHERE sequence_schema='public'
    """
    table_sql="""SELECT table_name FROM information_schema.tables
        WHERE table_schema='public' AND table_type != 'VIEW' AND 
        table_name NOT LIKE 'pg_ts_%%'
    """
    
    try:
        for table in [name for (name, ) in engine.execute(str(table_sql))]:
            engine.execute(str('DROP TABLE %s CASCADE' % table))
        for seq in [name for (name, ) in engine.execute(str(sequence_sql))]:
            engine.execute(str('DROP SEQUENCE %s CASCADE' % seq))
    except SQLError, e:
        print e
'''

def setup_db():
    schema.metadata.bind = db = component.getUtility(IDatabaseEngine, "bungeni-test")
    # !+DROP_ALL(ah,sep-2011)
    #drop_all(db)
    schema.metadata.drop_all()
    schema.metadata.create_all()
    schema.metadata.reflect()
    security.metadata.bind = db
    security.metadata.drop_all()
    security.metadata.create_all()
    return db

def create_sitting(group_id=1, language="en"):
    """Sitting to schedule content."""
    
    session = Session()
    sitting = domain.Sitting()
    sitting.start_date = datetime.datetime.now()
    sitting.end_date = datetime.datetime.now()
    sitting.activity_type = u"morning_sitting"
    sitting.meeting_type = u"plenary"
    sitting.convocation_type = u"ordinary"
    sitting.group_id = group_id
    sitting.language = language
    session.add(sitting)
    session.flush()
    
    return sitting

def get_audit_count_for_type(type_key):
    session = Session()
    return len([ au for au in session.query(domain.Audit).filter(
            domain.Audit.audit_type==type_key) ])


