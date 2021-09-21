# Vault Enhancement Proposal 4: Stash

## Current Behaviour

_Originally defined in the [design document](/doc/dev/design.md)._

A file is added to the `archive` branch of a vault using the following
command:

    vault archive FILE...

When the sweep phase of Sandman runs, files found in the `archive`
branch are:

* Checked for consistency;
* Have their source file (i.e., outside of the vault) deleted;
* Moved to the `.staged` branch;
* Logged and tracked as staged for archival.

This has the effect of removing the archived file from its original
location, staging it for the archive handler. When the handler runs, it
will be archived and finally completely removed from disk.

## Proposed Behaviour

This work should be done in the `feature/stash` branch.

Note: This VEP interacts with the work done in [VEP002](/doc/dev/vep/002-ViewUX/design.md),
which -- at time of writing -- is currently in review. Care must be
taken to avoid code divergence (e.g., merging from `feature/recover-ux`)
while both VEPs are in play.

Note: The bug outlined in [issue #17](https://github.com/wtsi-hgi/hgi-vault/issues/17),
addressed by [VEP003](https://github.com/wtsi-hgi/hgi-vault/blob/fix/vault-key/doc/dev/vep/003-LongVaultKeys/design.md),
should not interact with this VEP. However, while both VEPs are in
active development, care should be taken to be conscious of potential
conflicts when it comes to merging.

### The Vault

Each vault will have a new branch, named `stash`.

### `vault` CLI

#### `archive --stash`

The `archive` subcommand to the `vault` CLI will take an additional,
optional flag of `--stash` when specifying files to archive. i.e.,:

    vault archive --help
                | --view [CONTEXT] [--absolute]
                | --view-staged [CONTEXT] [--absolute]
                | [--stash] FILE [FILE...]

The effect of providing the `--stash` option is to add the specified
`FILE`s into the `stash` branch, rather than the `archive` branch (the
default and current behaviour).

#### `archive --view`

Files which are annotated for archival can now be in one of two
branches: `archive` and `stash`. The `--view` option to the `archive`
subcommand must therefore be changed to list the contents of both of
these branches simultaneously.

Note: It may be useful to mark stashed files, as opposed to archived
files, differently in the output (e.g., with an asterisk appended, etc.)

#### `untrack` (formerly `remove`)

The `untrack` subcommand must now support the untracking (removal) of
files from the `stash` branch, as well as `keep` and `archive`.

Note: Once staged, as with files marked for archival, stashed files
cannot be untracked.

### Sandman

During the sweep phase of Sandman, if it encounters a file in the
`stash` branch of a vault, it must follow the same process as it would
when encountering a file in the `archive` vault. However, there is one
exception: The source file (i.e., the original file, outside the vault)
must not be deleted, as it normally would be for files transitioning
from `archive` to `.staged`.

Note: Consistency checks are done on staged files, based on the number
of hardlinks. These will no longer be valid, as this could now be either
2 (for stashed files) or 1 (for archived files), with no way of
disambiguating them.
