#
import sys
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

def write_file(in_folder, file_name, contents):
    f = open(in_folder + file_name, 'w')
    f.write(contents)
    f.close()


def main(argv):
    output_folder = ''
    if (len(argv) > 0 ):
	    output_folder = argv[0]
	    if (output_folder.endswith("/") == False):
		output_folder = output_folder + "/"
    
    write_file(output_folder, 'bill.dot', bill.wf.dot())
    write_file(output_folder, 'question.dot', question.wf.dot())
    
    write_file(output_folder, 'motion.dot', motion.wf.dot())
    write_file(output_folder, 'version.dot', version.wf.dot())
    write_file(output_folder, 'groupsitting.dot', groupsitting.wf.dot())
    write_file(output_folder, 'groups.dot', groups.wf.dot())
    write_file(output_folder, 'question.dot', question.wf.dot())
    write_file(output_folder, 'address.dot', address.wf.dot())
    write_file(output_folder, 'tableddocument.dot', tableddocument.wf.dot())
    write_file(output_folder, 'agendaitem.dot', agendaitem.wf.dot())
    write_file(output_folder, 'committee.dot', committee.wf.dot())
    write_file(output_folder, 'parliament.dot', parliament.wf.dot())




if __name__ == "__main__":
    main(sys.argv[1:])


