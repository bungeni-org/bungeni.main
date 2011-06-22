# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni skin handling

$Id$
"""
log = __import__("logging").getLogger("bungeni.ui.skin")

from zope import interface

import interfaces

def handle_authenticated_principal_created_event(event):
    log.debug("[Authenticated Principal Event] [request:%s] [event:%s]" % (
        id(event.request), event))
    interface.alsoProvides(event.request, interfaces.IBungeniAuthenticatedSkin)

