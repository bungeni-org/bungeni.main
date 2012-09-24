# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Sitting attendance UI

$Id$
"""

log = __import__("logging").getLogger("bungeni.ui.attendance")

from operator import itemgetter

import zope.event
import zope.lifecycleevent
from zope.security.proxy import removeSecurityProxy
from zope import formlib
from zc.table import column
from zope.app.pagetemplate import ViewPageTemplateFile

from sqlalchemy import sql
from bungeni.core.dc import IDCDescriptiveProperties
from bungeni.alchemist import Session
from bungeni.models.interfaces import ISittingAttendance
from bungeni.models.domain import SittingAttendance

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
            column.GetterColumn(
                title=_("full names"),
                getter=lambda i,f: i.get("attendee")
            )
        ]
        for rcount, at_type in enumerate(self.attendance_types):
            at_column = column.GetterColumn(
                title=at_type.title,
                getter=lambda i, f: i,
                cell_formatter=lambda g, i, f, rc=rcount: \
                    '<input type="radio" name="%s" value="%s"%s/>' % (
                        i["records"][rc]["name"],
                        i["records"][rc]["value"],
                        i["records"][rc]["checked"] and ' checked="checked"' or ""
                )
            )
            listing_columns.append(at_column)
        return listing_columns
    
    
    def make_id(self, value):
        return "".join(
            (self.radio_prefix, "".join(str(value).encode("base64").split()))
        )

    @property
    def column_titles(self):
        return [ at.title for at in self.attendance_types ]
        
    @property
    def attendance_types(self):
        """ () -> zope.schema.vocabulary.SimpleVocabulary."""
        from bungeni.ui import vocabulary # !+
        return vocabulary.attendance_type
    
    @property
    def formatted_listing(self):
        formatter = TableFormatter(self.context, self.request, self.listing,
            prefix="attendance",
            visible_column_names=[ c.name for c in self.columns ],
            columns=self.columns
        )
        formatter.updateBatching()
        return formatter()
    
    @property
    def listing(self):
        list_data = []
        trusted = removeSecurityProxy(self.context)
        current_attendance = list(trusted.attendance.values())
        for member in trusted.group.members:
            attd = filter(
                lambda i:i.member_id==member.user_id,
                current_attendance
            )
            m_data = {}
            m_data["attendee"] = IDCDescriptiveProperties(member).title
            m_data["has_record"] = int(bool(attd))
            m_data["records"] = [ {
                    "name": self.make_id(member.user_id),
                    "checked": bool(attd) and (
                        attd[0].attendance_type == at_type.value),
                    "value": at_type.value
                } for at_type in self.attendance_types ]
            list_data.append(m_data)
        sorted_list = sorted(list_data,
            key=itemgetter("has_record", "attendee")
        )
        return sorted_list
    
    def has_listing(self, action):
        return bool(len(self.listing))
    
    @property
    def action_url(self):
        return ""

    @property
    def action_method(self):
        return "post"
    
    @formlib.form.action(label=_("Save"), name="save", condition=has_listing)
    def handle_save(self, action, data):
        self.process_attendance()

    @formlib.form.action(label=_("Save and view"), name="save_and_view",
                         condition=has_listing)
    def handle_save_view(self, action, data):
        self.process_attendance()
        next_url = url.absoluteURL(self.__parent__, self.request)
        self.request.response.redirect(next_url + "/attendance")
    
    @formlib.form.action(label=_("Cancel"), name="cancel")
    def handle_cancel(self, action, data):
        next_url = url.absoluteURL(self.__parent__, self.request)
        self.request.response.redirect(next_url)
    
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


    def get_selected(self):
        selected = [
            {
                "user_id": k[len(self.radio_prefix):].decode("base64"),
                "attendance_type": self.request.form.get(k)
            } 
            for k in self.request.form.keys() 
            if k.startswith(self.radio_prefix) and self.request.form.get(k)
        ]
        return selected   
    
    def process_attendance(self):
        session = Session()
        trusted = removeSecurityProxy(self.context)
        gs_id = trusted.sitting_id
        for selection in self.get_selected():
            member_id = selection.get("user_id")
            if not member_id:
                continue
            at = selection.get("attendance_type")
            if not at:
                continue
            member_id = int(member_id)
            # check existing attendance record
            query = session.query(SittingAttendance).filter(
                sql.and_(
                    SittingAttendance.member_id == member_id,
                    SittingAttendance.sitting_id == gs_id
                )
            )
            result = query.first()
            if result is not None:
                result.attendance_type = at
                session.flush()
                zope.event.notify(
                    zope.lifecycleevent.ObjectModifiedEvent(result,
                        zope.lifecycleevent.Attributes(
                            ISittingAttendance, "attendance_type")))
            else:
                m_attendance = SittingAttendance()
                m_attendance.sitting_id = gs_id
                m_attendance.attendance_type = at
                m_attendance.member_id = member_id
                session.add(m_attendance)
                session.flush()
                zope.event.notify(
                    zope.lifecycleevent.ObjectCreatedEvent(m_attendance))
        self.status = _("Updated attendance record")
    
    def __call__(self):
        self.update()
        return self.render()

