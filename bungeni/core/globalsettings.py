#!/usr/bin/env python
# encoding: utf-8
"""
global settings
"""


# the schema for the settings is in interfaces

import datetime

import sqlalchemy.sql.expression as sql

from bungeni.alchemist import Session
from bungeni.core.app import BungeniApp

from bungeni.models import domain
from bungeni.models import schema
from bungeni.models.interfaces import IBungeniSettings
from bungeni.models.settings import GlobalSettingFactory

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
            sql.between(date, schema.groups.c.start_date, schema.groups.c.end_date),
            sql.and_(schema.groups.c.start_date<=date, schema.groups.c.end_date==None)
            )
    if not date:
        date = datetime.date.today()
    session = Session()
    query = session.query(domain.Parliament).filter(getFilter(date))
    try:
        return query.one()
    except:
        pass #XXX raise(_(u"inconsistent data: none or more than one parliament found for this date"))

def getCurrentParliamentId(date=None):
    """Return the parliament_id for a given date (or the current for no date)
    """
    try:
        return get_current_parliament(date).parliament_id
    except:
        pass

''' !+UNUSED(mr, mar-2011)
def getQuestionSubmissionAllowed():
    return BungeniSettings(app).question_submission_allowed
'''

def getMaxQuestionsPerSitting():
    return BungeniSettings(app).max_questions_sitting
        
def getMaxQuestionsByMpPerSitting():
    return BungeniSettings(app).max_mp_questions_sitting
    
def getNoOfDaysBeforeQuestionSchedule():
    return BungeniSettings(app).days_before_question_schedule
    
    
def getNoOfDaysBeforeBillSchedule():
    """
    Parameter  : Elapsed days from date of publication for placement of bill	
    Configurable numeric value describing number of days after date of publication 
    of bill after which bill can be placed before the house
    """
    return BungeniSettings(app).days_before_bill_schedule
        
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

BungeniSettings = GlobalSettingFactory(IBungeniSettings)
