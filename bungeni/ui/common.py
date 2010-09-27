
from ore import yuiwidget

from zope.security import proxy

from bungeni.alchemist import container
from bungeni.alchemist import model
from bungeni.ui import browser
from bungeni.ui import z3evoque


class AjaxContainerListing(
    container.ContainerListing, 
    browser.BungeniBrowserView
):
    formatter_factory = yuiwidget.ContainerDataTableFormatter
    
    # evoque
    template = z3evoque.PageViewTemplateFile("container.html#generic")
    
    def __call__(self):
        self.update()
        return self.template()
    
    @property
    def form_name(self):
        dm = self.context.domain_model
        return getattr(model.queryModelDescriptor(dm), "container_name", 
            dm.__name__)
    
    @property
    def prefix(self):
        return "container_contents"
    
    @property
    def formatter(self):
        context = proxy.removeSecurityProxy(self.context)
        formatter = self.formatter_factory(
            context,
            self.request,
            (),
            prefix=self.prefix,
            columns=self.columns
        )
        formatter.cssClasses["table"] = "listing"
        formatter.table_id = "datacontents"
        return formatter



class AjaxTableFormatter(yuiwidget.ContainerDataTableFormatter):
    
    fields = None
    
    def getFields(self):
        if self.fields:
            return self.fields
        return super(AjaxTableFormatter, self).getFields()
        
