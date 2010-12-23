''' !+DATERANGEFILTER(mr, dec-2010) disabled until intention is understood

from sqlalchemy import sql
import domain

def between(column):
    return sql.and_(
        sql.or_(
            column >= sql.bindparam("start_date"),
            sql.bindparam("start_date") == None),
        sql.or_(
            column <= sql.bindparam("end_date"),
            sql.bindparam("end_date") == None),
        )

def bill_filter(domain_model): 
    return sql.or_(
    between(domain_model.submission_date),
    between(domain_model.publication_date)
    )

def motion_filter(domain_model):
    import pdb; pdb.set_trace();
    return sql.or_(
    between(domain_model.submission_date),
    between(domain_model.notice_date),
    between(domain_model.admissible_date),
    )

def question_filter(domain_model):
    return sql.or_(
    between(domain_model.submission_date),
    between(domain_model.ministry_submit_date),
    between(domain_model.admissible_date),
    )

def tableddocument_filter(domain_model):
    return sql.or_(
    between(domain_model.submission_date),
    between(domain_model.admissible_date),
    )


def group_filter(domain_model):
    return sql.or_(
    domain_model.start_date.between(
                sql.bindparam("start_date"), sql.bindparam("end_date")),
    domain_model.end_date.between(
                sql.bindparam("start_date"), sql.bindparam("end_date")),
    sql.between(sql.bindparam("start_date"), 
                domain_model.start_date, domain_model.end_date),
    sql.between(sql.bindparam("end_date"),
                domain_model.start_date, domain_model.end_date),
    sql.and_(
        domain_model.start_date <= sql.bindparam("end_date"),
        domain_model.end_date == None),
    )
            
    
def group_membership_filter(domain_model):
    return sql.or_(
    domain_model.start_date.between(
            sql.bindparam("start_date"), sql.bindparam("end_date")),
    domain_model.end_date.between(
            sql.bindparam("start_date"), sql.bindparam("end_date")),
    sql.between(sql.bindparam("start_date"), 
                domain_model.start_date, 
                domain_model.end_date),
    sql.between(sql.bindparam("end_date"),
                domain_model.start_date, 
                domain_model.end_date),
    sql.and_(
        domain_model.start_date <= sql.bindparam("end_date"),
        domain_model.end_date == None),
    )
    
    
def session_filter(domain_model):
    return sql.or_(
    domain_model.start_date.between(
                sql.bindparam("start_date"), sql.bindparam("end_date")),
    domain_model.ParliamentSession.end_date.between(
                sql.bindparam("start_date"), sql.bindparam("end_date")),
    sql.between(sql.bindparam("start_date"), 
                domain_model.start_date, domain_model.end_date),
    sql.between(sql.bindparam("end_date"),
                domain_model.start_date, domain_model.end_date),
    sql.and_(
        domain_model.start_date <= sql.bindparam("end_date"),
        domain_model.end_date == None),
    )
    
    
def sitting_filter(domain_model):
    return sql.or_(
    domain_model.start_date.between(
                sql.bindparam("start_date"), sql.bindparam("end_date")),
    domain_model.end_date.between(
                sql.bindparam("start_date"), sql.bindparam("end_date")),
    sql.between(sql.bindparam("start_date"), 
                domain_model.start_date, domain_model.end_date),
    sql.between(sql.bindparam("end_date"),
                domain_model.start_date, domain_model.end_date),
    sql.and_(
        domain_model.start_date <= sql.bindparam("end_date"),
        domain_model.end_date == None),
    )
    
    
'''
