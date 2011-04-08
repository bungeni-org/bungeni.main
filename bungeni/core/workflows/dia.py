#
import sys
from bungeni.core.workflows.adapters import get_workflow
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
    
    write_file(output_folder, "bill.dot", dot(get_workflow("bill")))
    write_file(output_folder, "question.dot", dot(get_workflow("question")))
    write_file(output_folder, "motion.dot", dot(get_workflow("motion")))
    write_file(output_folder, "version.dot", dot(get_workflow("version")))
    write_file(output_folder, "groupsitting.dot", 
        dot(get_workflow("groupsitting")))
    write_file(output_folder, "group.dot", dot(get_workflow("group")))
    write_file(output_folder, "question.dot", dot(get_workflow("question")))
    write_file(output_folder, "address.dot", dot(get_workflow("address")))
    write_file(output_folder, "tableddocument.dot", 
        dot(get_workflow("tableddocument")))
    write_file(output_folder, "agendaitem.dot", 
        dot(get_workflow("agendaitem")))
    write_file(output_folder, "committee.dot", 
        dot(get_workflow("committee")))
    write_file(output_folder, "parliament.dot", 
        dot(get_workflow("parliament")))


if __name__ == "__main__":
    main(sys.argv[1:])


