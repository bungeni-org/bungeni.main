from zope.interface import Interface
import zope.schema as schema
from bungeni.ui.i18n import _
from bungeni.ui.vocabulary import BaseVocabularyFactory
from bungeni.utils import naming
from bungeni.capi import capi

DEFAULT_LIMIT = 10

GROUP_TYPES = [ ("*", _(u"documents and people")), 
    ("document", _(u"documents")), 
    ("membership", _(u"people")) ]
class SearchGroupTypes(BaseVocabularyFactory):
    """vocabulary of searchable root types (limited to document)
    """
    def __call__(self, context):
        terms = []
        for value, title in GROUP_TYPES:
            terms.append(schema.vocabulary.SimpleTerm(value=value,
                token=value, title=title
            ))
        return schema.vocabulary.SimpleVocabulary(terms)
search_group_types = SearchGroupTypes()

class SearchDocumentTypes(BaseVocabularyFactory):
    """Searchable document types
    """
    def __call__(self, context):
        terms = []
        for type_key, info in capi.iter_type_info():
            if info.workflow and info.workflow.has_feature("workspace"):
                terms.append(schema.vocabulary.SimpleTerm(
                    value=type_key, 
                    token=type_key,
                    title=naming.split_camel(info.domain_model.__name__)
                ))
        terms.sort(key=lambda item:item.value)
        all_types=",".join([t.value for t in terms])
        terms.insert(0, schema.vocabulary.SimpleTerm(
            value=all_types,
            token=all_types,
            title=_(u"* all document types")
        ))
        return schema.vocabulary.SimpleVocabulary(terms)
search_document_types = SearchDocumentTypes()

doc_type = schema.Choice(title=_("document type"),
    vocabulary=search_document_types,
    required=False
)

search_group = schema.Choice(title=_("group type"),
    vocabulary=search_group_types,
    default="*",
    required=False
)


class ISearchRequest(Interface):
    """Schema definition for search request parameters
    """
    search = schema.TextLine(title=_("search text"), required=False)
    type = schema.List(title=_("document types"),
        value_type=doc_type,
        required=False
    )
    #group = schema.List(title=_("document groups"),
    #    value_type=search_group,
    #    required=False
    #)
    limit = schema.Choice(title=_("items per page"),
        values=(DEFAULT_LIMIT, 20, 50, 100),
        default=DEFAULT_LIMIT,
        required=False
    )
    #status
    #offset
    #role (captured auto)
