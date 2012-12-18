# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""The Bungeni Application - UI Setup

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.app")


from ore.wsgiapp.interfaces import IWSGIApplicationCreatedEvent
from bungeni.models.interfaces import IBungeniApplication
from bungeni.utils import register


@register.handler((IBungeniApplication, IWSGIApplicationCreatedEvent))
def on_wsgi_application_created_event(application, event):
    """Additional UI setup on IWSGIApplicationCreatedEvent.
    """
    # !+ui.app.on_wsgi_application_created_event ALWAYS called prior to core.app.
    log.debug("UI ON_WSGI_APPLICATION_CREATED_EVENT: %s, %s", application, event) 
    
    # ensure register workflow views
    import bungeni.ui.workflow
    
    # ensure register version views
    import bungeni.ui.versions
    
    import bungeni.ui.feature
    bungeni.ui.feature.setup_customization_ui()
    
    # load and apply-back UI descriptor customizations
    from bungeni.ui.descriptor import localization
    localization.check_reload_localization(None)
    
    bungeni.ui.feature.apply_customization_ui()

