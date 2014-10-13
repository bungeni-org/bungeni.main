# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Download feature implementation

$Id$
"""
log = __import__("logging").getLogger("bungeni.feature.download")


from bungeni.feature import feature
from bungeni.feature import interfaces


class Download(feature.Feature):
    """Support downloading as pdf/odt/rss/akomantoso.
    """
    feature_interface = interfaces.IFeatureDownload
    feature_parameters = {
        "allowed_types": dict(type="sst", default=None,
            doc="allowed download types")
    }
    subordinate_interface = None
    
    def validate_parameters(self):
        assert set(self.get_param("allowed_types")).issubset(interfaces.DOWNLOAD_TYPE_KEYS), \
            "Allowed download types: %s. You entered: %s" % (
                ", ".join(interfaces.DOWNLOAD_TYPE_KEYS),
                ", ".join(self.get_param("allowed_types")))
    
    
    # feature class utilities
    
    def get_allowed_types(self):
        """Get a subset of DOWNLOAD_TYPES.
        """
        if len(self.get_param("allowed_types")):
            return [ typ for typ in interfaces.DOWNLOAD_TYPES
                if typ[0] in self.get_param("allowed_types") ]
        else:
            return interfaces.DOWNLOAD_TYPES


