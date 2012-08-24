# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Support for UI Form Fields descriptions

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.descriptor.field")

from zope import schema
from bungeni.alchemist.model import ModelDescriptor, Field, show, hide
from bungeni.ui import widgets
from bungeni.ui.fields import VocabularyTextField
from bungeni.ui.i18n import _
from bungeni.ui.descriptor import listing, constraints


# supported value types
# {str: {property-kwarg:value}}
VALUETYPE = {
    "text": {},
    "date": {},
    "bool": {"default": True},
    "number": {},
    "language": {},
    "email": {"constraint": constraints.check_email},
    "login": {"min_length": 3, "max_length": 20, "constraint": constraints.check_login},
    "password": {},
    "image": {},
    "user": {},
}


# supported render types - determines the UI type for the field
# {str: zope.schema.Field} #!+kw:comma-separated-str
RENDERTYPE = {
    "text_line": schema.TextLine,
    "text_box": schema.Text,
    "rich_text": schema.Text,
    "date": schema.Date,
    "bool": schema.Bool,
    "number": schema.Int,
    "image": schema.Bytes,
    # special other user-conf params: "vocabulary" -> "type:vocabulary, required:True"
    "single_select": schema.Choice, 
    "radio": schema.Choice, 
    "tree_text": VocabularyTextField,
}
RENDERTYPE_WITH_VOCABULARIES = ("single_select", "radio", "tree_text")


# widget setting per mode, by (value_type, render_type)
# (value, render): (view, edit, add, search) # !+listing, delete
WIDGETS = {
    ("text", "text_line"):
        (None, None, None, None),
    ("text", "text_box"):
        (None, widgets.TextAreaWidget, widgets.TextAreaWidget, None),
    ("text", "rich_text"):
        (widgets.HTMLDisplay, widgets.RichTextEditor, widgets.RichTextEditor, 
            None),
    ("text", "radio"):
        (None, widgets.CustomRadioWidget, widgets.CustomRadioWidget, None),
    ("text", "single_select"):
        (None, None, None, None),
    ("text", "tree_text"):
        (widgets.TermsDisplayWidget, widgets.TreeVocabularyWidget, 
            widgets.TreeVocabularyWidget, None),
    ("date", "date"):
        (None, widgets.DateWidget, widgets.DateWidget, 
            widgets.date_input_search_widget),
    ("bool", "bool"):
        (None, None, None, None),
    ("number", "number"):
        (None, None, None, None),
    ("language", "single_select"):
        (None, None, widgets.LanguageLookupWidget, None),
    ("email", "text_line"):
        (None, None, None, None),
    ("login", "text_line"):
        (None, None, None, None),
    ("password", "text_line"):
        (None, None, None, None),
    ("image", "image"):
        (widgets.ImageDisplayWidget, widgets.ImageInputWidget, None, None),
    ("user", "single_select"):
        (widgets.UserURLDisplayWidget, None, widgets.AutoCompleteWidget(),
            None),
}


def F(name=None, label=None, description=None, 
        required=False, 
        #modes=None, #!+inferred from localizable
        localizable=None, #!+rename
        #property=None,
        #view_widget=None, edit_widget=None, add_widget=None, 
        #search_widget=None,
        value_type="text",
        render_type="text_line",
        vocabulary=None,
        # !+
        listing_column=None, 
        listing_column_filter=None, #!+tmp
    ):
    """
    A "configuration layer" for Fields, to decouple lower level details from 
    Form UI configuration. Intention is to offer a simpler, more 
    "user-oriented" and "xml-friendly" way to declare a field.
    
    New parameters introduced by the F layer type:
        required, value_type, render_type, vocabulary
    that, when coupled with some additional application-level settings, 
    replace the following Field init parameters:
        modes
        property (along with own parameters)
        view_widget, edit_widget, add_widget, search_widget
    !+tmp (to be otherwise declared or inferred)
        listing_column
        listing_column_filter
    
    Example:
    
        F(name="language", label="Language", description=None, 
            required=True,
            localizable=[ show("view edit add"), hide("listing"), ]
            value_type="language",
            render_type="single_select",
            vocabulary="language_vocabulary"
        )
    
    will be the "user-oriented" equivalent way to define the following Field:
    
        Field(name="language",
            label=_("Language"),
            modes="view edit add listing",,
            localizable=[
                show("view edit"), 
                hide("listing"), 
            ]
            property=schema.Choice(title=_("Language"),
                vocabulary="language_vocabulary"
            ),
            add_widget=widgets.LanguageLookupWidget,
        )
    
    """
    # integrity
    if render_type in RENDERTYPE_WITH_VOCABULARIES:
        assert vocabulary, \
            "Vocabulary may not be None for render_type=%r" % (render_type)
    if vocabulary is not None:
        assert render_type in RENDERTYPE_WITH_VOCABULARIES, \
            "render_type=%r may not have a vocabulary [%r]" % (
                render_type, vocabulary)
    if value_type is not None:
        assert value_type in VALUETYPE, "Unknown value_type=%r" % (value_type)
    assert (value_type, render_type) in WIDGETS, \
        "No widget set defined for (value_type=%r, render_type=%r)" % (
            value_type, render_type)
    
    # i18n attributes
    if label:
        label = _(label)
    if description:
        description = _(description)
    
    # Field
    f = Field(name=name, 
            label=label, 
            description=description, 
            #modes=None
            localizable=localizable,
            # !+tmp
            listing_column=listing_column, 
            listing_column_filter=listing_column_filter,
        )
    
    # Field.property -- see zope.schema.Field, TextLine, Choice, ...
    if render_type is not None:
        RType = RENDERTYPE[render_type]
        property_kwargs = dict(
            title=label,
            description=description,
            required=required
        )
        if vocabulary is not None:
            property_kwargs["vocabulary"] = vocabulary
        property_kwargs.update(VALUETYPE[value_type])
        f.property = RType(**property_kwargs)
    # Field.*_widgets
    (f.view_widget, f.edit_widget, f.add_widget, f.search_widget
        ) = WIDGETS[(value_type, render_type)]
    
    return f


