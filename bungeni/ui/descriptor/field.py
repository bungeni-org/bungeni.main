# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Support for UI Form Fields descriptions

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.descriptor.field")

import inspect
from zope import component, schema
from bungeni.alchemist.descriptor import Field
from bungeni.ui import widgets
from bungeni.ui.fields import VocabularyTextField
from bungeni.ui.descriptor import listing, constraints
from bungeni.utils import naming
from bungeni.capi import capi
from bungeni import _


# supported value types (and parameters passed to RType widget class)
# {str: {property-kwarg:value}} 
# !+VALUE_TYPE_PARAMS(mr, sep-2014):
# - either, move all params (other than "default", "constraints", ...?) to be
# handled by configurable constraints (currently in ui/descriptor/constraints.py)
# - or, better, add a capi field/integrity element (similar to descriptor/integrity) 
# and move all default/constraints/params to de declared there.
# - or, should these parms be on render_type in the first place?!
VALUETYPE = {
    "text": {},
    "date": {},
    "datetime": {},
    "time": {},
    "duration": {}, # !+ this "consumes" 2 columns, so probably have dedicated widget type? entirely 
    "bool": {"default": True},
    "number": {},
    "status": {},
    "language": {},
    "vocabulary": {}, # !+ constraint ?
    "email": {"constraint": constraints.check_email},
    "login": {"min_length": 3, "max_length": 64, "constraint": constraints.check_login},
    "password": {},
    "image": {},
    "file": {},
    "user": {},
    "member": {}, # !+ should be "archetype generic" e.g. should not assume "member of parliament"
    "signatory": {}, # !+
    #"combined_name": {}, # !+DERIVED_LISTING_FILTERING
    "group": {},
    "uri": {},
}


# supported render types - determines the UI type for the field
# {str: zope.schema.Field} #!+kw:comma-separated-str
RENDERTYPE = {
    "text_line": schema.TextLine,
    "text_raw": schema.TextLine,
    "text_schedule_type": schema.TextLine,
    "text_box": schema.Text,
    "rich_text": schema.Text,
    "time": schema.TextLine,
    "date": schema.Date,
    "datetime": schema.Datetime,
    "bool": schema.Bool,
    "number": schema.Int,
    "image": schema.Bytes,
    "file": schema.Bytes,
    "uri": schema.TextLine,
    # special other user-conf params: "vocabulary" -> "type:vocabulary, required:True"
    "single_select": schema.Choice, 
    "radio": schema.Choice, 
    "tree_text": VocabularyTextField,
    "no_input": None, # !+
}
RENDERTYPE_WITH_VOCABULARIES = ("single_select", "radio", "tree_text")


# widget setting per mode, by (value_type, render_type)
# (value, render): (view, edit, add, search, 
#   [listing_column_factory, listing_column_filter]) # !+delete
WIDGETS = {
    ("text", "text_line"):
        (None, None, None, None, 
            listing.truncatable_text_column, None),
    ("text", "text_raw"):
        (None, None, None, None, None, None),
    ("text", "text_schedule_type"):
        (None, None, None, None, 
            listing.schedule_type_column, None),
    ("text", "text_box"):
        (None, widgets.TextAreaWidget, widgets.TextAreaWidget, None, 
            listing.truncatable_text_column, None),
    ("text", "rich_text"):
        (widgets.HTMLDisplay, widgets.RichTextEditor, widgets.RichTextEditor, 
            None, listing.truncatable_text_column, None),
    ("text", "radio"):
        (None, widgets.CustomRadioWidget, widgets.CustomRadioWidget, None, None, None),
    ("text", "single_select"): # !+ merge with ("vocabulary", "single_select")
        (None, None, None, None, listing.vocabulary_column, None),
    ("text", "tree_text"):
        (widgets.TermsDisplayWidget, widgets.TreeVocabularyWidget, 
            widgets.TreeVocabularyWidget, None, None, None),
    ("text", "no_input"):
        (None, widgets.NoInputWidget, widgets.NoInputWidget, None, None, None),
    #!+DERIVED_LISTING_FILTERING
    #("combined_name", "text_line"):
    #    (None, None, None, None, 
    #        listing.combined_name_column, 
    #        listing.combined_name_column_filter),
    ("date", "date"):
        (None, widgets.DateWidget, widgets.DateWidget, 
            widgets.date_input_search_widget,
            listing.date_column, None),
    ("time", "time"):
        (None, widgets.TimeWidget, widgets.TimeWidget, None, None, None),
    ("datetime", "datetime"):
        (None, widgets.DateTimeWidget, widgets.DateTimeWidget, 
            widgets.date_input_search_widget,
            listing.datetime_column, None),
    ("duration", "datetime"):
        (None, widgets.DateTimeWidget, widgets.DateTimeWidget, 
            widgets.date_input_search_widget,
            listing.duration_column, None),
    ("bool", "bool"):
        (None, None, None, None, None, None),
    ("bool", "single_select"): # !+ merge with ("vocabulary", "single_select")
        (None, None, None, None, listing.vocabulary_column, None),
    ("number", "number"):
        (None, None, None, None, None, None),
    ("status", "single_select"):
        (None, None, None, None, listing.workflow_column, None),
    ("language", "single_select"):
        (None, None, widgets.LanguageLookupWidget, None, None, None),
    ("vocabulary", "single_select"):
        (None, None, None, None, listing.vocabulary_column, None),
    ("email", "text_line"):
        (None, None, None, None, None, None),
    ("login", "text_line"):
        (None, None, None, None, None, None),
    ("login", "single_select"): # !+ merge with ("vocabulary", "single_select")
        (None, None, None, None, listing.vocabulary_column, None),
    ("password", "text_line"):
        (None, None, None, None, None, None),
    ("image", "image"):
        (widgets.ImageDisplayWidget, widgets.ImageInputWidget, None, None,
            None, None),
    ("file", "file"):
        (widgets.FileDisplayWidget, widgets.FileEditWidget, widgets.FileAddWidget, None,
            None, None),
    ("uri", "uri"):
        (widgets.URIDisplayWidget, None, None, None, listing.uri_column, None),
    ("user", "no_input"): # !+User.user_id
        (None, widgets.HiddenTextWidget, widgets.HiddenTextWidget, None,
            listing.user_name_column,
            listing.user_name_column_filter),
    ("user", "single_select"):
        (widgets.UserURLDisplayWidget, None, 
            widgets.AutoCompleteWidgetOrSingleChoice, None,
            listing.related_user_name_column, 
            listing.related_user_name_column_filter),
    ("member", "single_select"): # !+combine with "user"
        (widgets.UserURLDisplayWidget, None, 
            widgets.AutoCompleteWidgetOrSingleChoice, None,
            listing.member_linked_name_column, 
            listing.related_user_name_column_filter),
    ("group", "single_select"):
        (None, None, None, None,
            listing.vocabulary_column, #!+listing.related_group_column,
            listing.related_group_column_filter),
}


def F(name=None, label=None, description=None, 
        required=False, 
        #modes=None, #!+inferred from localizable
        localizable=None, #!+rename
        #property=None,
        #view_widget=None, edit_widget=None, add_widget=None, 
        #search_widget=None,
        #listing_column=None, 
        #listing_column_filter=None,
        value_type="text",
        render_type="text_line",
        vocabulary=None,
        # only passed down
        extended=None,
        derived=None,
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
        listing_column, listing_column_filter
    
    Example:
    
        F(name="language", label="Language", description=None, 
            required=True,
            localizable=[ show("view edit add"), hide("listing"), ]
            value_type="language",
            render_type="single_select",
            vocabulary="language"
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
                vocabulary="language"
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
        naming.MSGIDS.add(label);
        label = _(label) # !+unicode
    if description:
        naming.MSGIDS.add(description)
        description = _(description) # !+unicode
    
    # modes    
    if localizable is not None:
        # !+ ensure unique, normalized order
        modes = [ mode for loc in localizable for mode in loc.modes ]
    else:
        modes = []
    
    # Field.*_widgets
    widgets = WIDGETS[(value_type, render_type)]
    
    # listing column params
    listing_column, listing_column_filter = None, None
    if "listing" in modes:
        listing_column_factory = widgets[4]
        if listing_column_factory is not None:
            listing_column = listing_column_factory(name, label, vocabulary=vocabulary)
        listing_column_filter = widgets[5]
    
    # Field.property -- see zope.schema.Field, TextLine, Choice, ...
    render_property = None
    if render_type is not None and RENDERTYPE[render_type] is not None:
        RType = RENDERTYPE[render_type]
        render_property_kwargs = dict(
            title=label,
            description=description,
            required=required
        )
        if vocabulary is not None:
            # check if the vocabulary is registered
            try:
                reg_vocab = component.getUtility(
                    schema.interfaces.IVocabularyFactory, name=vocabulary)
            except component.interfaces.ComponentLookupError:
                raise LookupException(
                    "Vocabulary named %r not found in registry." % vocabulary)
            render_property_kwargs["vocabulary"] = vocabulary
        
        # additional kwargs from VALUETYPE config
        rtype_argspec = inspect.getargspec(RType.__init__) # getfullargspec
        value_type_params = VALUETYPE[value_type]
        for kwarg_key in value_type_params:
            assert kwarg_key not in render_property_kwargs, kwarg_key
            # !+VALUE_TYPE_PARAMS
            if issubclass(RType, schema.Choice):
                if kwarg_key in ("min_length", "max_length"):
                    assert kwarg_key not in rtype_argspec.args, (
                        name, RType, kwarg_key, rtype_argspec)
                    log.warn("Skipping widget param [%r=%r] -- not supported by "
                        "widget %s (for render_type %r)" % (kwarg_key, 
                            value_type_params[kwarg_key], RType, render_type))
                    continue
            render_property_kwargs[kwarg_key] = value_type_params[kwarg_key]
        #render_property_kwargs.update(VALUETYPE[value_type])
        log.debug("field %r render_property %s(**%s)", name, RType, render_property_kwargs)
        render_property = RType(**render_property_kwargs)
    
    view_widget, edit_widget, add_widget, search_widget = widgets[0:4]
    
    # Field
    f = Field(name=name, 
            label=label, 
            description=description, 
            #modes=None, #!+inferred from localizable
            localizable=localizable,
            property=render_property,
            listing_column=listing_column, 
            listing_column_filter=listing_column_filter,
            view_widget=view_widget, 
            edit_widget=edit_widget, 
            add_widget=add_widget, 
            search_widget=search_widget,
            extended=extended,
            derived=derived,
        )
    # !+DECL remember all declarative attrs *as-is*
    f._decl = (
        ("name", name),
        ("label", label),
        ("description", description),
        ("required", required),
        #("localizable", localizable),
        ("value_type", value_type),
        ("render_type", render_type),
        ("vocabulary", vocabulary),
        ("extended", extended),
        ("derived", derived),
    )
    return f

