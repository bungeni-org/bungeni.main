# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt
'''Query-related utilities for the UI

usage: 
from bungeni.ui.utils import queries

$Id$
'''

import datetime
from zope import interface
from zope.schema.interfaces import IContextSourceBinder
from zope.schema import vocabulary
from zope.security.proxy import removeSecurityProxy

from bungeni.alchemist import Session
from bungeni.alchemist.container import valueKey
from bungeni.alchemist.container import stringKey

from bungeni.models import domain
from bungeni.models import schema
from sqlalchemy import desc
from sqlalchemy import sql
from bungeni.ui.i18n import _


# !+ COMBINE ui.utils.{queries, statements} WITH models.{queries, utils}
# !+ MOVE some models.utils to core.globals

''' !+UNUSED
def execute_sql(sql_statement, **kwargs):
    """Evaluates sql_statement for parameter values specified in kwargs
    and executes it
    """
    session = Session()
    connection = session.connection(domain.Parliament)
    query = connection.execute(sql.text(sql_statement), **kwargs)
    return query
'''

# !+ RENAME APPROPIATELY--these "validation" utilities do no actual "validation"!

# !+gen_other_dateranged_objects_overlapping_date
def validate_date_in_interval(obj, domain_model, date):
    query = Session().query(domain_model).filter(sql.expression.between(
            date, domain_model.start_date, domain_model.end_date))
    results = query.all()
    if results:
        if obj:
            # the object itself can overlap
            for result in results:
                if stringKey(result) == stringKey(obj):
                    continue
                else:
                    yield result
        else:
            # all results indicate an error
           for result in results:
                yield result


def validate_open_interval(obj, domain_model):
    query = Session().query(domain_model).filter(domain_model.end_date == None)
    results = query.all()
    if results:
        if obj:
            for result in results:
                if stringKey(result) == stringKey(obj):
                    continue
                else:
                    yield result
        else:
           for result in results:
                yield result


def validate_membership_in_interval(obj, domain_model, date, user_id, 
        group_id=None, parent_id=None, with_parent=False
    ):
    """ validates the start end for a user in a group or over
    all groups if group_id is not given
    """
    session = Session()
    query = session.query(domain_model).filter(
            sql.expression.and_(
            sql.expression.between(date, domain_model.start_date, domain_model.end_date),
            domain_model.user_id == user_id)
            )
    if group_id:
        query = query.filter(domain_model.group_id == group_id)
    if with_parent:
        query = query.filter(domain_model.parent_group_id == parent_id)
    results = query.all()
    if results:
        if obj:
            for result in results:
                if result.membership_id == obj.membership_id:
                    continue
                else:
                    yield result
        else:
           for result in results:
                yield result


def validate_open_membership(obj, domain_model, user_id, 
        group_id=None, parent_id=None, with_parent=False
    ):
    session = Session()
    query = session.query(domain_model).filter(
        sql.expression.and_(
            domain_model.end_date == None, domain_model.user_id == user_id)
    )
    if group_id:
        query = query.filter(domain_model.group_id == group_id)
    if with_parent:
        query = query.filter(domain_model.parent_group_id == parent_id)
    results = query.all()
    if results:
        if obj:
            for result in results:
                if result.membership_id == obj.membership_id:
                    continue
                else:
                    yield result
        else:
           for result in results:
                yield result

''' !+UNUSED
def get_parliament_by_date_range(start_date, end_date):
    session = Session()
    parliament = session.query(domain.Parliament).filter(
        (domain.Parliament.start_date < start_date) & \
        ((domain.Parliament.end_date == None) | \
         (domain.Parliament.end_date > end_date))).\
        order_by(desc(domain.Parliament.election_date)).first()
    #session.close()
    return parliament
'''

''' !+UNUSED
def get_session_by_date_range(start_date, end_date):
    session = Session()
    ps = session.query(domain.ParliamentSession).filter(
        (domain.ParliamentSession.start_date < start_date) & \
        ((domain.ParliamentSession.end_date == None) | \
         (domain.ParliamentSession.end_date > end_date))).first()
    #session.close()
    return ps 
'''

def get_sittings_between(sittings, start, end):
    modifier = sittings.getQueryModifier()
    sittings.setQueryModifier(
        sql.and_(
            modifier,
            sql.or_( 
                sql.between(schema.sitting.c.start_date, start, end), 
                sql.between(schema.sitting.c.end_date, start, end),
                sql.between(start, schema.sitting.c.start_date, 
                    schema.sitting.c.end_date),
                sql.between(end, schema.sitting.c.start_date, 
                    schema.sitting.c.end_date)
            ),
        ))
    query = sittings._query
    sittings.setQueryModifier(modifier)
    return query



''' UNUSED

# !+ mv to models.utils
def get_user_id(name):
    session = Session()
    userq = session.query(domain.User).filter(schema.user.c.login == name )
    results = userq.all()
    if results:
        user_id = results[0].user_id
    else:
        user_id = None
    return user_id

def check_with_sql(sql_statement, **check_dict):
    """
    Run SQL with variables in the dict
    """
    query = execute_sql(sql_statement, **check_dict)
    result = query.fetchone()
    if result is None:
        return result
    else:
        return result[0]


def check_date_in_interval( pp_key, checkDate, sql_statement):
    """
    Check if the checkDate is inside one of its 'peers'
    the passed sql statement must follow the restrictions:
    date: is the date to check (must be present!)
    parent_key: is usually the parents primary key (can be omitted to check all)
    """
    if (type(checkDate) is datetime.datetime or type(checkDate) is datetime.date):
        checkDict = { 'date': checkDate, 'parent_key': pp_key }
        return check_with_sql(sql_statement, **checkDict)
    else:
        raise TypeError


def check_start_end_dates_in_interval( pp_key, data, sql_statement):
    """ 
    Check if start and end dates are not overlapping with a prior or later peer
    """
    errors =[]
    overlaps = check_date_in_interval(pp_key, data['start_date'], sql_statement)
    if overlaps is not None:
        errors.append( interface.Invalid(_("The start date overlaps with (%s)" % overlaps), "start_date" ))
    if data['end_date'] is not None:
        overlaps = check_date_in_interval(pp_key, data['end_date'], sql_statement)
        if overlaps is not None:
            errors.append( interface.Invalid(_("The end date overlaps with (%s)" % overlaps), "end_date" )) 
    return errors 


class SQLQuerySource ( object ):
    """ Call with a SQL Statement and the rows which make up the vocabulary
    note that a % wildcard for sql LIKEs must be escaped as %%
   
    Values passed in the filter dictionary can be either constant strings 
    or they can refer to an attribute of the object. To denote the attribute 
    pass the attributes name with a leading dollar sign i.e: $member_id
     
    The value of the primary key of the *parent(!)* 
    can be accessed with :primary_key
       
    You can call this function without filters on any object, 
    if you need filters the object needs to have a context i.e, 
    you can call it on edit/view for any object. If you want to add an object
    it must be a childobject of something.
    """
    
    interface.implements( IContextSourceBinder )

        
    def getValueKey(self, context):
        """ Iterate through the parents until you get a valueKey 
        """
        if context.__parent__ is None:
            return None
        else:
            try:
                value_key = valueKey( context.__parent__.__name__ )[0]
            except:
                value_key = self.getValueKey( context.__parent__)
        return value_key
    
    def __init__( self, sql_statement, token_field, value_field, filter = {}, title_field=None ):
        self.sql_statement = sql_statement
        self.token_field = token_field
        self.value_field = value_field
        self.title_field = title_field
        self.filter = filter
    
    def constructFilterDict( self, filter_dict, context ):
        """
        replace the variable filtervalues with attribute values of the 
        current context object
        """
        trusted=removeSecurityProxy(context)
        filter = {}
        for key in filter_dict.keys():
            if str(filter_dict[key]).startswith('$'):
                value =filter_dict[key][1:]
                filter_dict[key] = trusted.__dict__[value]
        return filter_dict
        
        
        
    def constructQuery( self, context ):
        session = Session()
        if  self.sql_statement.find(':primary_key') > 1:
            #if the keyword primary key is present in the sql 
            #replace it with the parent pk
            pfk = self.getValueKey(context)
            filter_dict = {'primary_key' : pfk}
        else:
            filter_dict = {}
        filter_dict.update(self.filter)
        filter_dict = self.constructFilterDict( filter_dict, context )
        query = execute_sql(self.sql_statement, **filter_dict)
        return query
        
    def __call__( self, context=None ):
        query = self.constructQuery( context )
        results = query.fetchall()
        
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
 
/UNUSED'''


