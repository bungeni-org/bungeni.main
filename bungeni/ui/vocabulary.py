import datetime
from zope import interface
from zope.schema.interfaces import IContextSourceBinder
from zope.schema import vocabulary
from zope.security.proxy import removeSecurityProxy
from zope.security import checkPermission

import bungeni.alchemist.vocabulary
from bungeni.alchemist import Session
from bungeni.alchemist.container import valueKey

from sqlalchemy.orm import mapper,  column_property 
import sqlalchemy as rdb
import sqlalchemy.sql.expression as sql
from bungeni.models import schema, domain, utils, delegation
from bungeni.models.interfaces import ITranslatable

from zope.schema.interfaces import IVocabularyFactory
from zope.i18n import translate

from i18n import _

import datetime
from bungeni.core.translation import translate_obj
from bungeni.ui.calendar.utils import first_nth_weekday_of_month
from bungeni.ui.calendar.utils import nth_day_of_month
from bungeni.ui.calendar.utils import nth_day_of_week

days = [_('day_%d' % index, default=default)
        for (index, default) in enumerate(
            (u"Mon", u"Tue", u"Wed", u"Thu", u"Fri", u"Sat", u"Sun"))]

class WeekdaysVocabulary(object):
    interface.implements(IVocabularyFactory)
        
    def __call__(self, context):
        return vocabulary.SimpleVocabulary(
            [vocabulary.SimpleTerm(
                nth_day_of_week(index), str(index), msg)
             for (index, msg) in enumerate(days)])

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
QuestionType = vocabulary.SimpleVocabulary([
    vocabulary.SimpleTerm('O', _(u"Ordinary"), _(u"Ordinary")), 
    vocabulary.SimpleTerm('P', _(u"Private Notice"), _(u"Private Notice"))
])
ResponseType = vocabulary.SimpleVocabulary([
    vocabulary.SimpleTerm('O', _("Oral"), _("Oral")), 
    vocabulary.SimpleTerm('W', _(u"Written"), _(u"Written"))
])
Gender = vocabulary.SimpleVocabulary([
    vocabulary.SimpleTerm('M', _(u"Male"), _(u"Male")), 
    vocabulary.SimpleTerm('F', _(u"Female"), _(u"Female"))
])
ElectedNominated = vocabulary.SimpleVocabulary([
    vocabulary.SimpleTerm('E', _(u"elected"), _(u"elected")),
    vocabulary.SimpleTerm('N', _(u"nominated"), _(u"nominated") ), 
    vocabulary.SimpleTerm('O', _(u"ex officio"), _(u"ex officio"))
])
InActiveDead = vocabulary.SimpleVocabulary([
    vocabulary.SimpleTerm('A', _(u"active"), _(u"active")),
    vocabulary.SimpleTerm('I', _(u"inactive"), _(u"inactive")),
    vocabulary.SimpleTerm('D', _(u"deceased"),  _(u"deceased"))
])
ISResponse = vocabulary.SimpleVocabulary([
    vocabulary.SimpleTerm('I', _(u"initial"), _(u"initial")),
    vocabulary.SimpleTerm('S', _(u"subsequent"), _(u"subsequent"))
])
OfficeType = vocabulary.SimpleVocabulary([
    vocabulary.SimpleTerm('S', _(u"House Business Office"), 
        _(u"House Business Office")), 
    vocabulary.SimpleTerm('C', _(u"Clerks Office"), _(u"Clerks Office")), 
    vocabulary.SimpleTerm('T', _(u"Translators Office"), 
        _(u"Translators Office")), 
    vocabulary.SimpleTerm('L', _(u"Library Office"), _(u"Library Office")),
    vocabulary.SimpleTerm('R', _(u"Researcher Office"), 
        _(u"Researcher Office")),
])
YesNoSource = vocabulary.SimpleVocabulary( [
    vocabulary.SimpleTerm(True, _(u"Yes"), _(u"Yes")), 
    vocabulary.SimpleTerm(False, _(u"No"), _(u"No"))] )
AddressPostalType = vocabulary.SimpleVocabulary([
    vocabulary.SimpleTerm("P", _(u"P.O. Box"), _(u"P.O. Box")),
    vocabulary.SimpleTerm("S", _(u"Street / Physical"), 
        _(u"Street / Physical")),
    vocabulary.SimpleTerm("M", _(u"Military"), _(u"Military")),
    vocabulary.SimpleTerm("S", _(u"Undefined / Unknown"), 
        _(u"Undefined / Unknown")),
])

class DatabaseSource(bungeni.alchemist.vocabulary.DatabaseSource):

    def __call__( self, context=None ):
        query = self.constructQuery( context )
        results = query.all()
        
        terms = []
        title_field = self.title_field or self.token_field
        title_getter = self.title_getter or (lambda ob: getattr(ob, title_field))
        for ob in results:
            if ITranslatable.providedBy(ob):
                ob = translate_obj(ob)
            terms.append( 
                vocabulary.SimpleTerm( 
                    value = getattr( ob, self.value_field), 
                    token = getattr( ob, self.token_field),
                    title = title_getter(ob),
                    ))
                    
        return vocabulary.SimpleVocabulary( terms )

ParliamentSource = DatabaseSource(
    domain.Parliament, 'short_name', 'parliament_id',
    title_getter=lambda ob: "%s (%s-%s)" % (
        ob.full_name,
        ob.start_date and ob.start_date.strftime("%Y/%m/%d") or "?",
        ob.end_date and ob.end_date.strftime("%Y/%m/%d") or "?"))
                

class SpecializedSource( object ):
    interface.implements( IContextSourceBinder )
    def __init__( self, token_field, title_field, value_field ):
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
            
    def constructQuery( self, context ):
        raise NotImplementedError("Must be implemented by subclass.")
        
    def __call__( self, context=None ):
        query = self.constructQuery( context )
        results = query.all()
        
        terms = []
        title_field = self.title_field or self.token_field
        for ob in results:
            obj = translate_obj(ob)
            terms.append( 
                vocabulary.SimpleTerm( 
                    value = getattr( obj, self.value_field), 
                    token = getattr( obj, self.token_field),
                    title = getattr( obj, title_field) ,
                    ))
                    
        return vocabulary.SimpleVocabulary( terms )




class SittingTypes(SpecializedSource):
    #domain.SittingType, 'sitting_type', 'sitting_type_id',
    #title_getter=lambda ob: "%s (%s-%s)" % (
    #    ob.sitting_type.capitalize(), ob.start_time, ob.end_time))

    def constructQuery(self, context):
        session= Session()
        return session.query(domain.SittingType)

    def __call__( self, context=None ):
        query = self.constructQuery( context )
        results = query.all()
        
        terms = []
        title_field = self.title_field or self.token_field
        for ob in results:
            obj = translate_obj(ob)
            terms.append( 
                vocabulary.SimpleTerm( 
                    value = obj.sitting_type_id, 
                    token = obj.sitting_type,
                    title = "%s (%s-%s)" % (
                        obj.sitting_type, 
                        obj.start_time, 
                        obj.end_time),
                    ))
                    
        return vocabulary.SimpleVocabulary( terms )
                
        
#XXX
#SittingTypeOnly = DatabaseSource(
#    domain.SittingType, 
#    title_field='sitting_type',
#    token_field='sitting_type_id',
#    value_field='sitting_type_id')



class MemberOfParliament( object ):
    """ Member of Parliament = user join group membership join parliament"""
    
member_of_parliament = rdb.join( schema.user_group_memberships, 
                    schema.users,
                    schema.user_group_memberships.c.user_id == 
                    schema.users.c.user_id).join( schema.parliaments,
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
            query = session.query( domain.User 
                    ).filter(domain.User.user_id == 
                        user_id).order_by(domain.User.last_name,
                            domain.User.first_name,
                            domain.User.middle_name)
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

    def __call__( self, context=None ):
        query = self.constructQuery( context )
        results = query.all()
        terms = []
        for ob in results:
            terms.append( 
                vocabulary.SimpleTerm( 
                    value = getattr( ob, 'user_id'), 
                    token = getattr( ob, 'user_id'),
                    title = "%s %s" % (getattr( ob, 'first_name') ,
                            getattr( ob, 'last_name'))
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
                terms.append( 
                vocabulary.SimpleTerm( 
                    value = getattr( ob, 'user_id'), 
                    token = getattr( ob, 'user_id'),
                    title = "(%s %s)" % (getattr( ob, 'first_name') ,
                            getattr( ob, 'last_name'))
                    ))
        return vocabulary.SimpleVocabulary( terms )

class MemberOfParliamentSource(MemberOfParliamentImmutableSource):
    """ you may change the user in this context """
    def constructQuery(self, context):
        session= Session()
        trusted=removeSecurityProxy(context)
        user_id = getattr(trusted, self.value_field, None)
        parliament_id = self._get_parliament_id(trusted)
        if user_id:
            if parliament_id:
                query = session.query( MemberOfParliament
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
            user_ids=[user_id,]
            for result in delegation.get_user_delegations(user_id):
                user_ids.append(result.user_id)
            query = mp_query.filter(
                domain.MemberOfParliament.user_id.in_(user_ids))
            if len(query.all()) > 0:
                return query
        return mp_query
                       

class MinistrySource(SpecializedSource):
    """ Ministries in the current parliament """

    def __init__(self, value_field):
        self.value_field = value_field
    
    def constructQuery( self, context):
        session= Session()
        trusted=removeSecurityProxy(context)
        ministry_id = getattr(trusted, self.value_field, None)
        parliament_id = self._get_parliament_id(trusted)
        today = datetime.date.today()
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
               
    def __call__( self, context=None ):
        query = self.constructQuery( context )
        results = query.all()
        terms = []
        trusted=removeSecurityProxy(context)
        ministry_id = getattr(trusted, self.value_field, None)
        for ob in results:
            obj = translate_obj(ob)
            terms.append( 
                vocabulary.SimpleTerm( 
                    value = getattr( obj, 'group_id'), 
                    token = getattr( obj, 'group_id'),
                    title = "%s - %s" % (getattr( obj, 'short_name') ,
                            getattr( obj, 'full_name'))
                    ))
        if ministry_id:
            if query.filter(domain.Group.group_id == ministry_id).count() == 0:
                session = Session()
                ob = session.query(domain.Group).get(ministry_id)
                obj = translate_obj(ob)
                terms.append( 
                    vocabulary.SimpleTerm( 
                        value = getattr( obj, 'group_id'), 
                        token = getattr( obj, 'group_id'),
                        title = "%s - %s" % (getattr( obj, 'short_name') ,
                                getattr( obj, 'full_name'))
                        ))
                            
        return vocabulary.SimpleVocabulary( terms )

class MemberTitleSource(SpecializedSource):
    """ get titles (i.e. roles/functions) in the current context """
    
    def __init__(self, value_field):
        self.value_field = value_field 
    
    def _get_user_type(self, context):
        user_type = getattr(context, 'membership_type', None)
        if not user_type:
            user_type = self._get_user_type(context.__parent__)
        return user_type
    
    def constructQuery( self, context):
        session= Session()
        trusted=removeSecurityProxy(context)
        user_type = self._get_user_type(trusted)
        titles = session.query(domain.MemberTitle).filter(
            domain.MemberTitle.user_type == user_type).order_by(
                domain.MemberTitle.sort_order)
        return titles

    def __call__( self, context=None ):
        query = self.constructQuery( context )
        results = query.all()
        terms = []
        for ob in results:
            obj = translate_obj(ob)
            terms.append( 
                vocabulary.SimpleTerm( 
                    value = getattr( obj, 'user_role_type_id'), 
                    token = getattr( obj, 'user_role_type_id'),
                    title = getattr( obj, 'user_role_name'),
                    ))
        return vocabulary.SimpleVocabulary( terms )

                    
class UserSource(SpecializedSource):
    """ All active users """
    def constructQuery( self, context):
        session= Session()
        
        users = session.query(domain.User).order_by(
                domain.User.last_name, domain.User.first_name)
        return users
    

class UserNotMPSource(SpecializedSource):
    """ All users that are NOT a MP """
        
    def constructQuery( self, context):
        session= Session()
        trusted=removeSecurityProxy(context)
        parliament_id = self._get_parliament_id(trusted)
        mp_user_ids = sql.select([schema.user_group_memberships.c.user_id], 
            schema.user_group_memberships.c.group_id == parliament_id)
        query = session.query(domain.User).filter( sql.and_(
            sql.not_(domain.User.user_id.in_( mp_user_ids)),
            domain.User.active_p == 'A')).order_by(
                domain.User.last_name, domain.User.first_name)
        return query

    def __call__( self, context=None ):
        query = self.constructQuery( context )
        results = query.all()
        terms = []
        for ob in results:
            terms.append( 
                vocabulary.SimpleTerm( 
                    value = getattr( ob, 'user_id'), 
                    token = getattr( ob, 'user_id'),
                    title = "%s %s" % (getattr( ob, 'first_name') ,
                            getattr( ob, 'last_name'))
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
                    value = getattr( ob, 'user_id'), 
                    token = getattr( ob, 'user_id'),
                    title = "(%s %s)" % (getattr( ob, 'first_name') ,
                            getattr( ob, 'last_name'))
                    ))
        return vocabulary.SimpleVocabulary( terms )



class UserNotStaffSource(SpecializedSource):
    """ all users that are NOT staff """

class SittingAttendanceSource(SpecializedSource):
    """ all members of the group which do not have an attendance record yet"""
    def constructQuery(self, context):
        session= Session()
        trusted=removeSecurityProxy(context)
        user_id = getattr(trusted, self.value_field, None)
        if user_id:
            query = session.query( domain.User 
                    ).filter(domain.User.user_id == 
                        user_id).order_by(domain.User.last_name,
                            domain.User.first_name,
                            domain.User.middle_name)
            return query
        else:
            sitting = trusted.__parent__
            group_id = sitting.group_id
            sitting_id = sitting.sitting_id
            all_member_ids = sql.select([schema.user_group_memberships.c.user_id], 
                    sql.and_(
                        schema.user_group_memberships.c.group_id == group_id,
                        schema.user_group_memberships.c.active_p == True))
            attended_ids = sql.select([schema.sitting_attendance.c.member_id],
                     schema.sitting_attendance.c.sitting_id == sitting_id)
            query = session.query( domain.User).filter(
                sql.and_(domain.User.user_id.in_( all_member_ids),
                    ~ domain.User.user_id.in_(attended_ids) )).order_by(
                            domain.User.last_name,
                            domain.User.first_name,
                            domain.User.middle_name)
            return query
                 
    def __call__( self, context=None ):
        query = self.constructQuery( context )
        results = query.all()
        terms = []
        for ob in results:
            terms.append( 
                vocabulary.SimpleTerm( 
                    value = getattr( ob, 'user_id'), 
                    token = getattr( ob, 'user_id'),
                    title = "%s %s" % (getattr( ob, 'first_name') ,
                            getattr( ob, 'last_name'))
                    ))
        user_id = getattr(context, self.value_field, None) 
        if user_id:
            if len(query.filter(schema.users.c.user_id == user_id).all()) == 0:
                session = Session()
                ob = session.query(domain.User).get(user_id)
                terms.append( 
                vocabulary.SimpleTerm( 
                    value = getattr( ob, 'user_id'), 
                    token = getattr( ob, 'user_id'),
                    title = "(%s %s)" % (getattr( ob, 'first_name') ,
                            getattr( ob, 'last_name'))
                    ))
        return vocabulary.SimpleVocabulary( terms )


        
class SubstitutionSource(SpecializedSource):
    """ active user of the same group """
    def _get_group_id(self, context):
        trusted = removeSecurityProxy(context)
        group_id = getattr(trusted,'group_id', None)
        if not group_id:
             group_id = getattr(trusted.__parent__,'group_id', None)
        return group_id

    def _get_user_id(self, context):
        trusted = removeSecurityProxy(context)
        user_id = getattr(trusted,'user_id', None)
        if not user_id:
             user_id = getattr(trusted.__parent__,'user_id', None)
        return user_id

                     
    def constructQuery( self, context):
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
                    
        
        
    def __call__( self, context=None ):
        query = self.constructQuery( context )
        results = query.all()
        tdict = {}
        for ob in results:
            tdict[getattr( ob.user, 'user_id')] = "%s %s" % (
                    getattr( ob.user, 'first_name') ,
                    getattr( ob.user, 'last_name'))
        user_id = getattr(context, 'replaced_id', None) 
        if user_id:
            if len(query.filter(domain.GroupMembership.replaced_id == user_id).all()) == 0:
                session = Session()
                ob = session.query(domain.User).get(user_id)
                tdict[getattr( ob, 'user_id')] = "%s %s" % (
                            getattr( ob, 'first_name') ,
                            getattr( ob, 'last_name'))
        terms = []
        for t in tdict.keys():
            terms.append( 
                vocabulary.SimpleTerm( 
                    value = t, 
                    token = t,
                    title = tdict[t]
                    ))
        return vocabulary.SimpleVocabulary( terms )

class PartyMembership(object):
    pass




party_membership = sql.join(schema.political_parties, schema.groups,
                schema.political_parties.c.party_id == schema.groups.c.group_id).join(
                   schema.user_group_memberships,
                  schema.groups.c.group_id == schema.user_group_memberships.c.group_id)

mapper(PartyMembership,party_membership)

class BillSource(SpecializedSource):
    
    def constructQuery( self, context):
        session= Session()
        trusted=removeSecurityProxy(context)
        parliament_id = self._get_parliament_id(context)
        bill_id = getattr(context, self.value_field, None) 
        if bill_id:
            query = session.query(domain.Bill).filter(
                domain.Bill.parliamentary_item_id ==
                bill_id)
        else:
            query = session.query(domain.Bill).filter(
                sql.and_(
                sql.not_(domain.Bill.status.in_(
                    ['draft','withdrawn','approved','rejected'])),
                domain.Bill.parliament_id == parliament_id))
        return query
                
class CommitteeSource(SpecializedSource):

    def constructQuery( self, context):
        session= Session()
        trusted=removeSecurityProxy(context)
        parliament_id = self._get_parliament_id(context)
        query = session.query(domain.Committee).filter(
            sql.and_(
            domain.Committee.status == 'active',
            domain.Committee.parent_group_id == parliament_id))
        return query



class MotionPartySource(SpecializedSource):

    def constructQuery( self, context):
        session= Session()
        trusted=removeSecurityProxy(context)
        user_id = getattr(trusted, 'owner_id', None)
        if user_id is None:
            user_id = utils.get_db_user_id()
        parliament_id = self._get_parliament_id(context)
        
        if user_id: 
            query = session.query(PartyMembership
                ).filter(
                    sql.and_(PartyMembership.active_p ==True,
                        PartyMembership.user_id == user_id,
                        PartyMembership.parent_group_id == parliament_id)
                        )
        else:
            query = session.query(domain.PoliticalGroup).filter(
                        domain.PoliticalGroup.parent_group_id == parliament_id)
        return query
        

class QuerySource( object ):
    """ call a query with an additonal filter and ordering
    note that the domain_model *must* not have a where and order_by clause 
    (otherwise the parameters passed to this query will be ignored),
    the order_by and filter_field fields *must* be public attributes"""
    interface.implements( IContextSourceBinder )
    
    def getValueKey(self, context):
        """iterate through the parents until you get a valueKey """
        if context.__parent__ is None:
            return None
        else:
            try:
                value_key = valueKey( context.__parent__.__name__ )[0]
            except:
                value_key = self.getValueKey( context.__parent__)
        return value_key
        
        
    def __init__( self, 
                    domain_model, 
                    token_field, 
                    title_field, 
                    value_field, 
                    filter_field, 
                    filter_value=None, 
                    order_by_field=None,  ):
        self.domain_model = domain_model
        self.token_field = token_field
        self.value_field = value_field
        self.title_field = title_field
        self.filter_field = filter_field
        self.order_by_field = order_by_field
        self.filter_value = filter_value
        
    def constructQuery( self, context ):
        session = Session()
        trusted=removeSecurityProxy(context)
        if self.filter_value:
            query = session.query( self.domain_model ).filter(
                self.domain_model.c[self.filter_field] == 
                trusted.__dict__[self.filter_value] )
        else:
            pfk = self.getValueKey(context)
            query = session.query( self.domain_model )
            query = query.filter(self.domain_model.c[self.filter_field] == pfk )
            
        query = query.distinct()
        if self.order_by_field:
            query = query.order_by(self.domain_model.c[self.order_by_field])
            
        return query
        
    def __call__( self, context=None ):
        query = self.constructQuery( context )
        results = query.all()
        
        terms = []
        title_field = self.title_field or self.token_field
        for ob in results:
            terms.append( 
                vocabulary.SimpleTerm( 
                    value = getattr( ob, self.value_field), 
                    token = getattr( ob, self.token_field),
                    title = getattr( ob, title_field) ,
                    ))
                    
        return vocabulary.SimpleVocabulary( terms )
