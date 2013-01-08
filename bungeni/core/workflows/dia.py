#
import sys
# !+DIAGRAMMER(AH, 14-11-2012)
# the below import of bungeni.core.workflows.adpaters is neccessary to 
# set the adapter interfaces for the types correctly, otherwise the custom types
# are not loaded and other types have workflow set to None
from bungeni.core.workflows import adapters
from bungeni.core.workflow.dot import dot
from bungeni.capi import capi

def write_file(in_folder, file_name, contents):
    f = open(in_folder + file_name, "w")
    # !+UNICODETEXT(AH,2011-05-03) without the utf-8 encoding
    # the write fails for text with accents e.g. portoguese.
    f.write(contents.encode("UTF-8"))
    f.close()


def main(argv):
    output_folder = ""
    if len(argv):
        output_folder = argv[0]
        if not output_folder.endswith("/"):
            output_folder = output_folder + "/"
    
    seen = set()
    for key, ti in capi.iter_type_info():
        wf = ti.workflow 
        if wf and wf not in seen:
            seen.add(wf)
            write_file(output_folder, "%s.dot" % ti.workflow_key, dot(wf))


if __name__ == "__main__":
    main(sys.argv[1:])


