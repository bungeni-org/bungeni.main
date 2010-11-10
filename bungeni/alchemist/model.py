# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Alchemist model - [
    ore.alchemist.model
]

$Id$
"""
log = __import__("logging").getLogger("bungeni.alchemist")


# ore.alchemist.model

from ore.alchemist.model import queryModelDescriptor
from ore.alchemist.model import queryModelInterface


from zope import interface
from zope import schema
import ore.alchemist

class IModelDescriptorField(interface.Interface):
    # name
    # label
    # description
    modes = schema.ASCIILine(
        title=u"View Usage Modes for Field",
        description=u"Pipe separated string of different modes.. "
            "view|edit|add|listing|search are all valid"
    )
    # property
    listing_column = schema.Object(interface.Interface,
        title=u"A Custom Column Widget for Listing Views",
        required=False
    )
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

class Field(object):
    interface.implements(IModelDescriptorField)
    
    # INIT Parameter (and Defaults)
    
    # CONVENTION: the default value for each init parameter is the value 
    # assigned to the corresponding class attribute - reasons for this are:
    # a) makes it easier to override init param default values by trivial 
    # subclassing.
    # b) no need to set an instance attribute for init parameters that are 
    # not set, simply let the lookup pick the (default) value off the class.
    
    name = None      # str : field name
    label = ""       # str: title for field
    description = "" # str : description for field
    
    modes = "view|edit|add" # str : see _valid_modes for allows values
    
    property = None # zope.schema.interfaces.IField
    
    listing_column = None   # zc.table.interfaces.IColumn
    
    view_widget = None      # zope.app.form.interaces.IDisplayWidget
    edit_widget = None      # zope.app.form.interfaces.IInputWidget
    add_widget = None       # zope.app.form.interfaces.IInputWidget
    search_widget = None    # zope.app.form.interfaces.IInputWidget
    
    view_permission = "zope.Public"         # str
    edit_permission = "zope.ManageContent"  # str
    
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
    
    
    _valid_modes = ("view", "edit", "add", "listing", "search")
    
    def __init__(self, 
        name=None, label=None, description=None, 
        modes=None, property=None, listing_column=None, 
        view_widget=None, edit_widget=None, add_widget=None, search_widget=None,
        view_permission=None, edit_permission=None
    ):
        """The defaults of each init paremeter is set as a class attribute --
        if not explicitly specified, then an attribute on the instance is
        NOT set.
        
        CONVENTION: not specifying a parameter or specifying it as None
        are interpreted to be equivalent.
        """
        kw = vars()
        cls = self.__class__
        # parameter integrity
        assert name, "Field [%s] must specify valid name" % (name)
        assert not ((property or self.property) and 
                not (modes or self.modes)), \
            """Can't specify "property" and no "modes" for field: %s""" % (
                name)
        if modes: 
            assert not " " in modes, \
                """Field [%s] "modes" [%s] may not contain whitespace""" % (
                    name, modes)
        if listing_column:
            assert ((modes and "listing" in modes) or 
                    (self.modes and "listing" in self.modes)), \
                "Field [%s] sets listing_column but no listing mode" % (name)
        # set attribute values (for specified attributes only)
        for p in (
            "name", "label", "description", "modes", 
            "property", "listing_column", 
            "view_widget", "edit_widget", "add_widget", "search_widget", 
            "view_permission", "edit_permission"
        ):
            v = kw[p]
            if v is not None:
                setattr(self, p, v)
    
    def get(self, k, default=None):
        return self.__dict__.get(k, default)
    
    def __getitem__(self, k):
        return self.__dict__[k]


class ModelDescriptor(ore.alchemist.model.ModelDescriptor):
    """Model type descriptor for table/mapped objects. 
    
    The notion is that an annotation Field object corresponds to a column, 
    and Field attributes correspond to application specific column metadata.
    
    We use class attribute fields=[Field] directly i.e. Field instances on 
    the class itself, implying there is no instance.fields=[Field] attribute.
    
    Always retrieve the *same* descriptor *instance* for a model class via:
        queryModelDescriptor(model_interface)
    """
    # editable table listing !+
    #edit_grid = True 
    
    # fields - subclasses must set
    #fields = None # [Field]
    
    def __init__(self):
        self._fields_by_name = {}
        for f in self.__class__.fields:
            self.sanity_check_field(f)
        log.info("Initializing ModelDescriptor: %s" % self)
    
    def sanity_check_field(self, f):
        """Do necessary checks on supplied Field instances.
        """
        name = f["name"]
        assert name not in self._fields_by_name, \
            "[%s] Can't have two fields with same name [%s]" % (
                self.__class__.__name__, name)
        self._fields_by_name[name] = f
    
    # we override the following methods as, thanks to self._fields_by_name, 
    # they may be redefined in a much simpler way (as well as being faster).
    
    def get(self, name, default=None):
        return self._fields_by_name.get(name, default)
    
    def __getitem__(self, name):
        return self._fields_by_name[name]
    
    def __contains__(self, name):
        return name in self._fields_by_name

