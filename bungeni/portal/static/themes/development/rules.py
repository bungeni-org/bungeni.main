import urllib2
from pyquery import PyQuery as pq
from urlparse import urlsplit

def add_section_links(content, theme, resource_fetcher, log):
    """
    Add top level class links and logos for the different sections
    (workspace and portal).
    """
    host_url = urlsplit(log.theme_url)
    if len(theme('#portal-personaltools li:nth-child(4)')) > 0 or \
           content("#myareaavatarimg") or theme("#user-name"):
        theme('body').addClass('template-workspace')
    else:
        theme('body').addClass('template-portal')

def image_links(content, theme, resource_fetcher, log):
    """
    Use absolute links to the members image and political groups logo.
    """
    
    if content('#region-content').html() != None:
        link_value  = str(content('#region-content').html().encode("utf-8"))
        to_replace = 'file-image/image'
        to_replace = ['file-image/image', 'file-image/logo_data']
        for image in to_replace:
            if image in link_value:
                link_id= content('#portal-breadcrumbs a:last-child')
                link_id = str(link_id).split('href="')
                link_id = str(link_id[1]).split('">')[0]
                link_node = content('#region-content')
                new_value = link_value.replace('./'+image, 
                                               str(link_id)+'/'+image)
                link_node.replaceWith('<div id="region-content" \
                class="documentContent">' + new_value + '</div>')
                
