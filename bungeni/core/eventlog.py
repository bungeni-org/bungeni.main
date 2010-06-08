
import logging, sys
import zope.event

console = logging.StreamHandler( sys.stdout )
console.setLevel( logging.DEBUG )
evt_log = logging.getLogger('bungeni')
evt_log.setLevel( logging.DEBUG )
evt_log.addHandler( console )

idx_log = logging.getLogger('ore.xapian')
idx_log.setLevel( logging.DEBUG )
idx_log.addHandler( console )

filter_events = [
    'Registered',
    'BeforeTraverseEvent',
    'ContainerModifiedEvent',
    'BeforeUpdateEvent',
    'EndRequestEvent',
    'AuthenticatedPrincipalCreated',
    ]

def eventLog( event ):
    if event.__class__.__name__ in filter_events:
        return
    evt_log.info( "Event %r"%(event))

zope.event.subscribers.append( eventLog )
