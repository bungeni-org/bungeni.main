from interfaces import IFSUtility
from threading import RLock
from zope.component import getUtility
from zope.component.zcml import handler
from zope.interface import implements
from bungeni.utils.misc import get_bungeni_installation_dir
import os


class FileStorageUtility(object):
    """ see bungeni.core.interfaces.IFSUtility
    """

    implements(IFSUtility)

    def __init__(self, fs_path):
        self.fs_path = os.path.join(get_bungeni_installation_dir(), fs_path)
        self.lock = RLock()
        if not os.path.exists(self.fs_path):
            raise ValueError("Unable to find storage path: %s" % self.fs_path)

    def store(self, data, filename):
        filepath = os.path.join(self.fs_path, filename)
        self.lock.acquire()
        file = open(filepath, 'wb')
        file.write(data)
        file.close()
        self.lock.release()

    def remove(self, filename):
        filepath = os.path.join(self.fs_path, filename)
        self.lock.acquire()
        if os.path.exists(filepath):
            os.remove(filepath)
        self.lock.release()

    def get(self, filename):
        filepath = os.path.join(self.fs_path, filename)
        data = None
        if os.path.exists(filepath):
            self.lock.acquire()
            file = open(filepath, 'rb')
            data = file.read()
            file.close()
            self.lock.release()
        return data


def filestorage(_context, name=u'', fs_path=u''):
    r = FileStorageUtility(fs_path)
    _context.action(
        discriminator=('utility', IFSUtility, name),
        callable=handler,
        args=('registerUtility',
                r, IFSUtility, name)
        )

