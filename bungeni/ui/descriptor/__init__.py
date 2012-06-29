
# catalyse descriptors
from bungeni.alchemist import catalyst
from bungeni.ui.descriptor import descriptor
catalyst.catalyse_descriptors(descriptor)
# !+CATALYSE_DESCRIPTORS(mr, jun-2012) moving this into
# bungeni.ui.app.on_wsgi_application_created_event causes 
# ui.forms.fields.filterFields canWrite call for each form field to fail... 

