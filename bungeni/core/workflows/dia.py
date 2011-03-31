#
import sys
from bungeni.core.workflows.adapters import wf
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
    
    write_file(output_folder, "bill.dot", dot(wf("bill"))
    write_file(output_folder, "question.dot", dot(wf("question"))
    write_file(output_folder, "motion.dot", dot(wf("motion"))
    write_file(output_folder, "version.dot", dot(wf("version"))
    write_file(output_folder, "groupsitting.dot", dot(wf("groupsitting"))
    write_file(output_folder, "group.dot", dot(wf("group"))
    write_file(output_folder, "question.dot", dot(wf("question"))
    write_file(output_folder, "address.dot", dot(wf("address"))
    write_file(output_folder, "tableddocument.dot", dot(wf("tableddocument"))
    write_file(output_folder, "agendaitem.dot", dot(wf("agendaitem"))
    write_file(output_folder, "committee.dot", dot(wf("committee"))
    write_file(output_folder, "parliament.dot", dot(wf("parliament"))


if __name__ == "__main__":
    main(sys.argv[1:])


