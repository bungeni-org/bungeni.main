# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Vocabulary definitions
"""

log = __import__("logging").getLogger("bungeni.ui.vocabulary")

import os
import datetime
import hashlib
from lxml import etree

from zope import interface
from zope.schema.interfaces import IContextSourceBinder
from zope.schema import vocabulary
from zope.security.proxy import removeSecurityProxy
from zope.app.container.interfaces import IContainer
from zope.schema.interfaces import IVocabularyFactory
from zope.component import getUtility
from zope.i18n import translate
from zope.component import getUtilitiesFor
from zope.securitypolicy.interfaces import IRole
from i18n import _

from sqlalchemy.orm import mapper
import sqlalchemy as rdb
import sqlalchemy.sql.expression as sql

import bungeni.alchemist.vocabulary
from bungeni.utils.capi import capi
from bungeni.alchemist import Session
from bungeni.alchemist.container import valueKey

from bungeni.models.interfaces import ISubRoleAnnotations
from bungeni.models.interfaces import IBungeniGroup
from bungeni.models import schema, domain, utils, delegation
from bungeni.models.interfaces import (ITranslatable, ISignatory,)

from bungeni.core.translation import translate_obj
from bungeni.core.language import get_default_language
from bungeni.core.dc import IDCDescriptiveProperties
from bungeni.core.workflows.utils import get_group_local_role
from bungeni.core.workflows import adapters

from bungeni.ui.calendar.utils import first_nth_weekday_of_month
from bungeni.ui.calendar.utils import nth_day_of_month
from bungeni.ui.calendar.utils import nth_day_of_week
from bungeni.ui.utils import common
from bungeni.ui.interfaces import ITreeVocabulary
from bungeni.ui.reporting.generators import BUNGENI_REPORTS_NS

try:
    import json
except ImportError:
    import simplejson as json
import imsvdex.vdex


def get_translated_group_label(group):
    """Get a translated display text to refer to the group.
    """
    g = translate_obj(group)
    return "%s - %s" % (g.short_name, g.full_name)


days = [ _('day_%d' % index, default=default) for (index, default) in
         enumerate((u"Mon", u"Tue", u"Wed", u"Thu", u"Fri", u"Sat", u"Sun")) ]


def assignable_state_ids():
    _sids = set()
    for name, ti in adapters.TYPE_REGISTRY:
        wf = ti.workflow
        _sids.update(wf.get_state_ids(
                not_tagged=["private", "fail", "terminal"], restrict=False))
    return _sids
_assignable_state_ids = set(assignable_state_ids())


class WeekdaysVocabulary(object):
    interface.implements(IVocabularyFactory)
    
    def __call__(self, context):
        return vocabulary.SimpleVocabulary([
            vocabulary.SimpleTerm(nth_day_of_week(index), str(index), msg)
            for (index, msg) in enumerate(days)
        ])
WeekdaysVocabularyFactory = WeekdaysVocabulary()


class MonthlyRecurrenceVocabulary(object):
    """This vocabulary provides an option to choose between different
    modes of monthly recurrence.

    Vocabulary values are methods which take a date and generate
    future dates.
    """
    
    interface.implements(IVocabularyFactory)

    def __call__(self, context):
        today = datetime.date.today()
        weekday = today.weekday()
        day = today.day

        return vocabulary.SimpleVocabulary(
            (vocabulary.SimpleTerm(
                nth_day_of_month(day),
                "day_%d_of_every_month" % day,
                _(u"Day $number of every month", mapping={'number': day})),
             vocabulary.SimpleTerm(
                 first_nth_weekday_of_month(weekday),
                 "first_%s_of_every_month" % today.strftime("%a"),
                 _(u"First $day of every month", mapping={'day': translate(
                     today.strftime("%A"))})),
        ))
                
MonthlyRecurrenceVocabularyFactory = MonthlyRecurrenceVocabulary()

# you have to add title_field to the vocabulary as only this gets 
# translated, the token_field will NOT get translated
Gender = vocabulary.SimpleVocabulary([
    vocabulary.SimpleTerm('M', _(u"Male"), _(u"Male")), 
    vocabulary.SimpleTerm('F', _(u"Female"), _(u"Female"))
])
#ElectedNominated = vocabulary.SimpleVocabulary([
#    vocabulary.SimpleTerm('E', _(u"elected"), _(u"elected")),
#    vocabulary.SimpleTerm('N', _(u"nominated"), _(u"nominated")), 
#    vocabulary.SimpleTerm('O', _(u"ex officio"), _(u"ex officio"))
#])
InActiveDead = vocabulary.SimpleVocabulary([
    vocabulary.SimpleTerm('A', _(u"active"), _(u"active")),
    vocabulary.SimpleTerm('I', _(u"inactive"), _(u"inactive")),
    vocabulary.SimpleTerm('D', _(u"deceased"),  _(u"deceased"))
])
ISResponse = vocabulary.SimpleVocabulary([
    vocabulary.SimpleTerm('I', _(u"initial"), _(u"initial")),
    vocabulary.SimpleTerm('S', _(u"subsequent"), _(u"subsequent"))
])
YesNoSource = vocabulary.SimpleVocabulary([
    vocabulary.SimpleTerm(True, _(u"Yes"), _(u"Yes")), 
    vocabulary.SimpleTerm(False, _(u"No"), _(u"No"))])
#AddressPostalType = vocabulary.SimpleVocabulary([
#    vocabulary.SimpleTerm("P", _(u"P.O. Box"), _(u"P.O. Box")),
#    vocabulary.SimpleTerm("S", _(u"Street / Physical"), 
#        _(u"Street / Physical")),
#    vocabulary.SimpleTerm("M", _(u"Military"), _(u"Military")),
#    vocabulary.SimpleTerm("U", _(u"Undefined / Unknown"), 
#        _(u"Undefined / Unknown")),
#])
#CommitteeStatusVocabulary = vocabulary.SimpleVocabulary([
#    vocabulary.SimpleTerm("P", _("permanent"), _("permanent")),
#    vocabulary.SimpleTerm("T", _("temporary"), _("temporary")),
#])


# types

# !+TYPES_CUSTOM - enum sources to move out to bungeni custom

bill_type = vocabulary.SimpleVocabulary([
    vocabulary.SimpleTerm("government", title="Government Initiative"),
    vocabulary.SimpleTerm("member", title="Member Initiative"),
])
committee_type = vocabulary.SimpleVocabulary([
    vocabulary.SimpleTerm("housekeeping", title="House Keeping"),
    vocabulary.SimpleTerm("departmental", title="Departmental"),
    vocabulary.SimpleTerm("adhoc", title="Ad Hoc"),
    vocabulary.SimpleTerm("watchdog", title="Watch Dog"),
    vocabulary.SimpleTerm("liaison", title="Liaison"),
])
committee_continuity = vocabulary.SimpleVocabulary([
    vocabulary.SimpleTerm("permanent", title="Permanent"),
    vocabulary.SimpleTerm("temporary", title="Temporary"),
])
logical_address_type = vocabulary.SimpleVocabulary([
    vocabulary.SimpleTerm("office", title="Office"),
    vocabulary.SimpleTerm("home", title="Home"),
    vocabulary.SimpleTerm("other", title="Other"),
])
postal_address_type = vocabulary.SimpleVocabulary([
    vocabulary.SimpleTerm("street", title="Street/Physical"),
    vocabulary.SimpleTerm("pobox", title="P.O. Box"),
    vocabulary.SimpleTerm("military", title="Military"),
    vocabulary.SimpleTerm("unknown", title="Undefined/Unknown"),
])
attachment_type = vocabulary.SimpleVocabulary([
    vocabulary.SimpleTerm("image", title="Image"),
    vocabulary.SimpleTerm("annex", title="Annex"),
    vocabulary.SimpleTerm("document", title="Document"),
    vocabulary.SimpleTerm("bill", title="Bill"),
    # !+ATTACHED_FILE_TYPE_SYSTEM(mr, oct-2011) ui/downloaddocument and 
    # ui/forms/files.py expects this, but should NOT be presented as an 
    # option in the UI?
    #vocabulary.SimpleTerm("system", title="System"),
])
attached_file_type = attachment_type # !+DOCUMENT
attendance_type = vocabulary.SimpleVocabulary([
    vocabulary.SimpleTerm("present", title="Present"),
    vocabulary.SimpleTerm("absence_justified", title="Absence justified"),
    vocabulary.SimpleTerm("absent", title="Absent"),
])
member_election_type = vocabulary.SimpleVocabulary([
    vocabulary.SimpleTerm("elected", title="Elected"),
    vocabulary.SimpleTerm("nominated", title="Nominated"),
    vocabulary.SimpleTerm("ex_officio", title="Ex officio"),
])
question_type = vocabulary.SimpleVocabulary([
    vocabulary.SimpleTerm("ordinary", title="Ordinary"),
    vocabulary.SimpleTerm("private_notice", title="Private notice"),
])
response_type = vocabulary.SimpleVocabulary([
    vocabulary.SimpleTerm("oral", title="Oral"),
    vocabulary.SimpleTerm("written", title="Written"),
])


class OfficeRoles(object):
    interface.implements(IVocabularyFactory)
    def __call__(self, context=None):
        app = common.get_application()
        terms = []
        roles = getUtilitiesFor(IRole, app)
        for name, role in roles:
            #Roles that must not be assigned to users in an office
            if name not in ["bungeni.Anonymous",
                            "bungeni.Authenticated",
                            "bungeni.Owner",
                            "zope.Manager",
                            "zope.Member",
                            "bungeni.MP",
                            "bungeni.Minister",
                            "bungeni.Admin",
                            ]:
                terms.append(vocabulary.SimpleTerm(name, name, name))
        return vocabulary.SimpleVocabulary(terms)

office_roles = OfficeRoles()

class GroupSubRoles(object):
    interface.implements(IVocabularyFactory)
    def __call__(self, context):
        terms = []
        while not IBungeniGroup.providedBy(context):
            context = context.__parent__
            if not context:
                raise NotImplementedError("Context does not implement IBungeniGroup")
        trusted = removeSecurityProxy(context)
        role = getUtility(IRole, get_group_local_role(trusted))
        for sub_role in ISubRoleAnnotations(role).sub_roles:
            print sub_role
            terms.append(vocabulary.SimpleTerm(sub_role, sub_role, sub_role))
        return vocabulary.SimpleVocabulary(terms)

group_sub_roles = GroupSubRoles()
        
class DatabaseSource(bungeni.alchemist.vocabulary.DatabaseSource):
    
    def __call__(self, context=None):
        query = self.constructQuery(context)
        results = query.all()
        terms = []
        title_field = self.title_field or self.token_field
        title_getter = self.title_getter or (lambda ob: getattr(ob, title_field))
        for ob in results:
            if ITranslatable.providedBy(ob):
                ob = translate_obj(ob)
            terms.append(vocabulary.SimpleTerm(
                    value = getattr(ob, self.value_field), 
                    token = getattr(ob, self.token_field),
                    title = title_getter(ob),
            ))
        return vocabulary.SimpleVocabulary(terms)

ParliamentSource = DatabaseSource(
    domain.Parliament, 'short_name', 'parliament_id',
    title_getter=lambda ob: "%s (%s-%s)" % (
        ob.full_name,
        ob.start_date and ob.start_date.strftime("%Y/%m/%d") or "?",
        ob.end_date and ob.end_date.strftime("%Y/%m/%d") or "?"))

class SpecializedSource(object):
    interface.implements(IContextSourceBinder)
    
    def __init__(self, token_field, title_field, value_field):
        self.token_field = token_field
        self.value_field = value_field
        self.title_field = title_field
    
    def _get_parliament_id(self, context):
        trusted = removeSecurityProxy(context)
        parliament_id = getattr(trusted, 'parliament_id', None)
        if parliament_id is None:
            if trusted.__parent__ is None:
                return None
            else:
                parliament_id = self._get_parliament_id(trusted.__parent__)
        return parliament_id
    
    def constructQuery(self, context):
        raise NotImplementedError("Must be implemented by subclass.")
    
    def __call__(self, context=None):
        query = self.constructQuery(context)
        results = query.all()
        terms = []
        title_field = self.title_field or self.token_field
        for ob in results:
            obj = translate_obj(ob)
            terms.append(vocabulary.SimpleTerm(
                    value = getattr(obj, self.value_field), 
                    token = getattr(obj, self.token_field),
                    title = getattr(obj, title_field),
            ))
        return vocabulary.SimpleVocabulary(terms)


class Venues(object):
    interface.implements(IVocabularyFactory)
    def constructQuery(self, context):
        session= Session()
        return session.query(domain.Venue)

    def __call__(self, context=None):
        query = self.constructQuery(context)
        results = query.all()
        terms = []
        for ob in results:
            terms.append(vocabulary.SimpleTerm(
                    value = ob.venue_id, 
                    token = ob.venue_id,
                    title = "%s" % IDCDescriptiveProperties(ob).title
                )
            )
        return vocabulary.SimpleVocabulary(terms)

venues_factory = Venues()

class SittingTypes(SpecializedSource):
    #domain.SittingType, "group_sitting_type", "group_sitting_type_id",
    #title_getter=lambda ob: "%s (%s-%s)" % (
    #    ob.group_sitting_type.capitalize(), ob.start_time, ob.end_time))

    def constructQuery(self, context):
        session= Session()
        return session.query(domain.GroupSittingType)

    def __call__(self, context=None):
        query = self.constructQuery(context)
        results = query.all()
        terms = []
        for ob in results:
            obj = translate_obj(ob)
            terms.append(vocabulary.SimpleTerm(
                    value = obj.group_sitting_type_id, 
                    token = obj.group_sitting_type,
                    title = "%s (%s-%s)" % (
                        obj.group_sitting_type, 
                        obj.start_time, 
                        obj.end_time),
                ))
        return vocabulary.SimpleVocabulary(terms)

class TitleTypes(SpecializedSource):
    def __init__(self):
        pass
        
    def constructQuery(self, context):
        session= Session()
        return session.query(domain.TitleType) \
                .filter(schema.title_types.c.group_id == context.group_id)

    def __call__(self, context=None):
        while not IBungeniGroup.providedBy(context):
            context = context.__parent__
            if not context:
                raise NotImplementedError("Context does not implement IBungeniGroup")
        query = self.constructQuery(context)
        results = query.all()
        terms = []
        for ob in results:
            obj = translate_obj(ob)
            terms.append(vocabulary.SimpleTerm(
                    value = obj.title_type_id, 
                    token = obj.title_type_id,
                    title = obj.title_name,
                ))
        return vocabulary.SimpleVocabulary(terms)


        
#XXX
#SittingTypeOnly = DatabaseSource(
#    domain.SittingType, 
#    title_field="group_sitting_type",
#    token_field="group_sitting_type_id",
#    value_field="group_sitting_type_id")


class MemberOfParliament(object):
    """ Member of Parliament = user join group membership join parliament"""
    
member_of_parliament = rdb.join(schema.user_group_memberships, 
    schema.users,
    schema.user_group_memberships.c.user_id == schema.users.c.user_id
).join(schema.parliaments, 
    schema.user_group_memberships.c.group_id == 
        schema.parliaments.c.parliament_id) 

mapper(MemberOfParliament, member_of_parliament)
        

class MemberOfParliamentImmutableSource(SpecializedSource):
    """If a user is already assigned to the context 
    the user will not be editable.
    """
    def __init__(self, value_field):
        self.value_field = value_field
    
    def constructQuery(self, context):
        session= Session()
        trusted=removeSecurityProxy(context)
        user_id = getattr(trusted, self.value_field, None)
        if user_id:
            query = session.query(domain.User
                ).filter(domain.User.user_id == user_id
                ).order_by(
                    domain.User.last_name,
                    domain.User.first_name,
                    domain.User.middle_name
                )
            return query
        else:
            parliament_id = self._get_parliament_id(trusted)
            if parliament_id:
                query = session.query(MemberOfParliament).filter(
                    sql.and_(MemberOfParliament.group_id ==
                            parliament_id,
                            MemberOfParliament.active_p == True)
                   ).order_by(MemberOfParliament.last_name,
                            MemberOfParliament.first_name,
                            MemberOfParliament.middle_name) 
            else:
                query = session.query(domain.User).order_by(
                            domain.User.last_name,
                            domain.User.first_name,
                            domain.User.middle_name)
        return query

    def __call__(self, context=None):
        query = self.constructQuery(context)
        results = query.all()
        terms = []
        for ob in results:
            terms.append(
                vocabulary.SimpleTerm(
                    value = getattr(ob, 'user_id'), 
                    token = getattr(ob, 'user_id'),
                    title = "%s %s" % (getattr(ob, 'first_name'),
                            getattr(ob, 'last_name'))
                ))
        user_id = getattr(context, self.value_field, None) 
        if user_id:
            if len(query.filter(schema.users.c.user_id == user_id).all()) == 0:
                # The user is not a member of this parliament. 
                # This should not happen in real life
                # but if we do not add it her the view form will 
                # throw an exception 
                session = Session()
                ob = session.query(domain.User).get(user_id)
                terms.append(vocabulary.SimpleTerm(
                    value = getattr(ob, 'user_id'), 
                    token = getattr(ob, 'user_id'),
                    title = "(%s %s)" % (getattr(ob, 'first_name'),
                            getattr(ob, 'last_name'))
                ))
        return vocabulary.SimpleVocabulary(terms)


class MemberOfParliamentSource(MemberOfParliamentImmutableSource):
    """ you may change the user in this context """
    def constructQuery(self, context):
        session= Session()
        trusted=removeSecurityProxy(context)
        user_id = getattr(trusted, self.value_field, None)
        parliament_id = self._get_parliament_id(trusted)
        if user_id:
            if parliament_id:
                query = session.query(MemberOfParliament
                       ).filter(
                        sql.or_(
                        sql.and_(MemberOfParliament.user_id == user_id,
                                MemberOfParliament.group_id ==
                                parliament_id),
                        sql.and_(MemberOfParliament.group_id ==
                                parliament_id,
                                MemberOfParliament.active_p ==
                                True)
                        )).order_by(
                            MemberOfParliament.last_name,
                            MemberOfParliament.first_name,
                            MemberOfParliament.middle_name).distinct()
                return query
            else:
                query = session.query(MemberOfParliament).order_by(
                            MemberOfParliament.last_name,
                            MemberOfParliament.first_name,
                            MemberOfParliament.middle_name).filter(
                                MemberOfParliament.active_p == True)
        else:
            if parliament_id:
                query = session.query(MemberOfParliament).filter(
                    sql.and_(MemberOfParliament.group_id ==
                            parliament_id,
                            MemberOfParliament.active_p ==
                            True)).order_by(
                                MemberOfParliament.last_name,
                                MemberOfParliament.first_name,
                                MemberOfParliament.middle_name)
            else:
                query = session.query(domain.User).order_by(
                            domain.User.last_name,
                            domain.User.first_name,
                            domain.User.middle_name)
        return query


class MemberOfParliamentDelegationSource(MemberOfParliamentSource):
    """ A logged in User will only be able to choose
    himself if he is a member of parliament or those 
    Persons who gave him rights to act on his behalf"""
    def constructQuery(self, context):
        mp_query = super(MemberOfParliamentDelegationSource, 
                self).constructQuery(context)
        #XXX clerks cannot yet choose MPs freely
        user_id = utils.get_db_user_id()
        if user_id:
            user_ids = [user_id]
            for result in delegation.get_user_delegations(user_id):
                user_ids.append(result.user_id)
            query = mp_query.filter(
                domain.MemberOfParliament.user_id.in_(user_ids))
            if len(query.all()) > 0:
                return query
        return mp_query


class MemberOfParliamentSignatorySource(MemberOfParliamentSource):
    """Vocabulary for selection of signatories - Other MPs
       excluding pre-selected signatories and item owner
    """
    def constructQuery(self, context):
        mp_query = super(MemberOfParliamentSignatorySource, 
                self).constructQuery(context)
        trusted = removeSecurityProxy(context)
        if ISignatory.providedBy(context):
            trusted = removeSecurityProxy(trusted.__parent__)
        if IContainer.providedBy(trusted):
            exclude_ids = set(
                [ member.user_id for member in trusted.values() ]
            )
            if trusted.__parent__ is not None:
                trusted_parent = removeSecurityProxy(trusted.__parent__)
                exclude_ids.add(trusted_parent.owner_id)
            return mp_query.filter(
                sql.not_(domain.MemberOfParliament.user_id.in_(
                        list(exclude_ids)
                    )
                )
            )
        return mp_query


class MinistrySource(SpecializedSource):
    """Ministries in the current parliament.
    """

    def __init__(self, value_field):
        self.value_field = value_field
    
    def constructQuery(self, context):
        session= Session()
        trusted=removeSecurityProxy(context)
        ministry_id = getattr(trusted, self.value_field, None)
        parliament_id = self._get_parliament_id(trusted)
        if parliament_id:
            governments = session.query(domain.Government).filter(
                sql.and_(
                    domain.Government.parent_group_id == parliament_id,
                    domain.Government.status == u'active'
                ))
            government = governments.all()
            if len(government) > 0:
                gov_ids = [gov.group_id for gov in government]
                if ministry_id:
                    query = session.query(domain.Ministry).filter(
                        sql.or_(
                            domain.Ministry.group_id == ministry_id,
                            sql.and_(
                                domain.Ministry.parent_group_id.in_(gov_ids),
                                domain.Ministry.status == u'active'
                            ))
                    )
                else:
                    query = session.query(domain.Ministry).filter(
                            sql.and_(
                                domain.Ministry.parent_group_id.in_(gov_ids),
                                domain.Ministry.status == u'active'
                            ))
            else:
                if ministry_id:
                    query = session.query(domain.Ministry).filter(
                            domain.Ministry.group_id == ministry_id)
                else:
                    query = session.query(domain.Ministry)
        else:
            query = session.query(domain.Ministry)
        return query
               
    def __call__(self, context=None):
        query = self.constructQuery(context)
        results = query.all()
        terms = []
        trusted=removeSecurityProxy(context)
        ministry_id = getattr(trusted, self.value_field, None)
        for ob in results:
            terms.append(
                vocabulary.SimpleTerm(
                    value = getattr(ob, 'group_id'), 
                    token = getattr(ob, 'group_id'),
                    title = get_translated_group_label(ob)
                ))
        if ministry_id:
            if query.filter(domain.Group.group_id == ministry_id).count() == 0:
                session = Session()
                ob = session.query(domain.Group).get(ministry_id)
                terms.append(
                    vocabulary.SimpleTerm(
                        value = getattr(obj, 'group_id'), 
                        token = getattr(obj, 'group_id'),
                        title = get_translated_group_label(ob)
                ))
        return vocabulary.SimpleVocabulary(terms)

'''class MemberTitleSource(SpecializedSource):
    """ get titles (i.e. roles/functions) in the current context """
    
    def __init__(self, value_field):
        self.value_field = value_field 
    
    def _get_user_type(self, context):
        user_type = getattr(context, 'membership_type', None)
        if not user_type:
            user_type = self._get_user_type(context.__parent__)
        return user_type
    
    def constructQuery(self, context):
        session= Session()
        trusted=removeSecurityProxy(context)
        user_type = self._get_user_type(trusted)
        titles = session.query(domain.MemberTitle).filter(
            domain.MemberTitle.user_type == user_type).order_by(
                domain.MemberTitle.sort_order)
        return titles
    
    def __call__(self, context=None):
        query = self.constructQuery(context)
        results = query.all()
        terms = []
        for ob in results:
            obj = translate_obj(ob)
            terms.append(
                vocabulary.SimpleTerm(
                    value = getattr(obj, 'user_role_type_id'), 
                    token = getattr(obj, 'user_role_type_id'),
                    title = getattr(obj, 'user_role_name'),
                   ))
        return vocabulary.SimpleVocabulary(terms)'''


class UserSource(SpecializedSource):
    """ All active users """
    def constructQuery(self, context):
        session = Session()
        users = session.query(domain.User).order_by(
            domain.User.last_name, domain.User.first_name)
        return users

class GroupSource(SpecializedSource):
    """All active groups.
    """
    
    def constructQuery(self, context):
        # !+GROUP_FILTERS, refine, check for active, ...
        groups = Session().query(domain.Group).order_by(
            domain.Group.short_name, domain.Group.full_name)
        return groups
    
    def __call__(self, context=None):
        results = self.constructQuery(context).all()
        terms = []
        for ob in results:
            terms.append(
                vocabulary.SimpleTerm(
                    value = getattr(ob, "group_id"), 
                    token = getattr(ob, "group_id"),
                    title = get_translated_group_label(ob)
                ))
        return vocabulary.SimpleVocabulary(terms)


class MembershipUserSource(UserSource):
    """Filter out users already added to a membership container
    """
    def constructQuery(self, context):
        users = super(MembershipUserSource, self).constructQuery(
            context
        )
        trusted = removeSecurityProxy(context)
        exclude_ids = set()
        if IContainer.providedBy(trusted):
            for member in trusted.values():
                exclude_ids.add(member.user_id)
            users = users.filter(
                sql.not_(domain.User.user_id.in_(list(exclude_ids)))
            )
        return users

class UserNotMPSource(SpecializedSource):
    """ All users that are NOT a MP """
        
    def constructQuery(self, context):
        session= Session()
        trusted=removeSecurityProxy(context)
        parliament_id = self._get_parliament_id(trusted)
        mp_user_ids = sql.select([schema.user_group_memberships.c.user_id], 
            schema.user_group_memberships.c.group_id == parliament_id)
        query = session.query(domain.User).filter(sql.and_(
            sql.not_(domain.User.user_id.in_(mp_user_ids)),
            domain.User.active_p == 'A')).order_by(
                domain.User.last_name, domain.User.first_name)
        return query

    def __call__(self, context=None):
        query = self.constructQuery(context)
        results = query.all()
        terms = []
        for ob in results:
            terms.append(
                vocabulary.SimpleTerm(
                    value = getattr(ob, 'user_id'), 
                    token = getattr(ob, 'user_id'),
                    title = "%s %s" % (getattr(ob, 'first_name'),
                            getattr(ob, 'last_name'))
                   ))
        user_id = getattr(context, self.value_field, None) 
        if user_id:
            if query.filter(domain.GroupMembership.user_id == user_id).count() == 0:
                # The user is not a member of this group. 
                # This should not happen in real life
                # but if we do not add it her the view form will 
                # throw an exception 
                session = Session()
                ob = session.query(domain.User).get(user_id)
                terms.append(
                vocabulary.SimpleTerm(
                    value = getattr(ob, 'user_id'), 
                    token = getattr(ob, 'user_id'),
                    title = "(%s %s)" % (getattr(ob, 'first_name'),
                            getattr(ob, 'last_name'))
                   ))
        return vocabulary.SimpleVocabulary(terms)

class UserNotStaffSource(SpecializedSource):
    """ all users that are NOT staff """

class SittingAttendanceSource(SpecializedSource):
    """ all members of the group which do not have an attendance record yet"""
    def constructQuery(self, context):
        session= Session()
        trusted=removeSecurityProxy(context)
        user_id = getattr(trusted, self.value_field, None)
        if user_id:
            query = session.query(domain.User 
                   ).filter(domain.User.user_id == 
                        user_id).order_by(domain.User.last_name,
                            domain.User.first_name,
                            domain.User.middle_name)
            return query
        else:
            sitting = trusted.__parent__
            group_id = sitting.group_id
            group_sitting_id = sitting.group_sitting_id
            all_member_ids = sql.select([schema.user_group_memberships.c.user_id], 
                    sql.and_(
                        schema.user_group_memberships.c.group_id == group_id,
                        schema.user_group_memberships.c.active_p == True))
            attended_ids = sql.select([schema.group_sitting_attendance.c.member_id],
                     schema.group_sitting_attendance.c.group_sitting_id == group_sitting_id)
            query = session.query(domain.User).filter(
                sql.and_(domain.User.user_id.in_(all_member_ids),
                    ~ domain.User.user_id.in_(attended_ids))).order_by(
                            domain.User.last_name,
                            domain.User.first_name,
                            domain.User.middle_name)
            return query
                 
    def __call__(self, context=None):
        query = self.constructQuery(context)
        results = query.all()
        terms = []
        for ob in results:
            terms.append(
                vocabulary.SimpleTerm(
                    value = getattr(ob, 'user_id'), 
                    token = getattr(ob, 'user_id'),
                    title = "%s %s" % (getattr(ob, 'first_name'),
                            getattr(ob, 'last_name'))
                   ))
        user_id = getattr(context, self.value_field, None) 
        if user_id:
            if len(query.filter(schema.users.c.user_id == user_id).all()) == 0:
                session = Session()
                ob = session.query(domain.User).get(user_id)
                terms.append(
                vocabulary.SimpleTerm(
                    value = getattr(ob, 'user_id'), 
                    token = getattr(ob, 'user_id'),
                    title = "(%s %s)" % (getattr(ob, 'first_name'),
                            getattr(ob, 'last_name'))
                   ))
        return vocabulary.SimpleVocabulary(terms)

class SubstitutionSource(SpecializedSource):
    """ active user of the same group """
    def _get_group_id(self, context):
        trusted = removeSecurityProxy(context)
        group_id = getattr(trusted, 'group_id', None)
        if not group_id:
            group_id = getattr(trusted.__parent__, 'group_id', None)
        return group_id

    def _get_user_id(self, context):
        trusted = removeSecurityProxy(context)
        user_id = getattr(trusted, 'user_id', None)
        if not user_id:
            user_id = getattr(trusted.__parent__, 'user_id', None)
        return user_id

    def constructQuery(self, context):
        session= Session()
        query = session.query(domain.GroupMembership).order_by(
            'last_name', 'first_name').filter(
            domain.GroupMembership.active_p == True)
        user_id = self._get_user_id(context)
        if user_id:
            query = query.filter(
                domain.GroupMembership.user_id != user_id)
        group_id = self._get_group_id(context)
        if group_id:
            query = query.filter(
                domain.GroupMembership.group_id == group_id)
        return query

    def __call__(self, context=None):
        query = self.constructQuery(context)
        results = query.all()
        tdict = {}
        for ob in results:
            tdict[getattr(ob.user, 'user_id')] = "%s %s" % (
                    getattr(ob.user, 'first_name'),
                    getattr(ob.user, 'last_name'))
        user_id = getattr(context, 'replaced_id', None) 
        if user_id:
            if len(query.filter(domain.GroupMembership.replaced_id == user_id).all()) == 0:
                session = Session()
                ob = session.query(domain.User).get(user_id)
                tdict[getattr(ob, 'user_id')] = "%s %s" % (
                            getattr(ob, 'first_name'),
                            getattr(ob, 'last_name'))
        terms = []
        for t in tdict.keys():
            terms.append(
                vocabulary.SimpleTerm(
                    value = t, 
                    token = t,
                    title = tdict[t]
                   ))
        return vocabulary.SimpleVocabulary(terms)


# !+MODELS(mr, oct-2011) shouldn't this be elsewhere?
class PartyMembership(object):
    pass

party_membership = sql.join(schema.political_parties, schema.groups,
        schema.political_parties.c.party_id == schema.groups.c.group_id
    ).join(schema.user_group_memberships,
        schema.groups.c.group_id == schema.user_group_memberships.c.group_id)

mapper(PartyMembership, party_membership)


class PIAssignmentSource(SpecializedSource):
    
    def constructQuery(self, context):
        session= Session()
        trusted=removeSecurityProxy(context)
        parliament_id = self._get_parliament_id(context)
        item_id = getattr(context, self.value_field, None)
        trusted = removeSecurityProxy(context)
        existing_item_ids = [assn.item_id for assn in trusted.values()]
        if item_id:
            query = session.query(domain.ParliamentaryItem).filter(
                domain.ParliamentaryItem.parliamentary_item_id ==
                item_id)
        else:
            query = session.query(domain.ParliamentaryItem).filter(
                    sql.and_(
                        sql.not_(domain.ParliamentaryItem.status.in_(
                                _assignable_state_ids
                            )
                        ),
                        sql.not_(
                            domain.ParliamentaryItem.parliamentary_item_id.in_(
                                existing_item_ids
                            )
                        ),
                        domain.ParliamentaryItem.parliament_id == parliament_id
                    )
                )
        return query


class CommitteeSource(SpecializedSource):

    def constructQuery(self, context):
        session= Session()
        parliament_id = self._get_parliament_id(context)
        query = session.query(domain.Committee).filter(
            sql.and_(
            domain.Committee.status == 'active',
            domain.Committee.parent_group_id == parliament_id))
        return query



class MotionPartySource(SpecializedSource):

    def constructQuery(self, context):
        session= Session()
        trusted=removeSecurityProxy(context)
        user_id = getattr(trusted, 'owner_id', None)
        if user_id is None:
            user_id = utils.get_db_user_id()
        parliament_id = self._get_parliament_id(context)
        
        if user_id: 
            query = session.query(PartyMembership
               ).filter(
                    sql.and_(PartyMembership.active_p == True,
                        PartyMembership.user_id == user_id,
                        PartyMembership.parent_group_id == parliament_id)
                       )
        else:
            query = session.query(domain.PoliticalGroup).filter(
                        domain.PoliticalGroup.parent_group_id == parliament_id)
        return query
        

class QuerySource(object):
    """ call a query with an additonal filter and ordering
    note that the domain_model *must* not have a where and order_by clause 
    (otherwise the parameters passed to this query will be ignored),
    the order_by and filter_field fields *must* be public attributes"""
    interface.implements(IContextSourceBinder)
    
    def getValueKey(self, context):
        """iterate through the parents until you get a valueKey """
        if context.__parent__ is None:
            return None
        else:
            try:
                value_key = valueKey(context.__parent__.__name__)[0]
            except:
                value_key = self.getValueKey(context.__parent__)
        return value_key

    def __init__(self,
        domain_model, 
        token_field, 
        title_field, 
        value_field, 
        filter_field, 
        filter_value=None, 
        order_by_field=None
    ):
        self.domain_model = domain_model
        self.token_field = token_field
        self.value_field = value_field
        self.title_field = title_field
        self.filter_field = filter_field
        self.order_by_field = order_by_field
        self.filter_value = filter_value
        
    def constructQuery(self, context):
        session = Session()
        trusted=removeSecurityProxy(context)
        if self.filter_value:
            query = session.query(self.domain_model).filter(
                self.domain_model.c[self.filter_field] == 
                trusted.__dict__[self.filter_value])
        else:
            pfk = self.getValueKey(context)
            query = session.query(self.domain_model)
            query = query.filter(self.domain_model.c[self.filter_field] == pfk)
            
        query = query.distinct()
        if self.order_by_field:
            query = query.order_by(self.domain_model.c[self.order_by_field])
            
        return query
        
    def __call__(self, context=None):
        query = self.constructQuery(context)
        results = query.all()
        terms = []
        title_field = self.title_field or self.token_field
        for ob in results:
            terms.append(
                vocabulary.SimpleTerm(
                    value = getattr(ob, self.value_field), 
                    token = getattr(ob, self.token_field),
                    title = getattr(ob, title_field),
            ))
        return vocabulary.SimpleVocabulary(terms)

def child_selected(children, selected):
    return bool(set([_['key'] for _ in children]).intersection(selected)
        ) \
        or bool([_ for _ in children
                if _['children'] and child_selected(_['children'], 
                    selected
                )
            ]
        )

def dict_to_dynatree(input_dict, selected):
    """
    Adapted from collective.dynatree
    """
    if not input_dict:
        return []
    retval = []
    for key in input_dict.keys():
        title, children = input_dict[key]
        children = dict_to_dynatree(children, selected)

        new_item = {}
        new_item['title'] = title
        new_item['key'] = key
        new_item['children'] = children
        new_item['select'] = key in selected
        new_item['isFolder'] = bool(children)
        new_item['expand'] = bool(selected) and (
            child_selected(children, selected)
        )
        retval.append(new_item)
    return retval


class VDEXVocabularyMixin(object):
    def __init__(self, file_name):
        self.file_name = file_name
    
    @property
    def file_path(self):
        return capi.get_path_for("vocabularies", self.file_name)
    
    @property
    def vdex(self):
        ofile = open(self.file_path)
        vdex = imsvdex.vdex.VDEXManager(file=ofile, lang=capi.default_language)
        vdex.fallback_to_default_language = True
        ofile.close()
        return vdex
    
    def getTermById(self, value):
        return self.vdex.getTermById(value)

class BaseVDEXVocabulary(VDEXVocabularyMixin):
    """
    Base class to generate vdex vocabularies
    
    vocabulary = BaseVDEXVocabulary(file_name)
    Register utility for easier reuse
    """
    interface.implements(ITreeVocabulary)

    def generateJSON(self, selected = []):
        vdict = self.vdex.getVocabularyDict(lang=get_default_language())
        dynatree_dict = dict_to_dynatree(vdict, selected)
        return json.dumps(dynatree_dict)

    def validateTerms(self, value_list):
        for value in value_list:
            if self.getTermById(value) is None:
                raise LookupError

class FlatVDEXVocabulary(VDEXVocabularyMixin):
    def __call__(self, context=None):
        all_terms = self.vdex.getVocabularyDict(lang=get_default_language())
        terms = []
        assert self.vdex.isFlat() is True
        for (key, data) in all_terms.iteritems():
            term = vocabulary.SimpleTerm(key, key, data[0])
            terms.append(term)
        return vocabulary.SimpleVocabulary(terms)

subject_terms_vocabulary = BaseVDEXVocabulary("subject-terms.vdex")

#
# Sitting flat VDEX based vocabularies
#
sitting_activity_types = FlatVDEXVocabulary("sitting-activity-types.vdex")
sitting_meeting_types = FlatVDEXVocabulary("sitting-meeting-types.vdex")
sitting_convocation_types = FlatVDEXVocabulary("sitting-convocation-types.vdex")

#
# Vocabularies for XML configuration based report generation
#

class ReportXHTMLTemplates(object):
    """XHTML templates for generation of reports in scheduling.
    
    Templates can be customized/added in:
    `bungeni_custom/reporting/templates/scheduling/`
    """
    
    terms = []
    template_folder = "scheduling"
    
    def __init__(self):
        self.terms = self.buildTerms()
    
    def getTitle(self, path):
        title = None
        doctree = etree.fromstring(open(path).read())
        node = doctree.find("{%s}config/title" % BUNGENI_REPORTS_NS)
        if node is not None:
            title = node.text
        return title
    
    def buildTerms(self):
        vocabulary_terms = []
        template_folder = capi.get_path_for("reporting", "templates", 
            self.template_folder
        )
        if not os.path.exists(template_folder):
            log.error("Directory for XHTML templates does not exist: %s",
                template_folder
            )
            return
        file_list = filter(lambda fname: fname.endswith(".html"),
            os.listdir(template_folder)
        )
        for file_name in file_list:
            file_path = "/".join([template_folder, file_name])
            vocabulary_terms.append(
                vocabulary.SimpleTerm(file_path,
                    token=hashlib.md5(file_name).hexdigest(),
                    title=self.getTitle(file_path)
                )
            )
        return vocabulary_terms
    
    def __call__(self, context=None):
        return vocabulary.SimpleVocabulary(self.terms)

report_xhtml_templates = ReportXHTMLTemplates()

def update_term_doctype(term):
    template_file = open(term.value)
    doctree = etree.fromstring(template_file.read())
    node = doctree.find("{%s}config/doctypes" % BUNGENI_REPORTS_NS)
    if node is None:
        term.doctypes = None
    else:
        term.doctypes = [ dtype.strip() for dtype in node.text.split(",") ]
    template_file.close()
    return term

class DocumentXHTMLTemplates(ReportXHTMLTemplates):
    """XHTML templates for publication of documents in other formats.
    
    Templates can be customized or added in:
    `bungeni_custom/reporting/templates/documents`
    """
    template_folder = "documents"
    
    def __init__(self):
        super(DocumentXHTMLTemplates, self).__init__()
        self.updateTermDocTypes()
    
    def updateTermDocTypes(self):
        """Read configuration options and update terms with doctype property"""
        self.terms = map(update_term_doctype, self.terms)
    
document_xhtml_templates = DocumentXHTMLTemplates()


