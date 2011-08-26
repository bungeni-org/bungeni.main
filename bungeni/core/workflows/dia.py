#
import sys
from bungeni.core.workflows.adapters import get_workflow
from bungeni.core.workflow.dot import dot


def write_file(in_folder, file_name, contents):
    f = open(in_folder + file_name, "w")
    # !+UNICODETEXT(AH,2011-05-03) without the utf-8 encoding
    # the write fails for text with accents e.g. portoguese.
    f.write(contents.encode("UTF-8"))
    f.close()


def main(argv):
    output_folder = ""
    if (len(argv) > 0 ):
        output_folder = argv[0]
        if (output_folder.endswith("/") == False):
            output_folder = output_folder + "/"
    
    #!+bungeni_custom(mr, aug-2011) should be localized parameter, or 
    # generated dynamically e.g. listing of workflow file definitions.
    workflow_names = [
        "address", 
        "agendaitem", 
        "attachedfile",
        "bill",
        "committee",
        "event",
        "groupsitting",
        "group",
        "heading",
        "motion",
        "parliament", 
        "question",
        "report",
        "signatory",
        "tableddocument",
        "user",
    ]
    for name in workflow_names:
        write_file(output_folder, "%s.dot" % name, dot(get_workflow(name)))

if __name__ == "__main__":
    main(sys.argv[1:])


