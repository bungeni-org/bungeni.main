
# catalyse descriptors
from bungeni.ui.descriptor import descriptor
descriptor.catalyse_descriptors(descriptor) # !+catalyst
# !+CATALYSE_DESCRIPTORS(mr, jun-2012) moving this into
# bungeni.ui.app.on_wsgi_application_created_event causes 
# ui.forms.fields.filterFields canWrite call for each form field to fail... 

