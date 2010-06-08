from zope.component.interfaces import IObjectEvent

class IWorkflowTransitionEvent(IObjectEvent):
    """A workflow transition."""

###############
# Questions
###############
class IQuestionSubmittedEvent(IWorkflowTransitionEvent):
    """Question was submitted to Clerk's office."""

class IQuestionReceivedEvent(IWorkflowTransitionEvent):
    """Issued when a question was received by Clerk's office."""

class IQuestionCompleteEvent(IWorkflowTransitionEvent):
    """Issued when a question was reviewed by Clerk's office."""

class IQuestionRejectedEvent(IWorkflowTransitionEvent):
    """Issued when a question was rejected by the speakers office."""

class IQuestionClarifyEvent(IWorkflowTransitionEvent):
    """Issued when a question needs clarification by the MP"""

class IQuestionDeferredEvent(IWorkflowTransitionEvent):
    """Issued when a question was deferred by Clerk's office."""

class IQuestionScheduledEvent(IWorkflowTransitionEvent):
    """Issued when a question was scheduled by Speakers office."""

class IQuestionPostponedEvent(IWorkflowTransitionEvent):
    """Issued when a question was postponed by the speakers office."""

class IQuestionSentToMinistryEvent(IWorkflowTransitionEvent):
    """Issued when a question was sent to a ministry for written response."""

class IQuestionAnsweredEvent(IWorkflowTransitionEvent):
    """Issued when a questions answer was reviewed by Clerk's office."""

class IQuestionDebatedEvent(IWorkflowTransitionEvent):
    """ A question was debated in the plenary """ 
    
class IQuestionSchedulePendingEvent(IWorkflowTransitionEvent): 
    """ a question is made available for scheduling """
    
#######################
# Resonses to questions
#######################
class IResponseSubmittedEvent(IWorkflowTransitionEvent):
    """Issued when a response was sent from a ministry to clerks office"""
class IResponseCompletedEvent(IWorkflowTransitionEvent):
    """Issued when a response was marked complete by the clerks office"""

###################
# Motions
###################

class IMotionReceivedEvent(IWorkflowTransitionEvent):
    """ Motion recieved by clerks office"""

class IMotionSubmittedEvent(IWorkflowTransitionEvent):
    """ Motion submitted to clerks office """
    
class IMotionRejectedEvent(IWorkflowTransitionEvent):
    """Issued when a Motion was rejected by the speakers office."""

class IMotionClarifyEvent(IWorkflowTransitionEvent):
    """Issued when a Motion needs clarification by the MP"""

class IMotionDeferredEvent(IWorkflowTransitionEvent):
    """Issued when a Motion was deferred by Clerk's office."""

class IMotionScheduledEvent(IWorkflowTransitionEvent):
    """Issued when a Motion was scheduled by Speakers office."""

class IMotionPostponedEvent(IWorkflowTransitionEvent):
    """Issued when a Motion was postponed by the speakers office."""

class IMotionDebatedEvent(IWorkflowTransitionEvent):
    """Issued when a Motions answer was debated"""
    
class IMotionPendingEvent(IWorkflowTransitionEvent):
    pass
    
######################
# Bills
######################

###################
# Tabled Documents
###################

class ITabledDocumentReceivedEvent(IWorkflowTransitionEvent):
    """ TabledDocument recieved by clerks office"""

class ITabledDocumentSubmittedEvent(IWorkflowTransitionEvent):
    """ TabledDocument submitted to clerks office """
    
class ITabledDocumentRejectedEvent(IWorkflowTransitionEvent):
    """Issued when a TabledDocument was rejected by the speakers office."""

class ITabledDocumentClarifyEvent(IWorkflowTransitionEvent):
    """Issued when a TabledDocument needs clarification by the MP"""

class ITabledDocumentDeferredEvent(IWorkflowTransitionEvent):
    """Issued when a TabledDocument was deferred by Clerk's office."""

class ITabledDocumentScheduledEvent(IWorkflowTransitionEvent):
    """Issued when a TabledDocument was scheduled by Speakers office."""

class ITabledDocumentPostponedEvent(IWorkflowTransitionEvent):
    """Issued when a TabledDocument was postponed by the speakers office."""

class ITabledDocumentDebatedEvent(IWorkflowTransitionEvent):
    """Issued when a TabledDocuments answer was debated"""

class ITabledDocumentPendingEvent(IWorkflowTransitionEvent):
    pass
    
###################
# Agenda Item
###################

class IAgendaItemReceivedEvent(IWorkflowTransitionEvent):
    """ AgendaItem recieved by clerks office"""

class IAgendaItemSubmittedEvent(IWorkflowTransitionEvent):
    """ AgendaItem submitted to clerks office """
    
class IAgendaItemRejectedEvent(IWorkflowTransitionEvent):
    """Issued when a AgendaItem was rejected by the speakers office."""

class IAgendaItemClarifyEvent(IWorkflowTransitionEvent):
    """Issued when a AgendaItem needs clarification by the MP"""

class IAgendaItemDeferredEvent(IWorkflowTransitionEvent):
    """Issued when a AgendaItem was deferred by Clerk's office."""

class IAgendaItemScheduledEvent(IWorkflowTransitionEvent):
    """Issued when a AgendaItem was scheduled by Speakers office."""

class IAgendaItemPostponedEvent(IWorkflowTransitionEvent):
    """Issued when a AgendaItem was postponed by the speakers office."""

class IAgendaItemDebatedEvent(IWorkflowTransitionEvent):
    """Issued when a AgendaItem answer was debated"""

class IAgendaItemPendingEvent(IWorkflowTransitionEvent):
    pass
        
