import urllib2
from pyquery import PyQuery as pq
from urlparse import urlsplit

def get_theme_host(log):
    theme_host = urlsplit(log.theme_url)[1].split("/themes")[0]
    return theme_host

def add_section_links(content, theme, resource_fetcher, log):
    """
    Add top level class links and logos for the different sections
    (workspace and portal).
    """
    host_url = urlsplit(log.theme_url)
    if "logout" in theme('#portal-personaltools').html():
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
            obj_id = "/plone/groups/" + link.get("href").split("/", 3)[-1]
        pq(link).attr('href', obj_id)
        
def add_member_workspace_links(content, theme, resource_fetcher, log):
    """
    Add a member's 'private space' and 'web space' links to the workspace
    second level menu items (if they exist).
    """
    link_items = content("#portal-personaltools span")
    member_id = link_items.pop(0).text
    content('#portal-personaltools').append(
            "<li class='navigation'><a href='/plone/membership/" + member_id +
            "/private_space/folder_contents" + "'>private space</a></li>")
    
    host_url = urlsplit(log.theme_url)
    theme_host = get_theme_host(log).split(":")[0]
    test_url = "http://" + theme_host + ":8082" + "/plone/membership/" + \
                member_id + "/web_space"

    try:
        if urllib2.urlopen(test_url).code == 200:
            content('#portal-personaltools').append("<li class='navigation'>\
            <a href='/plone/membership/" + member_id + \
            "/web_space/folder_contents" + "'>web space</a></li>")
    except:
        pass 
        
        
def add_group_workspace_links(content, theme, resource_fetcher, log):
    """
    Add a groups 'web space' links to the workspace groups links.
    """
    
    group_table_contents = content("#workspace-table-my_groups")

    
def add_member_public_links(content, theme, resource_fetcher, log):
    """
    Add a member's 'web pages' links to the public view.
    """
    member_id = content(".MemberOfParliament .User .content-right-column")\
                .pop(4).text_content()
    link_value = "/plone/membership/" +  member_id.strip() + "/web_space"
    
def add_space_tab(content, theme, resource_fetcher, log, space_type):
    """
    Add the member's or groups web space as a tab
    """
    theme_host = get_theme_host(log)
    theme_url = "http://" + theme_host
    if len(theme_host.split(":")) > 1:
        theme_port = ":" + theme_host.split(":")[1]
        
    # !+HACK(mn, may-2011) - the plone port is hardcoded. 
    plone_port = ":8082"    
    plone_url = theme_url.split(":")[0] + ":" + theme_url.split(":")[1] + \
                plone_port
    if space_type == "member":
        item_id = content('#portal-breadcrumbs a:last-child')
        space_id = item_id.text().split( )
        link_val = plone_url + "/plone/membership/" + space_id[1] + "." + \
                    space_id[2] +"/web_space"        
    else:
        item_id = content('#portal-breadcrumbs a:last-child').attr("href")
        space_id =  item_id.split("-")[-1]
        if space_type == "committee":
            link_val = plone_url + "/plone/groups/group.committee." + \
                        space_id + "web_space"            
        else:
            link_val = plone_url + "/plone/groups/group.political-group." + \
                        space_id + "web_space" 
    try:
        if urllib2.urlopen(link_val).code == 200:
            response = urllib2.urlopen(link_val)
            html_content = pq(response.read())
            head_content = html_content("head").html().replace(
                            plone_port, theme_port)
            space_tab = html_content("#content-core").html().replace(
                        plone_port, theme_port)                    
            content("head").append(head_content)
            content(".enableFormTabbing").append(
            "<dt id='fieldsetlegend-web_space'>web space</dt>\
            <dd id='fieldset-web_space'>" + space_tab + "</dd>")
            theme(".level0").prepend(content("#portal-globalnav").children())
    except:
        pass   

def replace_login_link(content, theme, resource_fetcher, log):
    """Login and logout will be via plone to facilitate creation of
     member  and group spaces.
    """
    login_link = theme("a[href$='/login']")
    if len(login_link) > 0:
        if login_link.attr("href"):
            login_value = pq(login_link).attr("href").replace(
                            "login", "plone/login")
            pq(login_link).attr("href", login_value)
    
    logout_link = theme("a[href$='/logout']")
    if len(logout_link) > 0:
        if "plone/logout" not in logout_link.attr("href"):
            logout_value = pq(logout_link).attr("href").replace(
                            "logout", "plone/logout")
            pq(logout_link).attr("href", logout_value)


def add_menu_items(content, theme, resource_fetcher, log):
    """
    Add menu items
    """
    newlist = theme("div#portal-globalnav").clone()("li")

    theme(".row_1 .three-columns-equal .block_1").append(
        "<h1 class='documentFirstHeading'>Menu</h1>")    
    theme(".row_1 .three-columns-equal .block_1").append("<ul></ul>")    
    for item in newlist:
        pq(item).removeClass("plain")
        theme(".row_1 .three-columns-equal .block_1 ul").append(item)
        for list_item in theme("div#portal-column-one li"):
            check_val = urlsplit(pq(list_item.getchildren()).attr("href"))[2]
            if "plone" in pq(list_item.getchildren()).attr("href"):
                check_val = check_val.split("/")[2]
            else:
                check_val = check_val.split("/")[1]                
                
            if check_val in pq(item).children().attr("href"):
                pq(list_item).addClass("2ndlevel")
                theme(".row_1 .three-columns-equal .block_1 ul").append(
                    list_item)
     
def add_rss_feeds(content, theme, resource_fetcher, log):
    """
    Add rss feeds and news content.
    """
    news_query_value = "/plone/news"
    language_selector = content("#portal-languageselector .selected a").attr(
        "href")
    if language_selector != None:
        language = language_selector.split("=")[1]
        if language !="en":
            news_query_value = "/plone/news-" + language + "?set_language=" + \
                               language

    host_url = urlsplit(log.theme_url)
    source_dest_mapping = {news_query_value:
                           ".row_1 .three-columns-equal .block_2",
                           "/plone/feeds/sittings":
                           ".row_1 .three-columns-equal .block_3",                      
                           "/plone/feeds/question-listing":
                           ".row_1 .three-columns-equal .block_3",
                           "/plone/feeds/motion-listing":
                           ".row_1 .three-columns-equal .block_3",
                           "/plone/feeds/bill-listing":
                           ".row_1 .three-columns-equal .block_3"}
    for item in source_dest_mapping:
        try:
            response = urllib2.urlopen(host_url[0] + "://" + host_url[1] +
                                   item)
            url_content = response.read()
            content_data =  pq(url_content)
            theme(source_dest_mapping[item]).append(
                content_data("#content").html().replace("/akomantoso.xml", ""))
        except:
            pass

def reposition_contentActions(content, theme, resource_fetcher, log):
    """
    Move '.contentActions below '.documentDescription'
    !+ Some pages have 2 document descriptions whilst others have none,
    hence the explicit check. Should be revised immediately each document has 
    one top level description.
    """
    element_length = len(theme(".documentDescription"))
    if element_length == 1:
        ca = theme(".contentActions")
        theme.remove(".contentActions")            
        ca.insertAfter(theme(".documentDescription")) 
    elif element_length == 2:
        ca = theme(".contentActions")
        theme.remove(".contentActions")            
        ca.insertAfter(theme(".documentDescription:nth-child(2)"))             
 

def enable_text_editor(content, theme, resource_fetcher, log):
    """
    Disable rich text editor in favor of plain text editor for Selenium.
    """
    scripts = theme('#alchemist-form script')
    for script in scripts:
        if script.text.__contains__('YAHOO.widget.Editor'):
            script.text=""
            script.drop_tag()                               
