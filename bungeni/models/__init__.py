# this is not a namespace package
# encoding: utf-8
"""
__init__.py

Created by Kapil Thangavelu on 2007-11-22.
"""

import orm

from schema import metadata

from domain import User, Minister
from domain import (GroupMembership, Group, Government, Parliament,
    PoliticalParty, Ministry, Committee, CommitteeType, CommitteeTypeStatus
)
from domain import (GroupSitting, GroupSittingType, GroupSittingAttendance,
    AttendanceType
)
from domain import ParliamentSession, PoliticalGroup
from domain import (Question, QuestionVersion, QuestionChange, QuestionType, 
    ResponseType
)
from domain import Motion, MotionVersion, MotionChange
from domain import Bill, BillVersion, BillChange, BillType
from domain import Constituency, Parliament
from domain import Country, Region, Province
from domain import CurrentlyEditingDocument
from domain import MemberOfParliament, MemberElectionType
from domain import TitleType, MemberTitle
from domain import ItemSchedule

from domain import AddressType, GroupAddress, UserAddress, PostalAddressType

from zope.annotation import factory
from zope import component
from roles import SubRoleAnnotations
component.provideAdapter(factory(SubRoleAnnotations))
