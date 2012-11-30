# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Bungeni Schemas (RNC)

Note RNC is the master format to maintain. All RNG files (that is what is used 
by lxml for validation by lxml) are auto-generated from teh RNC, via a tool 
like:

java -jar trang.jar -I rnc -O rng workflow.rnc generated/workflow.rng

$Id$
"""
log = __import__("logging").getLogger("bungeni.schema")

__all__ = ["validate_file_rng"]


from lxml import etree
from os.path import join, dirname
from bungeni.utils import misc


def load_rng(name):
    # we use the auto-derived RNG version of the RNC workflow schema, 
    # as this is what is directly supported by lxml.etree.
    rng_path = join(dirname(__file__), "generated/%s.rng" % (name))
    return etree.RelaxNG(etree.parse(open(rng_path)))

RNG = {
    "workflow": load_rng("workflow"),
    "descriptor": load_rng("descriptor")
}

def validate_file_rng(name, file_path):
    """Load and validate XML file at file_patah, against named RNG schema."""
    xml_doc = etree.fromstring(misc.read_file(file_path))
    log.info("RNG %r SCHEMA validating file: %s", name, file_path)
    RNG[name].assertValid(xml_doc) # raises etree.DocumentInvalid
    return xml_doc

