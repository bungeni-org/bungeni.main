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
                
def switch_links_to_cynin(content, theme, resource_fetcher, log):
    """
    Switch links in the 'my_groups' tab of the workspace view to point
    to the cynin workspaces.
    """
    wtmg = content("#workspace-table-my_groups a")
    for link in wtmg:
        if "politicalgroups" in link.get("href"):
            obj_id = "/cynin/home/group.political-group." + \
                     link.get("href").split("/", 6)[-1].split("-", 1)[-1]
        else:
            obj_id = "/cynin/home/" + link.get("href").split("/", 3)[-1]
        pq(link).attr('href', obj_id)
        
def add_member_workspace_links(content, theme, resource_fetcher, log):
    """
    Add a member's 'private folder' and 'web pages' links to the workspace
    second level menu items.
    """
    
    link_items = content("#portal-personaltools span")
    member_id = link_items.pop(0).text
    content('#portal-personaltools').append("<li class='navigation'>\
    <a href='/cynin/home/" + member_id + "/private_folder" + "'>private folder\
    </a></li>")
    content('#portal-personaltools').append("<li class='navigation'>\
    <a href='/cynin/home/" + member_id + "/web_pages" + "'>web pages</a></li>")
    
    
def add_member_public_links(content, theme, resource_fetcher, log):
    """
    Add a member's 'web pages' links to the public view.
    """
    member_id = content(".MemberOfParliament .User .content-right-column")\
                .pop(4).text_content()
    link_value = "/cynin/home/" +  member_id.strip() + "/web_pages"


def replace_login_link(content, theme, resource_fetcher, log):
    """Login will be via cynin to facilitate creation of cynin member spaces.
    """
    if ("logout" or "Log out") not in theme.html() and \
           theme("#portal-personaltools").html() != None:
        login_url = theme("#portal-personaltools li:first-child a").attr("href")
        if "plone/login_form" in login_url:
            login_url = login_url.replace("plone", "cynin")
        else:
            login_url = login_url.replace("login", "cynin/login_form")
        pq(theme("#portal-personaltools li:first-child a")).attr("href", login_url)     


def enable_text_editor(content, theme, resource_fetcher, log):
    """
    Disable rich text editor in favor of plain text editor for Selenium.
    """
    scripts = theme('#alchemist-form script')
    for script in scripts:
        if script.text.__contains__('YAHOO.widget.Editor'):
            script.text=""
            script.drop_tag()                               
