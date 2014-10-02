# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""The Bungeni object domain

Created by Kapil Thangavelu on 2007-11-22.

$Id$
"""
log = __import__("logging").getLogger("bungeni.models.domain")

import md5
import random
import string
import datetime

from zope import interface, location
from zope.dublincore.interfaces import IDCDescriptiveProperties
import sqlalchemy.sql.expression as sql
from sqlalchemy.orm import object_mapper

from bungeni import alchemist
from bungeni.alchemist.traversal import one2many, one2manyindirect
from bungeni.models import interfaces


# base entity support

class HeadParentedMixin(object):
    """For sub-objects of a "head" object.
    
    Changes the behaviour of __parent__ to by default return the head object 
    UNLESS a non-None __parent__ is hard-set explicitly on the sub-instance
    (e.g. as within an alchemist container listing, alchemist sets the 
    __parent__ to the container).
    
    This default behaviour is needed as the roles a user has via a 
    sub-object may not include all the same roles the user has on its 
    head object, that may result in an incorrect permission decision,
    in particular as permission checking on sub-objects is often bound
    to permissions on the head object.
    """
    # remember if __parent__ has been explicitly set
    _explicit_parent = None
    # implement as a "clean" property, using the namespace containment of a 
    # "temporary" function, that returns a dict to be later used as keyword
    # args to define a same-named property.
    def __parent__():
        doc = "Returns the Zope 3 canonical location of the instance " \
            "i.e. the __parent__ object, usually needed to lookup security " \
            "settings on the instance."
        def fget(self):
            if self._explicit_parent is None:
                return self.head
            return self._explicit_parent
        def fset(self, parent):
            self._explicit_parent = parent
        def fdel(self):
            self._explicit_parent = None
        return locals()
    __parent__ = property(**__parent__())


class Entity(object):
    interface.implements(location.ILocation)
    __name__ = None
    __parent__ = None
    
    # list of names (may be empty) of dynamic features available for this type
    available_dynamic_features = []
    
    extended_properties = [] # [(name, type)]
    
    def __init__(self, **kw):
        try:
            domain_schema = alchemist.utils.get_derived_table_schema(type(self))
            known_names = [ k for k, d in domain_schema.namesAndDescriptions(all=True) ]
        except Exception, e:
            log.debug("Failed table schema lookup for %s: %s: %s", 
                type(self), type(e).__name__, e)
            known_names = None
        
        for k, v in kw.items():
            if known_names is None or k in known_names:
                setattr(self, k, v)
            else:
                log.error(
                    "Invalid attribute on %s %s", self.__class__.__name__, k)
    
    def on_create(self):
        """Hook to call on creation of an instance, to handle any business 
        setup/logic that the application MUST (i.e. not subject to any user
        configuration) take care of.
        """
        pass
    
    def on_delete(self):
        """Hook to call on deletion of an instance, to handle any business 
        setdown/logic that the application MUST (i.e. not subject to any user
        configuration) take care of.
        """
        pass
    
    @property
    def pk(self):
        """ () -> [(pk_name, pk_value)] -- intended primarily as debug utility.
        """
        return [ (c.name, getattr(self, c.name))
             for c in object_mapper(self).primary_key ]


# extended attributes - vertical properties

class VerticalProperty(Entity):
    """Base Vertical Property.
    """
    def __init__(self, object_, object_type, name, value):
        # !+backref sqlalchemy populates a self.object backref, but on flushing
        self._object = object_
        # sqlalchemy instruments a property per column, of same name
        self.object_id = get_mapped_object_id(object_)
        self.object_type = object_type # the db table's name
        self.name = name # the domain class's property name
        self.value = value
    
    def __repr__(self):
        #!+VP(mb, Aug-2012) Why is reference to self.object_ i.e.
        # hex(id(self._object)) sometimes not set? e.g. during serialization
        return "<%s %s=%r on (%r, %s)>" % (self.__class__.__name__, 
                self.name, self.value, self.object_type, self.object_id)

class vp(object):
    """A convenient vp namespace.
    """
    class Text(VerticalProperty):
        """VerticalProperty of type text.
        """
    class TranslatedText(VerticalProperty):
        """VerticalProperty of type translated text.
        """
        def __init__(self, object_, object_type, name, value, language=None):
            VerticalProperty.__init__(self, object_, object_type, name, value)
            # !+LANGUAGE(mr, mar-2012) using "en" as default... as
            # get_default_language() is in core, that *depends* on models!
            self.language = language or "en" # or get_default_language()
    class Datetime(VerticalProperty):
        """VerticalProperty of type datetime.
        """
    class Binary(VerticalProperty):
        """VerticalProperty of type binary.
        """
    class Number(VerticalProperty):
        """VerticalProperty of type number (integer).
        """


# change, audit, version

AUDIT_ACTIONS = ("add", "modify", "workflow", "remove", "version", "translate")

def assert_valid_change_action(action):
    assert action in AUDIT_ACTIONS, \
        "Invalid audit action: %s. Must be one of: %s" % (
            action, AUDIT_ACTIONS)

def get_changes(auditable, *actions):
    """Get changelog for auditable context, filtered for actions.
    """
    for action in actions:
        assert_valid_change_action(action)
    # lazy loading - merge to avoid sqlalchemy.orm.exc.DetachedInstanceError
    auditable = alchemist.Session().merge(auditable)
    # !+ for some reason, on event creation (with minimal log for one workflow 
    # and one add change) the following does not pick up the one workflow change:
    return [ c for c in auditable.changes if c.action in actions ]

def get_audit_table_name(kls):
    return "%s_audit" % (alchemist.utils.get_local_table(kls).name)

def get_mapped_object_id(ob):
    # !+ASSUMPTION_SINGLE_COLUMN_PK(mr, may-2012)
    return object_mapper(ob).primary_key_from_instance(ob)[0]


class Change(HeadParentedMixin, Entity):
    """Information about a change, along with the snapshot (on self.audit) of 
    the object attribute values as of *after* the change.
    """
    interface.implements(
        interfaces.IChange
    )
    
    @property
    def __name__(self):
        return "%s-%s" % (self.action, self.seq)
    
    @property
    def head(self):
        return self.audit.audit_head # orm property
    
    # !+Change.status(mr, apr-2012) needed? keep?
    # !+StatusDocPrincipal
    @property
    def status(self):
        return self.audit.status # assumption: audit.audit_head is workflowed
    
    @property
    def seq_previous(self):
        """The previous change in action seq on self.head. None if no previous.
        """
        changes = get_changes(self.head, self.action)
        for c in changes[1 + changes.index(self):]:
            return c
    
    @property
    def previous(self):
        """The previous change (any action) on self.head. None if no previous.
        """
        changes = get_changes(self.head, *AUDIT_ACTIONS)
        for c in changes[1 + changes.index(self):]:
            return c
    
    # change "note" -- as external extended attribute (vertical property) as:
    # a) presumably it may have to be translatable, and the initial language 
    #    may not be the same as that of the head object being audited.
    # b) it will be set very seldom.
    extended_properties = [
        ("note", vp.TranslatedText)
    ]

class ChangeTree(Entity):
    """Relates a parent change with a child change.
    """

# !+VERSION_CLASS_PER_TYPE(mr, apr-2012) should there be dedicated Version 
# type/descriptor, to facilitate UI views for each version type? Or should
# simply keep a single generic Change type, and handle all "type-specific" 
# aspects via the self.audit instance (and its type)?
class Version(Change):
    """A specialized change type, with the information of a version (a special 
    kind of change action) of an object. 
    
    Behaves somewhat like a combined Change and Audit record--attributes not 
    found on self (Change) will only fail if a further attempt to resolve them
    off self.audit fails. 
    
    This is an "abstract" class, it is not catalysed, and only sub-classes 
    are ever instantiated.
    """
    interface.implements(
        interfaces.IVersion,
    )
    
    '''!+
    def __init__(self, **kw):
        # !+SA_INCORRECT_TYPE_DEBUG strangely, sometimes the type of 
        # (this change's) self.audit that sqlalchemy returns does not 
        # correspond to self.head...
        super(Version, self).__init__(**kw)
        audit_id = self.audit_id
        def get_correctly_typed_change(change):
            for v in self.head.versions:
                if v.audit_id == audit_id:
                    return v
        correctly_typed_change = get_correctly_typed_change(self)
        if correctly_typed_change and correctly_typed_change is not self:
            print ("!+SA_INCORRECT_TYPE_DEBUG \n"
                "       %s.%s head/id=%s/%s, audit/id=%s/%s \n"
                "           SA INCORRECT TYPE:%s \n"
                "           SHOULD HAVE BEEN:%s" % (
                    type(self).__name__, name, 
                    self.head, self.head_id, 
                    self.audit, audit_id, 
                    self, correctly_typed_change))
            import pdb; pdb.set_trace()
        # !+/SA_INCORRECT_TYPE_DEBUG
    '''
    
    #@property
    #def __name__(self):
    #    return "ver-%s" % (self.seq)
    def __name__():
        doc = "dynamically set __name__ property, with a DEBUG setter"
        def fget(self):
            return "ver-%s" % (self.seq)
        def fset(self, name):
            # !+CONTAINED can't set attribute - alchemist/container.py contained()
            # -> obj.__name__ = name
            if not name == self.__name__:
                print "**RESETTING** domain.Version.name:", self, self.__name__, name
                import pdb; pdb.set_trace()
        return locals()
    __name__ = property(**__name__())    
    
    def __getattr__(self, name):
        """Try to pick any attribute (not found on this change record--this 
        method only gets called when a non-existent attribute is accessed) off 
        the related audit snapshot record (as every change record is related 
        to a type-dedicated audit record).

        !+ should this be on Change i.e. for all change actions?
        """
        audit = self.audit
        try:
            return getattr(audit, name)
        except AttributeError:
            # !+DocVersion.filevers
            try:
                from bungeni.alchemist import utils
                return utils.FILES_VERSION_CONTAINER_ATTRIBUTE_ERROR_HACK(self, name)
            except:
                import sys
                from bungeni.utils import probing
                probing.log_exc(sys.exc_info(), log_handler=log.error)
            
            raise AttributeError(
                "%r [audit_id=%r, audit_type=%r] object has no attribute %r" % (
                    self, self.audit_id, self.audit_type, name))


class Audit(HeadParentedMixin, Entity):
    """Base (abstract) audit record for a document.
    """
    interface.implements(
        interfaces.IChange # !+IAudit?
    )
    
    @classmethod
    def auditFactory(cls, auditable_cls):
        # Notes:
        # - each "TYPEAudit" class does NOT inherit from the "TYPE" class it audits.
        # - each "TYPEAudit" class inherits from "Audit"
        # - each auditable sub-TYPE gets own dedicated sub-type of "TYPEAudit"
        #   e.g. EventAudit inherits from DocAudit that inherits from Audit.
        # - just as all subtypes of "Doc" are persisted on "doc" table, so are 
        #   all subtypes of "DocAudit" persisted on "doc_audit".
        # 
        # define a subtype of Audit type
        audit_factory_name = "%sAudit" % (auditable_cls.__name__)
        # !+
        auditable_pk_column = [ c for c in 
            alchemist.utils.get_local_table(auditable_cls).primary_key ][0]
        factory = type(audit_factory_name, (cls,), {
            "head_id_column_name": auditable_pk_column.name })
        # define a subtype of Audit type
        audit_table_name = get_audit_table_name(auditable_cls)
        # ensure cls has own dedicated "extended_properties" list property --
        # extended properties from cls are inherited... but need to propagate 
        # onto audit_kls any extended properties defined by auditable_cls:
        factory.extended_properties = auditable_cls.extended_properties[:]
        alchemist.model.instrument_extended_properties(factory, audit_table_name)
        return factory
    
    head_id_column_name = None # set in cls.auditFactory()
    def audit_head_id():
        doc = "Returns the integer of the single PK of the head object."
        def fget(self):
            return getattr(self, self.head_id_column_name)
        def fset(self, head_id):
            return setattr(self, self.head_id_column_name, head_id)
        return locals()
    audit_head_id = property(**audit_head_id())
    
    # the label is used to for building display labels and/or descriptions of 
    # an audit record, but each type names its "label" attribute differently...
    label_attribute_name = "label"
    @property
    def label(self):
        return getattr(self, self.label_attribute_name)


# ARCHETYPES


# doc

class Doc(Entity):
    """Base class for a workflowed parliamentary document.
    """
    # allowed dynamic features by this archetype (inherited by sub-types)
    available_dynamic_features = ["audit", "version", "attachment", "event",
        "signatory", "schedule", "workspace", "notification",
        "email", "download", "user_assignment", "group_assignment"]
    interface.implements(
        interfaces.IOwned,
        interfaces.IBungeniContent,
        interfaces.IDoc,
        interfaces.ITranslatable,
        interfaces.ISerializable
    )
    
    def on_create(self):
        """Application-internal creation logic i.e. logic NOT subject to config.
        """
        # set chamber_id if not set -- requires that group_id is ALWAYS set, 
        # on all new doc, event, report instances
        if self.chamber_id is None:
            from bungeni.models import utils
            chamber = utils.get_chamber_for_group(self.group)
            # above will be None if self.group is None or is outside of a chamber...
            if chamber is None:
                owner = utils.get_user(self.owner_id)
                chamber = utils.get_user_chamber(owner)
                log.warn("Doc.on_create: falling back to picking off chamber_id "
                    "[%s] from Doc.owner_id [%s] for new doc %s [doc_id=%s]",
                        chamber.group_id, self.owner_id, self, self.doc_id)
            self.chamber_id = chamber.group_id
        # !+GROUP_ID_REQUIRED if no group_id, push back chamber_id as group_id...
        if self.group_id is None:
            self.group_id = self.chamber_id
            log.warn("Doc.on_create: setting None group_id to just be "
                "chamber_id [%s] for new doc %s [doc_id=%s]",
                    self.chamber_id, self, self.doc_id)
        # requires self db id to have been updated
        from bungeni.core import workflows
        workflows.utils.assign_ownership(self)
    
    # !+AlchemistManagedContainer these attribute names are part of public URLs!
    # !+item_id->head_id
    
    def _get_workflow_date(self, *states):
        """ (states:seq(str) -> date
        Get the date of the most RECENT workflow transition to any one of 
        the workflow states specified as input parameters. 
        
        Returns None if no such workflow states has been transited to as yet.
        """
        assert states, "Must specify at least one workflow state."
        # order of self.changes is reverse chronological (newest first)
        for c in get_changes(self, "workflow"):
            if c.audit.status in states:
                return c.date_active
    
    extended_properties = [
    ]

class DocAudit(Audit):
    """An audit record for a document.
    """
    label_attribute_name = "title"
    extended_properties = [
    ]

class DocVersion(Version):
    """A version-change of a document.
    """
    interface.implements(
        interfaces.IDocVersion,
    )
    # !+version_feature_attachment
    # !+FILES_VERSION_CONTAINER_ATTRIBUTE_ERROR_HACK note, "declaring" the 
    # container with bungeni.alchemist.model.add_container_property_to_model
    # gives same errors!
    filevers = one2manyindirect("filevers",
        "bungeni.models.domain.AttachmentVersionContainer", "head_id", "doc_id")
    
    # !+attachment_version.head (->Attachment) and attachment_version.head_id (->Doc) 
    # discrepancy!
    
    # !+version_feature_event
    #events = one2many("events",
    #    "bungeni.models.domain.DocVersionContainer", "head_id")


# event

class Event(HeadParentedMixin, Doc):
    """Base class for an event on a document.
    """
    #!+chamber_id is (has always been) left null for events, how best to 
    # handle this, possible related constraint e.g. head_id must NOT be null, 
    # validation, ... ?
    available_dynamic_features = ["audit", "version", "attachment",
        "notification", "email"]
    interface.implements(
        interfaces.IEvent,
    )



# principal: user, group

class Principal(Entity):
    """Base model for a Principal, that is a User or a Group.
    """
    principal_type = None


class User(Principal):
    """Domain Object For A User. General representation of a person.
    """
    principal_type = "user"
    available_dynamic_features = ["address"]
    
    interface.implements(
        interfaces.IOwned,
        interfaces.IBungeniUser, 
        interfaces.ITranslatable, 
        interfaces.ISerializable
    )
    
    def __init__(self, login=None, **kw):
        if login:
            self.login = login
        super(User, self).__init__(**kw)
        self.salt = self._makeSalt()
    
    def on_create(self):
        from bungeni.core.workflows import utils
        utils.assign_ownership(self)
    
    # !+SORT_ON_USER(mr, may-2013) make the __lt__ method on every domian model
    # be derived from configuration i.e. from descriptor.sort_on?
    def __lt__(self, other):
        return ((self.last_name, self.first_name, self.middle_name, self.user_id) < 
            (other.last_name, other.first_name, other.middle_name, other.user_id))
    
    def _makeSalt(self):
        return "".join(random.sample(string.letters[:52], 12))
    
    def _password():
        doc = "Set the password, encrypting it. Cannot retrieve."
        def fget(self):
            return None
        def fset(self, password):
            self.password = self.encode(password)
        return locals()
    _password = property(**_password())
    
    def encode(self, password):
        return md5.md5(password + self.salt).hexdigest()
    
    def checkPassword(self, password_attempt):
        attempt = self.encode(password_attempt)
        return attempt == self.password
    
    # !+ACTIVE_P replace with "status" in db
    def status():
        doc = """A "status" attribute as alias onto "active_p" attribute."""
        def fget(self):
            return self.active_p
        def fset(self, value):
            self.active_p = value
        return locals()
    status = property(**status())
    
    # !+ACTIVE normalize across user/group/member 
    @property
    def active(self):
        """Is this user active? 
        """
        return self.active_p == "A"
    
    delegations = one2many("delegations",
        "bungeni.models.domain.UserDelegationContainer", "user_id")


class AdminUser(Entity):
    """An admin user"""

class UserDelegation(Entity):
    """Delegate rights to act on behalf of a user to another user.
    """
    interface.implements(interfaces.IUserDelegation)

class PasswordRestoreLink(object):
    """Object containing hash and expiration date for
    password restoration form"""
    
    def expired(self):
        return self.expiration_date < datetime.datetime.now() 


class Group(Principal):
    """An abstract collection of users.
    """
    privilege_extent = "group"
    principal_type = "group"
    available_dynamic_features = ["audit", "version", "sitting", "address"]
    interface.implements(
        interfaces.IDrafted,
        interfaces.IGroup,
        interfaces.ITranslatable,
        interfaces.ISerializable
    )
    
    publications = one2many("publications", 
        "bungeni.models.domain.ReportContainer", "group_id")
    
    def __init__(self, **kw):
        super(Group, self).__init__(**kw)
    
    def on_create(self):
        """Application-internal creation logic i.e. logic NOT subject to config.
        """
        # requires self db id to have been updated
        from bungeni.core.workflows import utils
        utils.assign_ownership(self)
        utils.unset_group_local_role(self)
    
    # !+ACTIVE normalize across user/group/member !+ self.status == "active"
    # base on end_date or introduce across the board an @active attr on workflow states?
    @property
    def active(self):
        """Is this group active? 
        A group is taken to be active if valid (past) start_date and no end_date.
        """
        today = datetime.datetime.today().date()
        return (self.start_date <= today and 
            (not self.end_date or self.end_date > today))
    
    def active_membership(self, user_id):
        session = alchemist.Session()
        query = session.query(GroupMember).filter(
            sql.and_(
                GroupMember.group_id == self.group_id,
                GroupMember.user_id == user_id,
                GroupMember.active_p == True
            )
        )
        if query.count() == 0:
            return False
        else:
            return True
    
    def is_type_workspaced(self, type_key):
        """Is this type workspaced within this group context (for user)?
        """
        from bungeni.capi import capi
        ti = capi.get_type_info(type_key)
        workspace_feature = ti.workflow.get_feature("workspace")
        if workspace_feature is not None:
            group_names = workspace_feature.p["group_names"]
            return self.conceptual_name in group_names
        return False

class GroupAudit(Audit):
    """An audit record for a group.
    """
    label_attribute_name = "short_name"


# member 

class GroupMember(HeadParentedMixin, Entity):
    """A user's membership in a group-abstract basis for 
    ministers, committee_members, etc.
    """
    available_dynamic_features = ["audit", "version"]
    interface.implements(
        interfaces.IGroupMember,
        interfaces.ITranslatable,
        interfaces.ISerializable
    )
    
    subroles = one2many("subroles", 
        "bungeni.models.domain.MemberRoleContainer", "member_id")
    
    @property
    def image(self): 
        return self.user.image
    @property
    def first_name(self):
        return self.user.first_name
    @property
    def last_name(self):
        return self.user.last_name
    
    # !+ACTIVE normalize across user/group/member 
    # base on end_date, status, dedicated column "active_p", 
    # or introduce across the board an @active attr on workflow states?
    @property
    def active(self):
        """Is this member active? 
        A member is taken to be active if valid (past) start_date and no end_date.
        Note: when end_date is set, then "active_p" SHOULD always be False (but,
        there are data inconsistencies)
        """
        today = datetime.datetime.today().date()
        return (self.start_date <= today and 
            (not self.end_date or self.end_date > today))
    
    # !+SORT_ON_USER
    def __lt__(self, other):
        return self.user < other.user

class GroupMemberAudit(Audit):
    """An audit record for a group member.
    """
    #!+label_attribute_name = "user_id"
    @property
    def label(self):
        return IDCDescriptiveProperties(self.audit_head).title


# !+IS_GLOBAL rename table/class to member_subrole/MemberSubRole ?!
class MemberRole(Entity):
    """Association between an group member and subroles that are granted when 
    a document is assigned to a user.
    """
    interface.implements(interfaces.IMemberRole)
    
    def on_create(self):
        """Application-internal creation logic i.e. logic NOT subject to config.
        """
        from bungeni.core.workflows import utils
        if self.is_global:
            utils.set_role(self.role_id, self.member.user.login, 
                utils.get_group_privilege_extent_context(self.member.group))
    
    def on_delete(self):
        """Application-internal deletion logic i.e. logic NOT subject to config.
        """
        from bungeni.core.workflows import utils
        if self.is_global:
            utils.unset_role(self.role_id, self.member.user.login, 
                utils.get_group_privilege_extent_context(self.member.group))
    
    @property
    def group(self):
        return self.member.group


class MemberTitle(Entity):
    """The role title a member has in a specific context and one 
    official address for a official role.
    """
    interface.implements(
        interfaces.IMemberTitle,
        interfaces.ITranslatable
    )

class TitleType(Entity):
    """Types of titles in groups
    """
    interface.implements(interfaces.ITitleType, interfaces.ITranslatable)


# SUPPORT TYPES

# doc_principal

class DocPrincipal(Entity):
    """A qualified association between a doc and a principal.
    """
    available_dynamic_features = ["audit", "version"]

class DocPrincipalAudit(Audit):
    """An audit record for a doc_principal record.
    """
    #!+label_attribute_name = "principal_id" #!+
    @property
    def label(self):
        dp = self.audit_head
        return "%s -> %s" % (
            dp.doc.title, IDCDescriptiveProperties(dp.principal).title)
    
    @property # !+StatusDocPrincipal
    def status(self):
        return self.audit_head.status


class GroupAssignment(DocPrincipal):
    """Association between a doc and a group it's been assigned to.
    """
    interface.implements(interfaces.IGroupAssignment)
    
    @property # !+StatusGroupAssignment
    def status(self):
        """Placeholder getter for workflow status."""
        return "_"

class UserSubscription(DocPrincipal):
    """The document a user is tracking.
    """

class UserEditing(DocPrincipal):
    """The legislative document that the user is currently being editing.
    """
    

# sitting, session

class Sitting(Entity):
    """Scheduled meeting for a group (chamber, committee, etc).
    """
    available_dynamic_features = ["audit", "version", "notification", "email"]
    # !+SITTING_AUDIT cannot support audit/version without a sitting_audit db table ?!
    interface.implements(
        interfaces.ISitting,
        interfaces.ITranslatable,
        interfaces.IScheduleContent,
        interfaces.ISerializable
    )
    attendance = one2many("attendance",
        "bungeni.models.domain.SittingAttendanceContainer", "sitting_id")
    items = one2many("items",
        "bungeni.models.domain.ItemScheduleContainer", "sitting_id")
    sreports = one2many("sreports",
        "bungeni.models.domain.SittingReportContainer", "sitting_id")

    @property
    def duration(self):
        return IDCDescriptiveProperties(self).duration

class SittingAttendance(Entity):
    """A record of attendance at a meeting.
    """
    interface.implements(
        interfaces.ISittingAttendance,
    )

class Session(Entity):
    interface.implements(
        interfaces.ISession,
        interfaces.ITranslatable,
        interfaces.IScheduleContent
    )
    
    sittings = one2many("sittings",
        "bungeni.models.domain.SittingContainer", "session_id",
        [("group_id", "chamber_id")]
    )
    
    @property
    def group_id(self):
        return self.chamber_id


class Heading(Entity):
    """A heading in a report.
    """
    interface.implements(
        interfaces.IHeading,
        interfaces.IScheduleText,
        interfaces.IScheduleContent,
        interfaces.ITranslatable, 
    )
    
    type = "heading"
    
    @property
    def status_date(self):
        return None


class Report(Doc):
    """Agendas and minutes.
    """
    available_dynamic_features = ["audit", "version", "download",
        "notification", "email"]
    interface.implements(
        interfaces.IReport,
        interfaces.ITranslatable,
    )

class SittingReport(Entity):
    """Which reports are created for this sitting.
    """
    from bungeni.feature.interfaces import IFeatureDownload
    interface.implements(
        interfaces.ISittingReport,
        interfaces.IOwned,
        interfaces.IBungeniContent,
        IFeatureDownload, # !+not worklfowed
    )
    
    def __getattr__(self, name):
        """Look up values in either report or sitting"""
        try:
            return super(SittingReport, self).__getattr__(name)
        except AttributeError:
            try:
                return object.__getattribute__(self.report, name)
            except AttributeError:
                return object.__getattribute__(self.sitting, name)


# address

class Address(HeadParentedMixin, Entity):
    """Address base class
    !+ note corresponding tbls exist only for subclasses
    """
    available_dynamic_features = []
    interface.implements(interfaces.IAddress)
    
    def on_create(self):
        """Application-internal creation logic i.e. logic NOT subject to config.
        """
        # requires self db id to have been updated
        from bungeni.core.workflows import utils
        utils.assign_ownership(self)

# !+ADDRESS get rid of these two classes, just use Address?
class UserAddress(Address):
    """User address (personal)
    """
    interface.implements(interfaces.IUserAddress)
class GroupAddress(Address):
    """Group address (official)
    """
    interface.implements(interfaces.IGroupAddress)



# attachment

class Attachment(HeadParentedMixin, Entity):
    """A file attachment to a document. 
    """
    available_dynamic_features = ["audit", "version", "notification",
        "email"]
    interface.implements(
        interfaces.IDrafted,
        interfaces.IAttachment,
    )
    
    ''' !+PrincipalRoleMap attachments have a "drafter" but not an "owner"
    @property # !+OWNERSHIP
    def owner(self):
        from bungeni.models import utils # !+domain should not depend on utils
        return utils.get_owner_for_context(self)
    '''
    
    def on_create(self):
        """Application-internal creation logic i.e. logic NOT subject to config.
        """
        # requires self db id to have been updated
        from bungeni.core.workflows import utils
        utils.assign_ownership(self)

class AttachmentAudit(Audit):
    """An audit record for an attachment.
    """
    label_attribute_name = "title"

class AttachmentVersion(Version):
    """A version of an attachment.
    """
    #!+STRING_KEY
    def string_key(self):
        """A more useful string key for version instances, independent of db 
        PK identity but still uniquely identifies the attachment version 
        instance; for use in container listings (bubbles up to public URL).
        """
        return "obj-%s-%s" % (self.audit.attachment_id, self.seq)


# signatory

class Signatory(Entity):
    """Signatory for a Bill or Motion or other doc.
    """
    available_dynamic_features = ["audit", "version", "notification", "email"]
    interface.implements(
        interfaces.IOwned,
        interfaces.IBungeniContent,
        interfaces.ISignatory,
    )
    
    # !+ORM
    #@property
    #def owner(self):
    #    return self.user
    
    def on_create(self):
        from bungeni.core.workflows import utils
        utils.assign_ownership(self)
        signatory_feature = self.head.signatory_feature
        if (signatory_feature.document_submitted(self.head) or 
                signatory_feature.auto_sign(self.head)
            ):
            utils.set_role("bungeni.Signatory", self.user.login, self.head)
    
    @property
    def party(self):
        return self.member.party

class SignatoryAudit(Audit):
    """An audit record for a signatory.
    """
    label_attribute_name = None
    @property
    def label(self):
        return self.user.combined_name
    description = label
    
    @property
    def user(self):
        return self.audit_head.user


# other sys/support types

class Country(Entity):
    """Country.
    """
    interface.implements(
        interfaces.ICountry,
    )


class EditorialNote(Entity):
    """Arbitrary text inserted into schedule
    """
    type = u"editorial_note"
    interface.implements(
        interfaces.IEditorialNote,
        interfaces.IScheduleText,
        interfaces.IScheduleContent,
        interfaces.ITranslatable,
    )

class AgendaTextRecord(Entity):
    """Arbitrary text inserted into schedule
    """
    type = u"agenda_text_record"
    interface.implements(
        interfaces.IAgendaTextRecord,
        interfaces.IScheduleText,
        interfaces.ITranslatable,
    )


class ItemSchedule(Entity):
    """For which sitting was a parliamentary item scheduled.
    """
    interface.implements(
        interfaces.IItemSchedule,
    )
    discussions = one2many("discussions",
        "bungeni.models.domain.ItemScheduleDiscussionContainer", "schedule_id")
    votes = one2many("votes",
        "bungeni.models.domain.ItemScheduleVoteContainer", "schedule_id")
    
    def get_item_domain(self):
        if self.item_type is None:
            return # no item set
        from bungeni.capi import capi
        return capi.get_type_info(self.item_type).domain_model
    
    def item():
        doc = "Related (schdulable) item, via item_type and item_id. " \
            "Currently may be of (doc, heading, editorial_note) type."
        def fget(self):
            "Query for scheduled item by type and ORM mapped primary key."
            domain_class = self.get_item_domain()
            if domain_class is None:
                return None
            schedule_item = alchemist.Session().query(domain_class).get(self.item_id)
            schedule_item.__parent__ = self
            return schedule_item
        def fset(self, schedule_item):
            # !+object_id/object_type - use object_id/object_type as elsewhere
            self.item_id = get_mapped_object_id(schedule_item)
            self.item_type = schedule_item.type
        def fdel(self):
            raise NotImplementedError
        return locals()
    item = property(**item())
    
    # !+IDCDP(ob).title should probably be the default/fallback for all 
    # "labels" used to refer to the ob e.g. in listings. 
    # Then, the 2 props below ca be reduced to just @owner (and reuse @item defined above)
    @property
    def item_title(self):
        if interfaces.IScheduleText.providedBy(self.item):
            return self.item.text
        return IDCDescriptiveProperties(self.item).title
    @property
    def item_mover(self): # !+ item_owner_title
        # currently item may be (doc, heading, editorial_note) of which 
        # only doc has an "owner" attribute.
        schedule_item = self.item
        if hasattr(schedule_item, "owner"):
            return IDCDescriptiveProperties(schedule_item.owner).title
    @property
    def item_uri(self):
        return IDCDescriptiveProperties(self.item).uri

    @property
    def is_type_text_record(self):
        return self.get_item_domain() == AgendaTextRecord

    @property
    def type_heading(self):
        if self.get_item_domain() == AgendaTextRecord:
            return Heading.type == self.item.record_type
        return False
    
    @property
    def real_item_type(self):
        if self.get_item_domain() == AgendaTextRecord:
            return self.item.record_type
        return self.item_type
    
    @property
    def type_document(self):
        return not self.type_heading


class ItemScheduleDiscussion(Entity):
    """A discussion on a scheduled item.
    """
    interface.implements(
        interfaces.IItemScheduleDiscussion,
        interfaces.ITranslatable,
    )

class ItemScheduleVote(Entity):
    """Vote records on a scheduled item
    """
    interface.implements(interfaces.IItemScheduleVote)

    # file download
    @property
    def data(self):
        return self.roll_call
    
    # file download
    def name(self):
        return "vote-record-%d.xml" % self.vote_id


class Holiday(object):
    """Is this day a holiday?
    if a date in in the table it is otherwise not
    """


''' !+BookedResources
class Resource (object):
    """A Resource that can be assigned to a sitting.
    """

class ResourceBooking (object):
    """Assign a resource to a sitting.
    """
class ResourceType(object):
    """A Type of resource.
    """
'''

class Venue(Entity):
    """A venue for a sitting.
    """
    interface.implements(interfaces.ITranslatable, interfaces.IVenue,
        interfaces.IScheduleContent
    )


class FieldTranslation(object):
    """Get the field/attribute translations for an Entity instance.
    """

class TimeBasedNotication(Entity):
    """Time based Notifications
    """


# debate record

# !+NO_DESCRIPTOR
class DebateRecord(Entity):
    """Debate record object associated with a sitting
    """
    available_dynamic_features = ["audit", "version", "workspace", 
        "notification", "email", "user_assignment"]
    interface.implements(interfaces.IDebateRecord)
    media = one2many("media",
        "bungeni.models.domain.DebateMediaContainer", "debate_record_id")
    takes = one2many("takes",
        "bungeni.models.domain.DebateTakeContainer", "debate_record_id")
    type = "debate_record"

class DebateRecordItem(Entity):
    """Items that may be included in a debate record
    """
    interface.implements(interfaces.IDebateRecordItem)

class DebateDoc(DebateRecordItem):
    """A document that is discussed during a sitting
    """
    interface.implements(interfaces.IDebateDoc)
    available_dynamic_features = ["audit", "version"]

class DebateSpeech(DebateRecordItem):
    """A single speech in a debate record
    """
    available_dynamic_features = ["audit", "version"]
    interface.implements(interfaces.ITranslatable, interfaces.IDebateSpeech)

class DebateMedia(Entity):
    """Media files of a sitting
    """
    interface.implements(interfaces.IDebateMedia)

class DebateTake(Entity):
    """Debate takes
    """
    interface.implements(interfaces.IDebateTake)


# oauth

class OAuthApplication(Entity):
    """OAuth application registration
    """
    interface.implements(interfaces.IOAuthApplication)

class OAuthAuthorization(Entity):
    """OAuth authorization records
    """
    interface.implements(interfaces.IOAuthAuthorization)

class OAuthAuthorizationToken(Entity):
    """OAuth authorization tokens
    """
    interface.implements(interfaces.IOAuthAuthorizationToken)

class OAuthAccessToken(Entity):
    """OAuth access token
    """
    interface.implements(interfaces.IOAuthAccessToken)


# !+CUSTOM

class Chamber(Group):
    """A chamber in parliament.
    """
    interface.implements(interfaces.IChamber)

# legislature
# !+LEGISLATURE_AS_CHAMBER
class Legislature(Chamber):
    """The conceptual "parliament" singleton, that may be composed of one or 
    two chambers. 
    
    There must be only one legislature (active group) defined in the system.
    
    Always use the bungeni.capi.capi.legislature property to retrieve the same 
    Legislature singleton instance from anywhere in the application.
    """
    _instance = None
    def __new__(cls, *args, **kw):
        if not cls._instance:
            cls._instance = super(Legislature, cls).__new__(cls, *args, **kw)
        return cls._instance
    interface.implements(interfaces.ILegislature)


class Member(GroupMember):
    """Member of a Chamber i.e. of "Parliament")
    """
    interface.implements(interfaces.IMember)

# !+/CUSTOM

