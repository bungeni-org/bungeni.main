
# catalyse descriptors
from bungeni.alchemist import catalyst
from bungeni.ui.descriptor import descriptor
catalyst.catalyse_system_descriptors(descriptor)
# !+CATALYSE_SYSTEM_DESCRIPTORS(mr, jun-2012) [feb-2013, still true?] moving
# this into bungeni.ui.app.on_wsgi_application_created_event causes 
# ui.forms.fields.filterFields canWrite call for each form field to fail...
# ie. the edit event view shows fields in view mode!


