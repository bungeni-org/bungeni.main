#!/usr/bin/env python
# encoding: utf-8
"""
global settings
"""


# the schema for the settings is in interfaces
log = __import__("logging").getLogger("bungeni.core")

import datetime

import sqlalchemy.sql.expression as sql

from bungeni.alchemist import Session
from bungeni.core.app import BungeniApp

from bungeni.models import domain
from bungeni.models import schema

app = BungeniApp()

# !+ rename to globals.py
# !+ move the "global common" utils in models.utils to here
# !+ switch to bungeni naming standard (underscore-spearated words)
# !+CUSTOM(mr, mar-2011) migrate all "global parameters" here to bungeni_custom


def get_current_parliament(date=None):
    """Return the parliament for a given date (or the current for no date)
    """
    def getFilter(date):
        return sql.or_(
            sql.between(date, schema.group.c.start_date, schema.group.c.end_date),
            sql.and_(schema.group.c.start_date<=date, schema.group.c.end_date==None)
            )
    if not date:
        date = datetime.date.today()
    session = Session()
    query = session.query(domain.Parliament).filter(getFilter(date))
    try:
        return query.one()
    except:
        ##XXX raise(_(u"inconsistent data: none or more than one parliament found for this date"))
        #!+DATA(mb, July-2012) this should get the one active parliament
        # needs some review if there is more than one parliament active e.g.
        # bicameral legislatures
        query = session.query(domain.Parliament).filter(
            schema.group.c.status=="active"
        )
        try:
            return query.one()
        except Exception, e:
            log.error("Could not find active parliament. Activate a parliament"
                " in Bungeni admin :: %s", e.__repr__()
            )
            raise ValueError("Unable to locate active parliament")


def getCurrentParliamentId(date=None):
    """Return the parliament_id for a given date (or the current for no date)
    """
    try:
        return get_current_parliament(date).parliament_id
    except:
        pass

        
def getWeekendDays():
    """
    (0 is Monday, 6 is Sunday)
    """
    return [5,6]

def getFirstDayOfWeek():
    """
    (0 is Monday, 6 is Sunday)
    """
    return 0

def getPloneMenuUrl():
    """
    URL at which the plone menu is returned as a json string
    """

    raise NotImplementedError(
        "This method should not be used.")
