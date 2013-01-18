"""
User interface for Content Search


Todo - Canonical URL on index of results, tuple,
       AbsoluteURL adapter for results
       mark result class with interface


Supported xapian query operators
 |  OP_AND = 0
 |
 |  OP_AND_MAYBE = 4
 |
 |  OP_AND_NOT = 2
 |
 |  OP_ELITE_SET = 10
 |
 |  OP_FILTER = 5
 |
 |  OP_NEAR = 6
 |
 |  OP_OR = 1
 |
 |  OP_PHRASE = 7
 |
 |  OP_SCALE_WEIGHT = 9
 |
 |  OP_SYNONYM = 13
 |
 |  OP_VALUE_GE = 11
 |
 |  OP_VALUE_LE = 12
 |
 |  OP_VALUE_RANGE = 8
 |
 |  OP_XOR = 3
 |
"""
# !+ CLEAN UP THIS FILE, MINIMALLY AT LEAST THE SRC CODE FORMATTING !

import time
import urllib
import xapian as _xapian
from urlparse import urljoin

from zope import interface, schema, component
from zope.publisher.browser import BrowserView
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.security.proxy import removeSecurityProxy
from zope.formlib import form
from zope.cachedescriptors.property import CachedProperty
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary
from zope.security.checker import canAccess
from zope.security.checker import ProxyFactory
from zope.publisher.defaultview import getDefaultViewName
from zope.app.component.hooks import getSite
from zope.i18n import translate
from zope.component import queryMultiAdapter
from zope.dottedname import resolve
from zc.resourcelibrary import need
from zc.table import table, column

from ore.xapian import interfaces
from bungeni.alchemist import Session
from bungeni.models import domain
from bungeni.core.i18n import _
from bungeni.core.translation import translate_obj
from bungeni.core import index
from bungeni.ui import forms
from bungeni.ui import vocabulary
from bungeni.ui.widgets import SelectDateWidget
from bungeni.ui.utils.url import get_section_name, absoluteURL

from bungeni.alchemist.interfaces import IAlchemistContainer

MINIMAL_PARTIAL_QUERY = 4

ALLOWED_TYPES = {'workspace': ('Question', 'Motion', 'TabledDocument',\
                               'Bill', 'AgendaItem'),\
                 'business': ('Question', 'Motion', 'Committee', 'Bill', \
                              'TabledDocument', 'AgendaItem', 'Attachment'),
                 'archive': ('Question', 'Motion', 'Committee', \
                             'Bill', 'TabledDocument', 'AgendaItem', \
                             'Parliament', 'PoliticalGroup',
                             'MemberOfParliament', "Attachment"),
                 'members': ('MemberOfParliament', 'PoliticalGroup'),
                 'admin': ('Question', 'Motion', 'Committee', 'Bill', \
                           'TabledDocument', 'AgendaItem', 'Parliament', \
                           'PoliticalGroup', 'User', 'MemberOfParliament'),
                 }


def get_statuses_vocabulary(klass):
    try:
        return vocabulary.workflow_states(klass())
    except Exception:
        return None


def translated_vocabulary(voc, context):
    terms = []
    for term in voc:
        title = translate(term.title, domain="bungeni", context=context)
        nt = SimpleTerm(term.value, term.token, title)
        terms.append(nt)
    nv = SimpleVocabulary(terms)
    return nv


class ISearch(interface.Interface):

    full_text = schema.TextLine(title=_("Query"), required=False)


class IAdvancedSearch(ISearch):

    language = schema.Choice(
        title=_("Language"),
        values=("en", "fr", "pt", "sw", "it", "en-ke"),
        required=False)
    content_type = schema.Choice(
        title=_("Content type"),
        values=("Question",
            "MemberOfParliament",
            "Motion",
            "Committee",
            "User",
            "Parliament",
            "AgendaItem",
            "TabledDocument",
            "Goverment",
            "Ministry",
            "Report",
            "Attachment",
            "Bill",
            "Sitting",
            "PoliticalGroup"),
        required=False)
    status_date = schema.Date(title=_("Status date"), required=False)


class IHighLight(interface.Interface):

    highlight = schema.Bool(title=_("Highlight words"), required=False,
        default=True)


class ISearchResult(interface.Interface):

    title = schema.TextLine(title=_("Title"), required=False)
    annotation = schema.Text(title=_("Annotation"), required=False)


class UserToSearchResult(object):

    def __init__(self, context):
        self.context = context

    @property
    def title(self):
        return self.context.combined_name.strip()

    @property
    def annotation(self):
        return self.context.description


class MemberToSearchResult(object):

    def __init__(self, context):
        self.context = context

    @property
    def title(self):
        return self.context.user.combined_name.strip()

    @property
    def annotation(self):
        return self.context.notes


class ParliamentaryItemToSearchResult(object):

    def __init__(self, context):
        self.context = context

    @property
    def title(self):
        return self.context.title

    @property
    def annotation(self):
        return self.context.body


class AttachmentToSearchResult(object):

    def __init__(self, context):
        self.context = context

    @property
    def title(self):
        return self.context.title

    @property
    def annotation(self):
        return self.context.description


class GroupToSearchResult(object):

    def __init__(self, context):
        self.context = context

    @property
    def title(self):
        return self.context.short_name

    @property
    def annotation(self):
        return self.context.description


class ResultListing(object):

    formatter_factory = table.StandaloneFullFormatter

    results = None
    spelling_suggestion = None
    search_time = None
    doc_count = None

    columns = [
        column.GetterColumn(title=_(u"rank"),
            getter=lambda i, f:i.rank),
        column.GetterColumn(title=_(u"type"),
            getter=lambda i, f: i.data.get('object_type', ('',))[0]),
        column.GetterColumn(title=_(u"title"),
            getter=lambda i, f:i.data.get('title', ('',))[0]),
        column.GetterColumn(title=_(u"status"),
            getter=lambda i, f:i.data.get('status', ('',))[0]),
        column.GetterColumn(title=_(u"weight"),
            getter=lambda i, f:i.weight),
        column.GetterColumn(title=_(u"percent"),
            getter=lambda i, f:i.percent),
    ]

    def listing(self):
        columns = self.columns
        formatter = self.formatter_factory(self.context, self.request,
                            self.results or (),
                            prefix="results",
                            visible_column_names=[c.name for c in columns],
                            #sort_on = (('name', False)
                            columns=columns
        )
        formatter.cssClasses['table'] = 'listing'
        return formatter()


class HighlightMixin(object):

    @property
    def highlightscript(self):
        need("highlight")
        words = filter(lambda x: x,
            self.request.form.get("%s.full_text" % self.prefix, "").split(" "))

        def highliightword(x):
            return """$("#search-results").highlight("%s", true);""" % x
        words = "\n".join(map(highliightword, words))
        return """
               <script type="text/javascript">
                 var ch = document.getElementById("%s");
                 function highlightwords(){
                   $("#search-results").removeHighlight();
                   if (ch.checked) {
                     %s
                   }
                 }
                 function radioHighlightChangeonclick(){
                   ch.onclick=function(){
                     highlightwords();
                   }
                   highlightwords();
                 }
                 window.onload = radioHighlightChangeonclick;
               </script>
            """ % ("%s.highlight" % self.prefix, words)


class Search(forms.common.BaseForm, ResultListing, HighlightMixin):
    """  basic content search form and results
    """
    template = ViewPageTemplateFile('templates/search.pt')
    form_fields = form.Fields(ISearch, IHighLight)
    #selection_column = columns[0]

    @property
    def doc_count(self):
        return len(self._searchresults)

    @property
    def search_status(self):
        return _("Found ${total} results in ${search_time} Seconds",
            mapping={
                "total": self.doc_count, 
                "search_time": format(float(self.search_time), "0.5f")
            }
        )

    def setUpWidgets(self, ignore_request=False):
        # setup widgets in data entry mode not bound to context
        self.adapters = {}
        self.widgets = form.setUpDataWidgets(self.form_fields, self.prefix,
             self.context, self.request, ignore_request=ignore_request)

    def authorized(self, result):
        obj = result.object()
        defaultview = getDefaultViewName(obj, self.request)
        view = queryMultiAdapter((ProxyFactory(obj), self.request),
                                 name=defaultview)
        return canAccess(view, "__call__")

    def get_description(self, item):
        return item.description
    
    def get_title(self, item):
        return "%s %s" % (
            translate_obj(item.head, self.request.locale.id.language).title,
            _(u"changes from"))
    
    def get_url(self, item):
        site = getSite()
        base_url = absoluteURL(site, self.request)
        return "%s/business/%ss/obj-%s" % (
            base_url, item.head.type, item.head.doc_id)

    def get_user_subscriptions(self):
        """ Getting user subscribed items
        """
        session = Session()
        user = session.query(domain.User).filter(
            domain.User.login == self.request.principal.id).first()
        return user.subscriptions

    @CachedProperty
    def _searchresults(self):
        section = get_section_name()
        subqueries = []
        
        type_filter = ""
        
        if IAlchemistContainer.providedBy(self.context):
            for t in ALLOWED_TYPES["business"]:
                iface = resolve.resolve("bungeni.models.interfaces.I%sContainer"%t)
                if iface.providedBy(self.context):
                    type_filter = t
                    break
        
        if type_filter:
            type_query = self.searcher.query_field('object_type', type_filter)
        else:
            # Filter items allowed in current section
            for tq in ALLOWED_TYPES[section]:
                subqueries.append(self.searcher.query_field('object_type', tq))
                type_query = self.searcher.query_composite(self.searcher.OP_OR, 
                                                           subqueries)

        self.query = self.searcher.query_composite(self.searcher.OP_AND,
                                                   (self.query, type_query,))

        try:
            results = self.searcher.search(self.query, 0,
                self.searcher.get_doccount())
        except:
            results = []

        results = filter(self.authorized, results)

        return results

    @property
    def _results(self):
        return map(lambda x: x.object(), self._searchresults)

    @form.action(label=_(u"Search"), name="search")
    def handle_search(self, action, data):
        self.searcher = component.getUtility(interfaces.IIndexSearch)()
        search_term = data["full_text"]
        
        if not search_term:
            self.status = _(u"Invalid Query")
            return

        # Setting FLAG_PARTIAL to search incomplete words
        if len(search_term) > MINIMAL_PARTIAL_QUERY:
            self.searcher._qp_flags_base |= _xapian.QueryParser.FLAG_PARTIAL

        # compose query
        t = time.time()
        lang = self.request.locale.getLocaleID()
        if lang == "en_US":
            lang = "en"
        if lang == "en_KE":
            lang = "en-ke"
        text_query = self.searcher.query_parse(search_term)
        lang_query = self.searcher.query_field('language', lang)
        self.query = self.searcher.query_composite(self.searcher.OP_AND,
            (text_query, lang_query,))
        self.results = self._results
        self.search_time = time.time() - t

        # spelling suggestions
        suggestion = self.searcher.spell_correct(search_term)
        self.spelling_suggestion = (
            search_term != suggestion and suggestion or None)


class Pager(object):
    '''pager for search result page'''
    action_method = 'get'
    items_count = 5

    @property
    def page_number(self):
        try:
            page = int(self.request.form.get('page', 1))
        except ValueError:
            page = 1
        return page

    @property
    def _results(self):
        start = self.items_count * (self.page_number - 1)
        end = self.items_count * self.page_number
        return map(lambda x: x.object(),
                   self._searchresults[start:end])

    @property
    def pages(self):
        if self.doc_count > self.items_count:
            page_count = self.doc_count / self.items_count + \
                int(bool(self.doc_count % self.items_count))

            def generate_url(x):
                args = dict(self.request.form)
                args.pop('page', None)
                return str(self.request.URL) + '?' + \
                    urllib.urlencode(args) + '&page=%d' % x

            return map(lambda x: {'number': x,
                                  'url': generate_url(x)},
                       range(1, page_count + 1))


class PagedSearch(Pager, Search):
    template = ViewPageTemplateFile('templates/paged-search.pt')

    @property
    def search_status(self):
        return _("Showing ${page_start} to ${page_end} of ${total} "
            "results. Search done in ${search_time} seconds.",
            mapping = {
                "page_start": self.items_count * (self.page_number-1) + 1,
                "page_end": (self.items_count * (self.page_number-1) + 
                    len(self._results)),
                "total": self.doc_count,
                "search_time": format(float(self.search_time), "0.5f")
            }
        )
        
    @property
    def advanced_search_url(self):
        base_url = absoluteURL(getSite(), self.request)
        section = get_section_name()
        return urljoin(base_url, section) + "/advanced-search"

def get_users_vocabulary():
    session = Session()
    query = session.query(domain.User
                ).order_by(
                    domain.User.last_name,
                    domain.User.first_name,
                    domain.User.middle_name
                )
    results = query.all()
    terms = []
    for ob in results:
        terms.append(
            SimpleTerm(
                value = getattr(ob, 'user_id'),
                token = getattr(ob, 'user_id'),
                title = "%s %s" % (getattr(ob, 'first_name'),
                        getattr(ob, 'last_name'))
            ))
    return SimpleVocabulary(terms)


class AdvancedPagedSearch(PagedSearch):

    template = ViewPageTemplateFile('templates/advanced-paged-search.pt')
    form_fields = form.Fields(IAdvancedSearch)
    form_fields["status_date"].custom_widget = SelectDateWidget

    def __init__(self, *args):
        super(AdvancedPagedSearch, self).__init__(*args)
        statuses = SimpleVocabulary([])
        indexed_fields = ['all', ]
        content_type = self.request.get('form.content_type', '')
        if content_type:
            dotted_name = "bungeni.models.domain.%s" % content_type
            domain_class = resolve.resolve(dotted_name)
            statuses = get_statuses_vocabulary(domain_class)
            f = interfaces.IIndexer(domain_class()).fields()
            indexed_fields = indexed_fields + [i for i, fld in f]

        self.form_fields += \
            form.Fields(
                schema.Choice(__name__='owner', title=_("Owner"),
                    vocabulary=get_users_vocabulary(), required=False),
                schema.Choice(__name__='status', title=_("Status"),
                    vocabulary=statuses, required=False),
                schema.Choice(__name__='field', title=_('Field'),
                    values=indexed_fields, required=False),
                IHighLight
            )

    def update(self):
        need("advanced-search")
        super(AdvancedPagedSearch, self).update()

    @form.action(label=_(u"Search"), name="search")
    def handle_search(self, action, data):
        self.searcher = component.getUtility(interfaces.IIndexSearch)()
        search_term = data['full_text']
        content_type = data['content_type']
        lang = data['language']
        indexed_field = data.get('field', '')
        status = data.get('status', '')
        status_date = data['status_date']
        owner = data.get('owner', '')

        if not lang:
            lang = 'en'

        if not search_term:
            self.status = _(u"Invalid Query")
            return

        # Setting FLAG_PARTIAL to search incomplete words 
        if len(search_term) > MINIMAL_PARTIAL_QUERY:
            self.searcher._qp_flags_base |= _xapian.QueryParser.FLAG_PARTIAL

        # compose query
        t = time.time()

        if content_type and indexed_field and indexed_field != 'all':
            text_query = self.searcher.query_field(indexed_field, search_term)
            lang_query = self.searcher.query_field('language', lang)
            self.query = self.searcher.query_composite(
                self.searcher.OP_AND,
                (text_query, lang_query,))
        else:
            text_query = self.searcher.query_parse(search_term)
            lang_query = self.searcher.query_field('language', lang)
            self.query = self.searcher.query_composite(
                self.searcher.OP_AND,
                    (text_query, lang_query,))

        if content_type:
            content_type_query = self.searcher.query_field('object_type',
                                                           content_type)
            self.query = self.searcher.query_composite(
                self.searcher.OP_AND,
                (self.query, content_type_query,))

        if content_type and status:
            status_query = self.searcher.query_field('status', status)
            self.query = self.searcher.query_composite(
                self.searcher.OP_AND,
                (self.query, status_query,))

        if status_date:
            status_date_query = self.searcher.query_field('status_date', 
                                                          index.date_value(status_date))
            self.query = self.searcher.query_composite(
                self.searcher.OP_AND,
                (self.query, status_date_query,))

        if owner:
            owner_query = self.searcher.query_field('owner', str(owner))
            self.query = self.searcher.query_composite(
                self.searcher.OP_AND,
                (self.query, owner_query,))

        self.results = self._results
        self.search_time = time.time() - t

        # spelling suggestions
        suggestion = self.searcher.spell_correct(search_term)
        self.spelling_suggestion = (
            search_term != suggestion and suggestion or None)


class AjaxGetClassStatuses(BrowserView):

    def __call__(self):
        dotted_name = "bungeni.models.domain.%s" % self.request.form.get('dotted_name').split(".")[-1]
        tmp = '<option value="%s">%s</option>'
        try:
            domain_class = resolve.resolve(dotted_name)
            states = translated_vocabulary(
                get_statuses_vocabulary(domain_class), self.request)
            response = [tmp % (state.value, _(state.title))
                        for state in states]
            no_value = translate(u"vocabulary-missing-single-value-for-edit",
                                 domain="zope", context=self.request)
            if no_value == u"vocabulary-missing-single-value-for-edit":
                no_value = "(no value)"
            response.insert(0, tmp % ('', no_value))
            return '\n'.join(response)
        except Exception:
            return "ERROR"


class AjaxGetClassFields(BrowserView):

    def __call__(self):
        dotted_name = "bungeni.models.domain.%s" % self.request.form.get('dotted_name').split(".")[-1]
        tmp = '<option value="%s">%s</option>'
        try:
            domain_class = resolve.resolve(dotted_name)
            f = interfaces.IIndexer(domain_class()).fields()
            response = [tmp % (i, i) for i, fld in f]
            response = [tmp % ('all', 'all'), ] + response
            return '\n'.join(response)
        except Exception:
            return "ERROR"

''' !+UNUSED(mr, dec-2011) 
    and why does it not inherit/comply with container.ContainerJSONListing ?
    and, yikes, somebody should clean out this module !
    running pyflakes could be a good start...
    not to forget reading the source style guide 

class ConstraintQueryJSON(BrowserView):
    """ Full Text Search w/ Constraint """
    def __call__(self):
        search_term = self.request.form.get('query')
        #if not search_term:
        #    return simplejson.dumps(None)
        self.searcher = component.getUtility(interfaces.IIndexSearch)()
        results = self.query(search_term)
        return simplejson.dumps(results)

    def query(self, search_term, spell_correct=False):
        # result
        d = {}

        # compose and execute query
        t = time.time()
        start, limit = self.getOffsets()
        query = self.composeQuery(search_term)
        sort_key, sort_dir = self.getSort()
        if sort_dir == 'desc':
            sort_key = '-' + sort_key

        results = self.searcher.search(
            query, start, start + limit, sortby=sort_key)

        # prepare results
        d['results'] = self.formatResults(results)
        d['SearchTime'] = time.time() - t
        d['length'] = results.matches_estimated
        d["recordsReturned"] = len(results)
        d['sort'] = sort_key
        d['dir'] = sort_dir
        d['start'] = start
        return d

    def composeQuery(self, search_term):

        if search_term:
            query = self.searcher.query_parse(search_term)
        else:
            query = None

        constraint = self.getConstraintQuery()

        if constraint and query:
            query = self.searcher.query_multweight(query, 3.0)
            if isinstance(constraint, list):
                constraint.insert(0, query)
                query = constraint
            else:
                query = self.searcher.query_composite(
                    self.searcher.OP_AND, (query, constraint)
                )
        elif constraint and not query:
            return constraint
        elif query and not constraint:
            return query
        else:
            raise SyntaxError("invalid constraint query")

        return query

    def getConstraintQuery(self):
        raise NotImplemented

    def getOffsets(self, limit_default=30):
        start = self.request.get('start', 0)
        limit = self.request.get('limit', 25)
        try:
            limit_default = int(limit_default)
            start, limit = int(start), int(limit)
            if not limit:
                limit = limit_default
        except ValueError:
            start, limit = 0, 30
        # xapian end range is not inclusive
        return start, limit + 1

    def getSort(self):
        sort_key = self.request.get('sort', 'title')
        sort_dir = self.request.get('dir', 'asc')
        return sort_key, sort_dir

    def formatResults(self, results):
        r = []
        for i in results:
            r.append(
                dict(rank=i.rank,
                      object_type=i.data.get('object_type'),
                      title=i.data.get('title'),
                      weight=i.weight,
                      percent=i.percent
                )
            )
        return r
'''


class Similar(BrowserView, ResultListing):
    template = ViewPageTemplateFile('templates/similar.pt')

    def update(self):
        resolver = component.getUtility(interfaces.IResolver)

        doc_id = resolver.id(removeSecurityProxy(self.context))

        t = time.time()
        searcher = component.getUtility(interfaces.IIndexSearch)()
        query = searcher.query_similar(doc_id)
        # similarity includes original doc
        # grab first fifteen matching
        self.results = searcher.search(query, 0, 15)
        self.search_time = time.time() - t
        self.doc_count = searcher.get_doccount()

    def render(self):
        return self.template()

    def __call__(self):
        self.update()
        return self.render()


class SearchResultItem(object):

    template = ViewPageTemplateFile('templates/search-result.pt')

    @property
    def language(self):
        lang = self.request.get('form.language', '')
        if not lang:
            lang = self.request.locale.getLocaleID()
        return lang

    @property
    def item(self):
        return ISearchResult(self.context)

    def __call__(self):
        return self.template()
