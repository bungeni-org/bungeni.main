# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""File/Atachments event handlers

$Id$
"""
log = __import__("logging").getLogger("bungeni.core.files")

from zope.security.proxy import removeSecurityProxy
from zope.lifecycleevent import IObjectModifiedEvent, IObjectCreatedEvent
from bungeni.alchemist import Session
from bungeni.models.interfaces import IAttachedFile, IVersion
from bungeni.models import domain
from bungeni.core import audit
from bungeni.core.interfaces import IVersioned
from bungeni.utils import register


# !+CHANGELOG_DATA_DUPLICATION(mr, nov-2011)
@register.handler(adapts=(IAttachedFile, IObjectCreatedEvent))
def file_added(ob, event):
    """When a file is added, audit the change on the parent object.
    """
    event.action = "added"
    audit.object_attachment(removeSecurityProxy(ob), event)

# !+CHANGELOG_DATA_DUPLICATION(mr, nov-2011)
@register.handler(adapts=(IAttachedFile, IObjectModifiedEvent))
def file_modified(ob, event):
    """When a file is modified, audit the change on the parent object.
    """
    event.action = "modified"
    audit.object_attachment(removeSecurityProxy(ob), event)


@register.handler(adapts=(IVersion, IObjectCreatedEvent))
def objectNewVersion(ob, event):
    """When an object is versioned we copy the attachments to the version.
    """
    if type(ob) == domain.AttachedFileVersion:
        return
    ob = removeSecurityProxy(ob)
    session = Session()
    session.merge(ob)
    session.flush()
    ''' !+ATTACHED_FILE_VERSIONS(mr, sep-2011) consider alternative way to 
    handle the "snapshotting" of attached_files (on versioning of head object) 
    i.e:
    a) to NEVER modify a db record of a file attachment
    b) if EDIT of an attachment is to be supported, expose an edit view, but
    saving a "modified" attachment means *replacing* it with a new record (this 
    also serves as an automatic changelog mechanism on any change). 
    Note, each attached_file would need thus need to record pointer back to 
    "previous" version.
    c) this results in that an explicit VERSIONING of an attachment 
    (independently of its owning item) should no longer be needed... given that 
    any CHANGE in an attachment's info systematically causes a new version.
    d) versioning of a "head item" (and of any of its attachments at that time)
    now implies only copying of FK refs to any attachments on the head object.
    
    The above has several advantages:
    
    - multiple attachments per item are not needlessly copied over each time 
    a head object is versioned, thus reducing data duplication/noise.
    - does not *lose* semantics in the persisted information i.e. currently a
    version of a head item points to a *version* of an attachment that is 
    in *most* cases *identical* to the "head attachment" it is versioning...
    but to know whether it *is* the same object some additional checking 
    would be needed. With this scheme, if the head item OR ANY version of it 
    have the *same logical* attachment instance then they would point to the 
    SAME attachment db record.
    '''
    for attached_file in ob.head.attached_files:
        versions = IVersioned(attached_file)
        version = versions.create("version created on object versioning: %s" %
                getattr(ob.change, "description", ""))
        version.file_version_id = ob.version_id

