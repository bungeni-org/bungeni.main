# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Auditing of Changes for Domain Objects

$Id$


Auditing implementation rules to be aware of and comply with:

- Any change on an instance is audited ONLY on that instance i.e. for when 
instance is "contained" in some parent/head object, and changes on it must 
not be logged also as changes on the parent.

- Only the change action keywords should be used (verbs in present tense?):
    add
    modify
    workflow
    remove
    version (includes reversion)

- Each single "logical" change should only generate a single change record 
e.g. a workflow change implies a modify change but should only be logged once 
and using the "logical origin" of the change to determine what action verb to 
use, that in this example would therefore be "workflow". !+TBD

"""
log = __import__("logging").getLogger("bungeni.core.audit")


__all__ = ["get_auditor", "set_auditor"]


from datetime import datetime

from zope.lifecycleevent import IObjectModifiedEvent, IObjectCreatedEvent, \
    IObjectRemovedEvent
from zope.annotation.interfaces import IAnnotations
from zope.security.proxy import removeSecurityProxy

import sqlalchemy as sa
from bungeni.alchemist import Session

from bungeni.models import utils
from bungeni.models.interfaces import IFeatureAudit
from bungeni.models import schema
from bungeni.models import domain
from bungeni.core.interfaces import TranslationCreatedEvent
from bungeni.core.translation import translate_obj
from bungeni.core.workflow.interfaces import IWorkflowTransitionEvent
from bungeni.ui.utils import common
from bungeni.utils import register


def _trace_audit_handler(ah):
    """Simple decorator to log.debug each call to (specifically) an 
    audit handler. 
    """
    def _ah(ob, event):
        log.debug("AUDITING %s(%s, %s) originator=%s" % (
            ah.__name__, ob, event, getattr(event, "originator", None)))
        ah(ob, event)
    return _ah


# change handlers

@register.handler(adapts=(IFeatureAudit, TranslationCreatedEvent))
@_trace_audit_handler
def _object_translate(ob, event):
    auditor = get_auditor(ob)
    auditor.object_translate(removeSecurityProxy(ob), event)

@register.handler(adapts=(IFeatureAudit, IObjectCreatedEvent))
@_trace_audit_handler
def _object_add(ob, event):
    auditor = get_auditor(ob)
    auditor.object_add(removeSecurityProxy(ob), event)

@register.handler(adapts=(IFeatureAudit, IObjectModifiedEvent))
@_trace_audit_handler
def _object_modify(ob, event):
    # no audit ObjectModifiedEvent if originates from a WorkflowTransitionEvent
    orginator = getattr(event, "originator", None)
    if IWorkflowTransitionEvent.providedBy(orginator):
        log.debug("NOT AUDITING event [%s] as it originates from [%s]" % (
            event, orginator))
        return
    auditor = get_auditor(ob)
    auditor.object_modify(removeSecurityProxy(ob), event)

@register.handler(adapts=(IFeatureAudit, IObjectRemovedEvent))
@_trace_audit_handler
def _object_remove(ob, event):
    auditor = get_auditor(ob)
    auditor.object_remove(removeSecurityProxy(ob), event)

@register.handler(adapts=(IFeatureAudit, IWorkflowTransitionEvent))
@_trace_audit_handler
def _object_workflow(ob, event):
    auditor = get_auditor(ob)
    change_id = auditor.object_workflow(removeSecurityProxy(ob), event)
    event.change_id = change_id

''' !+OBSOLETE_VERSIONING versioning of an object is no longer event-based

from bungeni.core.interfaces import IVersionCreated, IVersionReverted

@register.handler(adapts=(IFeatureAudit, IVersionCreated))
@_trace_audit_handler
def _object_version(ob, event):
    """When an auditable object is versioned, we audit creation of new version.
    
    As version objects are objects that never change, no audit trail on them 
    is needed. But a change record on the head object is needed to provide the 
    following valuable information:
    
    - The "owner" of the object being versioned is categorically also always 
    the owner of any version made of it, irresepctive of who actually makes it. 
    The "user" who authored the change is recorded in the change record.
    - Possibly to specify an effective date (date_active)
    - Possibility to add a description of the change (as well as notes/extras).
    """
    auditor = get_auditor(ob)
    change_id = auditor.object_version(removeSecurityProxy(ob), event)
    event.version.change_id = change_id

@register.handler(adapts=(IFeatureAudit, IVersionReverted))
@_trace_audit_handler
def _object_reversion(ob, event):
    auditor = get_auditor(ob)
    change_id = auditor.object_reversion(removeSecurityProxy(ob), event)
    event.change_id = change_id
'''


# internal utilities

def _get_auditable_ancestor(obj):
    parent = obj.__parent__
    while parent:
        if IFeatureAudit.providedBy(parent):
            return parent
        else:
            parent = getattr(parent, "__parent__", None)


class _AuditorFactory(object):
    
    def __init__(self, audit_table, audit_class):
        self.audit_table = audit_table
        self.audit_class = audit_class
    
    # handlers, return the change_id
    
    def object_add(self, ob, event):
        return self._object_changed("add", ob)
    
    def object_modify(self, ob, event):
        change_data = self._get_change_data()
        return self._object_changed("modify", ob, 
                date_active=change_data["date_active"])
    
    def object_remove(self, ob, event):
        # !+AUDIT_REMOVE(mr, feb-2011) if this is a real delete (of a record 
        # from the db) then there is really no sense in auditing it at all in 
        # the first place (really deleting an item should also mean deleting 
        # what is owned by it e.g. its change records). [Plus, trying to audit
        # such a deletion gives a sqlalchemy.exc.InvalidRequestError, 
        # "Instance ... has been deleted".
        #
        # If this is a semantic "delete" e.g. to mark the item as obsolete, 
        # then it would be desireable to audit it as any other change action.
        #return self._object_changed("remove", ob)
        log.warn("!+AUDIT_REMOVE not auditing deletion of [%s]" % (ob))
    
    def object_workflow(self, ob, event):
        change_data = self._get_change_data()
        # update object's workflow status date (if supported by object)
        if hasattr(ob, "status_date"):
            ob.status_date = change_data["date_active"] or datetime.now()
        # as a "base" description, use human readable workflow state title
        #wf = IWorkflow(ob)
        #description = wf.get_state(event.destination).title # misc.get_wf_state
        return self._object_changed("workflow", ob, 
                date_active=change_data["date_active"],
                note=change_data.get("note", None))
    
    
    def object_version(self, ob, root=False):
        """NOTE: versioning of an object is not event based.
        """
        # action: ("version")
        change_data = self._get_change_data()
        
        if root:
            note = change_data.get("note")
            procedure = change_data.get("procedure", "m")
        else:
            # root version note is repeated for non-root-versions !+?
            note = change_data.get("note")
            # procedure="a" for non-root versions
            procedure = "a"
        # !+polymorphic_identity_multi REVERSION action MUST be same as "version"
        return self._object_changed("version", ob,
                date_active=change_data.get("date_active"),
                note=note,
                procedure=procedure)
    
    def object_translate(self, ob, event):
        # !+TRANSLATION_VERSION(mr, feb-2013) the audited values for the (head) 
        # object are those for the newly submitted translation BUT a "translation"
        # should really be bound to a specific *version* of the object, not to head.
        translated_ob = translate_obj(ob, event.language)
        translated_ob.language = event.language
        # !+TRANSLATE_DESCRIPTION(mr, feb-2013) this should really be passed
        # on such that is is picked up by the change description formattter,
        # and not persisted on the xp change.note (intended primarily for 
        # manual notes coming from the user).
        note = "fields: %s" % (", ".join(event.translated_attribute_names))
        return self._object_changed("translate", translated_ob, note=note)
    
    #
    
    def _object_changed(self, action, ob, 
            date_active=None,
            note=None,
            procedure="a",
        ):
        """() -> domain.Change
        
        date_active:
            the UI for some changes allow the user to manually set the 
            date_active -- this is what should be used as the *effective* date 
            i.e. the date to be used for all intents and purposes other than 
            for data auditing. When not user-modified, the value should be equal 
            to date_audit.
        """
        domain.assert_valid_change_action(action)
        user = utils.get_login_user()
        assert user is not None, "Audit error. No user logged in."
        # carry over a snapshot of head values
        def get_field_names_to_audit(kls):
            names_to_audit = []
            table = self.audit_table
            for column in table.columns:
                # skip all fields starting with "audit_"
                if column.name.startswith("audit_"):
                    continue
                # ok, column must therefore be a proper attribute from ob's class
                assert column.name in kls.__dict__, \
                    "Not in class: %s" % column.name
                # skip all primary keys (audit_head_id managed separately)
                if column.primary_key: 
                    continue
                names_to_audit.append(column.name)
            for vp_name, vp_type in kls.extended_properties:
                names_to_audit.append(vp_name)
            return names_to_audit
        
        def copy_field_values(head_cls, source, dest):
            for name in get_field_names_to_audit(head_cls):
                setattr(dest, name, getattr(source, name))
        
        # ensure real head object, in case we are dealing with reversioning 
        # off an Audit instance
        head_ob = ob
        if action == "version" and issubclass(ob.__class__, domain.Audit):
            # ob is an Audit instance, so need its head_ob
            head_ob = ob.audit_head
        
        # audit snapshot - done first, to ensure a valid audit_id...
        au = self.audit_class()
        au.audit_head = head_ob # attach audit log item to parent object
        copy_field_values(head_ob.__class__, ob, au)
        session = Session()
        session.add(au)
        
        # change/audit record
        # !+version Version instances are created as Change instances!
        ch = domain.Change()
        ch.seq = 0 # !+ reset below, to avoid sqlalchemy violates not-null constraint
        ch.audit = au # ensures ch.audit_id, ch.note.object_id
        ch.user_id = user.user_id
        ch.action = action
        ch.seq = self._get_seq(ch)
        # !+translate_seq(mr, feb-2013) this should be divided by language?
        # !+translate_action(mr, feb-2013) shoudl there be an action per 
        # language e.g. translate-fr for translations to french (resolves the 
        # noted translate_seq issue)
        ch.procedure = procedure
        ch.date_audit = datetime.now()
        if date_active:
            ch.date_active = date_active
        else:
            ch.date_active = ch.date_audit
        if note:
            ch.note = note
        
        # !+SUBITEM_CHANGES_PERMISSIONS(mr, jan-2012) permission on change 
        # records for something like item[@draft]->file[@attached]->fileversion 
        # need to remember also the root item's state, else when item later 
        # becomes visible to clerk and others, the file itself will also become 
        # visible to the clerk (CORRECT) but so will ALL changes on the file 
        # while that file itself was @attached (WRONG!). May best be addressed
        # when change persistence is reworked along with single document table.
        
        session.flush()
        log.debug("AUDIT [%s] %s" % (au, au.__dict__))
        log.debug("CHANGE [%s] %s" % (action, ch.__dict__))
        return ch
    
    #
    
    def _get_seq(self, ch):
        """Determine and return a next seq number for this (head, action).
        """
        ''' !+ALTERNATE_QUERY_CHANGE_SEQ_MAX, a little faster than head.changes?
        from time import time
        t0 = time() # via query using sa.func.max
        head_id_column_name = ch.audit.head_id_column_name
        audit_tbl = sa.orm.object_mapper(ch.audit).local_table
        max_seq_alt = Session().query(sa.func.max(domain.Change.seq)
            ).join(
                (audit_tbl, domain.Change.audit_id == audit_tbl.c.audit_id)
            ).filter(
                sa.sql.expression.and_(
                    domain.Change.action == ch.action,
                    audit_tbl.c[head_id_column_name] == 
                        getattr(ch.audit, head_id_column_name)
                )).scalar() or 0
        t1 = time() # via head.changes
        '''
        head = ch.audit.audit_head # ch.head
        seqs_for_action_to_date = [ c.seq for c in head.changes 
            if c.action == ch.action and c.seq is not None] or [0]
        max_seq = max(seqs_for_action_to_date)
        ''' !+ALTERNATE_QUERY_CHANGE_SEQ_MAX
        t2 = time()
        print "TIME to determine CHANGE SEQ MAX for (%s=%s, %s)" % (
            head_id_column_name, getattr(ch.audit, head_id_column_name), ch.action)
        print "    via RDB.FUNC.MAX = %s" % (t1 - t0)
        print "    via HEAD.CHANGES = %s" % (t2 - t1)
        assert max_seq == max_seq_alt, \
            "Results form alternate ways to get seq are different: %s, %s" % (
                max_seq_alt, max_seq)
        '''
        return max_seq + 1
    
    def _getKey(self, ob):
        mapper = sa.orm.object_mapper(ob)
        primary_key = mapper.primary_key_from_instance(ob)[0]
        return primary_key, unicode(ob.__class__.__name__)
    
    def _get_change_data(self):
        """If request defines change_data, use it, else return a dummy dict.
        
        !+ui.forms.workflow adds entries for: note, date_active, registry_number
        """
        try:
            cd = IAnnotations(common.get_request()).get("change_data")
            assert cd is not None, "change_data dict is None."
        except (TypeError, AssertionError):
            # Could not adapt... under testing, the "request" is a 
            # participation that has no IAnnotations.
            cd = {}
        cd.setdefault("note", cd.get("note", ""))
        cd.setdefault("date_active", cd.get("date_active", None))
        return cd


# module-level dedicated auditor singleton instance per auditable class
# !+type_info should we add audit_model and auditor?

def get_auditor(ob):
    """Get the module-level dedicated auditor singleton instance for the 
    auditable ob.__class__ -- raise KeyError if no such auditor singleton.
    """
    return globals()["%sAuditor" % (ob.__class__.__name__)]

def set_auditor(kls):
    """Set the module-level dedicated auditor singleton instance for the 
    auditable kls.
    """
    name = kls.__name__
    auditor_name = "%sAuditor" % (name)
    log.debug("Setting AUDITOR %s [for type %s]" % (auditor_name, name))
    from bungeni.alchemist.catalyst import MODEL_MODULE
    audit_kls = getattr(MODEL_MODULE, "%sAudit" % (name))
    audit_tbl = getattr(schema, domain.get_audit_table_name(kls))
    # !+debug check of repeat calls
    auditor = globals().get(auditor_name)
    if auditor is not None:
        if (auditor.audit_table, auditor.audit_class) is (audit_tbl, audit_kls):
            log.warn("SET_AUDITOR: ignoring attempt to reset Auditor for: %s" % audit_kls)
            return
        else:
            log.warn("SET_AUDITOR: resetting auditor for (tbl, kls), \n"
                "  changed from (%s, %s)\n"
                "            to (%s, %s)" % (
                    auditor.audit_table, auditor.audit_class,
                    audit_tbl, audit_kls))
    # /debug check of repeat calls
    globals()[auditor_name] = _AuditorFactory(audit_tbl, audit_kls)


