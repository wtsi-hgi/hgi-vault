**NOTE** This is now largely of historical significance, to establish
the original design. Changes to the design will be documented alongside
here in "Vault enhancement proposal" files, in the `vep` directory.

# Design Document

## Risk Mitigation and Certification

We are proposing a system that can irrecoverably delete data. Given the
high risk this poses:

* This specification **must not** be deviated from. Changes to the
  specification are allowed, but must go through a formal review process
  ([defined later](#change-process)).

* The system **must** be certified by the criteria outlined herein
  before it can be run in production. Changes to the system will require
  recertification.

The system will be written in Python 3.8, or newer. Certification
criteria for the system will be:

* The test suite **must** pass without warnings or errors on the target
  platform.

* Hot code ([defined later](#hot-and-warm-code)) **must** be replicated
  in isolation by at least three different developers.

* The [cyclomatic complexity](https://en.wikipedia.org/wiki/Cyclomatic_complexity)
  of the system **must** be:
  * At most 5 for hot and warm code;&ast;
  * At most 10 and **should** be below 7, elsewhere.&ast;

* The test suite **must** achieve:
  * 100% coverage for hot code;
  * At least 90% coverage for warm code;&ast;
  * And be no less than 80% coverage, elsewhere.&ast;

* The system's code **must** be type annotated and satisfy static
  analysis.

* The system's code **must** conform to the
  [PEP8 style](https://www.python.org/dev/peps/pep-0008).

* External (non-standard) libraries **may** be used, but it is
  discouraged.

* If used, external libraries **must** be pinned to an exact version and
  **should** be used sparingly, with appropriate interfaces defined to
  facilitate [dependency inversion](https://en.wikipedia.org/wiki/Dependency_inversion_principle).

* All development **must** be done in a development branch, which is not
  expected to pass certification; feature sub-branches **should** be
  used.

* All commits **must** follow a standard specification ([defined
  later](#commit-message-template)).

* All merges of the development branch to master **must** be reviewed
  and accepted by at least one, independent, senior developer.

* The master branch **must** always pass certification, per this
  definition.

Note that criteria marked with an asterisk (&ast;), above, are flexible
and subject to review for the sake of pragmatism.

The following tools may be useful to facilitate the above. This is not a
definitive list:

* Code coverage:             https://pypi.org/project/coverage
* Cyclomatic complexity:     https://pypi.org/project/radon
* Linting/PEP8 conformance:  https://pypi.org/project/pylint
* Static type analysis:      https://pypi.org/project/mypy

Preferably, the programmatic analysis should be automated.

## Source Control

* git will be used for source control; `origin` will be hosted by
  GitHub.

* The default branch will be named `develop`.

* Feature branches will branch from `develop` and be named
  `feature/DESC`, where `DESC` is a pithy description.

* Bugs and issues will be entered into the GitHub issue tracker.

* Fix branches will branch from the broken commit and be named
  `fix/ISSUE_ID`, where `ISSUE_ID` is the GitHub issue number.

* Commits will be small and done regularly (see later for a rule of
  thumb).

### Commit Message Template

Commit messages will follow this standard form:

    Short description of the commit

    Added:
    * List of added functionality
    * etc.

    Removed:
    * List of removed functionality, with justification for removal
    * etc.

    Changed:
    * List of changed functionality, with justification for the change
    * etc.

    Fixed:
    * List of fixed functionality, with a brief description of the original problem
    * etc.

Notes:

* Any of the Added, Removed, Changed or Fixed lists can be omitted in a
  commit message, if they are empty.

* Ideally, each list should contain only one or two items, with no more
  than five items across all lists; any more implies the commit it too
  large and should be done more frequently.

* If any item in the Fixed list refers to a GitHub issue, include the
  text `(resolves #ISSUE_ID)`, where `ISSUE_ID` is the GitHub issue
  number.

## Specification

The system will be comprised of two components, which may share common
code:

1. A user-facing CLI.
2. A batch process that actions requests, run periodically. Some actions
   may need to be deferred, for efficiency's sake, which will be acted
   upon asynchronously by means of intermediary state.

The purpose of the system is to mark files to be kept or archived,
action that respectively, and to delete files that have passed a
threshold age. Files will be marked by virtue of being hardlinked into
special "vault" directories, thus utilising the filesystem as an in-band
record of state.

### Change Process

Changes to the specification must be formally reviewed via the following
process:

* All stakeholders must meet to discuss the change.

* The proposer must justify the change in terms of cost vs. benefit and
  its risk assessment.

* This analysis needn't be formal, but changes that impinge on hot code
  ([defined later](#hot-and-warm-code)) will be subject to closer
  scrutiny.

* The change may be iterated upon during the meeting by any stakeholder.

* The (potentially modified) change is approved once all stakeholders
  agree.

* If a change is rejected, it may be resubmitted at a later date.

### Testing Methodology

#### Unit Testing

True-[TDD](https://en.wikipedia.org/wiki/Test-driven_development) is not
necessary and post-implementation testing will suffice, provided tests
are motivated on expected behaviour, rather than fulfilling arbitrary
path coverage. The former _should_ satisfy the latter, without coupling
the tests to the implementation, which should be seen as an antipattern.
Indeed, behavioural testing supersedes the attainment of coverage
thresholds, so leeway may be taken judiciously.

#### Integration Testing

<!-- TODO -->

#### User Acceptance Testing

<!-- TODO -->

### Hot and Warm Code

"Hot code" is defined to be code that immediately leads to irrecoverable
data loss. Any such code must be implemented in replicate by at least
three developers. Each implementation is assumed to follow similar
logic, but must nonetheless be implemented in isolation (before review).
All implementations will be called and only acted upon in the event of
unanimous consensus.

**If unanimity is not established, the process must exit immediately and
cease all further function.**

Different implementations of hot code must conform to the same signature
(argument and return types). While hot code can refer to potentially
mutable state, they must be implemented as pure functions. Such a
constraint cannot be enforced by Python at runtime, nor in its type
annotation system, so care must be taken to ensure this is respected.

**Hot code *MUST NOT* mutate state.**

Hot code must be written under the `hot.USERNAME` submodule (where
`USERNAME` is the username of the developer who originally wrote the
code). The full name and e-mail address of said developer must appear in
said code's comments, per the usual legalese. Changes to hot code must
be done by the original developer. When that is not possible, that code
may be either:

1. Inherited by a new developer, who will therein become its new
   maintainer. The change of owner will be documented in the comments
   and the module will change to reflect the new ownership. No developer
   can be the maintainer of more than one implementation of any specific
   piece of hot code.

2. Or retired, for reimplementation by a new developer. If retiring code
   would reduce the implementation count below three, then the
   reimplementation must first be written and certified to replace it.

Hot code may call other library code defined elsewhere in the project.
Such called code will be termed "warm code" and be subject to higher
scrutiny. To facilitate this, all references to warm code must be
documented in the opening comments of all hot code modules. Automatic
path dependencies may be established as part of the CI pipeline.

An index of all hot and warm code will be actively maintained amongst
the project's documentation.

#### Example

Say the following predicate needs to be implemented:

```py
can_delete: Callable[[Path], bool]
```

This function makes decisions on whether a file can be deleted. This
then may be used in a fashion similar to:

```py
from hot import ch12, fm12, pa11
can_deletes = [ch12.can_delete, fm12.can_delete, pa11.can_delete]

if not all(can_delete(file) for can_delete in can_deletes):
  # Fail immediately
  raise Exception("Consensus not reached!")

# Deletion code
file.unlink()
```

Note that, in this case, it isn't the deletion code itself that is "hot"
-- as this will almost certainly be a single standard library call and
necessarily mutates state -- but rather the code that facilitates or
guards against it.

Any `can_delete` implementation might refer to a library function named
`is_in_vault`, which would therefore be mentioned in the respective
implementation's comments. As well as facilitating review, seeing the
same reference in multiple implementations can serve as a sanity check
(e.g., an implementation that doesn't use this function, where others
do, may be suspect).

### The Vault

* The vault directory will be a single directory named `.vault` in the
  root of a group's directory ([defined later](#vault-location)).

* The vault directory will contain three subdirectories ("branches"):
  `keep`, `archive` and `.staged`. (Note that the `.staged` branch is
  for internal use.)

* Within these respective directories, hardlinks of marked files will
  exist in a structured way. Specifically:

  * The big-endian hexadecimal representation of their inode ID will be
    broken out into 8-bit words (padded, if necessary). All but the
    least significant word will be used to make a hierarchy of
    directories, if they don't already exist. (If the inode ID is less
    than 256, then no hierarchy need be created.)

  * In the lowest child directory, the file will be hardlinked, having a
    filename equal to the least significant word, concatenated
    (delimited with a `-`) with the base64 encoding of the marked file's
    path, relative to the vault's location, at the time of marking.

For example, say a user marks `my_group/path/to/some/file` for archival.
This file has inode ID `123456`, which is `0x1e240`, and a relative path
with respect to the vault location of `path/to/some/file`, which has a
base64 encoding of `cGF0aC90by9zb21lL2ZpbGU=`. Thus, the hardlink, and
intermediary directories, as needed, will be created as
`my_group/.vault/archive/01/e2/40-cGF0aC90by9zb21lL2ZpbGU=`.

This structure is justified by:

1. Encoding the inode ID into the hardlink's path allows for O(1)
   lookups in the vault, by inode ID, rather than expensively walking
   the filesystem.

2. Splitting the inode ID into 8-bit words means, at each level, there
   will never be more that 512 entries (256 hardlinks and 256
   directories) in any directory.

3. Encoding the original filename into the link provides information to
   the batch processes. Clearly the directory structure and naming of
   files could change in the meantime, but corrective procedures can be
   applied ad hoc if such an inconsistency is found.

4. The obfuscation of hardlinks in the vault will raise the bar to end
   users who might be "curious". It won't stop them, but it may be
   enough to deter most attempts at tampering.

Note that hardlinks cannot span physical devices. On a distributed
system, such as Lustre, this means the vault must reside on the same MDS
as the files that are to be marked. Enforcement of this constraint is
outside the scope of this project.

#### Vault Location

The location of the vault will be as a child of the highest directory up
the tree, from a reference point (e.g., the current working directory or
a specific file), that retains the same group ownership as that
reference point (i.e., the root of the homogroupic subtree). For
example:

    /                                   12345  root:root
    /projects                           12346  root:root
    /projects/my_project                12347  abc123:my_project
    /projects/my_project/foo            12348  xyz456:my_project
    /projects/my_project/foo/bar.xyzzy  12349  xyz456:my_project

If the file to be kept is `/projects/my_project/foo/bar.xyzzy`, then the
vault will be located in `/projects/my_project/.vault` and the hardlink
will be `/projects/my_project/.vault/keep/30/3d-Zm9vL2Jhci54eXp6eQ==`.

When created, the vault directory must have the same group ownership as
its parent and have the `setgid` bit set.

### Configuration

All components will share common configuration, read from file, in the
following precedence (highest first):

1. The file at the path in the environment variable `VAULTRC`;
2. `~/.vaultrc` (i.e., in the running user's home directory);
3. `/etc/vaultrc`

If no configuration is found, or is incomplete, then the process will
fail immediately.

The configuration will be [YAML](https://yaml.org)-based, with the
following schema:

```yaml
# Identity Management
# - ldap        Host (host) and port (port) of the LDAP server
# - users       Base DN (dn) and mappings (attributes) for users
# - groups      Base DN (dn) and mappings (attributes) for groups

# NOTE The following assumptions are made:
# * The server uses simple, bind-less authentication over cleartext
# * The search space of the User and Group trees are their respective
#   subtrees, in their entirety
# * The Group records' owners and members contain the fully qualified
#   DNs of users

identity:
  ldap:
    host: ldap.example.com
    port: 389

  users:
    dn: ou=users,dc=example,dc=com
    attributes:
      uid: uidNumber   # POSIX user ID
      name: cn         # Full name
      email: mail      # E-mail address

  groups:
    dn: ou=groups,dc=example,dc=com
    attributes:
      gid: gidNumber   # POSIX group ID
      owners: owner    # Group owner(s)
      members: member  # Group member(s)

# Sandman Persistence
# - postgres    Host (host) and port (port) of PostgreSQL server
# - database    Database name
# - user        Username
# - password    Password

persistence:
  postgres:
    host: postgres.example.com
    port: 5432

  database: sandman
  user: a_db_user
  password: abc123

# E-Mail Configuration
# - smtp        Host (host), port (port) and whether to use a secure
#               connection (tls) with the SMTP server
# - sender      E-mail address of the sender

email:
  smtp:
    host: mail.example.com
    port: 25
    tls: No

  sender: vault@example.com

# Deletion Control
# - threshold   Age (in days) at which a file can be deleted
# - warnings    List of warning times (in hours before the deletion age)
#               at which a file's owner and group owner(s) should be
#               notified. Note that no warning should exceed the
#               equivalent of 90 days (2160 hours).

# NOTE These timings are relative to the fidelity in which the batch
# process is run. For example, if it's only run once per week and a
# warning time of one hour is specified, it's very likely that this
# warning will never be triggered.

deletion:
  threshold: 90
  warnings:
  - 240  # 10 days' notice
  - 72   # 3 days' notice
  - 24   # 24 hours' notice

# Archival/Downstream Control
# - threshold   Minimum number of staged files to accumulate before
#               draining the queue
# - handler     Path to archiver/downstream handler executable

# NOTE The consumer of the queue is intended to perform the archival,
# however it is not limited to this purpose.

archive:
  threshold: 1000
  handler: /path/to/executable
```

Note that this schema is subject to change, during design and
implementation.

#### File Age

The age of a file is defined to be the duration from the file's `mtime`
to present. We use modification time, rather than change time, as it's a
better indicator of usage. (Unfortunately, access time is not reliably
available to us on all filesystems.)

### The User-Facing CLI

The user-facing CLI will have the following interface:

    vault ACTION [OPTIONS]

Where the CLI's first argument is an action of either `keep`, `archive`
or `remove`. The usual `--help` option will be available, both to the
base command and all the actions, which will show the respective usage
instructions.

#### The `keep` and `archive` Actions

    vault keep --view|FILE...
    vault archive --view|FILE...

The `keep` and `archive` actions take two forms, which perform the same
function on the respective branch of the appropriate vaults:

1. The `--view` option will list the contents of the respective branch
   of the vault relative to the current working directory ([see
   earlier](#vault-location)).

2. When given a list of (at least one and no more than ten) paths to
   files, either relative or absolute, these will be hardlinked into the
   respective branch of the vault relative to each file ([see
   earlier](#vault-location)).

   Note that the files provided must be regular files (rather than
   directories or symlinks, etc.); non-regular files should be skipped
   over and logged as such to the user. Moreover, as the files provided
   as arguments may be arbitrary, it cannot be assumed that they belong
   in the same vault.

   The list of files is restricted to, at most, ten (per invocation) to
   limit "abuse"; i.e., to nudge users to be mindful of what they
   annotate, rather than using arbitrary globs.

Specifically, the hardlinking function should do the following for each
regular file provided as an argument:

* If said file already exists in the vault (by virtue of matching inode
  IDs):

  * Check the directory structure/file name hasn't changed in the
    meantime:

    * If it has:
      * Correct the hardlinked name in the vault.
      * Log the change to the user.

  * Check in which branch the hardlink exists in the vault:

    * If it matches the action (`keep` or `archive`):
      * Log to the user that no further change is necessary.

    * If it differs:
      * Move the hardlink to the opposite branch, maintaining the
        necessary structure.
      * Log to the user that the file's status has changed,
        respectively. If the hardlink is moved to the archive branch,
        log that staging will happen later and will require the file to
        be unlocked for writing.

* If it doesn't exist in the vault:
  * Hardlink the file into the appropriate branch:
    * Create the hierarchy needed to address the inode ID; specifically
      its big-endian hexadecimal representation, zero-padded to a
      multiple of 8 and broken into 8-bit words, taking all but the
      least signficiant word to enumerate the tree.
    * Hardlink the file into the leaf of this tree, with its name given
      by the least significant word (from the previous step) and the
      base64 encoding of the file's path relative to the vault location,
      concatenated with a `-`.

  * Log to the user that said file has been actioned. If the file was
    added to the archive branch, log that staging will happen later and
    will require the file to be unlocked for writing.

#### The `remove` Action

    vault remove FILE...

The `remove` action will remove the given files from either the `keep`
or `archive` branch of the vault respective to said file ([see
earlier](#vault-location)). Again, it should not be assumed that files
provided as arguments will be removed from the same vault.

For each file:

* Check the ownership of the file:

  * If the file is owned by the current user or the current user is one
    of the group's owners (defined by the group's LDAP `owner` DN):

    * If the file already exists in the vault (by virtue of matching
      inode IDs), in either the `keep` or `archive` branch:
      * Delete the vault hardlink.
      * Log to the user that the file is no longer marked for the
        appropriate action.

    * If it is not in the vault:
      * Log to the user that the file is not marked.

  * If the file is not owned by the current user or the current user is
    not a group owner:
    * Log a permission denied error.

#### Permissions

All files within HGI managed project and team directories _should_ have
identical user and group POSIX permissions. This component will need to
do some additional management on top of that provided by the filesystem,
as described earlier. For example, the group permissions will allow the
group owner to make changes -- provided they are also a group member --
but this component will need to restrict operations from any other
member of that group who isn't also authorised to perform said action.

Note that this additional layer of management is trivially
circumventable, by performing the underlying filesystem operations
manually. This is an accepted trade-off, which may nonetheless be
mitigable with suitable `sudo`er rules.

The following conditions should be checked upfront for each file and, if
not satisfied, that action should fail for that file, logged
appropriately:

1. Check that the permissions of the file are at least `ug+rw`;
2. Check that the user and group permissions of the file are equal;
3. Check that the file's parent directory permissions are at least
   `ug+wx`.

(Note that the first condition is only technically required if the
kernel parameter `fs.protected_hardlinks = 1`. We fallback to the lowest
common denominator for simplicity's sake.)

#### Auditing and Logging

All above actions will be logged to the user, as described. In addition,
these logs will be appended to a `.audit` file that exists in the root
of the respective vault. The persisted log messages will be amended with
the username of whoever invoked the action.

### The Batch Process

The batch process is separated into two phases -- "sweep" and "drain" --
and is intended to be run periodically (e.g., from a `cron` job).
Because the draining phase is designed to facilitate the archival -- or
some other long-running process -- the two phases must run sequentially
to avoid race conditions.

For example, the sweep may run across several vaults and stage files for
archiving. The archive itself may take multiple days to complete,
whereas another sweep could be due to run again in the meantime. In the
proposed set up, this becomes possible and any additional archive events
can be added, by subsequent sweeps, to a backlog.

The batch process will have the following interface:

    sandman [--dry-run] [--force-drain] [--stats=FILE] DIR...

It must be called with at least one `DIR`, representing a path to a
directory (either relative or absolute) that is covered by a vault. It
may optionally be specified with a `FILE` representing the file listings
and `stat`s of the volume containing each `DIR` and its contents, per
the output generated by [`mpistat`](https://github.com/wtsi-hgi/mpistat);
this will be used to guide the sweep, rather than walking the filesystem.

An optional `--dry-run` argument may be provided, which will cause the
process to log what it would do, without affecting the filesystem. In
the following outline of the process, such actions are marked with an
asterisk (&ast;).

#### Sweep Phase

For each `DIR` provided as an argument, the sweep phase consists of the
following, in the given order:

* Establish that `DIR` is covered by a vault (i.e., there exists a vault
  in `DIR`, or in a direct ancestor to `DIR`).
  * If `DIR` is not covered by a vault, then log an error and skip this
    `DIR`.
  * If `DIR` is a vault itself, then log an error and skip this `DIR`.

* Walk the contents of `DIR`, either directly via the filesystem
  interface, or using the `stat` listings given by `FILE`, if provided.

Note that, for efficiency's sake, the walking of every provided `DIR` is
preferred, rather than walking each `DIR` separately.

Then, for each regular file in the walk:

* If it is physically contained within the `keep` or `archive` branch of
  the vault:

  * Check that the external file hasn't been deleted by the user,
    detected by a decrease in hardlink count. If it has:

    * Delete the orphaned vault file.&ast;
    * Log that the corruption has been corrected.

    ⚠️ Note that this is an important training point that users *must* be
    aware of and understand, otherwise they will lose data.

    Note that the detection mechanism will fail if other hardlinks
    exist; this is considered an acceptable trade-off.

* If it is contained within the respective vault:

  * Check the vault file for consistency (i.e., if the external file has
    been renamed or moved) and update it appropriately&ast; and log, if
    necessary.

  * Check which branch the file is in:

    * The `keep` and `.staged` branch:
      * Do nothing: If the file is marked for retention, then nothing
        needs to happen; if the file is staged for archival, then it is
        the responsibility of the downstream process invoked in the
        draining phase.

    * The `archive` branch:
      * Try to acquire a write lock on the file.
        * If this fails, then the file is currently being written to and
          should not yet be archived. Skip the rest of this process and
          move on to the next file, logging appropriately.
      * Delete the source file (i.e., that which exists outside the
        vault).&ast;
      * Move the vaulted file, recreating its associated hierarchy as
        needed, into the `.staged` branch.&ast;
      * Log that the file has been staged for archival.
      * Amend the list of files staged for archival for the file and
        vault owner.

* If it is not contained within the respective vault:

  * Take the file's age ([defined earlier](#file-age)) against the
    deletion threshold (in days):

    * If it has exceeded the threshold:
      * Try to acquire a write lock on the file.
        * If this fails, then the file is currently being written to and
          should not yet be deleted (presumably the `mtime` has yet to
          be updated). Skip the rest of this process and move on to the
          next file, logging appropriately.
      * Log that the deletion is about to happen.
      * Delete the file.&ast;
      * Log that the deletion has completed.
      * Amend the list of deleted files for the file and vault owner.

    * If it has yet to exceed the threshold, check the file's age
      against each of the configured warning checkpoints (in hours until
      deletion). For each checkpoint that is passed, amend the
      appropriate checkpoint list of files scheduled for deletion for
      the file and vault owner.

  ⚠️ Note that files that spontaneously appear in a directory -- e.g.,
  from a timestamp-preserving copy, etc. -- may be deleted without
  warning, if the appropriate conditions are met. This is an important
  training point that users *must* be aware of and understand, otherwise
  they will lose data.

Finally:

* For each user, collate the lists of files scheduled for deletion,
  files deleted and files staged for archival and use them to render and
  send an appropriate e-mail ([defined later](#regarding-e-mails)).&ast;

* Collate the lists of files scheduled for deletion, files deleted and
  files staged for archive for all users to log a summary.

* Invoke the [drain phase](#drain-phase).&ast;

For clarity's sake, to facilitate the e-mailing and summary, the sweep
will need to maintain the equivalent of the following distinct lists for
each user and group owner that's relevant:

* *N* lists of files that have passed the appropriate deletion warning
  checkpoint (where *N* is the number of configured checkpoints in
  `deletion.warnings`);
* A list of files that were actually deleted;
* A list of files that have been staged for archival.

These lists will need to be persisted to disk, rather than kept in
memory, such that:

* Importantly, the list of files that have been staged for archival will
  be used in the draining phase (the way in which they're stored must
  therefore take this into account).
* When files have exceeded a warning checkpoint, they will only be
  included in that e-mail once (e.g., if the sweep is run daily and
  there are checkpoints at 72 and 24 hours, this will ensure the 72 hour
  warning won't also be sent during the 48 and 24 hour sweeps).
* In the event of failure, actions that were performed before the
  failure can still be reported on retrospectively.

Note that the intended deletion time will also need to be stored, in
case the `mtime` of a file changes. That is, if this happens, then it's
possible that a previous warning will become re-eligible. For example:

* A file's age exceeds the 72 hour warning checkpoint and an e-mail is
  sent.
* The user updates the file, which changes its `mtime`, no longer making
  it eligible for automatic deletion.
* Eventually, the 72 hour warning relative to the new `mtime` is again
  exceeded; another e-mail is expected, despite a 72 hour warning being
  previously sent.

Note that when files are completely unlinked, their inodes are recycled
by the operating system. As such, they should not be used as unique keys
in any persistence model, unless they are respectfully recycled.

##### Regarding E-Mails

The batch process must not send an e-mail for each file that meets the
criteria for e-mailing. Instead, it should build up the contents of the
e-mail for each user and send them once it's completed its sweep, such
that each relevant user gets exactly one e-mail each.

The format of the e-mail should not be an intractable list of files for
the user to wade through. Rather it should be summarised into a
convenient form, with full listings provided as attachments. The
template for e-mails should be:

```jinja2
Dear {{ user.name }}

The following directories contain data that are scheduled for deletion.
Full listings can be found in the attachments. You MUST act now to
prevent these files from being deleted!

{% for warning in deletion.warnings | reverse %}
Your files will be IRRECOVERABLY DELETED from the following directories
within {{ warning }} hours:

{% for file in to_delete if file.age >= warning %}
* {{ file | group_by(file.group) | common_prefix }}: {{ file | group_by(file.group) | count }} files
{% else %}
* None
{% endfor %}
{% endfor %}

Space has been recovered from the following directories:

{% for file in deleted %}
* {{ file | group_by(file.group) | common_prefix }}: {{ file | group_by(file.group) | size | sum }} MiB
{% else %}
* None
{% endfor %}

The following vaults contain your data that is staged for archival:

{% for vault in staged %}
* {{ vault.root }}: {{ vault.files | branch("staged") | count }} files
{% else %}
* None
{% endfor %}

These will be acted upon shortly.
```

Note that the above templating tags should be considered pseudocode, to
describe the intent, rather than the expected underlying structure.
Where directories are mentioned -- for the deletion warnings and actual
deletions -- these should be aggregated by Unix group and then
summarised to their common directory prefix. For example:

    /path/to/foo/file1  user1:group1
    /path/to/foo/file2  user1:group1
    /path/to/bar/file3  user1:group2

...would be aggregated and summarised as:

    /path/to/foo: 2 files
    /path/to/bar: 1 file

Each e-mail will have the following attachments, if they are non-empty:

* `delete-WARNING.fofn.gz`, where `WARNING` is the hours' warning
  checkpoint, containing the list of files due for deletion within that
  time (e.g., `delete-24.fofn.gz` for files to be deleted within 24
  hours, etc.). There should be as many of these files as there are
  configured deletion warning checkpoints.

  Note that, necessarily, the later checkpoint files will be supersets
  of the earlier ones (e.g., everything due to be deleted within 24
  hours is also due to be deleted within 72 hours).

* `deleted.fofn.gz` containing the list of files that were deleted in
  this sweep.

* `staged.fofn.gz` containing the list of files that have been staged
  for archival in this sweep.

An example e-mail may look like:

> Dear Vault User
>
> The following directories contain data that are scheduled for
> deletion. Full listings can be found in the attachments. You MUST act
> now to prevent these files from being deleted!
>
> Your files will be IRRECOVERABLY DELETED from the following
> directories within 24 hours:
>
> * /path/to/my/project: 10 files
> * /path/to/another/project: 50 files
>
> Your files will be IRRECOVERABLY DELETED from the following
> directories within 72 hours:
>
> * /path/to/my/project: 85 files
> * /path/to/another/project: 52 files
> * /path/to/yet/another/project: 4 files
>
> Your files will be IRRECOVERABLY DELETED from the following
> directories within 240 hours:
>
> * /path/to/my/project: 1252 files
> * /path/to/another/project: 55 files
> * /path/to/yet/another/project: 10203 files
>
> Space has been recovered from the following directories:
>
> * /path/to/really/big/project: 12345 MiB
>
> The following vaults contain your data that is staged for archival:
>
> * None
>
> These will be acted upon shortly.
>
> ---
>
> Attachments: `delete-24.fofn.gz` `delete-72.fofn.gz`
> `delete-240.fofn.gz` `deleted.fofn.gz`

##### Intervault Operations

Our base assumption is that the homogroupic trees, which define where
vaults are located, are mutually exclusive and tightly silo data. That
is, files should not be moved between silos without their ownership
changing, which may or may not happen automatically or immediately. This
could result in ownership contention: one inode, with two files that
reside under different groups; an inode can only have one group owner,
so the complementary group would lose access. This cannot be detected,
so it is considered beyond the scope of this project to track files that
are moved between, or out of vaulted locations, on the same physical
device.

A minor exception to this is when files are moved across devices to
silos under the same group. In this case, the original hard link would
be removed (leaving an orphaned vault hardlink) and be reassigned on the
target volume, with no respective vault annotation. The design of the
sweeper is such that this could lead to irrecoverable data loss: an
orphaned source vault file will be cleaned automatically and files
spontaneously detected in the target vault that meet the deletion
criteria will be deleted without warning.

⚠️ Note that this is an important training point that users *must* be
aware of and understand, otherwise they will lose data.

#### Drain Phase

The only argument that is of interest to the drain phase is
`--force-drain`, which will drain the queue of staged files regardless
of it reaching its configured threshold. Note that if `--dry-run` is
specified, then the drain phase will not run at all.

The drain phase consists of the following:

* Check the downstream handler is ready ([defined
  later](#downstream-handler)).
  * If not, log appropriately and exit.

* Check the size of the archival queue exceeds the threshold, or
  `--force-drain` is specified.
  * If not, log appropriately and exit.

* Pull the list of staged files that have yet to be acted upon by the
  downstream handler. Stream these, `\0`-delimited, into the standard
  input of the downstream handler and marked them as acted upon.

##### Downstream Handler

The downstream handler will be an executable that provides the following
interface:

    /path/to/executable [READY_CHALLENGE]

The `READY_CHALLENGE`, if provided, will consist of the string `ready`
followed by an integer representing the number of bytes required to
satisfy the archive. The handler will exit with a zero exit code if it
is able to consume the queue; otherwise it will exit with 1, if the
handler is busy, or 2 if the archive location lacks capacity.

If no arguments are provided, then the handler will read `\0`-delimited
filenames from standard input. These will be the files to archive and
delete.

For example, something like the following Bash script might suffice as a
simple handler, which omits capacity checking:

```bash
#!/usr/bin/env bash

exec 123>.lock
flock -nx 123
locked=$?

case $1 in
  ready)  exit ${locked};;
  *)      (( locked )) && exit 1;;
esac

xargs -0 tar czf "/archive/$(date +%F).tar.gz" --remove-files --
```

This toy handler uses `flock` to provide filesystem-based locking, to
facilitate the `ready` interface (described above), otherwise it slurps
in standard input (the incoming list of filenames) and sends it to `tar`
to create an archive file. Clearly this is not production ready (e.g.,
it is not defensive against failure), but illustrates how a downstream
handler should operate.

Note that the stream of filenames provided from the drain phase will
be the vault files, with their obfuscated names. It is up to the
downstream handler to decode these, if necessary.

Note that, it is the downstream handler's responsibility to delete
staged files from vaults, once they are dealt with. Failing to delete
staged files will cause the vault to increase in size in perpetuity.

Note that the two-step process might seem redundant, but exists to
provide an out-of-band method for checking the availability of the
downstream handler, without any expensive lookups from the staging
queue.

#### Auditing and Logging

The batch process will be logged to the user, as described. In addition,
these logs will be appended to a `.audit` file that exists in the root
of the respective vault. The persisted log messages will be amended with
the username of whoever invoked the batch process.
