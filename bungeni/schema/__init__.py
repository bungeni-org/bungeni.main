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

__all__ = ["WORKFLOW_SCHEMA"]


WORKFLOW_SCHEMA = None

#

def set_WORKFLOW_SCHEMA():
    from lxml import etree
    from os.path import join, dirname
    # we use the auto-derived RNG version of the RNC workflow schema, 
    # as this is what is directly supported by lxml.etree.
    global WORKFLOW_SCHEMA
    WORKFLOW_SCHEMA = etree.RelaxNG(
        etree.parse(open(join(dirname(__file__), "generated/workflow.rng"))))
set_WORKFLOW_SCHEMA()

