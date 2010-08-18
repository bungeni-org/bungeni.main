# encoding: utf-8

log = __import__("logging").getLogger("bungeni.core")

class actions(object):

    @staticmethod
    def create(info, context):
        """Create a report"""
