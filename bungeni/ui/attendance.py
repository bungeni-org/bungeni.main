# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Sitting attendance UI

$Id:$
$URL:$
"""

log = __import__("logging").getLogger("bungeni.ui.attendance")

from operator import itemgetter

import zope.event
import zope.lifecycleevent
from zope.interface import Attribute
from zope.security.proxy import removeSecurityProxy
from zope import formlib
from zc.table import column
from zope.app.pagetemplate import ViewPageTemplateFile

from sqlalchemy import sql
from bungeni.core.dc import IDCDescriptiveProperties
from bungeni.alchemist import Session
from bungeni.models.interfaces import IGroupSittingAttendance
from bungeni.models.domain import AttendanceType, GroupSittingAttendance

from bungeni.ui.browser import BungeniBrowserView
from bungeni.ui.i18n import _
from bungeni.ui.table import TableFormatter
from bungeni.ui import forms
from bungeni.ui.utils import url

class AttendanceEditor(BungeniBrowserView, forms.common.BaseForm):
    """Multiple attendance record editor for sittings"""
    
    form_fields = []
    
    render = ViewPageTemplateFile("templates/attendance.pt")
    
    def __init__(self, context,  request):
        super(AttendanceEditor, self).__init__(context, request)

    @property
    def radio_prefix(self):
        return "sitting_attendance_radio"

    @property
    def columns(self):
        listing_columns = [
            column.GetterColumn(title=_("full names"),
            getter = lambda i,f: i.get('attendee')
            )
        ]
        r_counter = 0
        for at_type in self.attendance_types:
            at_column = column.GetterColumn(
                title=at_type.attendance_type,
                getter = lambda i,f,rcounter=r_counter: \
                    "<input type='radio' name='%s' value='%s' %s>"\
                    %(i["records"][rcounter]["name"],
                    i["records"][rcounter]["value"],
                    (i["records"][rcounter]["checked"] 
                        and 'checked=\"true\"') or ""
                    )
            )
            listing_columns.append(at_column)
            r_counter = r_counter + 1
        return listing_columns
    
    
    def makeId(self, value):
        return "".join((self.radio_prefix,
            "".join(str(value).encode('base64').split())
            )
        )

    @property
    def column_titles(self):
        return [attd.attendance_type for attd in self.attendance_types]
        
    @property
    def attendance_types(self):
        session = Session()
        return session.query(AttendanceType).all()

    @property
    def formatted_listing(self):
        formatter = TableFormatter(
            self.context,
            self.request,
            self.listing,
            prefix="attendance",
            visible_column_names = [c.name for c in self.columns],
            columns = self.columns
        )
        formatter.updateBatching()
        return formatter()
    
    @property
    def listing(self):
        list_data = []
        trusted = removeSecurityProxy(self.context)
        current_attendance = [
            attd for attd in trusted.attendance.values()
        ]
        for member in trusted.group.members:
            attd = filter(lambda i:i.member_id==member.user_id,
                current_attendance
            )
            m_data = {}
            m_data["attendee"] = IDCDescriptiveProperties(member).title
            m_data["has_record"] = int(bool(attd))
            m_data["records"] = [
                {"name" : self.makeId(member.user_id),
                "checked" : bool(attd) and (
                    attd[0].attendance_type_id == \
                        at_type.attendance_type_id
                    ),
                "value" : at_type.attendance_type_id
                }
                for at_type in self.attendance_types
            ]
            list_data.append(m_data)
        sorted_list = sorted(list_data,
            key=itemgetter("has_record", "attendee")
        )
        return sorted_list

    def hasListing(self, action):
        return bool(len(self.listing))

    @property
    def action_url(self):
        return ""

    @property
    def action_method(self):
        return "post"
    
    @formlib.form.action(label=_("Save"), condition=hasListing)
    def handle_save(self, action, data):
        self.processAttendance()

    @formlib.form.action(label=_("Cancel"))
    def handle_cancel(self, action, data):
        session = Session()
        next_url = url.absoluteURL(self.__parent__, self.request)
        self.request.response.redirect(next_url)
        # !+SESSION_CLOSE(taras.sterch, july-2011) there is no need to close the 
        # session. Transaction manager will take care of this. Hope it does not 
        # brake anything.
        #session.close()

    def setUpWidgets(self, ignore_request=False):
        actions = self.actions
        self.actions = []
        for action in actions:
            if getattr(action, "condition", None):
                if action.condition(self, self.context):
                    self.actions.append(action) 
            else:
                self.actions.append(action)
        super(AttendanceEditor, self).setUpWidgets(self)


    def getSelected(self):
        selection = [ 
            {"user_id": k[len(self.radio_prefix):].decode("base64"),
             "attendance_type_id": self.request.form.get(k)
            }
            for k in self.request.form.keys() \
            if k.startswith( self.radio_prefix )  \
                and self.request.form.get(k,'') != '']
        return selection   

    def processAttendance(self):
        session = Session()
        trusted = removeSecurityProxy(self.context)
        gs_id = trusted.group_sitting_id
        selected = self.getSelected()
        for selection in selected:
            member_id = selection.get("user_id")
            if not member_id:
                continue
            at_id = selection.get("attendance_type_id")
            if not at_id:
                continue
            member_id = int(member_id)
            at_id = int(at_id)
            #check existing attendance record
            query = session.query(GroupSittingAttendance).filter(
                sql.and_(
                    GroupSittingAttendance.member_id == member_id,
                    GroupSittingAttendance.group_sitting_id == gs_id
                )
            )
            result = query.first()
            if result is not None:
                result.attendance_type_id = at_id
                session.flush()
                zope.event.notify(
                    zope.lifecycleevent.ObjectModifiedEvent(result,
                        zope.lifecycleevent.Attributes(
                            IGroupSittingAttendance, 
                            "attendance_type_id"
                        )
                    )
                )
            else:
                m_attendance = GroupSittingAttendance()
                m_attendance.group_sitting_id = gs_id
                m_attendance.attendance_type_id = at_id
                m_attendance.member_id = member_id
                session.add(m_attendance)
                session.flush()
                zope.event.notify(
                    zope.lifecycleevent.ObjectCreatedEvent(m_attendance)
                )
        self.status = _(u"Updated attendance record")

    def __call__(self):
        self.update()
        return self.render()
