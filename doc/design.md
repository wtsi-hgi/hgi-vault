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

The system will be written in Python 3.7, or newer. Certification
criteria for the system will be:

* The state for the test suite **must** satisfy the Cartesian product of
  all options.

* The test suite **must** pass without warnings or errors on the target
  platform.

* Hot code ([defined later](#hot-and-warm-code)) **must** be replicated
  in isolation by at least three different developers.

* The [cyclomatic complexity](https://en.wikipedia.org/wiki/Cyclomatic_complexity) of
  the system **must** be:
  * At most 10 and **should** be below 7;
  * At most 5 for hot and warm code.

* The test suite **must** achieve:
  * 100% coverage for hot code;
  * At least 90% coverage for warm code;
  * And average no less than 80% coverage, elsewhere.

* The system's code **must** be fully type annotated and satisfy static
  analysis.

* The system's code **must** conform to the [PEP8
  style](https://www.python.org/dev/peps/pep-0008).

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
* Cyclomatic complexity:     https://pypi.org/project/mccabe
* Linting/PEP8 conformance:  https://pypi.org/project/pylint
* Static type analysis:      https://pypi.org/project/mypy

Preferably, the programmatic analysis should be automated.

## Source Control

* git will be used for source control; origin will be hosted by GitHub.

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

### Hot and Warm Code

"Hot code" is defined to be code that immediately leads to irrecoverable
data loss. Any such code must be implemented in replicate by at least
three developers. Each implementation is assumed to follow similar
logic, but must nonetheless be implemented in isolation (before review).
All implementations will be called and only acted upon in the event of
unanimous consensus.

**If unanimity is not established, the process must exit immediately and
cease all further function.**

Hot code must be written in a separate file, suffixed with
`-hot-USERNAME` (where `USERNAME` is the username of the developer who
originally wrote said code). The full name and e-mail address of said
developer must appear in said code's comments, per the usual legalese.
Changes to hot code must be done by the original developer. When that is
not possible, that code may be either:

1. Inherited by a new developer, who will therein become its new
   maintainer. The change of owner will be documented in the comments
   and the module suffix will change to reflect the new ownership. No
   developer can be the maintainer of more than one implementation of
   any specific piece of hot code.

2. Or retired, for reimplementation by a new developer. If retiring code
   would reduce the implementation count below three, then the
   reimplementation must first be written and certified to replace it.

Hot code may call other library code defined elsewhere in the project.
Such called code will be termed "warm code" and be subject to higher
scrutiny. To facilitate this, all references to warm code must be
documented in the opening comments of all hot code modules.

An index of all hot and warm code will be actively maintained amongst
the project's documentation.

#### Example

The following predicate may need to be defined:

```py
can_delete: Callable[[Path], bool]
```

This function makes decisions on whether a file can be deleted, which
would be used in a similar fashion to:

```py
can_deletes = [can_delete-hot-ch12.can_delete,
               can_delete-hot-fm12.can_delete,
               can_delete-hot-pa11.can_delete]

if not all(can_delete(file) for can_delete in can_deletes):
  # Fail immediately

# Deletion code
```

Any `can_delete` implementation _may_ refer to a library function named
`is_in_vault`, which would be therefore be mentioned in the respective
implementations' comments. As well as facilitating review, seeing the
same reference in multiple implementations can serve as a sanity check
(e.g., an implementation that doesn't use this function, where others
do, may be suspect).

### Overview

The system will be comprised of two subcomponents, which may share
common code:

1. A user-facing CLI.
2. A batch process that actions requests, run periodically.

The purpose of the system is to mark files to be kept or archived,
action that respectively, and to delete files that have passed a
threshold age. Files will be marked by virtue of being hardlinked into a
special "vault" directory.

#### The Vault

* The vault directory will be a single directory named `.vault` in the
  root of a group's directory.

* The vault directory will contain two subdirectories: `keep` and
  `archive`.

* Within these respective directories, hardlinks of marked files will
  exist, as well as their mirrored directory structure, which will be
  preserved at the time of marking.

For example, say a user marks `my_group/path/to/some/file` for archival,
it will be hardlinked to `my_group/.vault/archive/path/to/some/file`.
Clearly the directory structure and naming of files could change, but
the inode link will not; in such an event, it will be the batch process'
ultimate responsibility to correct this.

#### CLI

The CLI will have the following interface:

    hgi-vault keep|archive|remove FILE...

That is, the CLI's first argument is an action of either `keep`,
`archive` or `remove`. The subsequent arguments (at least one) are paths
to files, either relative or absolute, that should be marked. These
files must be regular files, rather than directories or symlinks, etc.
Non-regular files should be skipped over and logged as such to the user.

#### Vault Location

The location of the vault will be the highest directory up the tree,
from a reference point (e.g., the current working directory or a
specific file), that retains the same group ownership as that reference
point. For example:

    /                                   root:root
    /projects                           root:root
    /projects/my_project                abc123:my_project
    /projects/my_project/foo            xyz456:my_project
    /projects/my_project/foo/bar.xyzzy  xyz456:my_project

If the file to be kept is `/projects/my_project/foo/bar.xyzzy`, then the
vault will be located in `/projects/my_project/.vault` and the hardlink
will be `/projects/my_project/.vault/keep/foo/bar.xyzzy`.

##### `keep` and `archive`

The `keep` and `archive` actions will hardlink the given files into the
appropriate subdirectory (`keep` and `archive`, respectively) of the
vault respective to said file ([see earlier](#vault-location)). Note
that the files provided may not end up in the same vault.

For each file:

* If said file already exists in the vault (by virtue of matching inode
  IDs):

  * Check the directory structure/file name hasn't changed in the
    meantime:

    * If it has:
      * Correct the structure/name in the vault.
      * Log the change to the user.

  * Check in which branch the hardlink exists in the vault:

    * If it matches the action (`keep` or `archive`):
      * Log to the user that no change is necessary.

    * If it differs:
      * Move the hardlink to the opposite branch.
      * Log to the user that the file's status has changed,
        respectively.

* If it doesn't exist in the vault:
  * Mimic the directory structure of the file to action, relative to the
    vault root, in the respective branch of the vault.
  * Hardlink the file into that directory.
  * Log to the user that said file has been actioned.

##### `remove`

The `remove` action will remove the given files from either branch of
the vault respective to said file ([see earlier](#vault-location)).
Again, the files provided as arguments may not be removed from the same
vault.

For each file:

* Check the ownership of the file:

  * If the file is owned by the current user or the current user is one
    of the group's owners (defined by the group's LDAP `owner` DN):

    * If the file already exists in the vault (by virtue of matching
      inode IDs), in either the `keep` or `archive` branch:
      * Delete the hardlink.
      * Clean up any redundant directory structure that now exists in
        the vault (i.e., empty directories above the deleted hardlink).
      * Log to the user that the file is no longer marked for the
        appropriate action.

    * If it is not in the vault:
      * Log to the user that the file is not marked.

  * If the file is not owned by the current user or the current user is
    not a group owner:
    * Log a permission denied error.

##### Permissions

**TODO** Unanswered questions.

All files within HGI managed project and team directories should have
identical user and group POSIX permissions. This component will need to
do some additional management on top of that provided by the filesystem,
as described earlier. To address this, the following questions need to
be answered:

1. What permissions does a file and/or its parent directory need for a
   new hardlink to be created?

2. What permissions does a file and/or its parent directory need to be
   deletable?

The answers to these conditions ought to be checked upfront for each
file being marked and, if they are not satisfied, the action should fail
for that file, logged appropriately.

##### Auditing and Logging

All above actions will be logged to the user, as described. In addition,
these logs will be appended to a `.audit` file that exists in the root
of the respective vault. The persisted log messages will be amended with
the username of whoever invoked the action.

#### Batch Process

The batch process is intended to be run periodically (e.g., from a
`cron` job) and will have the following interface:

    vault-sweep [--dry-run] VAULTED_DIR...

Where at least one `VAULTED_DIR`, representing paths to directories
(either relative or absolute) that contain a `.vault` directory, is
supplied. An optional `--dry-run` argument may also be provided, which
will cause the batch process to log what it would do, without affecting
the filesystem.

**TODO** What the sweep should do and in what order.

##### Configuration

The batch process will read its configuration from file, following the
following precedence (highest first):

1. The file at the path in the environment variable `VAULTRC`;
2. `~/.vaultrc` (i.e., in the running user's home directory);
3. `/etc/vaultrc`

If no configuration is found, or is incomplete, then the process with
fail immediately.

The configuration will be [YAML](https://yaml.org)-based, with the
following schema:

```yaml
threshold:
  age: <Age, in days, at which to delete>
  grace: <Days warning to give each file's owner and group owner>

ldap:
  host: <LDAP Server>
  port: <LDAP Port>
  # TODO How to specify LDAP base DN/search string for users and groups

email:
  sender: <E-mail address of sender>
  smtp:
    host: <SMTP host>
    port: <SMTP port>

# TODO How to specify archiver/archive queue...
```

##### File Age

The age of a file is defined to be the duration from the file's `mtime`
to present. We use modification time, rather than change time, as it's a
better indicator of usage. (Access time is not reliably available to us
on all filesystems.)

##### Auditing and Logging

The sweep will be logged to the user, as described. In addition, these
logs will be appended to a `.audit` file that exists in the root of the
respective vault. The persisted log messages will be amended with the
username of whoever invoked the batch process.

### Test Driven Development

Test cases for any new functionality must be written upfront, where
functionality and interfaces will be [defined later](#detail). Tests
must cover the Cartesian product of all options and, where external
state is required, this must be specified upfront (again, [defined
later](#detail)) and cover all expected (per design) eventualities. The
test suite may be amended and altered afterwards to conform to
unexpected implementation details required for certification.

The Cartesian product of options has the potential of making the test
space very large. To therefore avoid intractability, options ought to be
constrained in both quantity and type. This will have the consequential
benefit of reducing cyclomatic complexity.

### Detail

**TODO** Detailed design should be worked on after the above has been
polished and finalised.
