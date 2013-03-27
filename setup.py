from setuptools import setup, find_packages

setup(name='bungeni',
      version='0.2',
      description="server packaging, deployment, startup of bungeni server",
      long_description="",
      keywords='',
      author='Bungeni Developers',
      author_email='bungeni-dev@googlegroups.com',
      url='http://www.bungeni.org',
      license='GPL',
      # Get more from http://www.python.org/pypi?%3Aaction=list_classifiers
      classifiers=['Programming Language :: Python',
                   'Environment :: Web Environment',
                   'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
                   'Framework :: Zope3',
                   ],

      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=['setuptools',
            # Following packages are required by :
            # bungeni.server
                        'zope.publisher',
                        'zope.traversing',
                        'zope.app.wsgi>=3.4.0',
                        'zope.app.appsetup',
                        'zope.app.zcmlfiles',
                        # The following packages aren't needed from the
                        # beginning, but end up being used in most apps
                        'zope.annotation',
                        'zope.copypastemove',
                        'zope.formlib',
                        'zope.i18n',
                        'zope.app.authentication',
                        'zope.app.session',
                        'zope.app.intid',
                        'zope.app.keyreference',
                        'zope.app.catalog',
                        # The following packages are needed for functional
                        # tests only
                        'zope.testing',
                        'zope.app.testing',
                        'zope.securitypolicy',
                        'zope.sendmail',
                        'ore.wsgiapp',
            #
            # The following are required by bungeni.models
                        'SQLAlchemy',
                        'zope.schema',
                        'zope.interface',
                        'zope.i18n',
                        # The following are required by bungeni.portal
            #
                'pyquery>=0.3.1',
                'Deliverance',
                #'chameleon.html',
            # The following are used by bungeni.core
            #
                        'ore.xapian',
                        'z3c.dav',
                        'plone.transforms',
                        'pika',
            # The following are used by bungeni.ui
                        'zope.app.cache',
                        'plone.memoize',
                        'ore.yui',
                        #'marginalia',
                        'z3c.menu.ready2go',
                        'zc.displayname',
                        'zope.formlib',
                        'imsvdex',
                        'zdhtmlxscheduler',
                        'z3tinymce',
            # The following packages are used by:
            # bungeni.ui & bungeni.rest                        
                        'simplejson',                                                
            #i18n tools - script generation during buildout
                        'lovely.recipe==1.0.0',
            ],
      entry_points =
    {
    'console_scripts' : [
        'bungeni-reset-db = bungeni.core.schema:reset_database',
                # !+DISABLE_XAPIAN
                #'bungeni-sync-index = bungeni.core.index:reset_index',
    ],
    'paste.app_factory' : [
        'main = bungeni.server.startup:application_factory'
    ],
    'zc.buildout' : [
        'i18n = bungeni.utils.i18n:I18n' 
    ]
    }
 )




