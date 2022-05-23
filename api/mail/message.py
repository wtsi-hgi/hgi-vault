"""
Copyright (c) 2020, 2022 Genome Research Limited

Authors:
    - Christopher Harrison <ch12@sanger.ac.uk>
    - Guillaume Noell <gn5@sanger.ac.uk>
    - Michael Grace <mg38@sanger.ac.uk>
    - Sendu Bala <sb10@sanger.ac.uk>

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
from abc import ABCMeta, abstractmethod
from dataclasses import asdict, dataclass
from gzip import GzipFile
from pathlib import Path

from core import idm, mail, persistence
from core import typing as T

from . import jinja2


class GZippedFOFN(mail.base.Attachment):
    """ Attachment representing a gzipped FOFN """

    def __init__(self, filename: str, files: T.Collection[T.Path]) -> None:
        self.filename = filename
        self.mime_type = "application/gzip"
        self.data = io.BytesIO()

        # Write gzipped data (\n-delimited paths) to buffer
        with GzipFile(fileobj=self.data, mode="wb") as gzip:
            for path in files:
                gzip.write(bytes(path))
                gzip.write(b"\n")

        # Rewind buffer
        self.data.seek(0)


class _BaseTemplatedMessage(mail.base.Message, metaclass=ABCMeta):
    """ Abstract base mixin class for templated messages """
    subject: T.ClassVar[str]
    template: T.ClassVar[str]

    @abstractmethod
    def _render(self, context: T.Any) -> str:
        """ Render the template with the given context """


class _Jinja2Message(_BaseTemplatedMessage):
    """ Jinja2 templating mixin implementation """

    def _render(self, context: T.Any) -> str:
        return jinja2.render(self.template, context)


_GroupSummariesT = T.Dict[idm.base.Group, persistence.GroupSummary]


@dataclass
class MessageContext:
    stakeholder: idm.base.User
    group_summary: _GroupSummariesT
    n_files: int
    file_list: T.Dict[T.Path, T.Dict[str, T.Any]]
    vault_documentation: str

    tminus: T.Optional[float] = None
    filelist_lustre_path: T.Optional[Path] = None

    @property
    def data(self) -> T.Dict[str, T.Any]:
        def _group_context(
                summaries: _GroupSummariesT) -> T.Dict[str, T.Dict[str, persistence.GroupSummary]]:
            return {
                group.name: asdict(summary)
                for group, summary in summaries.items()
            }

        return {
            "stakeholder": self.stakeholder.name,
            "n_files": self.n_files,
            "filelist_as_attachement": 'no' if self.file_list else 'yes',
            "vault_documentation": self.vault_documentation,
            "summary": _group_context(self.group_summary),
            "filelist": self.file_list,
            "deleted_within": self.tminus
        }


class _Message(_Jinja2Message):
    """
    Base class for all messages, making use of our IdM and using Jinja2
    for templating; implementations just need to define the subject and
    template, at a minimum.
    """

    def __init__(self, context: MessageContext) -> None:
        self.attachments: T.List[mail.base.Attachment] = []
        self.subject = self.subject
        self.body = self._render(context.data)

    def __iadd__(self, attachment: mail.base.Attachment) -> _Message:
        """ Add the attachment to the message """
        self.attachments.append(attachment)
        return self


class _DeletedEmail(_Message):
    """ Notification e-mail for deleted files"""
    subject = "Some of your data has been deleted from /lustre"
    template = Path(__file__).parent / 'templates' / 'deleted.j2'


class _StagedEmail(_Message):
    """ Notification e-mail for staged files"""
    subject = "Some of your data on /lustre has been staged for archival"
    template = Path(__file__).parent / 'templates' / 'staged.j2'


class _WarnedEmail(_Message):
    """ Notification e-mail (warning) for upcoming file deletions"""
    subject = "Some of your data on /lustre is scheduled for deletion"
    template = Path(__file__).parent / 'templates' / 'warned.j2'


class _UrgentEmail(_Message):
    """Notification email for when the file is getting deleted soon
    and hasn't been notified to the user (this shouldn't often happen,
    but just in case)"""
    subject = "URGENT: Lustre File Deletion SOON!"
    template = Path(__file__).parent / 'templates' / 'urgent.j2'


class MessageNamespace(T.SimpleNamespace):
    WarnedEmail = _WarnedEmail
    StagedEmail = _StagedEmail
    DeletedEmail = _DeletedEmail
    UrgentEmail = _UrgentEmail
    Message = _Message
