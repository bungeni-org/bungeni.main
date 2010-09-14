from bungeni.ui.calendar.utils import pack_date_range
from bungeni.ui.calendar.utils import unpack_date_range

date_range_cookie_name = "date_range"


def _get_first_url_component(request):
    """ (request) -> url_component:str
    
    NOTE: this should only be called AFTER traversing the root.
    """
    return request.getURL(level=0, path_only=True)


def get_date_range(request):
    cookie = request.getCookies().get(date_range_cookie_name)
    if cookie is not None:
        return unpack_date_range(cookie)
    return (None, None)


def set_date_range(request, start, end, path=None):
    """Set date range cookie.

    By default the path is set to the first path element.
    """
    if path is None:
        path = _get_first_url_component(request)
    request.response.setCookie(
        date_range_cookie_name, pack_date_range(start, end),
        max_age=3600, path=path)


def unset_date_range(request, path=None):
    """Unset (delete) date range cookie.
    
    By default the path is set to the first path element.
    """
    if path is None:
        path = _get_first_url_component(request)
    request.response.setCookie(date_range_cookie_name, "deleted", path=path)
    request.response.expireCookie(date_range_cookie_name, path=path)

