Setup
-----
Setting up Database Connection and Utilities:

   >>> import bungeni.models.domain as model
   >>> import datetime
   >>> import bungeni.models.testing
   >>> db = bungeni.models.testing.setup_db()
   >>> from bungeni.alchemist import Session
   >>> session = Session()
   >>> from bungeni.ui.forms.test_dates import today, yesterday, tomorrow, dayat

   
Note that we only test the overlap of 'peers' here.
refer to test_dates.py to test  that contained objects are inside
their parents dates
   
Parliaments
-----------
   
   >>> parliament = model.Parliament( short_name=u"p_1", start_date=today, election_date=yesterday, end_date=tomorrow)
   >>> parliament.language = "en"
   >>> session.add( parliament)
   >>> session.flush()
   
   >>> int(parliament.parliament_id) 
   1
   
   >>> from bungeni.ui.forms import validations

   
Before you can add a new parliament all others must be closed
   
   
Add a new (open ended) parliament
   >>> parliament2 = model.Parliament( short_name=u"p_2", start_date=tomorrow, election_date=today, end_date=None)
   >>> parliament2.language = "en"
   >>> session.add( parliament2)
   >>> session.flush()
   
Note that the date yesterday is well ouside our p_2 so it does not matter.

give the 2nd parliament an end date and save
   >>> parliament2.end_date = dayat
   >>> session.flush() 
   
No open parliaments  anymore 

   
Now check for overlapping dates but not for the current (edited) parliament
   

   
Add a governmemt:

   >>> gov = model.Government(short_name=u"gov_1", start_date=today, end_date=tomorrow )
   >>> gov.parent_group_id = parliament.parliament_id
   >>> gov.language = "en"
   >>> session.add( gov )
   >>> session.flush() 
 
   

Add a second government

   >>> gov2 = model.Government(short_name=u"gov_2", start_date=tomorrow, end_date=dayat )
   >>> gov2.parent_group_id = parliament.parliament_id
   >>> gov2.language = "en"
   >>> session.add( gov2 )
   >>> session.flush()


Sessions
-----------
A parliamentary Session

   >>> sess = model.Session()
   >>> sess.parliament_id = parliament.parliament_id
   >>> sess.short_name = u"First Session"
   >>> sess.full_name = u"First Session"
   >>> sess.start_date = yesterday
   >>> sess.end_date = today
   >>> sess.language = "en"
   >>> session.add(sess)
   >>> session.flush() 
 
   >>> int(sess.session_id)
   1
 

 
A second session
 
   >>> sess2 = model.Session()
   >>> sess2.parliament_id = parliament.parliament_id
   >>> sess2.short_name = u"2nd Session"
   >>> sess2.full_name = u"2nd Session"
   >>> sess2.start_date = tomorrow
   >>> sess2.end_date = dayat
   >>> sess2.language = "en"
   >>> session.add(sess2)
   >>> session.flush()
 

 
Sittings
---------
 
    >>> ssit = model.Sitting()
    >>> ssit.group_id = parliament.parliament_id
    >>> ssit.start_date = today
    >>> ssit.end_date = tomorrow
    >>> ssit.language = "en"
    >>> session.add(ssit)
    >>> session.flush()

Just check if we get something back because the return value depends on the times


   
   
For Edit we need to be sure we do not check for the current data itself.
   
    >>> ssit2 = model.Sitting()
    >>> ssit2.group_id = parliament.parliament_id
    >>> ssit2.start_date = yesterday
    >>> ssit2.end_date = today
    >>> ssit2.language = "en"
    >>> session.add(ssit2)
    >>> session.flush()
   
Just a quick check that the above validation for yesterday now fails

and the real check
            
Parliament members

add some users:
    >>> mp_1 = model.User(u"mp_1", 
    ...        first_name=u"a", 
    ...        last_name=u'ab', 
    ...        email=u"mp1@example.com", 
    ...        date_of_birth=today,
    ...        language="en",
    ...        gender='M')
    >>> mp_2 = model.User(u"mp_2", 
    ...        first_name=u"b", 
    ...        last_name=u"bc", 
    ...        date_of_birth=today,
    ...        email=u"mp2@example.com",
    ...        language="en",
    ...        gender='M')
    >>> session.add(mp_1)
    >>> session.add(mp_2)
    >>> session.flush()
    
    >>> mp1 = model.MemberOfParliament()
    >>> mp1.group_id = parliament.group_id
    >>> mp1.user_id = mp_1.user_id
    >>> mp1.start_date = today
    >>> mp1.provenace = "r1::p1::c1"
    >>> mp1.member_election_type = "elected"
    >>> mp1.language = "en"
    >>> session.add(mp1)
    >>> session.flush()
    
    >>> mp2 = model.MemberOfParliament()
    >>> mp2.group_id = parliament.group_id
    >>> mp2.user_id = mp_2.user_id
    >>> mp2.start_date = today
    >>> mp2.representation = "r1::p1::c1"
    >>> mp2.member_election_type = "nominated"
    >>> mp2.language = "en"
    >>> session.add(mp2)
    >>> session.flush()


clean up - commit open transactions
---------------------------------

   >>> session.flush()
   >>> session.close() 
         
         
   
