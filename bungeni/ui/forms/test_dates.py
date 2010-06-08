import unittest
import datetime
from bungeni.ui.forms.validations import validate_start_date_within_parent 
from bungeni.ui.forms.validations import validate_end_date_within_parent


# get some simple dates for comparisions
today = datetime.date.today()
yesterday = today - datetime.timedelta(1)
tomorrow = today + datetime.timedelta(1)
dayat = today + datetime.timedelta(2)

class DummyObject( object ):
    """
    This has just start and end dates
    """
    start_date = today
    end_date = today
    
class StartDateTestCase ( unittest.TestCase ):
    """ Test the start dates """
    
    
    def setUp( self ):
        self.parent = DummyObject()
        self.data =  {'start_date' : today, 'end_date': today }
        
    def test_startDate_is_none(self):
        """ No start_date never fails"""
        self.data =  {'start_date' : None, 'end_date': today }
        self.parent.start_date = today
        self.parent.end_date = today
        result = validate_start_date_within_parent( self.parent, self.data )
        self.assertEqual(result, [])
        self.parent.start_date = None
        self.parent.end_date = tomorrow
        self.data =  {'start_date' : tomorrow, 'end_date': today }
        result = validate_start_date_within_parent( self.parent, self.data )
        self.assertEqual(result, [])
        
    def test_startDate_eq_start(self):
        """ all dates may be equal """
        self.data =  {'start_date' : today, 'end_date': today }
        self.parent.start_date = today
        self.parent.end_date = today
        result = validate_start_date_within_parent( self.parent, self.data )
        self.assertEqual(result, [])
        
    def test_startDate_lt_start(self):
        "starts before parent"
        self.data =  {'start_date' : today, 'end_date': today }
        self.parent.start_date = tomorrow
        self.parent.end_date = today
        result = validate_start_date_within_parent( self.parent, self.data )
        self.failIfEqual(result, [])

    def test_startDate_gt_start(self):
        """ starts after and ends befor parent  """
        self.data =  {'start_date' : tomorrow, 'end_date': today }
        self.parent.start_date = today
        self.parent.end_date = tomorrow
        result = validate_start_date_within_parent( self.parent, self.data )
        self.assertEqual(result, [])
                
    def test_endDate_lt_start(self):
        """ starts after parents end """
        self.data =  {'start_date' : tomorrow, 'end_date': tomorrow }
        self.parent.start_date = today
        self.parent.end_date = today
        result = validate_start_date_within_parent( self.parent, self.data )
        self.failIfEqual(result, [])
                    
        
class EndDateTestCase ( unittest.TestCase ):
    """ Test the end dates"""
    
    def setUp( self ):
        self.parent = DummyObject()
        self.data =  {'start_date' : today, 'end_date': today }

    def test_endDate_is_none(self):
        """ No end_date never fails"""
        self.data =  {'start_date' : tomorrow, 'end_date': None }
        self.parent.start_date = today
        self.parent.end_date = today
        result = validate_end_date_within_parent( self.parent, self.data )
        self.assertEqual(result, [])
        self.parent.start_date = yesterday
        self.parent.end_date = None
        self.data =  {'start_date' : today, 'end_date': today }
        result = validate_end_date_within_parent( self.parent, self.data )
        self.assertEqual(result, [])
            
        
    def test_endDate_eq_start(self):
        """ all dates may be equal """
        self.data =  {'start_date' : today, 'end_date': today }
        self.parent.start_date = today
        self.parent.end_date = today
        result = validate_end_date_within_parent( self.parent, self.data )
        self.assertEqual(result, [])
        
    def test_endDate_lt_start(self):
        """ end < start """
        self.data =  {'start_date' : yesterday, 'end_date': yesterday }
        self.parent.start_date = today
        self.parent.end_date = tomorrow
        result = validate_end_date_within_parent( self.parent, self.data )
        self.failIfEqual(result, [])
        
    def test_endDate_gt_end(self):
        """ end < end """
        self.data =  {'start_date' : today, 'end_date': tomorrow }
        self.parent.start_date = yesterday
        self.parent.end_date = today
        result = validate_end_date_within_parent( self.parent, self.data )
        self.failIfEqual(result, [])
        
    def test_endDate_gt_start(self):
        """ start < end """
        self.data =  {'start_date' : today, 'end_date': yesterday }
        self.parent.start_date = today
        self.parent.end_date = yesterday
        result = validate_end_date_within_parent( self.parent, self.data )
        self.failIfEqual(result, [])
        
        
                
def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite( StartDateTestCase ))
    suite.addTest(unittest.makeSuite( EndDateTestCase ))
    return suite
    
if __name__ == '__main__':
    unittest.main()
