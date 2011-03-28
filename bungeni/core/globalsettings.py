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

    
def getSpeakersOfficeEmail():
    """
    return the official email address 
    of the speakers office
    """
    email = BungeniSettings(app).speakers_office_email
    return email
    
def getSpeakersOfficeReceiveNotification():
    """
    returns true if the Speakers office wants to be alerted by mail
    whenever a bill, motion, question is submitted 
    """
    return BungeniSettings(app).speakers_office_notification
            
def getClerksOfficeEmail():
    """
    return the official email address 
    of the clerks office
    """
    return BungeniSettings(app).clerks_office_email
    
def getClerksOfficeReceiveNotification():
    """
    returns true if the clerks office wants to be alerted by mail
    whenever a bill, motion, question is submitted 
    """
    return BungeniSettings(app).clerks_office_notification

def getMinistriesReceiveNotification():
    """
    returns true if the ministries want to be alerted by mail 
    wheneve a bill, motion, question is submitted.
    """    

    return BungeniSettings(app).ministries_notification
    
def getAdministratorsEmail():
    """
    email of the site admin
    """
    return BungeniSettings(app).administrators_email
        
        
def getDaysToDeferAdmissibleQuestions():
    """
    time after which admissible questions are automatically deferred
    """
     
    return datetime.timedelta(BungeniSettings(app).days_to_defer_question)
    
def getDaysToNotifyMinistriesQuestionsPendingResponse():
    """
    timeframe after which the clerksoffice and the ministry is alerted that
    questions that are pending response are not yet answered
    """
    
    return datetime.timedelta(BungeniSettings(app).days_to_notify_ministry_unanswered)

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
