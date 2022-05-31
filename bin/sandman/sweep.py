"""
Copyright (c) 2020, 2021, 2022 Genome Research Limited

Authors:
* Christopher Harrison <ch12@sanger.ac.uk>
* Piyush Ahuja <pa11@sanger.ac.uk>
* Pavlos Antoniou <pa10@sanger.ac.uk>
* Michael Grace <mg38@sanger.ac.uk>

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

# IMPORTANT ##########################################
#                                                    #
#  Search for "DELETION WARNING" for sensitive code  #
#                                                    #
######################################################


from contextlib import ExitStack
from functools import singledispatchmethod
from pathlib import Path

import core.file
import core.mail
import core.persistence
from api.config import Executable
from api.logging import Loggable
from api.mail import GZippedFOFN, MessageNamespace, Postman
from api.mail.message import MessageContext
from api.persistence.models import FileCollection, State
from api.vault import Branch, Vault, VaultFile
from bin.common import generate_config
from core import time
from core import typing as T
from core.file import hardlinks, touch
from core.vault import exception as VaultExc

from . import walk

Filter = core.persistence.Filter

config, _ = generate_config(Executable.SANDMAN)


def _can_delete(file: core.file.BaseFile, threshold: T.TimeDelta) -> bool:
    """ Check the file's age meets or exceeds the threshold """
    return file.age >= threshold


def _can_soft_delete(file: walk.File) -> bool:
    return _can_delete(file, config.deletion.threshold)


def _can_permanently_delete(file: walk.File) -> bool:
    return _can_delete(file, config.deletion.limbo)


class Sweeper(Loggable):
    """ Encapsulation of the sweep phase """
    _walker: walk.BaseWalker
    _persistence: core.persistence.base.Persistence
    _weaponised: bool

    def __init__(
        self,
        walker: walk.BaseWalker,
        persistence: core.persistence.base.Persistence,
        weaponised: bool,
        postman: T.Type[core.mail.base.Postman] = Postman
    ) -> None:
        self._walker = walker
        self._persistence = persistence
        self._weaponised = weaponised
        self._postman = postman

        # Run the phase steps
        self.sweep()
        if self.Yes_I_Really_Mean_It_This_Time:
            self.notify()

    @property
    def Yes_I_Really_Mean_It_This_Time(self) -> bool:
        # Solemnisation :P
        return self._weaponised

    def sweep(self) -> None:
        """ Walk the files and pass them off to be handled """
        for vault, file, status in self._walker.files():
            self._handler(status, vault, file)

    def notify(self) -> None:
        """ E-mail stakeholders """
        log = self.log
        postman = self._postman(config.email)
        # maximum number of files listed directly in e-mail body:
        #   (otherwise, list of files is attached to email as fofn.txt.gz)
        max_filelist_in_body = config.email.max_filelist_in_body
        # communicate HGI end-user vault documentation web link in e-mails:
        vault_documentation = config.email.vault_documentation

        # Create and send the e-mail for each stakeholder
        for stakeholder in self._persistence.stakeholders:
            log.debug(f"Creating e-mail for UID {stakeholder.uid}")

            with ExitStack() as stack:
                # For convenience
                def _files(
                        state: T.Type[core.persistence.base.State], **kwargs) -> FileCollection.User:
                    """
                    Filtered file factory for the current stakeholder in
                    this context management stack with the given state
                    """
                    state_args = {"notified": False, **kwargs}
                    criteria = Filter(state=state(
                        **state_args), stakeholder=stakeholder)
                    return stack.enter_context(
                        self._persistence.files(criteria))

                # E-mails are split below across 3 notification types, handled separately:
                #   - E-mail notification for deleted files
                #   - E-mail notification for staged (archived) files
                #   - E-mail notification (warning) for upcoming file deletions

                # Deleted and Staged files that require notification
                attachments = {
                    "deleted": _files(State.Deleted),
                    "staged": _files(State.Staged)
                }

                group_summaries = {
                    "deleted": _files(State.Deleted).accumulator,
                    "staged": _files(State.Staged).accumulator
                }

                file_lists = {
                    # only pass down file path for now,
                    # but other file meta-data, e.g. exact deletion date, could
                    # be added
                    "deleted": {
                        file.path: {"filepath": file.path}
                        for file in _files(State.Deleted)
                    },
                    "staged": {
                        file.path: {"filepath": file.path}
                        for file in _files(State.Staged)
                    }
                }

                n_files = {
                    "deleted": len(file_lists["deleted"]),
                    "staged": len(file_lists["staged"]),
                }

                tminuses: T.Dict[str, int] = {}
                lustre_paths: T.Dict[str, Path] = {}

                _email_constructors: T.Dict[str, T.Type[MessageNamespace.Message]] = {
                    "deleted": MessageNamespace.DeletedEmail,
                    "staged": MessageNamespace.StagedEmail
                }

                # Warned files that require notification
                _warn_type = "urgent"
                for tminus in (config.sandman_run_interval, *config.deletion.warnings):

                    to_warn = _files(State.Warned, tminus=tminus)
                    hours = int(time.seconds(tminus) / 3600)

                    _key = f"delete-{hours}" if _warn_type != "urgent" else _warn_type
                    attachments[_key] = to_warn
                    group_summaries[_key] = to_warn.accumulator
                    file_lists[_key] = {
                        file.path: {"filepath": file.path} for file in to_warn
                    }
                    n_files[_key] = len(
                        file_lists[_key])
                    tminuses[_key] = time.seconds(tminus)
                    lustre_paths[_key] = Path("")  # TODO
                    _email_constructors[_key] = MessageNamespace.WarnedEmail if _warn_type != "urgent" else MessageNamespace.UrgentEmail

                    # first one is urgent email, so now we can set it to "warning"
                    _warn_type = "warning"

                for key, cons in _email_constructors.items():
                    if not attachments[key]:
                        continue

                    context = MessageContext(
                        stakeholder=stakeholder,
                        group_summary=group_summaries[key],
                        n_files=n_files[key],
                        file_list={},
                        vault_documentation=vault_documentation,
                        tminus=tminuses.get(key),
                        filelist_lustre_path=lustre_paths.get(key)
                    )

                    _mail_attachments: T.List[core.mail.base.Attachment] = []
                    if len(attachments[key]) <= max_filelist_in_body:
                        context.file_list = file_lists[key]
                    else:
                        _mail_attachments.append(GZippedFOFN(
                            f"{key}.txt.gz", {file.path for file in attachments[key]}))

                    mail = cons(context)
                    for _attachment in _mail_attachments:
                        mail += _attachment

                    postman.send(mail, stakeholder)
                    log.info(
                        f"Sent e-mail for {key} files to {stakeholder.name} ({stakeholder.email})")

        # TODO? The design states that an overall summary should be
        # logged at the end of the notification step and output to the
        # log stream. The current implementation doesn't allow for that
        # because notifications are grouped by user and multiple users
        # can be stakeholders of the same file (i.e., we can't simply
        # add up the summaries for each user and present them at the
        # end, because that will double count). For the same reason, we
        # don't log the summary for each user, either; it would be
        # confusing. However, is it right to log no summary whatsoever?
        # Given that the details are logged by the sweep handlers, then
        # for now the answer is: "Maybe"... :P

    @singledispatchmethod
    def _handler(self, status, vault: Vault, file: walk.File) -> None:
        """
        Single dispatch handler for files reported by the sweep

        @param  status  Vault status of said file
        @param  vault   The Vault that takes command over the file
        @param  file    The file and its stat information
        """
        raise NotImplementedError(f"Unknown status for {file}: {repr(status)}")

    # File Handler Implementations ###################################

    @_handler.register
    def _(self, status: VaultExc.PhysicalVaultFile, vault, file):
        """
        Handle files that are physically contained within the vault's
        special directories
        """
        log = self.log
        log.debug(
            f"{file.path} is physically contained within the vault in {vault.root}")

        # We only need to check for corruptions (i.e., single hardlink)
        # of files that physically exist in the keep or archive branches
        for branch in Branch.Keep, Branch.Archive, Branch.Limbo:
            bpath = vault.location / branch

            try:
                _ = file.path.relative_to(bpath)
            except ValueError:
                # File is not in the current branch
                continue

            if branch == Branch.Limbo:
                if hardlinks(file.path) > 1:
                    log.warning(
                        f"Corruption detected: Physical vault file {file.path} in limbo has more than one hardlink")

                if _can_permanently_delete(file):
                    log.info(
                        f"Permanently Deleting: {file.path} has passed the hard-deletion threshold")
                    if self.Yes_I_Really_Mean_It_This_Time:
                        try:
                            file.delete()  # DELETION WARNING
                        except PermissionError:
                            log.error(
                                f"Could not delete {file.path}: Permission denied")

            else:
                if hardlinks(file.path) == 1:
                    log.warning(
                        f"Corruption detected: Physical vault file {file.path} does not link to any source")
                    if self.Yes_I_Really_Mean_It_This_Time:
                        try:
                            file.delete()  # DELETION WARNING
                            log.info(
                                f"Corruption corrected: {file.path} deleted")
                        except PermissionError:
                            log.error(
                                f"Could not delete {file.path}: Permission denied")

    ####################################################################

    @_handler.register
    def _(self, status: VaultExc.VaultCorruption, vault, file):
        """
        Handle files that raise a vault corruption

        That is, tracked files that:
        1. Exist in the same/multiple branches simultaneously
        2. Are staged or limboed, but have more than 1 hardlink each
        3. Are in keep or archive, but have only 1 hardlink each

        1. and 2. should never happen during normal operation; while 3.
        can happen, it would be impossible to detect from this direction
        and, instead, is corrected by the physical vault file handler
        (above). As such, as we cannot distinguish amongst these cases,
        all we can realistically do is log it here and move on.
        """
        self.log.error(f"Corruption detected: {status}")

    ####################################################################

    @_handler.register
    def _(self, status: Branch, vault, file):
        """
        Handle files that are tracked by the vault

        We only care about files that exist in the Archive branch;
        everything else can be skipped over. Once the file is added to
        staging, the original source file is hard-deleted
        """
        log = self.log
        log.debug(
            f"{file.path} is in the {status} branch of the vault in {vault.root}")

        if status in [Branch.Stash, Branch.Archive]:
            if file.locked:
                log.info(
                    f"Skipping: {file.path} is marked for archival, but is locked by another process")
                return

            log.info(f"Staging {file.path} for archival")

            if self.Yes_I_Really_Mean_It_This_Time:
                # 1. Move the file to the staging branch
                staged = vault.add(Branch.Staged, file.path)

                # 2. Persist to database
                to_persist = file.to_persistence(key=staged.path)
                self._persistence.persist(
                    to_persist, State.Staged(notified=False))

                log.info(f"{file.path} has been staged for archival")

            if status == Branch.Archive:
                # 3. Delete source
                assert hardlinks(file.path) > 1
                try:
                    file.delete()  # DELETION WARNING
                except PermissionError:
                    log.error(
                        f"Could not hard-delete {file.path}: Permission denied")

    ####################################################################

    @_handler.register
    def _(self, status: None, vault: Vault, file: walk.File):
        """
        Handle files that are not tracked by the vault

        Untracked files that exceed the deletion threshold are
        soft-deleted; otherwise warning notifications are raised if
        their ages exceed warning thresholds
        """
        log = self.log
        log.debug(f"{file.path} is untracked")

        try:
            if not VaultFile(vault, Branch.Limbo, file.path).can_add:
                # Check we'll actually be able to soft-delete the file
                # This only needs to be here, as this is the only time
                # we interact with untracked files automatically
                log.info(
                    f"Skipping: {file.path} has correctable permission issues")
                return
        except core.vault.exception.VaultCorruption:
            # this will be handled when the file is added to the branch
            pass

        if _can_soft_delete(file):
            if file.locked:
                log.info(
                    f"Skipping: {file.path} has passed the soft-deletion threshold, but is locked by another process")
                return

            _warnings = self._persistence.states(
                Filter(
                    state=State.Warned(
                        notified=True,
                        tminus=core.persistence.Anything
                    ),
                    file=file
                )
            )

            if len(_warnings) == 0:
                log.info(
                    f"{file.path} has passed the soft-deletion threshold, but hasn't been warned to anyone. We'll send a warning")
                self._persistence.persist(file.to_persistence(), State.Warned(
                    notified=False, tminus=config.sandman_run_interval))
                return

            log.info(
                f"Deleting: {file.path} has passed the soft-deletion threshold")
            if self.Yes_I_Really_Mean_It_This_Time:
                # 0. Instantiate the persisted file model before it's
                #    deleted so we don't lose its stat information
                to_persist = file.to_persistence()

                # 1. Move file to Limbo and delete source
                limboed = vault.add(Branch.Limbo, file.path)
                touch(limboed.path)
                assert hardlinks(file.path) > 1
                try:
                    file.delete()  # DELETION WARNING
                    log.info(f"Soft-deleted {file.path}")

                except PermissionError:
                    log.error(
                        f"Could not soft-delete {file.path}: Permission denied")
                    return

                log.info(f"{file.path} has been soft-deleted")

                # 2. Persist to database
                self._persistence.persist(
                    to_persist, State.Deleted(notified=False))

        elif self.Yes_I_Really_Mean_It_This_Time:
            # Determine passed checkpoints, if any
            until_delete = config.deletion.threshold - file.age
            checkpoints = [
                t for t in config.deletion.warnings if t > until_delete]

            # Persist warnings for passed checkpoints
            if len(checkpoints) > 0:
                to_persist = file.to_persistence()
                for tminus in checkpoints:
                    self._persistence.persist(
                        to_persist, State.Warned(notified=False, tminus=tminus))
