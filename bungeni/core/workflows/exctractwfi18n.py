#!/usr/bin/env python
# encoding: utf-8
# This is used to make the workflow actions and states translatable
# it simply builds a pagetemplate which i18nextract will look into 
# to build the pot file
from bungeni.core.workflows import adapters
from bungeni.core.workflows import bill
from bungeni.core.workflows import question
from bungeni.core.workflows import motion
from bungeni.core.workflows import version
from bungeni.core.workflows import groupsitting
from bungeni.core.workflows import group
from bungeni.core.workflows import address
from bungeni.core.workflows import tableddocument
from bungeni.core.workflows import agendaitem
from bungeni.core.workflows import committee
from bungeni.core.workflows import parliament
from bungeni.core.workflows import attachedfile
from bungeni.core.workflows import event
from bungeni.core.workflows import user
from bungeni.core.workflows import report
import os

path = os.path.split(os.path.abspath(bill.__file__))[0]

f = open('%s/wfi18n.pt' % path, 'w')


f.write(
"""
<html xmlns:tal="http://xml.zope.org/namespaces/tal"
      xmlns:metal="http://xml.zope.org/namespaces/metal"
      xmlns:i18n="http://xml.zope.org/namespaces/i18n"
      i18n:domain="bungeni.core"> <body>
      """)

for wf in [bill, question, motion, version, groupsitting, group,
    address, tableddocument, agendaitem, committee, parliament,
    attachedfile, event, report]:
    name = wf.__name__.split('.')[-1]
    for state in wf.states:
        #f.write( '<b i18n:translate="%s_wf_state_%s" >' % ( name, state))
        f.write('<b i18n:translate="" >' + wf.states[state].title + '</b>')
        f.write('\n')
    for t in wf.wf._id_transitions:
        #f.write( '<b i18n:translate="%s_wf_transition_%s" >' %( name, t))
        f.write('<b i18n:translate="" >' + wf.wf.getTransitionById(t).title + '</b>')
        f.write('\n')
f.write('</body></html>')
f.close()

