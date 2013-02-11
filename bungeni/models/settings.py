# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Settings
We model settings as zope3 interfaces and schemas.
We can define a property sheet for an arbitrary database object, 
or for the application itself.

$Id$
$URL$
"""

# !!!!! Cleanout this source file !!!!!

from zope import schema
from zope.security.proxy import removeSecurityProxy
import sqlalchemy as sa
from sqlalchemy import orm
from schema import setting

import datetime
import interfaces

class TypeSerializer( object ):

    mapping = {
        schema.Int : ( str, int ),
        schema.Date : ( lambda x: "%s-%s-%s"%(x.year, x.month, x.day ), lambda x: datetime.date(*(map( int, x.split('-'))) ) ),
        schema.Float : ( str, float ),
        schema.Bool : ( lambda x: str(int(x)), lambda x: bool( int( x ) ) ),
        }

    @classmethod
    def serialize( cls, value, field ):
        ops = cls.mapping.get( field.__class__ )
        if ops is None:
            return value
        serializer, deserializer = ops
        return serializer( value )

    @classmethod
    def deserialize( cls, value, field ):
        ops = cls.mapping.get( field.__class__)
        if ops is None:
            return value
        serializer, deserializer = ops
        return deserializer( value )
        
    
class SettingsBase( object ):
    
    settings_schema = None

    def __init__( self, context ):
        self.context = context
        self._data, self._storedattrs = self._fetch()
    
    def _fetch( self ):
        oid, otype = self._context()
        values = sa.select( [setting.c.name, setting.c.value ],
                             sa.and_( setting.c.propertysheet == self.settings_schema.__name__,
                                       setting.c.object_type == otype,
                                       setting.c.object_id == oid )
                             )
        d = {}
        names = set()
        for r in values.execute():
            field = self.settings_schema.get( r.name )
            if not field:
                continue
            d[ r.name ] = TypeSerializer.deserialize( r.value, field )
            names.add( r.name )
        for i in ( set( self.settings_schema.names(1) ) - names ):
            field = self.settings_schema[i]
            d[i] = field.default
        return d, names
        
    def _context( self ):
        unwrapped = removeSecurityProxy( self.context )
        mapper = orm.object_mapper( unwrapped )
        primary_key = mapper.primary_key_from_instance( unwrapped )[0]
        return primary_key,  unwrapped.__class__.__name__.lower()

    def _store( self, k, v ):

        fs = self.settings_schema.get( k )
        if not fs:
            raise AttributeError("Invalid Settings Field %s"%k)
        
        oid, otype = self._context()
        field = self.settings_schema.get( k )
        svalue = TypeSerializer.serialize( v, field )
        values=dict( object_id = oid,
                     object_type = otype,
                     propertysheet = self.settings_schema.__name__,
                     name = k,
                     value = svalue,
                     type = fs.__class__.__name__ )
        if k not in self._storedattrs:
            statement = setting.insert(values=values)
            self._storedattrs.add( k )
        else:
            statement = setting.update(
                whereclause=sa.and_( setting.c.name == k,
                    setting.c.propertysheet == \
                        self.settings_schema.__name__,
                    setting.c.object_type == otype,
                    setting.c.object_id == oid,
                ),
                values=values,
            )
        statement.execute()

    # mapping interface
    
    def __getitem__( self, k ):
        return self._data[k]
    
    def get( self, k, default=None ):
        return self._data.get(k, default)

    def __setitem__( self, k, v):
        if k in self._data and self._data[k] == v:
            return
        self._store( k, v)
        self._data[k] = v
        
    def keys( self ):
        return self._data.keys()

    def items( self ):
        return self._data.items()

    def __len__( self ):
        return len(self._data)
    
class UserSettingsBase( SettingsBase ):
    pass

class GlobalSettingsBase( SettingsBase ):

    def _context( self ):
        return None, None

_marker = object()

def UserSettingFactory( iface ):
    """
    given a zope3 interface construct a user settings adapter
    """

    fields = dict( settings_schema = iface )
    for fs in schema.getFields( iface ).values():
        def get( self, field_name=fs.__name__, default=fs.default ):
            value = self.get( field_name, _marker )
            if value is _marker:
                return default
            return value
        def set( self, value, field_name=fs.__name__):
            self[field_name]=value

        fields[ fs.__name__ ] = property( get, set )
        
    return type( "UserSettings%s"%( iface.__name__),
                 ( UserSettingsBase, ),
                 fields )

def GlobalSettingFactory( iface ):
    fields = dict( settings_schema = iface )
    for fs in schema.getFields( iface ).values():
        def get( self, field_name=fs.__name__, default=fs.default ):
            value = self.get( field_name, _marker )
            if value is _marker:
                return default
            return value
        def set( self, value, field_name=fs.__name__):
            self[field_name]=value

        fields[ fs.__name__ ] = property( get, set )
        klass = type( "GlobalSettings%s"%( iface.__name__),
                      ( GlobalSettingsBase, ), fields )
                      
    return klass

UserSettings = UserSettingFactory( interfaces.IBungeniUserSettings )
EmailSettings = GlobalSettingFactory( interfaces.IBungeniEmailSettings )
RegistrySettings = GlobalSettingFactory( interfaces.IBungeniRegistrySettings )

class EmailSettingsUtility( object ):
    #!-EMAIL(murithi, mar-2011) to register utility after app starts
    def __call__( self ):
        return EmailSettings( None )

class RegistrySettingsUtility( object ):
    def __call__( self ):
        return RegistrySettings( None )

