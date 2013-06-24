# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""The Bungeni Application - Feature handling for domain models

IFeature marker interfaces -- apply to a domain model, to declare that it 
implements the feature. To avoid "english language anomalies of derived names" 
e.g "schedule" -> ISchedulable, adopt a very KISS feature->interface naming 
convention: "schedule"->IFeatureSchedule

$Id$
"""
log = __import__("logging").getLogger("bungeni.feature")


from zope import interface
from bungeni import _


class IFeature(interface.Interface):
    """Base feature marker interface.
    """
class IFeatureAudit(IFeature):
    """Marks support for "audit" feature.
    """
class IFeatureVersion(IFeature):
    """Marks support for "version" feature (requires "audit").
    """
class IFeatureAttachment(IFeature):
    """Marks support for "attachment" feature.
    """
class IFeatureEvent(IFeature):
    """Marks support for "event" feature.
    """
class IFeatureSignatory(IFeature):
    """Marks support for "signatory" feature.
    """
class IFeatureSchedule(IFeature):
    """A document can be scheduled: support for the "schedule" feature.
    """
class IFeatureSitting(IFeature):
    """A group can hold sittings: support for the "sitting" feature.
    """
class IFeatureAddress(IFeature):
    """Can have addresses: support for the "address" feature.
    """
class IFeatureWorkspace(IFeature):
    """Marks support for "workspace" feature.
    """
class IFeatureNotification(IFeature):
    """Marks support for "notification" feature.
    """
class IFeatureEmail(IFeature):
    """Marks support for "email" notifications feature.
    """
class IFeatureDownload(IFeature):
    """Marker for classes supporting "download" feature".
    """
class IFeatureUserAssignment(IFeature):
    """Marks support for "user assignment" feature
    """
class IFeatureGroupAssignment(IFeature):
    """Marks support for "group assignment" feature
    """


DOWNLOAD_TYPES = [
    ("pdf", _("as pdf")),
    ("odt", _("as open document")),
    ("doc", _("as MS Word")),
    ("docx", _("as MS Word 2007+")),
    ("txt", _("as text")),
    ("rtf", _("as rich text")),
    ("htm", _("as html")),
]
DOWNLOAD_TYPE_KEYS = [ k for k,v in DOWNLOAD_TYPES ]


