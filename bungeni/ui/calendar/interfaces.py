# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Calendar Interfaces

$Id$
"""

import zope.interface
import zope.schema

from bungeni.core.language import get_default_language
from bungeni.ui.i18n import _

class IDhtmlxCalendarSittingsEditForm(zope.interface.Interface):
    ids = zope.schema.TextLine(title=u"ID", description=u"Sitting ID",
        required=False
    )
    short_name = zope.schema.TextLine(title=u"Name of Activity",
        description=u"Name of Activity", required=False
    )
    start_date = zope.schema.Datetime(
        title=_(u"Start date and time of sitting"),
        description=_(u"Choose sitting's start date and time"),
        required=True
    )
    end_date = zope.schema.Datetime(title=_(u"End date and time of sitting"),
        description=_(u"Choose sitting's end date and time"),
        required=True
    )
    venue = zope.schema.Choice(title=_(u"Venue"),
        description=_(u"Venues"),
        source="bungeni.vocabulary.Venues",
        required=True
    )
    language = zope.schema.Choice(title=_(u"Language"),
        description=_(u"Language"),
        vocabulary="language_vocabulary",
        default=get_default_language(),
        required = True
    )
    rec_type = zope.schema.TextLine(title=u"Recurrence Type",
        required=False,
        description=(u"A string that contains the rules for reccurent " 
            u"sittings if any"
        )
    )
    event_length = zope.schema.TextLine(title=u"Event Length",
        description = u"Length of event",
        required=False
    )
    nativeeditor_status = zope.schema.TextLine(title=u"editor status",
        description = u"Editor Status",
        required=False
    )
    activity_type = zope.schema.Choice(title=u"Activity Type",
        description=u"Sitting Activity Type",
        vocabulary="bungeni.vocabulary.SittingActivityTypes",
        required=False
    )
    meeting_type = zope.schema.Choice(title=u"Meeting Type",
        description=u"Sitting Meeting Type",
        vocabulary="bungeni.vocabulary.SittingMeetingTypes",
        required=False
    )
    convocation_type = zope.schema.Choice(title=u"Convocation Type",
        description=u"Convocation Type",
        vocabulary="bungeni.vocabulary.SittingConvocationTypes",
        required=False
    )
