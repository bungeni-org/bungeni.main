Every document type that has notifications enabled may have email notifications

The email notifications follow a simple format eg.
<?xml version="1.0"?>
<template html="false"
  xmlns:tal="http://xml.zope.org/namespaces/tal"
  xmlns:metal="http://xml.zope.org/namespaces/metal">
    <block state="submitted">
        <subject>
            Agenda item has been submitted : <span tal:replace="item/title"/>
        </subject>
        <body>
            The agenda item
            <span tal:replace="item/title"/> was submitted on <span tal:replace="item/status_date"/>
        </body>
    </block>
</template>

The html attribute of the root template element specifies whether the emails
sent should be in html format.

The email template for each state is defined in a block. Within this block 
there should be two child nodes, subject and body, which specify the email subject 
and body respectively. Both use ZPT as the template language.

See -> http://en.wikipedia.org/wiki/Zope#Zope_Page_Templates
