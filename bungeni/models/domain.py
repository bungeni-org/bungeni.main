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
import ore.xapian.interfaces
from bungeni import alchemist
from bungeni.alchemist.traversal import one2many, one2manyindirect
import sqlalchemy.sql.expression as sql
from sqlalchemy.orm import object_mapper

from bungeni.models import interfaces


def object_hierarchy_type(object):
    if isinstance(object, User):
        return "user"
    if isinstance(object, Group):
        return "group"
    if isinstance(object, Doc):
        return "doc"
    return ""


CHANGE_ACTIONS = ("add", "modify", "workflow", "remove", "version")

def assert_valid_change_action(action):
    assert action in CHANGE_ACTIONS, \
        "Invalid audit action: %s. Must be one of: %s" % (
            action, CHANGE_ACTIONS)

def get_changes(auditable, *actions):
    """Get changelog for auditable context, filtered for actions.
    """
    for action in actions:
        assert_valid_change_action(action)
    # lazy loading - merge to avoid sqlalchemy.orm.exc.DetachedInstanceError
    auditable = alchemist.Session().merge(auditable)
    return [ c for c in auditable.changes if c.action in actions ]

def get_audit_table_name(kls):
    return "%s_audit" % (alchemist.utils.get_local_table(kls).name)

def get_mapped_object_id(ob):
    # !+ASSUMPTION_SINGLE_COLUMN_PK(mr, may-2012)
    return object_mapper(ob).primary_key_from_instance(ob)[0]

#

class HeadParentedMixin(object):
    """For sub-objects of a "head" object.
    
    Changes the behaviour of __parent__ to by default return the head object 
    UNLESS a non-None __parent__ is hard-set explicitly set on the sub-instance
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
            log.debug("Failed table schema lookup for %s: %s: %s" % (
                type(self), type(e).__name__, e))
            known_names = None
        
        for k, v in kw.items():
            if known_names is None or k in known_names:
                setattr(self, k, v)
            else:
                log.error(
                    "Invalid attribute on %s %s" % (
                        self.__class__.__name__, k))
    
    def on_create(self):
        """Hook to call on creation of an instance, to handle any business 
        setup/logic that the application MUST (i.e. not subject to any user
        configuration) take care of.
        """
        pass
    
    @property
    def pk(self):
        """ () -> [(pk_name, pk_value)] -- intended primarily as debug utility.
        """
        return [ (c.name, getattr(self, c.name))
             for c in object_mapper(self).primary_key ]


class User(Entity):
    """Domain Object For A User. General representation of a person.
    """
    available_dynamic_features = ["address"]
    
    interface.implements(interfaces.IBungeniUser, interfaces.ITranslatable)
    
    def __init__(self, login=None, **kw):
        if login:
            self.login = login
        super(User, self).__init__(**kw)
        self.salt = self._makeSalt()

    def _makeSalt(self):
        return "".join(random.sample(string.letters[:52], 12))

    def setPassword(self, password):
        self.password = self.encode(password)

    def getPassword(self):
        return None

    def encode(self, password):
        return md5.md5(password + self.salt).hexdigest()

    def checkPassword(self, password_attempt):
        attempt = self.encode(password_attempt)
        return attempt == self.password

    def _get_status(self):
        return self.active_p
    def _set_status(self, value):
        self.active_p = value
    status = property(_get_status, _set_status)
    
    # !+FULLNAME(mr, jul-2012) inconsistent naming
    @property
    def fullname(self):
        if not self.middle_name:
            return "%s %s" % (self.first_name, self.last_name)
        return "%s %s %s" % (self.first_name, self.middle_name, self.last_name)
    
    delegations = one2many("delegations",
        "bungeni.models.domain.UserDelegationContainer", "user_id")
    _password = property(getPassword, setPassword)


class AdminUser(Entity):
    """An admin user"""

class UserDelegation(Entity):
    """Delgate rights to act on behalf of a user to another user .
    """
    interface.implements(interfaces.IUserDelegation)

class CurrentlyEditingDocument(object):
    """The document (parliamentary item) 
    that the user is currently being editing"""
    
class PasswordRestoreLink(object):
    """Object containing hash and expiration date for
    password restoration form"""
    
    def expired(self):
        return self.expiration_date < datetime.datetime.now() 

class UserSubscription(Entity):
    """The documents a user is tracking"""


######

class Group(Entity):
    """An abstract collection of users.
    """
    available_dynamic_features = ["address"]
    interface.implements(interfaces.IBungeniGroup, interfaces.ITranslatable)
    
    #users = one2many("users", 
    #   "bungeni.models.domain.GroupMembershipContainer", "group_id")
    #sittings = one2many("sittings", 
    #   "bungeni.models.domain.SittingContainer", "group_id")
    
    headings = one2many("headings", "bungeni.models.domain.HeadingContainer",
        "group_id"
    )
    editorial_notes = one2many("editorialnotes", 
        "bungeni.models.domain.EditorialNoteContainer",
        "group_id"
    )
    
    def on_create(self):
        """Application-internal creation logic i.e. logic NOT subject to config.
        """
        # requires self db id to have been updated
        from bungeni.core.workflows import utils
        utils.assign_role_owner_to_login(self)
        utils.unset_group_local_role(self)
    
    def active_membership(self, user_id):
        session = alchemist.Session()
        query = session.query(GroupMembership).filter(
            sql.and_(
                GroupMembership.group_id == self.group_id,
                GroupMembership.user_id == user_id,
                GroupMembership.active_p == True
            )
        )
        if query.count() == 0:
            return False
        else:
            return True


class GroupMembership(HeadParentedMixin, Entity):
    """A user's membership in a group-abstract basis for 
    ministers, committeemembers, etc.
    """
    available_dynamic_features = []
    interface.implements(
        interfaces.IBungeniGroupMembership, interfaces.ITranslatable)

    @property
    def image(self):
        return self.user.image


class OfficesHeld(Entity):
    """Offices held by this group member.
    """

class CommitteeStaff(GroupMembership):
    """Committee Staff.
    """
    interface.implements(interfaces.ICommitteeStaff)
    titles = one2many("titles",
        "bungeni.models.domain.MemberTitleContainer", "membership_id")
    subroles = one2many(
        "subroles", "bungeni.models.domain.GroupMembershipRoleContainer",
        "membership_id"
    )


class GroupMembershipRole(Entity):
    """Association between an group member and subroles
       that are granted when a document is assigned to a user
    """
    interface.implements(interfaces.IGroupMembershipRole)


class GroupDocumentAssignment(Entity):
    """Association between a doc and groups it's been assigned to
    """
    interface.implements(interfaces.IGroupDocumentAssignment)
    
    @property
    def status(self):
        """Placeholder getter for workflow status."""
        return "_"


# auditable (by default), but not a Doc
class Sitting(Entity):
    """Scheduled meeting for a group (parliament, committee, etc).
    """
    available_dynamic_features = ["audit", "version", "attachment",
        "notification", "email"]
    # !+SITTING_AUDIT cannot support audit/version without a sitting_audit db table ?!
    interface.implements(
        interfaces.ISitting,
        interfaces.ITranslatable,
    )
    attendance = one2many("attendance",
        "bungeni.models.domain.SittingAttendanceContainer", "sitting_id")
    items = one2many("items",
        "bungeni.models.domain.ItemScheduleContainer", "sitting_id")
    sreports = one2many("sreports",
        "bungeni.models.domain.SittingReportContainer", "sitting_id")

class SittingAttendance(Entity):
    """A record of attendance at a meeting .
    """
    interface.implements(
        interfaces.ISittingAttendance,
    )


#############

class Parliament(Group):
    """A parliament.
    """
    interface.implements(interfaces.IParliament)
    sessions = one2many("sessions",
        "bungeni.models.domain.SessionContainer", "parliament_id")
    committees = one2many("committees",
        "bungeni.models.domain.CommitteeContainer", "parent_group_id")
    governments = one2many("governments",
        "bungeni.models.domain.GovernmentContainer", "parent_group_id")
    parliamentmembers = one2many("parliamentmembers",
        "bungeni.models.domain.MemberOfParliamentContainer", "group_id")
    politicalgroups = one2many("politicalgroups",
        "bungeni.models.domain.PoliticalGroupContainer", "parent_group_id")
    sittings = one2many("sittings",
        "bungeni.models.domain.SittingContainer", "group_id")
    title_types = one2many("title_types",
        "bungeni.models.domain.TitleTypeContainer", "group_id")

class MemberOfParliament(GroupMembership):
    """Defined by groupmembership and additional data.
    """
    interface.implements(interfaces.IMemberOfParliament)
    titles = one2many("titles",
        "bungeni.models.domain.MemberTitleContainer", "membership_id")
    # !+MEMBER_ADDRESSES(mr, oct-2012) is it correct to assume that all 
    # user addresses are also "member" addresses?
    addresses = one2manyindirect("addresses", 
        "bungeni.models.domain.UserAddressContainer", "user_id")

class PoliticalGroup(Group):
    """A political group in a parliament.
    """
    interface.implements(
        interfaces.IPoliticalGroup,
        interfaces.ITranslatable
    )
    group_members = one2many("group_members",
        "bungeni.models.domain.PoliticalGroupMemberContainer", "group_id")
    title_types = one2many("title_types",
        "bungeni.models.domain.TitleTypeContainer", "group_id")
class PoliticalGroupMember(GroupMembership):
    """Member of a political group, defined by its group membership.
    """
    interface.implements(
        interfaces.IPoliticalGroupMember,
    )
    titles = one2many("titles",
        "bungeni.models.domain.MemberTitleContainer", "membership_id")

class Government(Group):
    """A government.
    """
    interface.implements(
        interfaces.IGovernment,
    )
    ministries = one2many("ministries",
        "bungeni.models.domain.MinistryContainer", "parent_group_id")

class Ministry(Group):
    """A government ministry.
    """
    interface.implements(
        interfaces.IMinistry,
    )
    ministers = one2many("ministers",
        "bungeni.models.domain.MinisterContainer", "group_id")
    # !+MINISTRY_ID(mr, jun-2012) alchemist does not want target attribute to 
    # be a domain class property [ministry_id] so the property corresponding 
    # directly to the db table column [group_id] is used instead.
    questions = one2many("questions",
        "bungeni.models.domain.QuestionContainer", "group_id")
    # !+MINISTRY_ID
    bills = one2many("bills",
        "bungeni.models.domain.BillContainer", "group_id")
    title_types = one2many("title_types",
        "bungeni.models.domain.TitleTypeContainer", "group_id")
class Minister(GroupMembership):
    """A Minister defined by its user_group_membership in a ministry (group).
    """
    interface.implements(
        interfaces.IMinister,
    )
    titles = one2many("titles",
        "bungeni.models.domain.MemberTitleContainer", "membership_id")


class Committee(Group):
    """A parliamentary committee of MPs.
    """
    interface.implements(interfaces.ICommittee)
    # !+ManagedContainer(mr, oct-2010) why do all these Managed container 
    # attributes return a list of processed-id-derived strings instead of the 
    # list of actual objects in question? 
    # e.g. committee.committeemembers returns: ['obj-41', 'obj-42']
    #
    committeemembers = one2many("committeemembers",
        "bungeni.models.domain.CommitteeMemberContainer", "group_id")
    committeestaff = one2many("committeestaff",
        "bungeni.models.domain.CommitteeStaffContainer", "group_id")
    agendaitems = one2many("agendaitems",
        "bungeni.models.domain.AgendaItemContainer", "group_id")
    sittings = one2many("sittings",
        "bungeni.models.domain.SittingContainer", "group_id")
    title_types = one2many("title_types",
        "bungeni.models.domain.TitleTypeContainer", "group_id")

class CommitteeMember(GroupMembership):
    """A Member of a committee defined by its membership to a committee (group).
    """
    interface.implements(interfaces.ICommitteeMember)
    titles = one2many("titles",
        "bungeni.models.domain.MemberTitleContainer", "membership_id")

class Office(Group):
    """Parliamentary Office like speakers office, clerks office etc. 
    Internal only.
    """
    interface.implements(
        interfaces.IOffice,
    )
    officemembers = one2many("officemembers",
        "bungeni.models.domain.OfficeMemberContainer", "group_id")
    title_types = one2many("title_types",
        "bungeni.models.domain.TitleTypeContainer", "group_id")

class OfficeMember(GroupMembership):
    """Clerks, .... 
    """
    interface.implements(
        interfaces.IOfficeMember,
    )
    titles = one2many("titles",
        "bungeni.models.domain.MemberTitleContainer", "membership_id")
    subroles = one2many(
        "subroles", "bungeni.models.domain.GroupMembershipRoleContainer",
        "membership_id"
    )

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
        utils.assign_role_owner_to_login(self)

class UserAddress(Address):
    """User address (personal)
    """
    interface.implements(interfaces.IUserAddress)
class GroupAddress(Address):
    """Group address (official)
    """
    interface.implements(interfaces.IGroupAddress)


# extended attributes - vertical properties

# !+could use __metaclass__ but that causes internal breaks elsewhere...
# !+could be a class decorator 
def instrument_extended_properties(cls, object_type, from_class=None):
    # !+class not yet mapped
    #from sqlalchemy.orm import class_mapper
    #object_type = class_mapper(cls).local_table.name 
    if from_class is None:
        from_class = cls
    # ensure cls.__dict__.extended_properties
    cls.extended_properties = cls.extended_properties[:]
    for vp_name, vp_type in from_class.extended_properties:
        if (vp_name, vp_type) not in cls.extended_properties:
            cls.extended_properties.append((vp_name, vp_type))
        setattr(cls, vp_name, vertical_property(object_type, vp_name, vp_type))

def vertical_property(object_type, vp_name, vp_type, *args, **kw):
    """Get the external (non-SQLAlchemy) extended Vertical Property
    (on self.__class__) as a regular python property.
    
    !+ Any additional args/kw are exclusively for instantiation of vp_type.
    """
    _vp_name = "_vp_%s" % (vp_name) # name for SA mapper property for this
    doc = "VerticalProperty %s of type %s" % (vp_name, vp_type)
    def fget(self):
        vp = getattr(self, _vp_name, None)
        if vp is not None:
            return vp.value
    def fset(self, value):
        vp = getattr(self, _vp_name, None)
        if vp is not None:
            vp.value = value
        else:
            vp = vp_type(self, object_type, vp_name, value, *args, **kw)
            setattr(self, _vp_name, vp)
    def fdel(self):
        setattr(self, _vp_name, None)
    return property(fget=fget, fset=fset, fdel=fdel, doc=doc)

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


class Doc(Entity):
    """Base class for a workflowed parliamentary document.
    """
    # allowed dynamic features by this archetype (inherited by sub-types)
    available_dynamic_features = ["audit", "version", "attachment", "event",
        "signatory", "schedule", "workspace", "notification",
        "email", "download", "user_assignment", "group_assignment"]
    interface.implements(
        interfaces.IBungeniContent,  # IOwned
        interfaces.IDoc,
        interfaces.ITranslatable
    )
    
    def on_create(self):
        """Application-internal creation logic i.e. logic NOT subject to config.
        """
        # requires self db id to have been updated
        from bungeni.core.workflows import utils
        utils.assign_role_owner_to_login(self)
        # !+utils.setParliamentId(self)
    
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
    
    @property
    def submission_date(self):
        # As base meaning of "submission_date" we take the most recent date
        # of workflow transition to "submit" to clerk. Subclasses may need
        # to overload as appropriate for their respective workflows.
        return self._get_workflow_date("submitted")
    
    extended_properties = [
    ]
#instrument_extended_properties(Doc, "doc")


class AdmissibleMixin(object):
    """Assumes self._get_workflow_date().
    """
    @property
    def admissible_date(self):
        return self._get_workflow_date("admissible")


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
        changes = get_changes(self.head, *CHANGE_ACTIONS)
        for c in changes[1 + changes.index(self):]:
            return c
    
    # change "note" -- as external extended attribute (vertical property) as:
    # a) presumably it may have to be translatable, and the initial language 
    #    may not be the same as that of the head object being audited.
    # b) it will be set very seldom.
    extended_properties = [
        ("note", vp.TranslatedText)
    ]
instrument_extended_properties(Change, "change")

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
    
    Behaves somewhat like a combined Change and Audit record, as this will 
    automatically try to resolve additional attrs off self.audit before failing.
    """
    interface.implements(
        interfaces.IVersion,
    )
    
    @property
    def __name__(self):
        return "ver-%s" % (self.seq)
    
    # !+ should only be when type(self.head) is versionable
    # !+ other features?
    files = one2many("files",
        "bungeni.models.domain.AttachmentContainer", "head_id")
    
    def __getattr__(self, name):
        """Try to pick any attribute (not found on this change record--this 
        method only gets called when a nonexistent attribute is accessed) off 
        the related audit snapshot record (as every change record is related 
        to a type-dedicated audit record).

        !+ should this be on Change i.e. for all change actions?
        !+ possible issue with attribute hiding, if an type has a 
           same-named property as one in in Change type/table, then that one
           will always be retrieved first (and so the one on the related
           Audit type/table will be unreachable in this way).
        """
        try:
            return getattr(self.audit, name)
        except AttributeError:
            # !+SA_INCORRECT_TYPE_DEBUG strangely, sometimes the type of 
            # (this change's) self.audit that sqlalchemy returns does not 
            # correspond to self.head...
            audit_id = self.audit_id
            def get_correctly_typed_change(change):
                for v in change.head.versions:
                    if v.audit_id == audit_id:
                        return v
            correctly_typed_change = get_correctly_typed_change(self)
            if correctly_typed_change and correctly_typed_change is not self:
                print ("*** %s.%s head/id=%s/%s, audit/id=%s/%s \n"
                    "    SA INCORRECT TYPE:%s \n"
                    "    SHOULD HAVE BEEN:%s" % (
                        type(self).__name__, name, 
                        self.head, self.head_id, 
                        self.audit, audit_id, 
                        self, correctly_typed_change))
            # !+/SA_INCORRECT_TYPE_DEBUG
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
        auditable_pk_column = [ c for c in 
            alchemist.utils.get_local_table(auditable_cls).primary_key ][0]
        factory = type(audit_factory_name, (cls,), {
            "head_id_column_name": auditable_pk_column.name })
        # define a subtype of Audit type
        audit_table_name = get_audit_table_name(auditable_cls)
        # Extended properties from cls are inherited... but need to propagate 
        # onto audit_kls any extended properties defined by auditable_cls:
        instrument_extended_properties(factory, audit_table_name, 
            from_class=auditable_cls)
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

class DocAudit(Audit):
    """An audit record for a document.
    """
    label_attribute_name = "title"
    extended_properties = [
    ]
#instrument_extended_properties(DocAudit, "doc_audit")

class DocVersion(Version):
    """A version of a document.
    """
    files = one2many("files",
        "bungeni.models.domain.AttachmentVersionContainer", "head_id")
    #!+eventable items supporting feature "event":
    #events = one2many("events",
    #    "bungeni.models.domain.DocVersionContainer", "head_id")
    
    submission_date = None # !+bypass error when loading a doc version view
    # !+ proper logic of this would have to be the value of 
    # self.head.submission_date at the time of *this* version!
    

class AgendaItem(AdmissibleMixin, Doc):
    """Generic Agenda Item that can be scheduled on a sitting.
    """
    interface.implements(
        interfaces.IBungeniParliamentaryContent,
        interfaces.IAgendaItem,
    )
#AgendaItemAudit

class Bill(Doc):
    """Bill domain type.
    """
    interface.implements(
        interfaces.IBungeniParliamentaryContent,
        interfaces.IBill,
    )
    
    #!+doc_type: default="government", nullable=False,
    
    # !+BILL_MINISTRY(fz, oct-2011) the ministry field here logically means the 
    # bill is presented by the Ministry and so... Ministry should be the author,
    # not a "field" 
    # !+MINISTRY_ID
    def ministry_id():
        doc = "Related group must be a ministry."
        def fget(self):
            return self.group_id
        def fset(self, ministry_id):
            # !+validate ministry group constraint
            self.group_id = ministry_id
        def fdel(self):
            self.group_id = None
        return locals()
    ministry_id = property(**ministry_id())
    
    @property
    def publication_date(self):
        return self._get_workflow_date("gazetted")
    
    extended_properties = [
        #("short_title", vp.TranslatedText),
    ]
#instrument_extended_properties(Bill, "doc")
#BillAudit

class Motion(AdmissibleMixin, Doc):
    """Motion domain type.
    """
    interface.implements(
        interfaces.IBungeniParliamentaryContent,
        interfaces.IMotion,
    )
    
    @property
    def notice_date(self):
        return self._get_workflow_date("scheduled")
#MotionAudit



class Question(AdmissibleMixin, Doc):
    """Question domain type.
    """
    interface.implements(
        interfaces.IBungeniParliamentaryContent,
        interfaces.IQuestion,
    )
    
    #!+doc_type: default="ordinary", nullable=False,
    #!+response_type: default="oral", nullable=False,
    
    # !+MINISTRY_ID
    def ministry_id():
        doc = "Related group must be a ministry."
        def fget(self):
            return self.group_id
        def fset(self, ministry_id):
            # !+validate ministry group constraint
            self.group_id = ministry_id
        def fdel(self):
            self.group_id = None
        return locals()
    ministry_id = property(**ministry_id())
    
    @property
    def ministry_submit_date(self):
        return self._get_workflow_date("response_pending")
    
    extended_properties = [
        #("response_type", vp.Text),
        #("response_text", vp.TranslatedText),
    ]
#instrument_extended_properties(Question, "doc")
#QuestionAudit

class TabledDocument(AdmissibleMixin, Doc):
    """Tabled document: captures metadata about the document (owner, date, 
    title, description) and can have multiple physical documents attached.
    
    The tabled documents form should have the following:
    - Document title
    - Document link
    - Upload field (s)
    - Document source  / author agency (who is providing the document)
      (=> new table agencies)
    
    - Document submitter (who is submitting the document)
      (a person -> normally mp can be other user)
    
    It must be possible to schedule a tabled document for a sitting.
    """
    interface.implements(
        interfaces.IBungeniParliamentaryContent,
        interfaces.ITabledDocument,
    )
#TabledDocumentAudit


class Event(HeadParentedMixin, Doc):
    """Base class for an event on a document.
    """
    #!+parliament_id is (has always been) left null for events, how best to 
    # handle this, possible related constraint e.g. head_id must NOT be null, 
    # validation, ... ?
    available_dynamic_features = ["audit", "version", "attachment",
        "notification", "email"]
    interface.implements(
        interfaces.IEvent,
    )
    
    #!+delete submission_date
    
    @property
    def event_date(self):
        # !+ should this be when first added? if in a "attached" state, the 
        # latest of these (what is returned here) ? if in "internal"??
        return self._get_workflow_date("attached")
#EventAudit


class Attachment(HeadParentedMixin, Entity):
    """A file attachment to a document. 
    """
    available_dynamic_features = ["audit", "version", "notification",
        "email"]
    interface.implements(
        interfaces.IAttachment, # IOwned
        ore.xapian.interfaces.IIndexable, # !+bungeni_custom
    )
    
    @property # !+OWNERSHIP
    def owner(self):
        from bungeni.models import utils # !+domain should not depend on utils
        principal_id = utils.get_prm_owner_principal_id(self)
        return utils.get_user_for_principal_id(principal_id)

    def on_create(self):
        """Application-internal creation logic i.e. logic NOT subject to config.
        """
        # requires self db id to have been updated
        from bungeni.core.workflows import utils
        utils.assign_role_owner_to_login(self)

class AttachmentAudit(Audit):
    """An audit record for an attachment.
    """
    label_attribute_name = "title"

class AttachmentVersion(Version):
    """A version of an attachment.
    """

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

# auditable (by default), but not a Doc
class Signatory(Entity):
    """Signatory for a Bill or Motion or other doc.
    """
    available_dynamic_features = ["audit", "version", "attachment",
        "notification", "email"]
    interface.implements(
        interfaces.IBungeniContent, # IOwned
        interfaces.ISignatory,
    )
    
    @property
    def owner(self):
        return self.user
        
    @property
    def party(self):
        return self.member.party

class SignatoryAudit(Audit):
    """An audit record for a signatory.
    """
    label_attribute_name = None
    @property
    def label(self):
        return self.user.fullname
    description = label
    
    @property
    def user(self):
        return self.audit_head.user

#############

class Session(Entity):
    """
    """
    interface.implements(
        interfaces.ISession,
        interfaces.ITranslatable,
        interfaces.IScheduleContent
    )

''' !+SUBSCRIPTIONS(mr, jun-2012) unused
class ObjectSubscriptions(object):
    """
    """
'''

# ###############

class Country(Entity):
    """Country.
    """
    interface.implements(
        interfaces.ICountry,
    )


# ##########

class TitleType(Entity):
    """Types of titles in groups
    """
    interface.implements(interfaces.ITitleType, interfaces.ITranslatable)


class MemberTitle(Entity):
    """The role title a member has in a specific context and one 
    official address for a official role.
    """
    interface.implements(
        interfaces.IMemberTitle,
        interfaces.ITranslatable
    )


class MinistryInParliament(object):
    """Auxilliary class to get the parliament and government for a ministry.
    """


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


class ItemSchedule(Entity):
    """For which sitting was a parliamentary item scheduled.
    """
    interface.implements(
        interfaces.IItemSchedule,
    )
    discussions = one2many("discussions",
        "bungeni.models.domain.ItemScheduleDiscussionContainer", "schedule_id")
    
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
    def type_heading(self):
        return self.get_item_domain() == Heading
    
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
    interface.implements(
        interfaces.ISittingReport,
    )
    
    def __getattr__(self, name):
        """Look up values in either report or sitting"""
        try:
            return super(SittingReport, self).__getattr__(name)
        except AttributeError:
            try:
                return getattr(self.report, name)
            except AttributeError:
                return getattr(self.sitting, name)

class ObjectTranslation(object):
    """Get the translations for an Object.
    """

class TimeBasedNotication(Entity):
    """Time based Notifications
    """
