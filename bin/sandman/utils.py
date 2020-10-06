"""
Copyright (c) 2020 Genome Research Limited

Author: Christopher Harrison <ch12@sanger.ac.uk>

This program is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or (at your
option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
Public License for more details.

You should have received a copy of the GNU General Public License along
with this program. If not, see https://www.gnu.org/licenses/
"""

import dataclasses

from core import typing as T, idm
from api.persistence.models import GroupSummary


def _summary_context(group_summary:GroupSummary) -> T.Dict:
    """ Convert group summaries into a notification context """
    return {
        group: dataclasses.asdict(summary)
        for group, summary in group_summary.items()
    }

def notification_context(stakeholder:idm.base.User, deleted:GroupSummary, staged:GroupSummary, warned) -> T.Dict:
    """
    Create the context in a form expected by the notification template

    @param   stakeholder  Stakeholder
    @param   deleted      Deleted group summaries
    @param   staged       Staged group summaries
    @param   warned       Warned group summaries, by T-minus
    @return  Context
    """
    # TODO This function has just been sketched out for the time being;
    # the warned argument (at the moment) is a list of tuples of
    # int/TimeDelta(?) and GroupSummary. Maybe it doesn't really belong
    # here; it's better in api.mail, but then the GroupSummary model
    # crosses an abstraction boundary... FIXME
    return {
        "stakeholder": stakeholder.name,
        "deleted": _summary_context(deleted),
        "staged": _summary_context(staged),
        "warned": [{"tminus": tminus, "summary": _summary_context(summary)}
                   for tminus, summary in warned]
    }
