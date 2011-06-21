# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Alchemist model - [
    ore.alchemist.model
]

$Id$
"""
log = __import__("logging").getLogger("bungeni.alchemist")

from zope import component, interface, schema
from zope.interface.interfaces import IInterface

from bungeni.alchemist.interfaces import (
    IAlchemistContent,
    IModelAnnotation,
    IIModelInterface,
    IModelDescriptor
)

from bungeni.ui.utils import common 


# ore.alchemist.model


def queryModelInterface(cls):
    """This queries the domain model class for the exclusively alchemist
    IIModelInterface interface. If cls is already such an interface it itself 
    is returned.
    """
    if not IInterface.providedBy(cls):
        candidates = list(interface.implementedBy(cls))
        ifaces = filter(IIModelInterface.providedBy, candidates)
        #import pdb; pdb.set_trace()
        if not ifaces:
            for i in candidates:
                if issubclass(i, IAlchemistContent):
                    ifaces.append(i)
        if not ifaces:
            raise SyntaxError("No Model Interface on Domain Object [%s]" % (cls))
        if ifaces:
            assert len(ifaces)==1, "Multiple Model Interfaces on Domain Object"
        #import pdb; pdb.set_trace()
        return ifaces[0]
    else:
        assert IIModelInterface.providedBy(cls), "Invalid Interface"
        return cls


def queryModelDescriptor(ob):
    if not IInterface.providedBy(ob):
        ob = filter(IIModelInterface.providedBy, 
            list(interface.implementedBy(ob)))[0]    
    name = "%s.%s" % (ob.__module__, ob.__name__)
    return component.queryAdapter(ob, IModelDescriptor, name)

# Register queryModelDescriptor adaptor (to override their upstream ZCML reg)
# signature: factory, adapts:[iface], provides:iface, name, event=False
component.getGlobalSiteManager().registerAdapter(queryModelDescriptor, 
    [IAlchemistContent],
    IModelAnnotation # !+IModelDescriptor ?
)


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

class IModelDescriptorField(interface.Interface):
    # name
    # label
    # description
    modes = schema.ASCIILine(
        title=u"View Usage Modes for Field",
        description=u"Whitespace separated string of different modes."
    )
    # property
    listing_column = schema.Object(interface.Interface,
        title=u"A Custom Column Widget for Listing Views",
        required=False
    )
    # !+LISTING_WIDGET(mr, nov-2010) why inconsistently named "listing_column"?
    view_widget = schema.Object(interface.Interface,
        title=u"A Custom Widget Factory for Read Views",
        required=False
    )
    edit_widget = schema.Object(interface.Interface,
        title=u"A Custom Widget Factory for Write Views",
        required=False,
    )
    add_widget = schema.Object(interface.Interface,
        title=u"A Custom Widget Factory for Add Views",
        required=False
    )
    search_widget = schema.ASCIILine(
        title=u"A Custom Search Widget Factory",
        required=False
    )
    ''' !+FIELD_PERMISSIONS(mr, nov-2010) these params are deprecated -- when 
    applied to any field (that corresponds to an attribute of the domain's 
    class), the domain.zcml setting for that same class attribute will anyway 
    take precedence.

    view_permission = schema.ASCIILine(
        title=u"Read Permission",
        description=u"If the user does not have this permission this field "
            "will not appear in read views",
        required=False
    )
    edit_permission = schema.ASCIILine(
        title=u"Read Permission",
        description=u"If the user does not have this permission this field "
            "will not appear in write views",
        required=False
    )
    '''
    
class Field(object):
    interface.implements(IModelDescriptorField)
    
    # A field in a descriptor must be displayable in at least one of these modes
    _modes = ["view", "edit", "add", "listing", "search"]
    @classmethod 
    def validated_modes(cls, modes, nullable=False):
        return validated_set("modes", cls._modes, modes, nullable=nullable)
    
    # The list of roles exposed to localization
    _roles = [
        #"bungeni.Admin", # parliament, has all privileges
        "bungeni.Clerk", "bungeni.Speaker", 
        "bungeni.Owner", # instance + special objects with no mp context
        "bungeni.MP", # parliament 
        "bungeni.Signatory", #signatory
        "bungeni.Minister", # ministry 
        #"bungeni.Translator", # parliament
        #"bungeni.Authenticated", # all authenticated users, all above roles
        "bungeni.Anonymous" # unauthenticated user, anonymous
    ]
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
    
    # displayable modes
    modes = validated_set("modes", _modes, "view edit add listing")
    
    # the default list of show/hide localization directives -- by default
    # a field is NOT localizable in any mode and for any role.
    localizable = None # [ either(show, hide) ]
    _localizable_modes = None # to cache the set of localizable modes
    
    property = None # zope.schema.interfaces.IField
    
    listing_column = None   # zc.table.interfaces.IColumn
    
    view_widget = None      # zope.app.form.interaces.IDisplayWidget
    edit_widget = None      # zope.app.form.interfaces.IInputWidget
    add_widget = None       # zope.app.form.interfaces.IInputWidget
    search_widget = None    # zope.app.form.interfaces.IInputWidget
    
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
            modes=None, localizable=None, property=None, listing_column=None, 
            view_widget=None, edit_widget=None, add_widget=None, 
            search_widget=None,
            #view_permission=None, edit_permission=None
            # !+FIELD_PERMISSIONS(mr, nov-2010) deprecated -- permission on any 
            # domain class attribute (and so, descriptor field) are declared in
            # domain.zcml. There is however still the possibility that these may 
            # be useful for when a descriptor field does not correspond directly 
            # to a domain class attribute (to be determined). 
        ):
        """The defaults of each init parameter is set as a class attribute --
        if not explicitly specified, then an attribute on the instance is
        NOT set (falling back on the value held in the class attribute).
        
        CONVENTION: not specifying a parameter or specifying it as None
        are interpreted to be equivalent.
        """
        # set attribute values
        kw = vars()
        for p in (
                "name", "label", "description", "modes", 
                "localizable", "property", "listing_column", 
                "view_widget", "edit_widget", "add_widget", "search_widget", 
                #"view_permission", "edit_permission"
                # !+FIELD_PERMISSIONS(mr, nov-2010) deprecated
            ):
            v = kw[p]
            if v is not None:
                setattr(self, p, v)
        
        # parameter integrity
        assert self.name, "Field [%s] must specify a valid name" % (self.name)
        self.modes = self.validated_modes(self.modes)
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
        # the default list of show/hide localization directives
        if self.localizable is None:
            self.localizable = []
        self.validate_localizable()
    
    def validate_localizable(self, reference_localizable_modes=None):
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
        for mode in self._localizable_modes:
            if reference_localizable_modes is not None:
                # only modes listed here may be localized
                assert mode in reference_localizable_modes, \
                    "Field [%s] may only localize mode [%s] if mode is " \
                    "localizable i.e. one of: %s." % (
                        self.name, mode, reference_localizable_modes)
                # must localize all localizable modes
                assert len(reference_localizable_modes) == \
                    len(self._localizable_modes), \
                        "Field [%s] localizable modes mismatch:" \
                        "\nB: %s\nC: %s" % (
                            self.name, reference_localizable_modes, 
                            list(self._localizable_modes))
            else:
                # only displayable modes
                assert mode in self.modes, \
                    "Field [%s] may only localize mode [%s] if mode is " \
                    "displayable i.e. one of: %s." % (
                        self.name, mode, self.modes)
    
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
        # on the other hand, when Adnis is a loclaizable role, we treat it 
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
        return False
    
    def get(self, k, default=None):
        return self.__dict__.get(k, default)
    
    def __getitem__(self, k):
        return self.__dict__[k]


# Model

class MDType(type):
    """Meta class for ModelDescriptor"""
    
    def __init__(self, name, bases, attrs):
        super(MDType, self).__init__(name, bases, attrs)
        self.update_default_field_order()
    
    def update_default_field_order(self):
        """Apply default_field_order to class's fields list, any unmentioned 
        fields preserve their current order but will follow the specified fields.
        """
        fields_by_name = dict([ (f.name, f) for f in self.fields ])
        ordered_fields = [ fields_by_name[name] 
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
    
    Always retrieve the *same* descriptor *instance* for a model class via:
        queryModelDescriptor(model_interface)
    """
    __metaclass__ = MDType
    interface.implements(IModelDescriptor)
    
    # Is this descriptor exposed for localization? 
    localizable = False
    
    # editable table listing !+
    #edit_grid = True 
    
    # for subclasses to reset
    fields = [] # [Field] - may be explicit, defined in place, constructed via 
    # copying plus extending, etc.
    default_field_order = () # [field.name] - explicit default ordering 
    # (before Descriptor is localized) by field name, for all fields in 
    # this ModelDescriptor.
    
    properties = () # !+USED?
    schema_order = () # !+USED?
    schema_invariants = ()
    
    def __call__(self, iface):
        """Models are also adapters for the underlying objects
        """
        return self
    
    def __init__(self):
        # !+NO_NEED_TO_INSTANTIATE(mr, jun-2011) there is really no longer 
        # any need to singleton-instantiate each ModelDescriptor class, 
        # just use the class definition directly!
        log.info("Initializing ModelDescriptor: %s" % self)
        self._fields_by_name = {}
        self.sanity_check_fields()
    
    def sanity_check_fields(self):
        """Do necessary checks on all specified Field instances.
        """
        self._fields_by_name.clear()
        for f in self.__class__.fields:
            name = f["name"]
            assert name not in self._fields_by_name, \
                "[%s] Can't have two fields with same name [%s]" % (
                    self.__class__.__name__, name)
            self._fields_by_name[name] = f
        # !+DESCRIPTOR_VALIDATION(mr, nov-2010) a descriptor may specify a 
        # field with a name that does not correspond to an attribute on the 
        # model -- this may be useful, but we do not use it, and any such
        # occurance is most likely a code error... should we check for such
        # situations?
    
    # we use self._fields_by_name to define the following methods as this 
    # makes the implementation simpler and faster.
    
    def get(self, name, default=None):
        #print '!+ModelDescriptor.get("%s")' % (name), self
        return self._fields_by_name.get(name, default)
    
    def keys(self):
        #print "!+ModelDescriptor.keys", self
        return self._fields_by_name.keys()
    
    def values(self):
        #print "!+ModelDescriptor.values", self
        return self._fields_by_name.values()
    
    def __getitem__(self, name):
        #print "!+ModelDescriptor.__getitem__", self
        return self._fields_by_name[name]
    
    def __contains__(self, name):
        #print "!+ModelDescriptor.__contains__", self
        return name in self._fields_by_name
    
    def _mode_columns(self, mode):
        # request-relevant roles to determine displayabe fields in this mode
        request_context_roles = common.get_request_context_roles(None)
        return [ field for field in self.__class__.fields 
            if field.is_displayable(mode, request_context_roles) ]
    
    @property
    def listing_columns(self): # !+listing_column_NAMES(mr, nov-2010) !
        return [ f.name for f in self._mode_columns("listing") ]
    @property
    def search_columns(self): 
        return self._mode_columns("search")
    @property
    def edit_columns(self):
        return self._mode_columns("edit")
    @property
    def add_columns(self):
        return self._mode_columns("add")
    @property
    def view_columns(self):
        return self._mode_columns("view")
    

