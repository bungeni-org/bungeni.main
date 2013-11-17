from zope.interface import Interface
import zope.component
import zope.schema as schema

from bungeni.core.interfaces import IWorkspaceSection, IWorkspaceTabsUtility

from bungeni.ui.vocabulary import BaseVocabularyFactory
from bungeni.ui.utils.common import get_workspace_roles

from bungeni.utils import naming
from bungeni.capi import capi
from bungeni import _


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

def get_search_doc_types(context):
    """get types searchable in a context"""
    types = []
    if IWorkspaceSection.providedBy(context):
        ws_config = zope.component.getUtility(IWorkspaceTabsUtility)
        roles = get_workspace_roles()
        wf_types = set()
        for role in roles:
            types = []
            wf_types.update(*[ wsp.keys() 
                for wsp in ws_config.workspaces[role].values() ])
        types = [ capi.get_type_info(typ) for typ in wf_types ]
    else:
        types = [ info for key, info in capi.iter_type_info() ]
    return types

class SearchDocumentTypes(BaseVocabularyFactory):
    """Searchable document types
    """
    def __call__(self, context):
        terms = []
        for info in get_search_doc_types(context):
            if info.workflow and info.workflow.has_feature("workspace"):
                terms.append(schema.vocabulary.SimpleTerm(
                    value=info.type_key, 
                    token=info.type_key,
                    title=_(naming.split_camel(info.domain_model.__name__))
                ))
        terms.sort(key=lambda item:item.value)
        if len(terms) > 1:
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

class SearchWorkflowStatus(BaseVocabularyFactory):
    """workflow document status vocabulary"""
    def __call__(self, context):
        terms = []
        seen_keys = []
        for info in get_search_doc_types(context):
            if info.workflow and info.workflow.has_feature("workspace"):
                for state in info.workflow._states_by_id.values():
                    if not state.id in seen_keys:
                        terms.append(schema.vocabulary.SimpleTerm(
                            value=state.id, 
                            token=state.id,
                            title=_(state.title)
                        ))
                        seen_keys.append(state.id)
        terms.insert(0, schema.vocabulary.SimpleTerm(
            value="*",
            token="*",
            title=_(u"* any status")
        ))
        return schema.vocabulary.SimpleVocabulary(terms)
workflow_statuses = SearchWorkflowStatus()

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
    status = schema.Choice(title=_("workflow status"),
        vocabulary=workflow_statuses,
        default="*",
        required=False
    )
    limit = schema.Choice(title=_("items per page"),
        values=(DEFAULT_LIMIT, 20, 50, 100),
        default=DEFAULT_LIMIT,
        required=False
    )
    #offset
    #role (captured auto)
