# encoding: utf-8
#Automatically transition Questions 
#The system needs to provide a settable time-frame beyond which “Admissible” 
#questions which are available for scheduling - change status to “Deferred”
import sys
import datetime

import zope.lifecycleevent

import sqlalchemy.sql.expression as sql

from bungeni.alchemist import Session

import bungeni.models.domain as domain
import bungeni.models.schema as schema
import bungeni.core.audit as audit

#import bungeni.core.workflows.question as question_workflow
import bungeni.core.globalsettings as prefs
import bungeni.core.workflows.dbutils as dbutils

#from bungeni.core.workflow.interfaces import IWorkflowController

##############################
# imports for main
from zope import component
from sqlalchemy import create_engine
from bungeni.alchemist.interfaces import IDatabaseEngine
import bungeni.core.interfaces
import bungeni.core.workflows.question
import bungeni.core.workflows.adapters
from bungeni import core as model

#import pdb



def _getQuestionsApprovedBefore(date, status):
    """Get all questions in the workflow status, that were approved before date.
    """
    session = Session()
    qfilter=sql.and_(domain.Question.status == status)
    query = session.query(domain.Question).filter(qfilter)
    return [ q for q in query.all() if (
        (q.admissible_date is not None) and (q.admissible_date < date) 
    ) ]

''' !+UNUSED/fireTransitionToward(mr, dec-2010)
def _deferAdmissibleQuestionsBefore(date):
    """
    set all admissible Questions before this
    date to defered
    """
    status = u"admissible"
    admissibleQuestions = _getQuestionsApprovedBefore(date, status)
    for question in admissibleQuestions:
        IWorkflowController(question).fireTransitionToward(u'deferred', 
                check_security=False)


def deferAdmissibleQuestions():
    """
    get the timeframe and defer all questions 
    before the current date - timeframe
    """
    timedelta = prefs.getDaysToDeferAdmissibleQuestions()
    deferDate = datetime.date.today() - timedelta
    _deferAdmissibleQuestionsBefore(deferDate)
'''

def main(argv=None):
    """
    run this as a cron job and execute all
    time based transitions
    """
    db = create_engine('postgres://localhost/bungeni', echo=False)
    component.provideUtility( db, IDatabaseEngine, 'bungeni-db' )
    model.metadata.bind = db
    session = Session()
    component.provideAdapter(
      bungeni.core.workflow.states.StateController,
      (bungeni.core.interfaces.IBungeniContent,))

    component.provideAdapter(
      bungeni.core.workflows.question.QuestionWorkflowAdapter,
      (domain.Question,))

    component.provideAdapter(
      bungeni.core.workflow.states.WorkflowController,
      (domain.Question,))

    component.provideHandler(
      bungeni.core.workflows.question.workflowTransitionEventDispatcher)
    # add autitor for time based transitions
    #component.provideAdapter(
    #    (bungeni.core.interfaces.IAuditable, bungeni.core.interfaces.IQuestion, ),
    #    (domain.Question, ))
    #component.provideAdapter( audit.objectModified, 
    #(domain.Question, bungeni.core.interfaces.IAuditable, ))
    
    deferAdmissibleQuestions() 
    session.flush()
    session.commit()
    
if __name__ == "__main__":
    sys.exit(main())


