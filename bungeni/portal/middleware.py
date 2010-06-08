from pyquery import rules
from deliverance import middleware
from deliverance import security

def make_deliverance_middleware(app, global_conf, rule_uri):
    rule_getter = middleware.SubrequestRuleGetter(rule_uri)
    app = middleware.DeliveranceMiddleware(app, rule_getter)
    return security.SecurityContext.middleware(app,
        display_local_files=True, display_logging=True)
        

