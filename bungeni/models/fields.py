from hashlib import md5
from sqlalchemy.types import TypeDecorator, String
from sqlalchemy.util import buffer
from zope.component import getUtility


class FSBlob(TypeDecorator):
    """ Sqlalchemy's type to store
        blob data in IFSUtility and the
        file name in the database
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

    def result_processor(self, dialect):
        def process(value):
            if not value:
                return None
            return buffer(self.fs.get(value))
        return process

    def copy(self):
        return FSBlob()
