# -*- coding: utf-8 -*-
from zope.app.form.browser.itemswidgets import ItemsEditWidgetBase
from zc.resourcelibrary import need

template = """
    %(html)s
    %(javascript)s
    """

OPT_PREFIX = 'yui_'
LEN_OPT_PREFIX = len(OPT_PREFIX)

class AutoCompleteWidget(ItemsEditWidgetBase):
    """Zope3 Implementation of YUI autocomplete widget.
    Can be used with common ChoiceProperty"""

    @property
    def options(self):
        _options = {
            "autoHighlight": True,
            "forceSelection": True,
            "allowBrowserAutocomplete": False

        }

        for k in dir(self):
            if k.startswith(OPT_PREFIX):
                _options[k[LEN_OPT_PREFIX:]] = getattr(self, k)

        items = []

        for k, v in _options.items():
            if isinstance(v, bool):
                v = str(v).lower()
            elif isinstance(v, (str, unicode)):
                try:
                    v = int(v)
                except ValueError:
                    v = "\"%s\"" % v
            items.append("oAC.%s = %s;" % (k, v))

        return "\n".join(items)


    @property
    def dataSource(self):
        items = map(lambda x: """{name: "%(name)s", id: "%(id)s" }""" \
            % {'id': x.token, 'name': self.textForValue(x)},
            self.vocabulary)

        return "[%s]" % ",\n".join(items)

    @property
    def javascript(self):
        kw = {"id": self.name,
              "dsname": self.name.replace('.', '_'),
              "data": self.dataSource,
              "options": self.options
              }

        return """
            <script type="text/javascript">
                YAHOO.namespace('oa.autocomplete');
                YAHOO.oa.autocomplete.%(dsname)s_func = new function() {
                    var %(dsname)s_data = %(data)s;

                    var %(dsname)s_filter = function(sQuery) {
                        var query = unescape(sQuery).toLowerCase(),
                            item,
                            items,
                            i=0,
                            j=0,
                            ll,
                            l=%(dsname)s_data.length,
                            matches = [];

                        for(; i<l; i++) {
                            item = %(dsname)s_data[i];
                            items = item.name.split(" ");
                            items[items.length] = item.name;
                            ll = items.length;
                            for(j=0; j<items.length; j++) {
                                if (items[j].toLowerCase().indexOf(query) == 0) {
                                    matches[matches.length] = item;
                                    break;
                                }
                            }
                        }

                        return matches;
                    };

                    var oDS = new YAHOO.util.FunctionDataSource(%(dsname)s_filter);

                    oDS.responseSchema = {fields : ["name", "id"]};
                    var oAC = new YAHOO.widget.AutoComplete("%(id)s",
                        "%(id)s.container", oDS);
                    %(options)s
                    oAC.resultTypeList = false;
                    var myHiddenField = YAHOO.util.Dom.get("%(id)s.hidden");
                    var myHandler = function(sType, aArgs) {
                        var myAC = aArgs[0];
                        var elLI = aArgs[1];
                        var oData = aArgs[2];
                        myHiddenField.value = oData.id;
                    };
                    oAC.itemSelectEvent.subscribe(myHandler);
                    return {
                        oDS: oDS,
                        oAC: oAC
                    };
                }();
            </script>
            """ % kw

    @property
    def html(self):
        kw = {"id": self.name}

        if self._data is not None and self._data is not self._data_marker:
            term = self.vocabulary.getTerm(self._data)
            kw["value"] = term.token
            kw["text"] = self.textForValue(term)
        else:
            kw["text"] = kw["value"] = ""

        return """
            <div id="%(id)s.autocomplete" class="yui-skin-sam">
              <input id="%(id)s" type="text" value="%(text)s">
              <div id="%(id)s.container"></div>
              <input id="%(id)s.hidden" name="%(id)s" value="%(value)s"
                  type="hidden">
            </div>
            """ % kw

    def __call__(self):
        need("autocomplete")

        contents = []
        contents.append(template % {"html": self.html,
            "javascript": self.javascript})
        contents.append(self._emptyMarker())

        return self._div(self.cssClass, "\n".join(contents))
