# Bungeni Parliamentary Information System - http://www.bungeni.org/
# Copyright (C) 2010 - Africa i-Parliaments - http://www.parliaments.info/
# Licensed under GNU GPL v2 - http://www.gnu.org/licenses/gpl-2.0.txt

"""Models init

$Id$
"""
log = __import__("logging").getLogger("bungeni.models")

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
from domain import Question, QuestionType, ResponseType
from domain import Motion 
from domain import Bill, BillType
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
