from zope import interface

import interfaces

def handle_authenticated_principal_created_event(event):
    interface.alsoProvides(event.request, interfaces.IBungeniAuthenticatedSkin)
    
