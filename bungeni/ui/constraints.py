import re
import zope.schema

EMAIL_RE = re.compile(
    "([0-9a-zA-Z_&.+-]+!)*[0-9a-zA-Z_&.+-]+@"
    "(([0-9a-zA-Z]([0-9a-zA-Z-]*[0-9a-z-A-Z])?\.)"
    "+[a-zA-Z]{2,6}|([0-9]{1,3}\.){3}[0-9]{1,3})$")

def check_email( email ):
    if EMAIL_RE.match( email ) is None:
        raise NotAnEmailAddress(email)
        return False
    return True

class NotAnEmailAddress(zope.schema.ValidationError):
    """This is not a valid email address"""
     
