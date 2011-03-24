#
import sys
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

from bungeni.core.workflow.dot import dot


def write_file(in_folder, file_name, contents):
    f = open(in_folder + file_name, "w")
    f.write(contents)
    f.close()


def main(argv):
    output_folder = ""
    if (len(argv) > 0 ):
	    output_folder = argv[0]
	    if (output_folder.endswith("/") == False):
		output_folder = output_folder + "/"
    
    write_file(output_folder, "bill.dot", dot(bill.wf))
    write_file(output_folder, "question.dot", dot(question.wf))
    write_file(output_folder, "motion.dot", dot(motion.wf))
    write_file(output_folder, "version.dot", dot(version.wf))
    write_file(output_folder, "groupsitting.dot", dot(groupsitting.wf))
    write_file(output_folder, "group.dot", dot(group.wf))
    write_file(output_folder, "question.dot", dot(question.wf))
    write_file(output_folder, "address.dot", dot(address.wf))
    write_file(output_folder, "tableddocument.dot", dot(tableddocument.wf))
    write_file(output_folder, "agendaitem.dot", dot(agendaitem.wf))
    write_file(output_folder, "committee.dot", dot(committee.wf))
    write_file(output_folder, "parliament.dot", dot(parliament.wf))


if __name__ == "__main__":
    main(sys.argv[1:])


