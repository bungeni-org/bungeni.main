#

from bungeni.core.workflows import adapters

from bungeni.core.workflows import bill
from bungeni.core.workflows import question
from bungeni.core.workflows import motion
from bungeni.core.workflows import version
from bungeni.core.workflows import groupsitting
from bungeni.core.workflows import groups
from bungeni.core.workflows import address
from bungeni.core.workflows import tableddocument
from bungeni.core.workflows import agendaitem
from bungeni.core.workflows import committee
from bungeni.core.workflows import parliament


def main():
    f = open('bill.dot', 'w')
    f.write(bill.wf.dot())
    f.close()

    f = open('question.dot', 'w')
    f.write(question.wf.dot())
    f.close()
    
    f = open('motion.dot', 'w')
    f.write(motion.wf.dot())
    f.close()

    f = open('version.dot', 'w')
    f.write(version.wf.dot())
    f.close()
    
    f = open('groupsitting.dot', 'w')
    f.write(groupsitting.wf.dot())
    f.close()

    f = open('groups.dot', 'w')
    f.write(groups.wf.dot())
    f.close()

    f = open('address.dot', 'w')
    f.write(address.wf.dot())
    f.close()
    
    f = open('tableddocument.dot', 'w')
    f.write(tableddocument.wf.dot())
    f.close()

    f = open('agendaitem.dot', 'w')
    f.write(agendaitem.wf.dot())
    f.close()

    f = open('committee.dot', 'w')
    f.write(committee.wf.dot())
    f.close()

    f = open('parliament.dot', 'w')
    f.write(parliament.wf.dot())
    f.close()



if __name__ == "__main__":
    main()


