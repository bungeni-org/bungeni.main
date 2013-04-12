# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Alchemist Ui Descriptor

$Id$
"""
log = __import__("logging").getLogger("bungeni.alchemist.descriptor")


# used directly in bungeni
__all__ = [
    "ModelDescriptor",
    "Field",
    "show",
    "hide",
    "norm_sorted", 
]


from zope import interface
from bungeni.alchemist.interfaces import (
    IModelDescriptor,
    IModelDescriptorField
)
from bungeni.models import roles
from bungeni.ui.utils import common
from bungeni.utils import naming


# local utils

class interned(object):
    """Re-use of same immutable instances."""
    _tuples = {}
    @classmethod
    def tuple(cls, seq):
        key = intern("".join([ str(s) for s in seq ]))
        if not cls._tuples.has_key(key):
           cls._tuples[key] = tuple(seq)
        return cls._tuples[key]

def norm_sorted(seq, normalized_ordering, difference=False):
    if not difference:
        return [ s for s in normalized_ordering if s in seq ]
    else:
        return [ s for s in normalized_ordering if s not in seq ]
        

def validated_set(key, allowed_values, str_or_seq, nullable=False):
    """ (key:str, # the kind of values e.g. "modes" or "roles"
         allowed_values:sequence(str), # full list of valid values
         str_or_seq:either(str, sequence), # whitespace separated str or seq
         nullable:bool # whether to leave a None str_or_seq as is
        ) -> tuple
    
    Note the zero length sequence (or string) is considered valid here--the 
    returned value being the empty tuple.
    
    We return a tuple because tuples are immutable and we can thus safely and
    easily reuse same instances (to reduce application runtime memory usage 
    for these numerous and repetitive memory-resident instances).
    """
    if str_or_seq is None:
        if nullable:
            # we keep None as value, letting the appropriate default value 
            # to be determined downstream
            return None
        str_or_seq = allowed_values
    if isinstance(str_or_seq, basestring):
        # convert to a list, removing any additional whitespace
        seq = str_or_seq.split()
    else: 
        # assume we already have a sequence
        seq = str_or_seq
    for value in seq:
        assert value in allowed_values, \
            """Invalid "%s" item: %s. Must be one of: %s.""" % (
                key, value, tuple(allowed_values))
    # remove duplicates, and ensure a standard ordering -- 
    # as "normalized ordering" we take the order defined by allowed_values
    seq_no_dups = norm_sorted(seq, allowed_values)
    assert len(seq) == len(seq_no_dups), \
        "No duplicates allowed [%s]: %s" % (key, seq)
    return interned.tuple(seq_no_dups)


# show/hide directives

class show(object):
    __slots__ = ["modes", "roles", "_from_hide"]
    def __init__(self, modes=None, roles=None):
        self.modes = Field.validated_modes(modes, nullable=True)
        self.roles = Field.validated_roles(roles, nullable=False)
        self._from_hide = False
    
    def _repr_map(self):
        if not self._from_hide:
            return dict(tag="show", modes=self.modes, roles=self.roles)
        else:
            return dict(tag="hide", modes=self.modes, 
                roles=norm_sorted(self.roles, Field._roles, difference=True))
    def __str__(self):
        return "<%(tag)s(modes=%(modes)s, roles=%(roles)s)>" % (
            self._repr_map())

def hide(modes=None, roles=None):
    """Syntactic sugar, shorthand for show() when negating is easier to state.
    """
    roles = Field.validated_roles(roles, nullable=False)
    s = show(modes, norm_sorted(roles, Field._roles, difference=True))
    s._from_hide = True
    return s


# Field

# Notes:
#
# Field parameters, if specified, should be in the following order:
#   name, label, description, localizable, property, 
#   listing_column, view_widget, edit_widget, add_widget, search_widget
#
#   !+FIELD_PERMISSIONS(mr, nov-2010) view_permission/edit_permission params
#   are deprecated -- when applied to any field (that corresponds to an
#   attribute of the domain's class), the domain.zcml setting for that same
#   class attribute will anyway take precedence.
#
# property
# by default, property itself is None
# if not None, then the property's default values for schema.Field init params:
#   title="", description="", __name__="",
#   required=True, readonly=False, constraint=None, default=None
#
# required
# - Field.property.required: by default required=True for all schema.Field

 
class Field(object):
    interface.implements(IModelDescriptorField)
    
    # A field in a descriptor must be displayable in at least one of these modes
    _modes = ["view", "edit", "add", "listing"] #!+"search"]
    @classmethod
    def validated_modes(cls, modes, nullable=False):
        return validated_set("modes", cls._modes, modes, nullable=nullable)
    _roles = list(roles.SYSTEM_ROLES)
    
    @classmethod
    def validated_roles(cls, roles, nullable=False):
        return validated_set("roles", cls._roles, roles, nullable=nullable)
    
    # INIT Parameter Defaults: 
    # 
    # convention: the default value for each init parameter is the value 
    # assigned to the corresponding class attribute - reasons for this are:
    # a) makes it easier to override init param default values by trivial 
    # subclassing.
    # b) no need to set an instance attribute for init parameters that are 
    # not set, simply let the lookup pick the (default) value off the class.
    
    name = None      # str : field name
    label = ""       # str : title for field
    description = "" # str : description for field
    
    _decl = None # seq((str:name, value)): cache of original (xml) decl attr values
    
    # displayable modes
    def modes():
        doc = "Field.modes property, list of defaulted/validated displayable modes"
        def fget(self):
            # in self.__dict__ or in  self.__class__.__dict__
            return self._modes 
        def fset(self, str_or_seq):
            self._modes = self.validated_modes(str_or_seq)
        def fdel(self):
            del self._modes
        return locals()
    modes = property(**modes())
    
    # the default list of show/hide localization directives -- by default
    # a field is NOT localizable in any mode and for any role.
    localizable = None # [ either(show, hide) ]
    _localizable_modes = None # to cache the set of localizable modes
    
    property = None # zope.schema.interfaces.IField
    
    listing_column = None   # zc.table.interfaces.IColumn
    
    # listing_column_filter must be a function that accepts three parameters
    # 1. an sqlalchemy session query
    # 2. the string to filter the column on
    # 3. the sqlalchemy sort expression desc or asc
    listing_column_filter = None
    
    view_widget = None      # zope.formlib.interaces.IDisplayWidget
    edit_widget = None      # zope.formlib.interfaces.IInputWidget
    add_widget = None       # zope.formlib.interfaces.IInputWidget
    search_widget = None
    
    # /INIT Parameter Defaults
    
    view_permission = "zope.Public"         # str
    edit_permission = "zope.ManageContent"  # str
    # !+FIELD_PERMISSIONS(mr, nov-2010) these attributes are left here because 
    # alchemist.catalyst.domain.ApplySecurity accesses them directly (even if
    # resulting permission is anyway what is specified in domain.zcml).
    
    # OTHER Attributes (and Defaults)
    
    # required flag can only be used if the field is not required by database
    #required = False 
    # !+Field.required(mr, oct-2010) this is OBSOLETED as it has no affect on
    # generated forms -- whether a field, in the UI, is handled as required 
    # or not depends entirely on the value of Field.property.required and/or 
    # whether the corresponding column is nullable or not.
    
    #fieldset = "default"
    # !+FIELDSET(mr, oct-2010) not used - determine intention, remove.
    
    # for relations, we want to enable grouping them together based on
    # model, this attribute specifies a group. the relation name will be
    # used on a vocabulary. perhaps an example is cleaner, so say we
    # have a movie object with separate relations to directors and actors
    # if we specify both as group "People", we inform the view machinery
    # to create a single relation viewlet, that displays and edits
    # via a single provider with a vocabulary for the relation.
    #group = None
    # !+GROUP(mr, oct-2010) not used - determine intention, remove.
    
    def __init__(self, 
            name=None, label=None, description=None, 
            #modes=None, #!+inferred from localizable
            localizable=None, property=None,
            listing_column=None, listing_column_filter=None,
            view_widget=None, edit_widget=None, add_widget=None, 
            search_widget=None,
            #view_permission=None, edit_permission=None
            # !+FIELD_PERMISSIONS(mr, nov-2010) deprecated -- permission on any 
            # domain class attribute (and so, descriptor field) are declared in
            # domain.zcml. There is however still the possibility that these may 
            # be useful for when a descriptor field does not correspond directly 
            # to a domain class attribute (to be determined).
            extended=None,
            derived=None,
        ):
        """The defaults of each init parameter is set as a class attribute --
        if not explicitly specified, then an attribute on the instance is
        NOT set (falling back on the value held in the class attribute).
        
        CONVENTION: not specifying a parameter or specifying it as None
        are interpreted to be equivalent.
        """
        # !+LOCALIZATION_AND_SCHEMA_INTEGRITY for displayable but not-localizable
        # (e.g. "add" for when column is not nullable) add a db-column-validation 
        # on load of each field or catch and handle in a user-friendly way any 
        # IntegrityErrors downstream
        if localizable is None:
            localizable = [show(modes=self.__class__._modes[:])]
        modes = [ mode for loc in localizable for mode in loc.modes ]
        # !+ ensure modes unique, in normalized order
        
        # set attribute values
        kw = vars()
        for p in (
                "name", "label", "description", "modes", 
                "localizable", "property",
                "listing_column", "listing_column_filter",
                "view_widget", "edit_widget", "add_widget", "search_widget", 
                #"view_permission", "edit_permission"
                # !+FIELD_PERMISSIONS(mr, nov-2010) deprecated
            ):
            v = kw[p]
            if v is not None:
                setattr(self, p, v)
        
        self.extended = extended
        self.derived = derived
        
        # parameter integrity, model-related constraints (may not be expressed in RNC)
        assert self.name, "Field [%s] must specify a valid name" % (self.name)
        
        #self.modes = self.validated_modes(self.modes)
        # Ensure that a field is included in a descriptor only when it is 
        # relevant to the UI i.e. it is displayed in at least one mode -- 
        # this obsoletes/replaces the previous concept of descriptor "omit". 
        # Apparently there has been a security-related issue as motivation 
        # for the previous "omit" concept -- as per this discussion:
        # http://groups.google.com/group/bungeni-dev/browse_thread/thread/7f7831b32e798708
        # But, testing the UI with all such fields removed has uncovered no 
        # such security-related issues (see r19 commit log of bungeni-testing).
        assert self.modes, "Field [%s] must specify one or more modes." % (
            self.name)
        
        if listing_column:
            assert "listing" in self.modes, \
                "Field [%s] sets listing_column but no listing mode" % (
                    self.name)
        if listing_column_filter:
            assert "listing" in self.modes, \
                "Field [%s] sets listing_column_filter but no listing mode" % (
                    self.name)
        
        if derived:
            non_view_fmodes = [ mode for mode in modes if mode not in ("view", "listing") ]
            assert not non_view_fmodes, \
                "Unsupported modes %r in derived field %r. " \
                "Derived fields are read-only and may ony specify modes in: %r." % (
                    non_view_fmodes, self.name, ("view", "listing"))
        
        # the default list of show/hide localization directives
        if self.localizable is None:
            self.localizable = []
        self.validate_localizable()
    
    def validate_localizable(self): #+reference_localizable_modes=None):
        self._localizable_modes = set() # reset cache of localizable modes
        for loc in self.localizable:
            # if modes is still None, we now default to this field's modes
            if loc.modes is None:
                loc.modes = self.modes
            # each loc directive must specify at least one mode (but OK to have 
            # empty roles--meaning no roles)
            assert loc.modes, \
                "Invalid modes for Field [%s] localizable directive: %s" % (
                    self.name, loc)
            # build list of localizable modes
            count = len(self._localizable_modes)
            self._localizable_modes.update(loc.modes)
            assert (count + len(loc.modes) == len(self._localizable_modes)), \
                "Field [%s] duplicates mode in localizable directive: %s" % (
                    self.name, loc)
        # !+LOCALIZATION_AND_SCHEMA_INTEGRITY add db-column-validation here?
    
    def is_displayable(self, mode, user_roles):
        """Does this field pass localization directives for this mode?
        """
        # not displayable
        if mode not in self.modes:
            return False
        # OK, displayable, and not localizable
        if mode not in self._localizable_modes:
            return True
        # special handling for "bungeni.Admin" -- for when the Admin role is 
        # not a localizable role we display everything that is displayable;
        # on the other hand, when Admin is a localizable role, we treat it 
        # just like any other role.
        if "bungeni.Admin" not in self.__class__._roles:
            if "bungeni.Admin" in user_roles:
                return True
        # displayable and localizable, process localizable (show) declarations
        for loc in self.localizable:
            if mode in loc.modes:
                for role in user_roles:
                    if role in loc.roles:
                        return True
                    elif loc.roles == roles.SYSTEM_ROLES:
                        #!+FIELDS(mb, Dec-2012) workaround to display fields
                        # for non-localizable types see thread: http://goo.gl/6B7fo
                        if not loc._from_hide:
                            return True
        return False
    
    def get(self, k, default=None):
        return self.__dict__.get(k, default)
    
    def __getitem__(self, k):
        return self.__dict__[k]
    
    # to allow: with field as f:
    def __enter__(self): 
        return self
    def __exit__(self, type, value, traceback): 
        pass


# Model

class classproperty(object):
    "A read-only class property descriptor."
    def __init__(self, getter):
        self.getter = getter
    def __get__(self, instance, cls):
        return self.getter(cls)

class MDType(type):
    """Meta class for ModelDescriptor"""
    
    def __init__(self, name, bases, attrs):
        super(MDType, self).__init__(name, bases, attrs)
        if self.fields is None:
            self.fields = []
        self.fields_by_name = {}
        self.sanity_check_fields()
        self.update_default_field_order()
        # declare display/container names as i18n msgids (for extraction)
        naming.MSGIDS.add(self.display_name)
        naming.MSGIDS.add(self.container_name)
    
    def update_default_field_order(self):
        """Apply default_field_order to class's fields list, any unmentioned 
        fields preserve their current order but will follow the specified fields.
        """
        ordered_fields = [ self.fields_by_name[name]
            for name in self.default_field_order ]
        other_fields = [ f for f in self.fields 
            if f not in ordered_fields ]
        # update class's field list instance
        self.fields[:] = ordered_fields + other_fields

class ModelDescriptor(object):
    """Model type descriptor for table/mapped objects. 
    
    The notion is that an annotation Field object corresponds to a column, 
    and Field attributes correspond to application specific column metadata.
    
    We use class attribute fields=[Field] directly i.e. Field instances on 
    the class itself, implying there is no instance.fields=[Field] attribute.
    
    Retrieve the descriptor model (class) for a model class via:
        alchemist.utils.get_descriptor(type_info_discriminator)
    """
    __metaclass__ = MDType
    interface.implements(IModelDescriptor)
    
    # Is this descriptor exposed for localization? 
    localizable = False
    
    # descriptor scope:
    #   system: a support type provided by system
    #   archetype: an archetype (may base custom types on it) provided by system
    #   custom: a custom type (also a "custom archetype" as may base other 
    #       custom types on it) provided by the user
    scope = "system"
    
    # editable table listing !+
    #edit_grid = True 
    
    fields = None # [Field] - may be explicit, defined in place, constructed via 
    # copying plus extending, etc. Every sub-class must define own list instance.
    fields_by_name = None # {field.name: field} - a cache for internal use, 
    # initialized on class construction, must be kept "in sync" with fields
    
    default_field_order = () # [field.name] - explicit default ordering 
    # (before Descriptor is localized) by field name, for all fields in 
    # this ModelDescriptor.
    
    #properties = () # !+UNUSED
    schema_order = () # !+UNUSED but needed by ore/alchemist/sa2zs.py
    schema_invariants = ()
    custom_validators = ()
    
    # information about the container attributes--to be instrumented on the 
    # *model*--as loaded from the descriptor configuration.
    info_containers = () # [ (name, target_type_key, rel_attr) ]
    
    # a means to specify relative order to be used as needed by the usage 
    # context e.g. when listing different containers for the different types,
    # you may wish to fix the appearance order. 
    # A "high" value, as default, such that unset will sort out last...
    order = 999 # !+bungeni_custom
    
    # sort_on: the list of column names the query is sorted on by default
    sort_on = None
    
    # sort_dir = desc | asc
    sort_dir = "desc"
    
    '''!+NO_NEED_TO_INSTANTIATE
    def __call__(self, iface):
        """Models (classes) are also adapters for the underlying objects.
        """
        return self.__class__
    '''
    def __init__(self):
        # !+NO_NEED_TO_INSTANTIATE(mr, jun-2011) there is no need
        # to singleton-instantiate each ModelDescriptor class,
        # just use the class definition directly!
        raise NotImplementedError(
            "May not initialize a ModelDescriptor class: %s" % self)
    
    @classmethod
    def sanity_check_fields(cls):
        """Do necessary checks on all specified Field instances.
        Also updates internally used fields_by_name mapping.
        """
        cls.fields_by_name.clear()
        for f in cls.fields:
            assert f.name not in cls.fields_by_name, \
                "[%s] Can't have two fields with same name [%s]" % (
                    cls.__name__, f.name)
            cls.fields_by_name[f.name] = f
    
    # we use cls.fields_by_name to define the following methods as this
    # makes the implementation simpler and faster.
    
    @classmethod
    def get(cls, name, default=None):
        #print '!+ModelDescriptor.get("%s")' % (name), cls
        return cls.fields_by_name.get(name, default)
    
    @classmethod
    def keys(cls):
        #print "!+ModelDescriptor.keys", cls
        return cls.fields_by_name.keys()
    
    @classmethod
    def values(cls):
        #print "!+ModelDescriptor.values", cls
        return cls.fields_by_name.values()
    
    @classmethod
    def __getitem__(cls, name):
        #print "!+ModelDescriptor.__getitem__", cls
        return cls.fields_by_name[name]
    
    @classmethod
    def __contains__(cls, name):
        #print "!+ModelDescriptor.__contains__", cls
        return name in cls.fields_by_name
    
    @classmethod
    def _mode_columns(cls, mode):
        # request-relevant roles to determine displayabe fields in this mode
        request_context_roles = common.get_request_context_roles(None)
        return [ field for field in cls.fields 
            if field.is_displayable(mode, request_context_roles) ]
    
    # !+_mode_fields(mr, jan-2012)
    # !+listing_field_names(mr, jan-2012) !
    
    @classproperty
    def listing_columns(cls):
        return [ f.name for f in cls._mode_columns("listing") ]
    @classproperty
    def search_columns(cls): 
        return cls._mode_columns("search")
    @classproperty
    def edit_columns(cls):
        return cls._mode_columns("edit")
    @classproperty
    def add_columns(cls):
        return cls._mode_columns("add")
    @classproperty
    def view_columns(cls):
        return cls._mode_columns("view")
    
    # fallback values for descriptor display_name and container_name
    
    @classproperty
    def display_name(cls):
        cls_name = naming.model_name(
            naming.type_key("descriptor_class_name", cls.__name__))
        return naming.split_camel(cls_name) # !+unicode
    @classproperty
    def container_name(cls):
        return naming.plural(cls.display_name) # !+unicode

