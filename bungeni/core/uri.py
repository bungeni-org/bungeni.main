import bungeni.ui.utils as ui_utils

def generate_uri(object, event):
    uri = ''

    if object.type == 'bill':
        if object.publication_date is not None:
            uri = "/bungeni/%s/%s/%s/%s/%s@/main" % ("ke", object.type, object.publication_date, object.registry_number, object.language)
    else:
        if object.status_date is not None:
            uri = "/bungeni/%s/%s/%s/%s/%s@/main" % ("ke", object.type, object.status_date.date(), object.registry_number, object.language)

    if object.uri is None and uri:
        object.uri = uri