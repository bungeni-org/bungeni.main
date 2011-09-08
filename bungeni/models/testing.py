import datetime

from zope import component
from bungeni.alchemist.security import schema as security
from bungeni.alchemist.interfaces import IDatabaseEngine
from sqlalchemy import create_engine
from bungeni.models import domain
from bungeni.models import metadata
from bungeni.models import schema
from bungeni.alchemist import Session

def add_content(kls, *args, **kwargs):
    session = Session()
    instance = kls(*args)

    for name, value in kwargs.items():
        setattr(instance, name, value)
        
    session.add(instance)
    session.flush()

    return instance

# !+DROP_ALL(ah,sep-2011) sqlalchemy drop_all() is insufficient, does not drop sequences
# or when there are cyclical foreign keys   
def drop_all(engine):
    """
    Drops all tables and sequences as the metadata.drop_all() is insufficient
    to drop all tables and sequences
    """    
    from sqlalchemy.exceptions import SQLError

    sequence_sql='''SELECT sequence_name FROM information_schema.sequences
                    WHERE sequence_schema='public'
                 '''
    
    table_sql='''SELECT table_name FROM information_schema.tables
                 WHERE table_schema='public' AND table_type != 'VIEW' AND 
                 table_name NOT LIKE 'pg_ts_%%'
              '''
    try:
        for table in [name for (name, ) in engine.execute(str(table_sql))]:
            engine.execute(str('DROP TABLE %s CASCADE' % table))
        for seq in [name for (name, ) in engine.execute(str(sequence_sql))]:
                engine.execute(str('DROP SEQUENCE %s CASCADE' % seq))
    except SQLError, e:
        print e

def setup_db():
    db = create_engine('postgres://localhost/bungeni-test', echo=False)
    component.provideUtility( db, IDatabaseEngine, 'bungeni-db' )
    metadata.bind = db
    # !+DROP_ALL(ah,sep-2011) drop_all() is insufficient, does not drop sequences
    # or when there are cyclical foreign keys   
    #metadata.drop_all()
    drop_all(db)    
    metadata.create_all()
    metadata.reflect()
    schema.QuestionSequence.create(db) 
    schema.MotionSequence.create(db)
    schema.registrySequence.create(db)
    schema.tabled_documentSequence.create(db)
    security.metadata.bind = db
    security.metadata.drop_all()
    security.metadata.create_all()
    return db

def create_sitting(group_id=1, language="en"):
    """Sitting to schedule content."""
    
    session = Session()
    
    st = domain.GroupSittingType()
    st.group_sitting_type = u"morning"
    st.start_time = datetime.time(8,30)
    st.end_time = datetime.time(12,30)
    st.language = language
    session.add(st)
    session.flush()

    sitting = domain.GroupSitting()
    sitting.start_date = datetime.datetime.now()
    sitting.end_date = datetime.datetime.now()
    sitting.group_sitting_type_id = st.group_sitting_type_id
    sitting.group_id = group_id
    sitting.language = language
    session.add(sitting)
    session.flush()
    
    return sitting

