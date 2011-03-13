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

import time, simplejson, urllib
from bungeni.ui import forms
from ore.xapian import interfaces

from zope import interface, schema, component
from zope.publisher.browser import BrowserView
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.security.proxy import removeSecurityProxy
from zope.formlib import form
from zc.table import table, column
from bungeni.core.i18n import _


class ISearch(interface.Interface):

    full_text = schema.TextLine(title=_("Query"), required=False)


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

    @property
    def search_status(self):
        return "Found %s Results in %s Documents in %0.5f Seconds" % (
            len(self.results), self.doc_count, self.search_time)

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


class Search(forms.common.BaseForm, ResultListing):
    """  basic content search form and results
    """
    template = ViewPageTemplateFile('templates/search.pt')
    form_fields = form.Fields(ISearch)
    #selection_column = columns[0]

    def setUpWidgets(self, ignore_request=False):
        # setup widgets in data entry mode not bound to context
        self.adapters = {}
        self.widgets = form.setUpDataWidgets(self.form_fields, self.prefix,
             self.context, self.request, ignore_request=ignore_request)


    def do_search(self, searcher, query):
      return searcher.search(query, 0, self.doc_count)

    @form.action(label=_(u"Search"))
    def handle_search(self, action, data):
        searcher = component.getUtility(interfaces.IIndexSearch)()
        search_term = data[ 'full_text' ]

        if not search_term:
            self.status = _(u"Invalid Query")
            return

        # compose query
        t = time.time()
        query = searcher.query_parse(search_term)
        self.doc_count = searcher.get_doccount()
        self.results = self.do_search(searcher, query)
        self.search_time = time.time() - t

        # spelling suggestions
        suggestion = searcher.spell_correct(search_term)
        self.spelling_suggestion = (
            search_term != suggestion and suggestion or None)


class Pager(object):
  '''pager for search result page'''
  action_method = 'get'
  items_count = 1

  def do_search(self, searcher, query):
    try:
        page = int(self.request.form.get('page', 1))
    except ValueError:
        page = 1

    if self.doc_count > self.items_count:
        page_count = self.doc_count / self.items_count + \
          int(bool(self.doc_count % self.items_count))

        def generate_url(x):
            args = dict(self.request.form)
            args.pop('page', None)

            return str(self.request.URL) + '?' + \
                urllib.urlencode(args) + '&page=%d' % x

        self.pages = map(lambda x: {'number':x,
            'url': generate_url(x)}, range(1, page_count + 1))

    return searcher.search(query, self.items_count * (page - 1),
        self.items_count * page)

class PagedSearch(Pager, Search):
  template = ViewPageTemplateFile('templates/pagedsearch.pt')

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

