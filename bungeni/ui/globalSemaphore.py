from threading import BoundedSemaphore
from zope.component import getUtility
from interfaces import IOpenOfficeConfig

# Singleton semaphore used to limit the number of connections to openoffice
# to number set in openoffice.zcml
maxConnections = getUtility(IOpenOfficeConfig).getMaxConnections()
globalOpenOfficeSemaphore =  BoundedSemaphore(value=maxConnections) 
