-------------
Bungeni Model
-------------

Setup
-----

some setup for tests
   >>> from zope import component
   >>> from bungeni.alchemist import Session
   >>> from bungeni.models import domain as model
   >>> import datetime
   >>> from sqlalchemy.orm import mapper
   >>> from bungeni.models import domain, schema
   >>> import bungeni.models.testing
   >>> db = bungeni.models.testing.setup_db()
   >>> session = Session()

region, country, province
--------------------------
get some values in those tables as they are needed later on

 >>> country = domain.Country()
 >>> country.country_id = 'KE'
 >>> country.country_name = u"Kenya"
 >>> country.iso_name = u"KENYA" 
 >>> country.language = "en" 
 >>> session.add(country)
 >>> session.flush()
 >>> country.country_id
 'KE'
 >>> country.country_name
 u'Kenya'

Representation (region/province/constituency) is a (UI) hierarchical UI vocabulary.

Users
-----

First we can create some users.

  >>> user = domain.User("jsmith")
  >>>

Members of Parliament
---------------------

  >>> mp_1 = domain.User(u"mp_1", 
  ...        first_name=u"a", 
  ...        last_name=u'ab', 
  ...        birth_country="KE",
  ...        email=u"mp1@example.com", 
  ...        date_of_birth=datetime.datetime.now(),
  ...        language="en",
  ...        gender='M')
  >>> mp_2 = domain.User(u"mp_2", 
  ...        first_name=u"b", 
  ...        last_name=u"bc", 
  ...        birth_country="KE",
  ...        date_of_birth=datetime.datetime.now(),
  ...        email=u"mp2@example.com",
  ...        language="en",
  ...        gender='M')
  >>> mp_3 = domain.User(u"mp_3",
  ...        first_name=u"c", 
  ...        birth_country="KE",
  ...        last_name=u"cd",
  ...        date_of_birth=datetime.datetime.now(),
  ...        email=u"mp3@example.com", 
  ...        language="en",
  ...        gender='F')

Groups
------

Bungeni uses groups to model any collection of users. The relational inheritance
features of sqlalchemy to allow for subclassing group, with value storage in a 
different table. Bungeni uses this feature to model parliaments, committees, 
political groups, etc. Let's create some groups in the system to examine how
they work.

  >>> parliament = domain.Parliament(short_name=u"p_1", start_date=datetime.datetime.now(), election_date=datetime.datetime.now(), group_role="bungeni.MP")
  >>> parliament.principal_name = "parl_01"
  >>> parliament.language = "en"
  >>> session.add(parliament)
  >>> session.flush()
  
  >>> political_group_a = domain.PoliticalGroup(short_name=u"pp_1", start_date=datetime.datetime.now(), group_role="bungeni.MemberPoliticalGroupAssembly")
  >>> political_group_a.principal_name = "pga_01"
  >>> political_group_a.parent_group_id = parliament.parliament_id
  >>> political_group_a.language = "en"
  >>> political_group_b = domain.PoliticalGroup(short_name=u"pp_2", start_date=datetime.datetime.now(), group_role="bungeni.MemberPoliticalGroupAssembly")
  >>> political_group_b.principal_name = "pgb_01"
  >>> political_group_b.parent_group_id = parliament.parliament_id
  >>> political_group_b.language = "en"
  >>> session.add(political_group_a)
  >>> session.add(political_group_b)
  >>> session.flush()

  >>> session.add(mp_1)
  >>> session.add(mp_2)
  >>> session.add(mp_3)
  >>> session.flush()


The actual committee

  >>> committee_a = domain.Committee(short_name=u"committee_1", 
  ...       start_date=datetime.datetime.now(),
  ...       principal_name="com_01",
  ...       group_role="bungeni.CommitteeMember")
  >>> committee_a.parent_group_id = parliament.parliament_id
  >>> committee_a.sub_type = "housekeeping"
  >>> committee_a.group_continuity = "permanent"
  >>> committee_a.language = "en"
  >>> session.add(committee_a)

A user is associated to a group via a membership, where we can store additional properties, such
as a user's role/title in a group.

Let's create some memberships and see what we can do with them.

  >>> for mp in [ mp_1, mp_2, mp_3 ]:
  ...    membership = domain.GroupMembership()
  ...    membership.user = mp
  ...    membership.group = committee_a
  ...    membership.language = "en"
  ...    session.add(membership)
  ...    membership = domain.GroupMembership()
  ...    membership.user = mp
  ...    membership.group = political_group_a
  ...    membership.language = "en"
  ...    session.add(membership)
  

Check that we can access the membership through the containment object

  >>> session.flush()
  >>> len(list(committee_a.members))
  3

Group and user addresses
-------------------------

Add a user address
  >>> user_address_1 = domain.UserAddress()
  >>> user_address_1.principal_id = mp_1.user_id
  >>> user_address_1.logical_address_type = "home"
  >>> user_address_1.postal_address_type = "street"
  >>> user_address_1.street = u"MP1 Avenue"
  >>> user_address_1.city = u"Megapolis"
  >>> user_address_1.country = country
  >>> session.add(user_address_1)
  >>> session.flush()
  >>> int(user_address_1.address_id)
  1
  >>> len(list(mp_1.addresses))
  1

Add a group address
  >>> group_address_1 = domain.GroupAddress()
  >>> group_address_1.principal_id = parliament.group_id
  >>> group_address_1.logical_address_type = "home"
  >>> group_address_1.postal_address_type = "street"
  >>> group_address_1.street = u"Parliament Road"
  >>> group_address_1.city = u"Loliondo"
  >>> group_address_1.country = country
  >>> session.add(group_address_1)
  >>> session.flush()
  >>> int(group_address_1.address_id)
  2
  >>> len(list(parliament.addresses))
  1

Government
----------
  >>> gov = domain.Government(short_name=u"gov_1", start_date=datetime.datetime.now())
  >>> gov.principal_name = "gov_01"
  >>> gov.group_role = "bungeni.GovernmentMember"
  >>> gov.parent_group_id = parliament.parliament_id
  >>> gov.language = "en"
  >>> session.add(gov)
  >>> session.flush()
  >>> gov.parent_group
  <bungeni.models.domain.Parliament object at ...>


Ministries
-----------
  >>> ministry = domain.Ministry(short_name=u"ministry", start_date=datetime.datetime.now())
  >>> ministry.principal_name = "min_01"
  >>> ministry.group_role = "bungeni.MinistryMember"
  >>> ministry.parent_group_id = gov.group_id
  >>> ministry.language = "en"
  >>> session.add(ministry)
  >>> session.flush()
  
  >>> ministry.parent_group
  <bungeni.models.domain.Government object at ...>
  
  >>> gov.contained_groups
  [<bungeni.models.domain.Ministry object at ...>]


Groups in a parliament:
-----------------------
  >>> from bungeni.models.utils import get_all_group_ids_in_parliament
  >>> pgroups = get_all_group_ids_in_parliament(parliament.parliament_id)
  
  >>> len(pgroups)
  6



Offices
--------------------------------
Test office and office role and sub role creation

  >>> speaker_office = domain.Office()
  >>> speaker_office.short_name = u"Speakers office"
  >>> speaker_office.start_date = datetime.datetime.now()
  >>> speaker_office.principal_name = "so_01"
  >>> speaker_office.group_role = "bungeni.Speaker"
  >>> speaker_office.language = "en"
  >>> session.add(speaker_office)
  >>> session.flush()

Speaker's Office Sub Role

  >>> title_type = domain.TitleType()
  >>> title_type.group = speaker_office
  >>> title_type.title_name = u"Speaker's Assistant"
  >>> title_type.role_id = "bungeni.Speaker.Assistant"
  >>> title_type.user_unique = True
  >>> title_type.sort_order = 10
  >>> title_type.language = "en"
  >>> session.add(title_type)
  >>> session.flush()

Speaker's Office User

  >>> office_user = domain.User()
  >>> office_user.login = "speaker.P1_01"
  >>> office_user.first_name = "First"
  >>> office_user.last_name = "Last"
  >>> office_user.email = "speaker@bungeni.org"
  >>> office_user.gender = "M"
  >>> office_user.language = "en"
  
Speaker's Office membership 
 
  >>> office_membership = domain.OfficeMember()
  >>> office_membership.user_id = office_user.user_id
  >>> office_membership.group_id = speaker_office.group_id
  >>> office_membership.start_date = datetime.datetime.now()
  
Speaker's Office Title with Sub role  
  
  >>> office_title = domain.MemberTitle()
  >>> office_title.membership_id = office_membership.membership_id
  >>> office_title.title_type_id = title_type.title_type_id
  >>> office_title.start_date = datetime.datetime.now()

Members of parliament
----------------------
Members of parliament are defined by their membership in
the parliaments group and additional attributes.

  >>> mp4 = domain.MemberOfParliament()
  >>> mp4.group_id = parliament.group_id
  >>> mp4.user_id = mp_1.user_id
  >>> mp4.start_date = datetime.datetime.now()
  >>> mp4.representation = "r1::p2::c3"
  >>> mp4.member_election_type = "elected"
  >>> mp4.language = "en"
  >>> session.add(mp4)
  >>> session.flush()
  >>> int(mp4.membership_id)
  7


Sittings
--------

any group can schedule a sitting, a sitting is treated as a physical
meeting of the group by the system. 

 >>> sit = domain.Sitting()
 >>> sit.group_id = committee_a.group_id
 >>> sit.start_date = datetime.datetime.now()
 >>> sit.end_date = datetime.datetime.now()
 >>> sit.language = "en"
 >>> session.add(sit)
 >>> session.flush() 

Sitting attendance
-------------------

the attendance of a member at a sitting.

 >>> gsa = domain.SittingAttendance()
 >>> gsa.sitting_id = sit.sitting_id
 >>> gsa.member_id = mp_1.user_id
 >>> gsa.attendance_type = "present"
 >>> session.add(gsa)
 >>> session.flush() 
 
Sessions
-----------
A parliamentary Session

 >>> sess = domain.Session()
 >>> sess.parliament_id = parliament.parliament_id
 >>> sess.short_name = u"First Session"
 >>> sess.full_name = u"First Session XXXX"
 >>> sess.start_date = datetime.datetime.now()
 >>> sess.end_date = datetime.datetime.now()
 >>> sess.language = "en"
 >>> session.add(sess)
 >>> session.flush() 
 
 >>> int(sess.session_id)
 1
 
Sitting in this session 
 
 >>> ssit = domain.Sitting()
 >>> ssit.group_id = parliament.parliament_id
 >>> ssit.start_date = datetime.datetime.now()
 >>> ssit.end_date = datetime.datetime.now()
 >>> ssit.language = "en"
 >>> session.add(ssit)
 >>> session.flush() 
 
Attendance

 >>> sgsa = domain.SittingAttendance()
 >>> sgsa.sitting_id = ssit.sitting_id
 >>> sgsa.member_id = mp_1.user_id
 >>> sgsa.attendance_type = "present"
 >>> session.add(sgsa)
 >>> session.flush() 

Motions
-------
  >>> motion = domain.AssemblyMotion()
  >>> motion.title = u"Motion"
  >>> motion.language = 'en'
  >>> motion.owner = mp_1
  >>> session.add(motion)
  >>> session.flush()

Motions

Questions
---------

Note that the questions workflow is tested separated (see workflows/question.txt).

  >>> question = domain.AssemblyQuestion()
  >>> question.title = u"question"
  >>> question.language = 'en'
  >>> question.owner = mp_2
  >>> question.question_type = "ordinary"
  >>> session.add(question)
  >>> session.flush()
  
  >>> int(question.doc_id)
  2
  

Bill
----

  >>> bill = domain.AssemblyBill()
  >>> bill.title = u"Bill"
  >>> bill.doc_type = "member"
  >>> bill.language = 'en'
  >>> bill.owner = mp_3
  >>> session.add(bill)
  >>> session.flush()


Schedule items for a sitting:
-----------------------------

we may either add the id only:

  >>> item_schedule = domain.ItemSchedule()
  >>> item_schedule.item_id = bill.doc_id
  >>> item_schedule.item_type = bill.type
  >>> item_schedule.sitting_id = sit.sitting_id
  >>> session.add(item_schedule)
  >>> session.flush()
  >>> item_schedule.item
  <bungeni.models.domain.AssemblyBill object at ...>
  >>> item_schedule.item.title
  u'Bill'
  >>> item_schedule.item.type
  'assembly_bill'
      
or we can add an object: 
  >>> item_schedule = domain.ItemSchedule()
  >>> item_schedule.item
  
  >>> item_schedule.item = question
  >>> item_schedule.sitting_id = sit.sitting_id
  >>> session.add(item_schedule)
  >>> session.flush()
  >>> item_schedule.item
  <bungeni.models.domain.AssemblyQuestion object at ...>
  
  >>> item_schedule.item_id == question.doc_id
  True
  >>> item_schedule.item.title
  u'question'
  >>> item_schedule.item.type
  'assembly_question'
  
  
  
Rota Preparation
----------------
 
Debates
--------------



Clean up commit outstanding transactions
-----------------------------------------
 >>> session.flush() 
 >>> session.commit()
 >>> session.close()


