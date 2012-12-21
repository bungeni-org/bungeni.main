Localization of Form UI Views
=============================

To localize the visibility of fields for each Bungeni Object Type -- to state 
in what modes and to what roles should an object field be displayed in the UI.

----
Generate the default localization file

Executing the following command:

    $ {cinst}/bin/python {cinst}/src/bungeni.main/bungeni/ui/descriptor/localization.py

will generate--or regenerate and OVERWRITE--the file:

    {bungeni_custom}/forms/ui.xml

The {bungeni_custom} folder is the current active one. The generated file 
corresponds exactly to all Form UI View settings in stock bungeni. 

----
Customize the localization file: forms/ui.xml

Modify the fields order of each descriptor and/or the visibility modifiers on 
each field as needed. 

For a general description, see the the "Localization API" section in 
the document:

    Localization of Bungeni Forms
    http://code.google.com/p/bungeni-portal/wiki/DevFormLocalization#Localization_API

Additional tips useful when editing the localization file: forms/ui.xml

- When a `<show>` or `<hide>` element does not define a `roles` attribute, 
then the value implied is the value of the `roles` attribute on the document's
root elemenet i.e. `<ui>`.

- Each `<field>` element specifies a `displayable` attribute and a `localizable`
attribute--these reflect the settings in Bungeni and are provided for 
information only to help make customization easier.

- A `<field>` may specify a `<show>` or `<hide>` element per localizable mode,
or, as a shorthand (when the values of `roles` is the same), may combine 
multiple modes into a single statement. For example, the following element:
    <show modes="view edit add" />
is just a shorthand for the following elements:
    <show modes="view" />
    <show modes="edit" />
    <show modes="add" />

- To test a modified customization, restart the bungeni application.


