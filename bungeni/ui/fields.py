# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Custom fields for some content attributes

$Id$
$URL$
"""

from zope.schema import Text
from zope.schema.interfaces import IVocabularyFactory
from zope.interface import implements    
from zope.component import getUtility
from zope.schema.interfaces import ValidationError
from bungeni.ui.interfaces import IVocabularyTextField
from bungeni.ui.i18n import _

class InvalidVocabularySelection(ValidationError):
    __doc__ = _("""Choose items from provided vocabulary""")

class VocabularyTextField(Text):
    """Field for selection of controlled heirarchical (ITreeVocabulary) 
    vocabulary terms.
    """
    implements(IVocabularyTextField)
    
    @property
    def vocabulary(self):
        return getUtility(IVocabularyFactory, self.vocabulary_name)
    
    def __init__(self, vocabulary, **kw):
        self.vocabulary_name = vocabulary
        super(VocabularyTextField, self).__init__(**kw)
    
    def _validate(self, values):
        super(VocabularyTextField, self)._validate(values)
        if values:
            try:
                self.vocabulary.validateTerms(values.split("\n"))
            except LookupError:
                raise InvalidVocabularySelection(values, ())
                

