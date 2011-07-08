from zope.viewlet.interfaces import IViewletManager
from zope import interface

class ISubFormViewletManager(IViewletManager):
    """Viewlet manager for subform viewlets.
    """

class ISubformRssSubscriptionViewletManager(IViewletManager):
    """ Viewlet manager for subform rss subscription
        icons.
    """


class Modified(interface.Invalid):
    """ Marker interface for diff modified error.
    """

