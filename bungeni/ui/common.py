
from bungeni.alchemist import container
from zope.security import proxy
from ore import yuiwidget

class AjaxContainerListing(container.ContainerListing):
    formatter_factory = yuiwidget.ContainerDataTableFormatter
    
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
        
