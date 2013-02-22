# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Schemas (RNC)

Note RNC is the master format to maintain. All RNG files (that is what is used 
by lxml for validation by lxml) are auto-generated from the RNC, via a tool 
like:

java -jar trang.jar -I rnc -O rng workflow.rnc generated/workflow.rng

$Id$
"""
log = __import__("logging").getLogger("bungeni.schema")

__all__ = [
    "validate_file_rng",
    "qualified_permission_actions",
    "qualified_permission_action",
    "qualified_pid",
    "qualified_roles",
]


from lxml import etree
from os.path import join, dirname
from bungeni.utils import misc


# validation against RNG schemas

def _load_rng(name):
    # we use the auto-derived RNG version of the RNC workflow schema, 
    # as this is what is directly supported by lxml.etree.
    rng_path = join(dirname(__file__), "generated/%s.rng" % (name))
    return etree.RelaxNG(etree.parse(open(rng_path)))

RNG = {
    "workflow": _load_rng("workflow"),
    "descriptor": _load_rng("descriptor"),
    "roles": _load_rng("roles"),
    "workspace": _load_rng("workspace"),
    "notifications": _load_rng("notifications")
}

def validate_file_rng(name, file_path):
    """Load and validate XML file at file_patah, against named RNG schema."""
    xml_doc = etree.fromstring(misc.read_file(file_path))
    log.info("RNG %r SCHEMA validating file: %s", name, file_path)
    RNG[name].assertValid(xml_doc) # raises etree.DocumentInvalid
    return xml_doc


# parsing permissions

"""
ptk, permission_type_key:
    the type_key str to use to qualify a permission action
pa, permission_action:
    a capitalized verb indicating an action e.g. "Add", "Edit", "View".
rpa, relative_permission_action:
    a str indicating a permission action on a specified or implied type
    i.e. may be of the forms ".{Action}" or "{type_key}.{Action}"
qpa, qualified_permission_action:
    a str indicating a permission action on a type 
    i.e. is of the form "type_key.Action"
"""

def qualified_permission_actions(ptk, rpas):
    """(ptk:str, rpas:[str]) -> [(ptk, pa)]
    """
    return [ qualified_permission_action(ptk, pa) for pa in rpas ]

def qualified_permission_action(ptk, pa):
    """str -> (ptk, pa)
    """
    # !+do not allow a preceeding "bungeni."?
    if pa.startswith("bungeni."):
        pa = pa[len("bungeni."):]
    qpa = pa.split(".", 1)
    assert len(qpa) == 2, \
        "No dot in workflow %r permission action %r" % (ptk, pa)
    return (qpa[0] or ptk, qpa[1])

def qualified_pid(ptk, pa):
    return "bungeni.%s.%s" % qualified_permission_action(ptk, pa)


def qualified_roles(roles):
    """space-separated-str -> [role_id]
    Parse space separated string into a list of qualified role ids where 
    each role word-str may be: "Role" or ".Role" or "bungeni.Role"
    """
    qrs = []
    for r in roles.split():
        if r.startswith("bungeni."):
            qrs.append(r)
        elif r.startswith("."):
            qrs.append("bungeni%s" % (r))
        else:
            qrs.append("bungeni.%s" % (r))
    # !+alchemist.model.validated_set
    # !+alchemist.model.norm_sorted
    return sorted(qrs)

