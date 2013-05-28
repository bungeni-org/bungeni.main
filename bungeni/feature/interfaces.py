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


class ISignatoryManager(interface.Interface):
    """Validation machinery for iterms with signatories"""

    signatories = interface.Attribute("""signatories iteratable""")
    min_signatories = interface.Attribute("""minimum consented signatories""")
    max_signatories = interface.Attribute("""maximum consented signatories""")
    signatories_count = interface.Attribute("""number of signatories""")
    consented_signatories = interface.Attribute("""number of consented """)
    
    def validate_signatories():
        """Validate signatories count on parliamentary item i.e. number added
        """
    
    def require_signatures():
        """Does the document or object require signatures
        """
    
    def validate_consented_signatories():
        """Validate number of consented signatories against min and max
        """
    
    def allow_signature():
        """Check that the current user has the right to consent on document 
        """
    
    def document_submitted():
        """Check that the document has been submitted
        """
    
    def document_is_draft():
        """Check that the document is in draft stage
        """
    
    def expire_signatures():
        """Should pending signatures be archived
        """
    
    def update_signatories():
        """Fire any workflow transitions within current state.
        This should update all signatures depending on parent document state.
        """
    
    def setup_roles():
        """Set local signatories/owner roles on document and signature
        objects.
        """
    
    def fire_workflow_actions():
        """Fire off any changes after workflow change on parent document"""

class ISchedulingManager(interface.Interface):
    """Configurator for class implementing scheduling feature
    """
    schedulable_states = interface.Attribute("""object's schedulable states""")
    scheduled_states = interface.Attribute("""object's scheduled states""")


DOWNLOAD_TYPES = [
    ("pdf", _("as pdf")),
    ("odt", _("as open document")),
    ("doc", _("as MS Word")),
    ("docx", _("as MS Word 2007+")),
    ("txt", _("as text")),
    ("rtf", _("as rich text")),
    ("htm", _("as html")),
]
DOWNLOAD_TYPE_KEYS = [ k for k,v in DOWNLOAD_TYPES]
def validate_download_types(obj):
    assert set(obj.allowed_types).issubset(DOWNLOAD_TYPE_KEYS), \
        ("allowed download types:  %s. you entered: %s" 
            %(", ".join(DOWNLOAD_TYPE_KEYS),
                ", ".join(obj.allowed_types)))

class IDownloadManager(interface.Interface):
    """Schema for download manager config adapters.
    """
    allowed_types = interface.Attribute("""allowed download types""")
    
    interface.invariant(validate_download_types)
    
    def get_allowed_types():
        """Get a subset of DOWNLOAD_TYPES.
        """




