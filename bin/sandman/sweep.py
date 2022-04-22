"""
Copyright (c) 2020, 2021 Genome Research Limited

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


        ## IMPORTANT ###########################################
        ##                                                    ##
        ##  Search for "DELETION WARNING" for sensitive code  ##
        ##                                                    ##
        ########################################################


from contextlib import ExitStack
from functools import singledispatchmethod

import core.file
import core.persistence
from api.logging import Loggable
from api.mail import Postman, NotificationEMail, GZippedFOFN
from api.persistence.models import FileCollection, State
from api.vault import Vault, Branch, VaultFile
from bin.common import config
from core import time, typing as T
from core.file import hardlinks, touch
from core.vault import exception as VaultExc
from hot import ch12, an12, gn5, pa11
from hot.combinator import agreed
from . import walk

Filter = core.persistence.Filter


# Hot code implementations
_hot = agreed(*(m.can_delete for m in (ch12, an12, gn5, pa11)))

def _can_soft_delete(file:walk.File) -> bool:
    return _hot(file, config.deletion.threshold)

def _can_permanently_delete(file:walk.File) -> bool:
    return _hot(file, config.deletion.limbo)


class Sweeper(Loggable):
    """ Encapsulation of the sweep phase """
    _walker:walk.BaseWalker
    _persistence:core.persistence.base.Persistence
    _weaponised:bool

    def __init__(self, walker:walk.BaseWalker, persistence:core.persistence.base.Persistence, weaponised:bool) -> None:
        self._walker      = walker
        self._persistence = persistence
        self._weaponised  = weaponised

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
        postman = Postman(config.email)

        # Create and send the e-mail for each stakeholder
        for stakeholder in self._persistence.stakeholders:
            log.debug(f"Creating e-mail for UID {stakeholder.uid}")

            with ExitStack() as stack:
                # For convenience
                def _files(state:T.Type[core.persistence.base.State], **kwargs) -> FileCollection.User:
                    """
                    Filtered file factory for the current stakeholder in
                    this context management stack with the given state
                    """
                    state_args = {"notified": False, **kwargs}
                    criteria = Filter(state=state(**state_args), stakeholder=stakeholder)
                    return stack.enter_context(self._persistence.files(criteria))

                # Deleted and Staged files that require notification
                attachments = {
                    "deleted": _files(State.Deleted),
                    "staged":  _files(State.Staged)
                }

                # Convenience aliases for e-mail constructor
                deleted = attachments["deleted"].accumulator
                staged  = attachments["staged"].accumulator
                warned  = []

                # Warned files that require notification
                for tminus in config.deletion.warnings:
                    to_warn = _files(State.Warned, tminus=tminus)

                    hours = int(time.seconds(tminus) / 3600)
                    attachments[f"delete-{hours}"] = to_warn
                    warned.append((tminus, to_warn.accumulator))

                # Construct e-mail and add non-trivial attachments
                non_trivial = False
                mail = NotificationEMail(stakeholder, deleted, staged, warned)
                for filename, files in attachments.items():
                    if len(files) > 0:
                        non_trivial = True
                        mail += GZippedFOFN(f"{filename}.fofn.gz",
                                            [file.path for file in files])
                if non_trivial:
                    postman.send(mail, stakeholder)
                    log.info(f"Sent summary e-mail to {stakeholder.name} ({stakeholder.email})")

                else:
                    log.debug("Skipping: Trivial e-mail")

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
    def _handler(self, status, vault:Vault, file:walk.File) -> None:
        """
        Single dispatch handler for files reported by the sweep

        @param  status  Vault status of said file
        @param  vault   The Vault that takes command over the file
        @param  file    The file and its stat information
        """
        raise NotImplementedError(f"Unknown status for {file}: {repr(status)}")

    ## File Handler Implementations ####################################

    @_handler.register
    def _(self, status:VaultExc.PhysicalVaultFile, vault, file):
        """
        Handle files that are physically contained within the vault's
        special directories
        """
        log = self.log
        log.debug(f"{file.path} is physically contained within the vault in {vault.root}")

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
                    log.warning(f"Corruption detected: Physical vault file {file.path} in limbo has more than one hardlink")

                if _can_permanently_delete(file):
                    log.info(f"Permanently Deleting: {file.path} has passed the hard-deletion threshold")
                    if self.Yes_I_Really_Mean_It_This_Time:
                        try:
                            file.delete()  # DELETION WARNING
                        except PermissionError:
                            log.error(f"Could not delete {file.path}: Permission denied")

            else:
                if hardlinks(file.path) == 1:
                    log.warning(f"Corruption detected: Physical vault file {file.path} does not link to any source")
                    if self.Yes_I_Really_Mean_It_This_Time:
                        try:
                            file.delete()  # DELETION WARNING
                            log.info(f"Corruption corrected: {file.path} deleted")
                        except PermissionError:
                            log.error(f"Could not delete {file.path}: Permission denied")

    ####################################################################

    @_handler.register
    def _(self, status:VaultExc.VaultCorruption, vault, file):
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
    def _(self, status:Branch, vault, file):
        """
        Handle files that are tracked by the vault

        We only care about files that exist in the Archive branch;
        everything else can be skipped over. Once the file is added to
        staging, the original source file is hard-deleted
        """
        log = self.log
        log.debug(f"{file.path} is in the {status} branch of the vault in {vault.root}")

        if status in [Branch.Stash, Branch.Archive]:
            if file.locked:
                log.info(f"Skipping: {file.path} is marked for archival, but is locked by another process")
                return

            log.info(f"Staging {file.path} for archival")

            if self.Yes_I_Really_Mean_It_This_Time:
                # 1. Move the file to the staging branch
                staged = vault.add(Branch.Staged, file.path)

                # 2. Persist to database
                to_persist = file.to_persistence(key=staged.path)
                self._persistence.persist(to_persist, State.Staged(notified=False))
                
                log.info(f"{file.path} has been staged for archival")

            if status == Branch.Archive:
                # 3. Delete source
                assert hardlinks(file.path) > 1
                try:
                    file.delete()  # DELETION WARNING
                except PermissionError:
                    log.error(f"Could not hard-delete {file.path}: Permission denied")

    ####################################################################

    @_handler.register
    def _(self, status:None, vault: Vault, file: walk.File):
        """
        Handle files that are not tracked by the vault

        Untracked files that exceed the deletion threshold are
        soft-deleted; otherwise warning notifications are raised if
        their ages exceed warning thresholds
        """
        log = self.log
        log.debug(f"{file.path} is untracked")

        if not VaultFile(vault, Branch.Limbo, file.path).can_add:
            # Check we'll actually be able to soft-delete the file
            # This only needs to be here, as this is the only time
            # we interact with untracked files automatically
            raise core.file.exception.UnactionableFile(f"{file.path} can't be actioned")

        if _can_soft_delete(file):
            if file.locked:
                log.info(f"Skipping: {file.path} has passed the soft-deletion threshold, but is locked by another process")
                return

            log.info(f"Deleting: {file.path} has passed the soft-deletion threshold")
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
                    log.error(f"Could not soft-delete {file.path}: Permission denied")
                    return

                log.info(f"{file.path} has been soft-deleted")

                # 2. Persist to database
                self._persistence.persist(to_persist, State.Deleted(notified=False))

        elif self.Yes_I_Really_Mean_It_This_Time:
            # Determine passed checkpoints, if any
            until_delete = config.deletion.threshold - file.age
            checkpoints = [t for t in config.deletion.warnings if t > until_delete]

            # Persist warnings for passed checkpoints
            if len(checkpoints) > 0:
                to_persist = file.to_persistence()
                for tminus in checkpoints:
                    self._persistence.persist(to_persist, State.Warned(notified=False, tminus=tminus))
