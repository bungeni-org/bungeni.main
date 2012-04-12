# encoding: utf-8
# sent time based notifications

# The system should also store the following parameters:
#     * maximum number of days that can elapse between the time a question is sent to the relevant 
#       Ministry and the time the question is placed on the Order Paper.
#     * maximum number of days that may elapse between the days a Minister receives a question 
#       and the day a written response is submitted to the clerk.
#     * maximum number of days that may elapse between the day a question by private notice 
#       (questions that in the opinion of the Speaker are of an urgent nature) is scheduled for reply.

# Notifications will be sent to the Speaker and the Clerk listing all questions that have exceeded the limits stated above. 
import sys
import datetime

from zope.i18n import translate

from email.mime.text import MIMEText


import sqlalchemy.sql.expression as sql

from bungeni.alchemist import Session
from bungeni.core.workflows import  dbutils, utils
from bungeni.models import domain
from bungeni.models import schema
import bungeni.core.globalsettings as prefs
#from bungeni.core.workflows.question import states as q_state
from bungeni.server.smtp import dispatch

##############################
# imports for main
from zope import component
from sqlalchemy import create_engine
from bungeni.alchemist.interfaces import IDatabaseEngine
#import bungeni.core.interfaces

# !+MODEL_MAPPING(mr, oct-2011) import bungeni.models.orm is needed to ensure 
# that mappings of domain classes to schema tables is executed.
import bungeni.models.orm


def _getQuestionsPendingResponse(date, ministry):
    """
    returns all questions that are in the state 
    'pending written response from a ministry'
    and were sent to the ministry before this date
    """
    status = u"Question pending response" #q_state.response_pending
    session = Session()
    qfilter=sql.and_(
                (domain.Question.ministry_submit_date < date ),
                (domain.Question.status == status),
                (domain.Question.ministry_id == ministry.group_id)
                )
    query = session.query(domain.Question).filter(qfilter)
    return query.all()



def _getAllMinistries(date):
    """
    returns all ministries that are 
    valid for this date
    """
    session = Session()
    mfilter=sql.or_( 
        sql.between(date, schema.groups.c.start_date, schema.groups.c.end_date),
        sql.and_(
                (schema.groups.c.start_date < date ),
                (schema.groups.c.end_date == None)
                )
        )
    query = session.query(domain.Ministry).filter(mfilter)
    return query.all()
    
def _getMemberOfParliamentEmail(question):
    user_id = question.owner_id
    session = Session()
    user = domain.Person.get(user_id)
    return user.email
    

    
def sendNotificationToMP(date):
    """
    send a mail to the MP asking the question that the deadline 
    of the question is aproaching
    """
    status = u"Question pending response" #q_state.response_pending
    text = translate('notification_email_to_mp_question_pending_response',
                     target_language='en',
                     domain='bungeni.core',
                     default="Questions pending responses.")
    session = Session()
    qfilter=sql.and_(
                (domain.Question.ministry_submit_date < date ),
                (domain.Question.status == status),
                )
    questions = session.query(domain.Question).filter(qfilter).all()
    for question in questions:
        mailto = _getMemberOfParliamentEmail(question)
        if mailto and True: #!+NOTIFICATION_SETTINGS = True
            msg = MIMEText(text)
            msg['Subject'] = u'Questions pending response'
            msg['From'] = prefs.getAdministratorsEmail()
            msg['To'] =  mailto
            text = text + '\n' + question.subject + '\n'
            print msg
            # !+SENDMAIL(ah,18-03-2010)
            #Mail sending is commented out below
            dispatch(msg)
    
def sendNotificationToClerksOffice(date):
    """
    send a mail to the clerks office with
    stating all questions per ministry that
    are approaching the deadline
    """
    text = translate('notification_email_to_clerk_question_pending_response',
                     target_language='en',
                     domain='bungeni.core',
                     default="Questions pending responses.")
    ministries = _getAllMinistries(date)
    for ministry in ministries:
        questions = _getQuestionsPendingResponse(date, ministry)
        if questions:
            text = text + '\n' + ministry.full_name +': \n'
        for question in questions:
            text = text + question.subject + '\n'
    
    msg = MIMEText(text)
    
    msg['Subject'] = u'Questions pending response'
    msg['From'] = prefs.getAdministratorsEmail()
    msg['To'] = prefs.getClerksOfficeEmail()
    print msg
    # !+SENDMAIL(ah,18-03-2010)
    #Mail sending is commented out below
    dispatch(msg)


def sendNotificationToMinistry(date):
    """
    send a notification to the ministry stating
    all questions that are approaching the deadline
    """
    text = translate("notification_email_to_ministry_question_pending_response",
                     target_language="en",
                     domain="bungeni",
                     default="Questions pending responses.")
    ministries = _getAllMinistries(date)
    for ministry in ministries:
        questions = _getQuestionsPendingResponse(date, ministry)
        text = translate("notification_email_to_ministry_question_pending_response",
                     target_language="en",
                     domain="bungeni",
                     default="Questions assigned to the ministry pending responses.")
        if questions: 
            text = "%s\n%s: \n" % (text, ministry.full_name) + \
                "\n".join([ question.subject for question in questions ])
            emails = [ utils.formatted_user_email(minister)
                for minister in dbutils.get_ministers(ministry) ]
            msg = MIMEText(text)
            msg["Subject"] = "Questions pending response"
            msg["From"] = prefs.getClerksOfficeEmail()
            msg["To"] = " ,".join(emails)
            print msg
            # !+SENDMAIL(ah,18-03-2010)
            #Mail sending is commented out 
            dispatch(msg)
        
def sendAllNotifications():
    """
    get the timeframes and send all notifications out
    """
    delta = prefs.getDaysToNotifyMinistriesQuestionsPendingResponse()
    date = datetime.date.today()
    sendNotificationToMinistry(date)
    sendNotificationToClerksOffice(date)
    sendNotificationToMP(date)
            
def main(argv=None):
    """
    run this as a cron job and execute all
    time based transitions
    """
    # !+HARDCODED_DB_SETTING(ah, 18-03-2011) 
    #This needs to be factored out
    db = create_engine('postgres://localhost/bungeni', echo=False)
    component.provideUtility( db, IDatabaseEngine, 'bungeni-db' )
    schema.metadata.bind = db
    session = Session()
    
    sendAllNotifications()
    
    #session.flush()
    #session.commit()

if __name__ == "__main__":
    sys.exit(main())

