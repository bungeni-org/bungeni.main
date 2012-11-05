import zope.i18n
from zope.i18nmessageid import MessageFactory

_ = MessageFactory = MessageFactory("bungeni")

def translate(msgid, **kwargs):
    """Translate to default domain if none is provided
    """
    if kwargs.get("domain", None) is None:
        kwargs["domain"] = "bungeni"
    return zope.i18n.translate(msgid, **kwargs)
