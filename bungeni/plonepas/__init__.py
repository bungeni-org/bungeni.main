#

def initialize( context ):
    
    from AccessControl.Permissions import add_user_folders
    from Products.PluggableAuthService.PluggableAuthService import registerMultiPlugin, MultiPlugins

    import group, user
    
    if group.GroupManager.meta_type not in MultiPlugins:
        registerMultiPlugin( group.GroupManager.meta_type )
    
    context.registerClass(group.GroupManager,
            permission = add_user_folders,
            constructors = (group.manage_addBungeniGroupManagerForm,
                            group.manage_addBungeniGroupManager ),
            visibility = None)

    if user.UserManager.meta_type not in MultiPlugins:
        registerMultiPlugin( user.UserManager.meta_type )
    
    context.registerClass(user.UserManager,
            permission = add_user_folders,
            constructors = (user.manage_addBungeniUserManagerForm,
                            user.manage_addBungeniUserManager ),
            visibility = None)
    
