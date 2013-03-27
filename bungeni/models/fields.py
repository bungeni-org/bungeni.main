from md5 import md5
from sqlalchemy.types import TypeDecorator, Binary, String
from sqlalchemy.util import buffer
from zope.component import getUtility

class FSBlob(TypeDecorator, Binary):
    """Sqlalchemy's type to store blob data in IFSUtility and the file name 
    in the database. Deriving also from Binary class, for alchemist to be able
    to translate it to zope.schema's field.
    """
    
    impl = String
    
    @property
    def fs(self):
        from bungeni.core.interfaces import IFSUtility
        return getUtility(interface=IFSUtility)
    
    def bind_processor(self, dialect):
        def process(value):
            if value:
                fname = md5(value).hexdigest()
                self.fs.store(value, fname)
                return fname
        return process
    
    def result_processor(self, dialect, coltype=None):
        def process(value):
            if not value:
                return None
            return buffer(self.fs.get(value) or "")
        return process
    
    def copy(self):
        return FSBlob()
