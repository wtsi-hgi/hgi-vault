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

from __future__ import annotations

import io
import importlib.resources as resource
from abc import ABCMeta, abstractmethod
from dataclasses import asdict
from functools import singledispatchmethod
from gzip import GzipFile

from core import idm, mail, persistence, time, typing as T
from . import jinja2


class GZippedFOFN(mail.base.Attachment):
    """ Attachment representing a gzipped FOFN """
    def __init__(self, filename:str, files:T.Collection[T.Path]) -> None:
        self.filename  = filename
        self.mime_type = "application/gzip"
        self.data      = io.BytesIO()

        # Write gzipped data (\n-delimited paths) to buffer
        with GzipFile(fileobj=self.data, mode="wb") as gzip:
            for path in files:
                gzip.write(bytes(path))
                gzip.write(b"\n")

        # Rewind buffer
        self.data.seek(0)


class _BaseTemplatedMessage(mail.base.Message, metaclass=ABCMeta):
    """ Abstract base mixin class for templated messages """
    _template:T.Classvar[str]

    @abstractmethod
    def _render(self, context:T.Any) -> str:
        """ Render the template with the given context """

class _Jinja2Message(_BaseTemplatedMessage):
    """ Jinja2 templating mixin implementation """
    def _render(self, context:T.Any) -> str:
        return jinja2.render(self._template, context)

class _Message(_Jinja2Message):
    """
    Base class for all messages, making use of our IdM and using Jinja2
    for templating; implementations just need to define the template.
    """
    def __init__(self, *, to:idm.base.User, subject:str, context:T.Any) -> None:
        self.addressees  = []
        self.attachments = []

        self += to
        self.subject = subject
        self.body = self._render(context)

    @singledispatchmethod
    def __iadd__(self, rhs:T.Any) -> _Message:
        raise NotImplementedError

    @__iadd__.register
    def _(self, addressee:idm.base.User):
        """ Add the user's e-mail address to the list of addressees """
        if (address := addressee.email) is not None:
            self.addressees.append(address)
        return self

    @__iadd__.register
    def _(self, attachment:mail.base.Attachment):
        """ Add the attachment to the list of attachments """
        self.attachments.append(attachment)
        return self


_GroupSummariesT = T.Dict[idm.base.Group, persistence.GroupSummary]
_WarnedSummariesT = T.Collection[T.Tuple[T.TimeDelta, _GroupSummariesT]]

class NotificationEMail(_Message):
    """ Notification e-mail """
    _template = resource.read_text("api.mail", "notification.j2")

    @staticmethod
    def Context(stakeholder:idm.base.User, deleted:_GroupSummariesT, staged:_GroupSummariesT, warned:_WarnedSummariesT) -> T.Dict:
        """
        Helper method to create the context that the notification
        template expects

        @param   stakeholder  Stakeholder
        @param   deleted      Deleted group summaries
        @param   staged       Staged group summaries
        @param   warned       Warned group summaries, by T-minus
        @return  Template context
        """
        # Convert group summaries into the expected context form
        def _group_context(summaries:_GroupSummariesT) -> T.Dict:
            return {
                group.name: asdict(summary)
                for group, summary in summaries.items()
            }

        return {
            "stakeholder": stakeholder.name,
            "deleted":     _group_context(deleted),
            "staged":      _group_context(staged),
            "warned": [
                {
                    "tminus":  time.seconds(tminus),
                    "summary": _group_context(summary)
                }
                for tminus, summary in warned
            ]
        }
