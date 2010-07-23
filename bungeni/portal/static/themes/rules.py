from pyquery import PyQuery as pq
from urlparse import urlsplit

def add_section_links(content, theme, resource_fetcher, log):
    """
    Add top level class links and logos for the different sections (workspace and portal).
    """
    host_url = urlsplit(log.theme_url)
    if len(theme('#portal-personaltools li:nth-child(4)')) > 0:

        theme('#portal-logo img').attr('src', host_url[0] + '://' +  host_url[1] +'/++resource++portal/logo-workspace.png')
        theme('#portal-logo img').attr('width', '803px')
        theme('#portal-logo img').attr('height', '60px')
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
                link_node.replaceWith('<div id="region-content" class="documentContent">' + new_value + '</div>')


def add_plone_tabs(content, theme, resource_fetcher, log):
    """
    Add top level dummy menu tabs to represent plone content.
    """
    theme('.level0').append("<li class='plain'><a href='#'>have your say</a></li>")
    theme('.level0').append("<li class='plain'><a href='#'>how we work</a></li>")
    theme('.level0').append("<li class='plain'><a href='#'>reference material</a></li>")

def rewrite_links(content, theme, resource_fetcher, log):
    """
    Fix links for css imports.
    """
    head_styles = content("head style")
    for stylevalue in head_styles:
        stylevalue =  stylevalue.text.split('(')[1]
        stylevalue = stylevalue.split(')')[0]
        
        content('head').append('<link rel="stylesheet" type="text/css" href=' \
                               + stylevalue + ' />')
