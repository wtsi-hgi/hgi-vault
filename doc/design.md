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

* The state for the test suite **must** satisfy the Cartesian product of
  all options.

* The test suite **must** pass without warnings or errors on the target
  platform.

* Hot code ([defined later](#hot-and-warm-code)) **must** be replicated
  in isolation by at least three different developers.

* The [cyclomatic complexity](https://en.wikipedia.org/wiki/Cyclomatic_complexity)
  of the system **must** be:
  * At most 5 for hot and warm code;
  * At most 10 and **should** be below 7, elsewhere.

* The test suite **must** achieve:
  * 100% coverage for hot code;
  * At least 90% coverage for warm code;
  * And be no less than 80% coverage, elsewhere.

* The system's code **must** be fully type annotated and satisfy static
  analysis.

* The system's code **must** conform to the
  [PEP8 style](https://www.python.org/dev/peps/pep-0008).

* External (non-standard) libraries **may** be used, but it is
  discouraged.

* If used, external libraries **must** be pinned to an exact version and
  **should** be used sparingly.

* All development **must** be done in a development branch, which is not
  expected to pass certification; feature sub-branches **should** be
  used.

* All commits **must** follow a standard specification ([defined
  later](#commit-message-template)).

* All merges of the development branch to master **must** be reviewed
  and accepted by at least one, independent, senior developer.

* The master branch **must** always pass certification, per this
  definition.

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

* Ideally, each lists should contain only one or two items, with no more
  than five items across all lists; any more implies the commit it too
  large and should be done more frequently.

* If any item in the Fixed list refers to a GitHub issue, include the
  text `(resolves #ISSUE_ID)`, where `ISSUE_ID` is the GitHub issue
  number.

## Specification

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

### Test Driven Development

Test cases for any new functionality must be written upfront. Tests must
cover the Cartesian product of all options and, where external state is
required, this must be specified upfront and cover all expected (per
design) eventualities. The test suite may be amended and altered
afterwards to conform to unexpected implementation details required for
certification.

The Cartesian product of options has the potential of making the test
space very large. To therefore avoid intractability, options ought to be
constrained in both quantity and type. This will have the consequential
benefit of reducing cyclomatic complexity.

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
implementations' comments. As well as facilitating review, seeing the
same reference in multiple implementations can serve as a sanity check
(e.g., an implementation that doesn't use this function, where others
do, may be suspect).

### Overview

The system will be comprised of three components, which may share common
code:

1. A user-facing CLI.
2. A batch process that actions requests, run periodically. Some actions
   may need to be deferred, for efficiency's sake, which will be
   published to a message queue.
3. A consumer of that message queue to action deferred events. (Note
   that this maybe implemented as a mode of the batch process.)

The purpose of the system is to mark files to be kept or archived,
action that respectively, and to delete files that have passed a
threshold age. Files will be marked by virtue of being hardlinked into
special "vault" directories, thus utilising the filesystem as an in-band
record of state.

#### The Vault

* The vault directory will be a single directory named `.vault` in the
  root of a group's directory ([defined later](#vault-location)).

* The vault directory will contain two subdirectories ("branches"):
  `keep` and `archive`.

* Within these respective directories, hardlinks of marked files will
  exist in a structured way. Specifically:

  * The big-endian hexidecimal representation of their inode ID will be
    broken out into 8-bit words (padded, if necessary). All but the
    least significant word will be used to make a heirarchy of
    directories, if they don't already exist. (If the inode ID is less
    than 256, then no heirarchy need be created.)

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
   directories).

3. Encoding the original filename into the link provides information to
   the sweep when archiving data. Clearly the directory structure and
   naming of files could change in the meantime, but corrective
   procedures can be applied ad hoc if such an inconsistency is found.

4. The obfuscation of hardlinks in the vault will raise the bar to end
   users who might be curious. It won't stop them, but it may be enough
   to deter most attempts at tampering.

Note that hardlinks cannot span physical devices. On a distributed
system, such as Lustre, this means the vault must reside on the same MDS
as the files that are to be marked. Enforcement of this constraint is
outside the scope of this project.

##### Vault Location

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

#### Configuration

All components will share common configuration, read from file, in the
following precedence (highest first):

1. The file at the path in the environment variable `VAULTRC`;
2. `~/.vaultrc` (i.e., in the running user's home directory);
3. `/etc/vaultrc`

If no configuration is found, or is incomplete, then the process with
fail immediately.

The configuration will be [YAML](https://yaml.org)-based, with the
following schema:

```yaml
# Identity Management
# - ldap       Host (host) and port (port) of the LDAP server
# - users      Base DN (dn) and search attribute (attr) for users
# - groups     Base DN (dn) and search attribute (attr) for groups

# NOTE Group LDAP records are assumed to have owner and member
# attributes, containing the DNs of users.

identity:
  ldap:
    host: ldap.example.com
    port: 389

  users:
    dn: ou=users,dc=example,dc=com
    attr: uid

  groups:
    dn: ou=groups,dc=example,dc=com
    attr: cn

# E-Mail Configuration
# - smtp       Host (host) and port (port) of the SMTP server
# - sender     E-mail address of the sender

email:
  smtp:
    host: mail.example.com
    port: 25

  sender: vault@example.com

# Deletion Control
# - threshold  Age (in days) at which a file can be deleted
# - warnings   List of warning times (in hours before the deletion age)
#              at which a file's owner and group owner should be
#              notified

# NOTE These timings are relative to the fidelity in which the batch
# process is run. For example, if it's only run once per week and a
# warning time of one hour is specified, it's very likely that this
# warning will never be triggered.

deletion:
  threshold: 90
  warnings:
  - 700  # 10 days' notice
  - 72   # 3 days' notice
  - 24   # 24 hours' notice

# Archival/Downstream Control
# - amqp       Host (host) and port (port) of the AMQP server
# - exchange   Exchange to which to publish archival events
# - threshold  Minimum number of events to accumulate before
#              draining the queue

# NOTE The consumer of the message queue is intended to perform the
# archival, and a consumer is provided for this end, however it is not
# limited to this purpose.

archive:
  amqp:
    host: amqp.example.com
    port: 5672

  exchange: vault
  threshold: 1000
```

Note that this schema is subject to change, during design and
implementation.

##### File Age

The age of a file is defined to be the duration from the file's `mtime`
to present. We use modification time, rather than change time, as it's a
better indicator of usage. (Unfortunately, access time is not reliably
available to us on all filesystems.)

#### The User-Facing CLI

The user-facing CLI will have the following interface:

    vault ACTION [OPTIONS]

Where the CLI's first argument is an action of either `keep`, `archive`
or `remove`. The usual `--help` option will be available, both to the
base command and all the actions, which will show the respective usage
instructions.

##### The `keep` and `archive` Actions

    vault keep --view|FILE...
    vault archive --view|FILE...

The `keep` and `archive` actions take two forms, which perform the same
function on the respective branch of the appropriate vaults:

1. The `--view` option will list the contents of the respective branch
   of the vault relative to the current working directory ([see
   earlier](#vault-location)).

2. When given a list of (at least one) paths to files, either relative
   or absolute, these will be hardlinked into the respective branch of
   the vault relative to each file ([see earlier](#vault-location)).

   Note that the files provided must be regular files (rather than
   directories or symlinks, etc.); non-regular files should be skipped
   over and logged as such to the user. Moreover, as the files provided
   as arguments may be arbitrary, it cannot be assumed that they belong
   in the same vault.

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
        respectively.

* If it doesn't exist in the vault:
  * Hardlink the file into the appropriate branch:
    * Create the hierarchy needed to address the inode ID; specifically
      its big-endian hexidecimal representation, zero-padded to a
      multiple of 8 and broken into 8-bit words, taking all but the
      least signficiant word to enumerate the tree.
    * Hardlink the file into the leaf of this tree, with its name given
      by the least significant word (from the previous step) and the
      base64 encoding of the file's path relative to the vault location,
      concatenated with a `-`.

  * Log to the user that said file has been actioned.

##### The `remove` Action

    vault remove FILE...

The `remove` action will remove the given files from either branch of
the vault respective to said file ([see earlier](#vault-location)).
Again, it should not be assumed that files provided as arguments will be
removed from the same vault.

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

##### Permissions

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

##### Auditing and Logging

All above actions will be logged to the user, as described. In addition,
these logs will be appended to a `.audit` file that exists in the root
of the respective vault. The persisted log messages will be amended with
the username of whoever invoked the action.

#### The Batch Process and Message Queue Consumer

The batch process and message queue consumer are intended to be run
periodically (e.g., from a `cron` job) and will have the following
interface:

    sandman sweep [--dry-run] VAULTED_DIR...
    sandman drain

Where at least one `VAULTED_DIR`, representing paths to directories
(either relative or absolute) that contain a `.vault` directory, is
supplied. An optional `--dry-run` argument may also be provided to the
sweeper, which will cause the batch process to log what it would do,
without affecting the filesystem; the drainer has no dry-run option.

##### Auditing and Logging

The sweep will be logged to the user, as described. In addition, these
logs will be appended to a `.audit` file that exists in the root of the
respective vault. The persisted log messages will be amended with the
username of whoever invoked the batch process.

**TODO** What the sweeper and drainer should do and in what order.

**TODO** Why the sweeper and drainer are separated.
