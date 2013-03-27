# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Alchemist - ZCML directives

$Id$
"""
log = __import__("logging").getLogger("bungeni.alchemist")

from zope import interface, schema
from zope.configuration.fields import GlobalObject

from zope import component
from zope.security.metaconfigure import utility, PublicPermission

import sqlalchemy
import interfaces


class IEngineDirective(interface.Interface):
    """Creates A Database Engine. Database Engines are named utilities.
    """
    url = schema.URI(title=u"Database URL", 
        description=u"SQLAlchemy Database URL", 
        required=True)
    name = schema.Text(title=u"Engine Name",
        description=u"Empty if this engine is the default engine.",
        required=False,
        default=u"")
    echo = schema.Bool(title=u"Echo SQL statements",
        description=u"Debugging Echo Log for Engine",
        required=False,
        default=False)
    pool_recycle = schema.Int(title=u"Connection Recycle",
        description=u"Time Given in Seconds",
        required=False,
        default=-1)
# keyword arguments to pass to the engine
IEngineDirective.setTaggedValue("keyword_arguments", True)

def engine(_context, url, name="", echo=False, pool_recycle=-1, **kwargs):
    engine_component = sqlalchemy.create_engine(
        url, echo=echo, pool_recycle=pool_recycle, **kwargs)
    utility(_context,
        provides=interfaces.IDatabaseEngine,
        component=engine_component,
        permission=PublicPermission,
        name=name)


class IBindDirective(interface.Interface):
    """ Binds a MetaData to a database engine.
    """
    engine = schema.Text(title=u"Engine Name")
    metadata = GlobalObject(title=u"Metadata Instance",
        description=u"Metadata Instance to be bound")
    
def bind(_context, engine, metadata):
    
    def _bind(engine_name, metadata):
        metadata.bind = component.getUtility(interfaces.IDatabaseEngine, engine)
    
    _context.action(
        discriminator=("alchemist.bind", metadata),
        callable=_bind,
        args=(engine, metadata))

