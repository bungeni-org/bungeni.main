# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Report generation and publishing interfaces 

$Id$
"""

from zope.interface import Interface, Attribute
from exceptions import Exception

class IReportGenerator(Interface):
    """Specification for report generation"""
    
    context = Attribute("""Context for which report is being generated""")
    report_template_file = Attribute("""Filesystem path to report template""")
    report_template = Attribute("""Parsed report template document tree""")
    coverage = Attribute("""Period in hours covered by the report""")
    title = Attribute("""Title of the report""")
    language = Attribute("""Language of the Report""")

    def loadConfiguration():
        """Load report configuration from a config file. Sets up attributes."""
        
    def generateReport():
        """Generates text for report"""

    def publishReport(renderer):
        """Publishes text report using a renderer"""

    def persistReport():
        """Persist report to storage"""

class IReportRenderer(Interface):
    """Specification for report renderers"""
    
    target_format = Attribute("""Indentifier for target format for report""")
    template = Attribute("""Path or other specification to rendering template""")
    content = Attribute("""Content to render onto template""")
    
    def render():
        """Render the report content using the specified template"""

class ReportException(Exception):
    """Exception raised during report processing.
    
    Should pass in a useful i18n message in call to show to the user
    """
