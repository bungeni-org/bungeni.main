from Testing import ZopeTestCase
from zope.component import testing

import transaction
import Products.Five

from Products.Five import zcml
#from Products.Five import pythonproducts

ZopeTestCase.installProduct('PlonePAS')
ZopeTestCase.installProduct('PluggableAuthService')
ZopeTestCase.installProduct('StandardCacheManagers')

from Products.PlonePAS.Extensions import Install as ppasinstall
#pythonproducts.setupPythonProducts(None)

import sqlalchemy as rdb

import bungeni.plonepas
from bungeni.plonepas import schema

SANDBOX_ID = 'sandbox'

class SQLLayer:

    @classmethod
    def setUp( cls ):
        testing.setUp()
        zcml.load_config('meta.zcml', Products.Five)
        zcml.load_config('configure.zcml', bungeni.plonepas )

        app = ZopeTestCase.app()

        # Create our sandbox
        app.manage_addFolder(SANDBOX_ID)
        sandbox = app[SANDBOX_ID]
        
        # Setup the DB connection and PAS instances
        db = rdb.create_engine('sqlite://')
        schema.metadata.bind = db
        schema.metadata.create_all()
        cls.pas = cls.setupPAS(sandbox)

        transaction.commit()
        ZopeTestCase.close(app)

    @classmethod
    def tearDown(cls):
        testing.tearDown()
        app = ZopeTestCase.app()
        schema.metadata.drop_all()
        app.manage_delObjects( SANDBOX_ID )
        transaction.commit()
        ZopeTestCase.close(app)
        
    @classmethod
    def setupPAS(cls, container):
        factory = container.manage_addProduct['PluggableAuthService']
        factory.addPluggableAuthService(REQUEST=None)
        pas = container.acl_users
        ppasinstall.registerPluginTypes(pas)
        from bungeni.plonepas import install
        install.install_pas_plugins( container )
        return pas

class BaseTestCase( ZopeTestCase.ZopeTestCase ):
    
    layer = SQLLayer

    def getPAS( self ):
        return self.layer.pas
    
    def beforeTearDown( self ):
        schema.user_group_memberships.delete().execute()
        schema.groups.delete().execute()
        schema.users.delete().execute()
