"""
This is used to make the workflow actions and states translatable
it simply builds a pagetemplate which i18nextract will look into 
to build the pot file. 

To run (from within ~/cinst/bungeni): 

$ bin/python src/bungeni.main/bungeni/core/workflows/exctractwfi18n.py

"""

import os
from bungeni.core.workflows.adapters import get_workflow

path = os.path.split(os.path.abspath(__file__))[0]

f = open("%s/wfi18n.pt" % path, "w")

f.write("""
<html xmlns:tal="http://xml.zope.org/namespaces/tal"
      xmlns:metal="http://xml.zope.org/namespaces/metal"
      xmlns:i18n="http://xml.zope.org/namespaces/i18n"
      i18n:domain="bungeni"> <body>
""")

for name in [
    "bill", 
    "question", 
    "motion", 
    "version", 
    "groupsitting", 
    "user", 
    "group", 
    "address", 
    "tableddocument", 
    "agendaitem", 
    "committee", 
    "parliament", 
    "attachedfile", 
    "event", 
    "report"
]:
    workflow = get_workflow(name)
    for status, state in workflow.states.items():
        f.write("""<b i18n:translate="">%s</b>""" % (state.title))
        f.write("\n")
    for transition in workflow._transitions_by_id.values():
        f.write("""<b i18n:translate="">%s</b>""" % (transition.title))
        f.write("\n")

f.write("</body></html>")
f.write("\n")
f.close()

