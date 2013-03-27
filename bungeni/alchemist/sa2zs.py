# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Alchemist - SQLAlchemy to Zope3 Schemas

$Id$
"""
log = __import__("logging").getLogger("bungeni.alchemist")

# List everything from this module intended for package-external use.
__all__ = [
    "transmute",
    "SQLAlchemySchemaTranslator",
]


# from bungeni.alchemist, used only here

from bungeni.alchemist.interfaces import (
    ITableSchema,
    TransmutationException, 
    IAlchemistTransmutation,
    #IModelDescriptor,
    IIModelInterface
)


from zope import interface, schema #, component
from zope.interface.interface import InterfaceClass
from zope.schema.interfaces import ValidationError

from sqlalchemy.util import OrderedDict
from sqlalchemy import types as rt
import sqlalchemy as rdb


interface.moduleProvides(IAlchemistTransmutation)


class TableAnnotation(object):
    """Annotations for Table objects, to annotate as needed, the notion
    is that the annotation keys correspond to column, and values correspond
    to application specific column metadata.
    """
    
    _marker = object()
    schema_invariants = ()
    
    def __init__(self, table_name, columns=(), properties=(), 
            schema_order=(), listing_columns=(), order_by=()
        ):
        self.table_name = table_name
        self._options = {}
        self._annot = OrderedDict()
        
        for info in columns:
            self._annot[info["name"]] = info
        
        self.properties = properties
        self.schema_order = schema_order        
        self.listing_columns = listing_columns
        self.order_by = order_by
    
    def __call__(self, iface):
        return self
    
    def __setitem__(self, name, value):
        self._annot[name] = value
    
    def get(self, name, default=None):
        return self._annot.get(name, default)
    
    def __getitem__(self, name):
        return self.get(name)
    
    def values(self):
        return self._annot.values()
    
    def __contains__(self, name):
        return not self._marker == self.get(name, self._marker)


class ColumnTranslator(object):
    
    def __init__(self, schema_field):
        self.schema_field = schema_field
    
    def extract_info(self, column, info):
        d = {}
        d["title"] = unicode(info.get("label", column.name))
        d["description"] = unicode(info.get("description", ""))
        d["required"] = not column.nullable
        
        if not d["required"] and info.get("required"):
            d["required"] = True
        
        # this could be all sorts of things ...
        if isinstance(column.default, rdb.ColumnDefault):
            default = column.default.arg
        else:
            default = column.default
        
        # create a field on the fly to validate the default value... 
        validator = self.schema_field()
        try:
            validator.validate(default)
            d["default"] = default
        except ValidationError:
            pass
        
        return d
    
    def __call__(self, column, annotation):
        info = annotation.get(column.name, {})
        d = self.extract_info(column, info)
        return self.schema_field(**d)


class SizedColumnTranslator(ColumnTranslator):
    
    def extract_info(self, column, info):
        d = super(SizedColumnTranslator, self).extract_info(column, info)
        d["max_length"] = column.type.length
        return d
        

class ColumnVisitor(object):
    
    column_type_map = [
        (rt.Float, ColumnTranslator(schema.Float)),
        (rt.SmallInteger, ColumnTranslator(schema.Int)),
        (rt.Date, ColumnTranslator(schema.Date)),
        (rt.DateTime, ColumnTranslator(schema.Datetime)),
        (rt.Time, ColumnTranslator(schema.Time)),
        (rt.TEXT, ColumnTranslator(schema.Text)),
        (rt.Boolean, ColumnTranslator(schema.Bool)),
        (rt.String, SizedColumnTranslator(schema.TextLine)),
        (rt.Binary, ColumnTranslator(schema.Bytes)),
        (rt.Unicode, SizedColumnTranslator(schema.Bytes)),
        (rt.Numeric, ColumnTranslator(schema.Float)),
        (rt.Integer, ColumnTranslator(schema.Int))
    ]
    
    def __init__(self, info):
        self.info = info or {}
    
    def visit(self, column):
        column_handler = None
        for ctype, handler in self.column_type_map:
            if isinstance(column.type, ctype):
                if isinstance(handler, str):
                    # allow for instance method customization
                    handler = getattr(self, handler)
                column_handler = handler
                break
        if column_handler is None:
            raise TransmutationException("No column handler for %r" % (column))
        return column_handler(column, self.info)


class SQLAlchemySchemaTranslator(object):
    
    def apply_properties(self, field_map, annotation):
        # apply manually overridden fields/properties, pay attention
        # to field ordering according to values passed into the
        # annotation.
        
        # field_map: {field_name: zope.schema.*}
        
        order_value = 0
        cascade_order = False
        
        values = list(annotation.values())
        for idx in range(len(values)): # annotation.fields_by_name !!
            info = values[idx] # info -> field_descriptor !
            if info.name in field_map:
                #zsp = field_map[info.name]
                #print "    before:", info.name, zsp.order, info.property, "<>", zsp, info.property is zsp
                if info.property:
                    if cascade_order:
                        order_value += 2
                        field_map[info.name] = f = info.property
                        f.order = order_value
                if cascade_order:
                    order_value += 2
                    field_map[info.name].order = order_value
                else:
                    order_value = field_map[info.name].order
            if not info.property:
                continue
            cascade_order = True
            order_value += 2
            field_map[info.name] = info.property
            field_map[info.name].order = order_value
            #zsp = field_map[info.name]
            #print "     after:", info.name, zsp.order, info.property, "<>", zsp, info.property is zsp
    
    def apply_ordering(self, field_map, schema_order):
        """Apply global ordering to all fields, any fields not specified have 
        ordering preserved, but are now located after fields specified in the 
        schema order, which is a list of field names.
        """
        self.verify_names(field_map, schema_order) # verify all names are in present
        visited = set() # keep track of fields modified
        order = 1  # start off ordering values
        for s in schema_order:
            field_map[s].order = order
            visited.add(s)
            order += 1
        remainder = [(field.order, field) 
            for field_name, field in field_map.items() 
            if field_name not in visited ]
        remainder.sort()
        for order, field in remainder:
            field.order = order
            order += 1
    
    def verify_names(self, field_map, names):
        for n in names:
            if not n in field_map:
                raise AssertionError("invalid field specified  %s"%(n))
    
    def generate_fields(self, table, annotation):
        visitor = ColumnVisitor(annotation)        
        d = {}
        for column in table.columns:
            #!+OMIT obsolete
            #if annotation.get(column.name, {}).get("omit", False):
            #    continue
            d[column.name] = visitor.visit(column)
        return d
    
    def apply_tagged_values(self, iface, annotation, kw):
        invariants = kw.get("invariants") or annotation.schema_invariants 
        if not invariants:
            return
        assert isinstance(invariants, (list, tuple))
        iface.setTaggedValue("invariants", invariants)
    
    def translate(self, table, annotation, __module__, **kw):
        annotation = annotation or TableAnnotation(table.name) 
        iname = kw.get("interface_name") or "I%sTable"%table.name
        field_map = self.generate_fields(table, annotation)
        
        # apply manually overridden fields/properties
        self.apply_properties(field_map, annotation)
        
        # apply global schema ordering
        schema_order = kw.get("schema_order", None) or annotation.schema_order
        if schema_order:
            self.apply_ordering(field_map, schema_order)
        
        # verify table columns
        #if annotation.listing_columns:
        #    self.verify_names(field_map, annotation.listing_columns)
        
        # extract base interfaces
        if "bases" in kw:
            bases = (ITableSchema,) + kw.get("bases")
        else:
            bases = (ITableSchema,)
        
        DerivedTableSchema = InterfaceClass(iname,
            attrs=field_map,
            bases=bases,
            __module__=__module__)
        
        self.apply_tagged_values(DerivedTableSchema, annotation, kw)
        
        return DerivedTableSchema


def transmute(table, annotation=None, __module__=None, **kw):
    assert __module__ is not None, "Must specify target module."
    z3iface = SQLAlchemySchemaTranslator().translate(
        table, annotation, __module__, **kw)
    # mark the interface itself as being model driven
    interface.directlyProvides(z3iface, IIModelInterface)
    ''' !+UNUSED?
    # provide a named annotation adapter to go from the iface back to the annotation
    if annotation is not None:
        name = "%s.%s"%(z3iface.__module__, z3iface.__name__)
        component.provideAdapter(annotation,
            adapts=(IIModelInterface,),
            provides=IModelDescriptor, name = name)
    '''
    return z3iface


'''
def transmute_mapper(mapper, annotation=None, __module__=None, **kw):
    pass
'''    
