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
    # ensure register workflow views
    import bungeni.ui.workflow
    
    # ensure register version views
    import bungeni.ui.versions

