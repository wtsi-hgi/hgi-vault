# VEP004 Review

https://github.com/wtsi-hgi/hgi-vault/compare/e7b7fa4...ca23fb9

## General

* Please remove the `.gitmessage` file in the repository root. The
  commit template should not be here; it already exists in
  `.ci/commit.message`.

* Please amend the commit messages of the following commits so they
  conform to the template (i.e., include a short description on the
  first line):

  * `7624800`
  * `1fb5c64` (you can potentially delete this commit altogether, which
    will resolve the previous point)

* Commit `2710f91` and `714f1bf` appear to be identical, but the commit
  message in the latter has been tidied up. Please either remove commit
  `2710f91`, or correct its commit message and remove `714f1bf`.

* The majority of this VEP concerns user interface changes to `vault`;
  the functional implementation in `sandman` is trivial (although, see
  notes below). The interface changes made need refactoring work
  (discussed below). To facilitate this, I would recommend becoming more
  acquainted with the [`argparse`](https://docs.python.org/3.8/library/argparse.html)
  module, in the Python standard library.

* I have not reviewed the tests. Given they pass, when the argument
  parsing code needs work, suggests that the tests are either incorrect
  or don't cover this part of the code adequately.

## `api/vault/file.py`

Don't comment out functionality that is no longer required (i.e., L95
and 96). We have version control, so just delete those lines and make an
appropriate note of it in the commit message.

## `bin/sandman/sweep.py`

The original code has this pattern:

```python
if status == Branch.Archive:
  # do
  # some
  # stuff
```

The stashing code is almost identical to the archive code, but it has
been added as a completely new conditional branch:

```python
if status == Branch.Stash:
  # do
  # almost the same
  # stuff

if status == Branch.Archive:
  # do
  # some
  # stuff
```

The best code is the code you don't write!

By copy-and-pasting the archive code, you've doubled your maintenance
cost: If changes need to be made in this code, then whoever comes along
do to this will have to remember to make the same changes in both the
archive and stash code; if there happens to be a bug in the archive
code, now you have two bugs! etc.

A better pattern would be to generalise and make special cases when
needed:

```python
if status in [Branch.Archive, Branch.Stash]:
  # do...

  if status == Branch.Archive:
    # ...Archive-specific stuff

  # and
  # general
  # stuff
```

## `bin/vault/__init__.py`

L199: `stash` is not an "action", it's a behaviour flag to the `archive`
action. The `_action_to_branch` dictionary is a mapping between actions
and their appropriate branches. You then reference it in L215, but it's
a redundant layer of indirection.

Rather than trying to shoehorn the new behaviour into the original code,
it seems like the code would benefit from being refactored to make it
clearer as to what's going on. Something like (untested!):

```python
_action_to_branch = {
  "keep": Branch.Keep,

  "archive": {
    # stash  view_staged
    # -----  -----------
    ( False, False       ): Branch.Archive,
    ( True,  False       ): Branch.Stash,
    ( False, True        ): Branch.Staged
  },

  "recover": Branch.Limbo
}

if args.action in _action_to_branch.keys():
  # Map our action (and behaviour) to a branch
  branch = _action_to_branch[args.action]
  if args.action == "archive":
    branch = branch[(args.stash, args.view_staged)]

  # Are we viewing?
  if context := (args.view or (args.action == "archive" and args.view_staged)):
    view(branch, _view_contexts[context], args.absolute)
    if args.action == "archive" and not args.view_staged:
      view(Branch.Stash, _view_contexts[context], args.absolute)

  # ...otherwise:
  else:
    if args.action == "recover":
      recover(None if args.all else args.files)

    else:
      add(branch, args.files)

else:
  untrack(args.files)
```

In my option, this code is clearer. However, it's worth pointing out
that the more actions or special behaviours we add, the more complicated
this will become. As such, while I do recommend refactoring your code, I
don't necessarily recommend following the route I've outlined above.
This strikes me instead as an opportunity to develop a better approach,
which may be facilitated by the `argparse` module (e.g., function
dispatch, based on action).

## `bin/vault/usage.py`

L63-66: What is this for? Instead you should update the help text for
the `archive` action, on L54, to include the new `--stash` option:

    %(prog)s [-h] ((--view [{all | here | mine}] | --view-staged [{all | here | mine}]) [--absolute] | [--stash] FILE [FILE...])

The only place you use `_actions["stash"]` is when setting the `--stash`
option's help. However, this is the wrong help text. The help for this
option should just be a simple string, like "archive without deleting".
Moreover, this option should not be added to the `archive_view_group`
mutually exclusive group; that makes no sense.

The grouping of options here is a bit broken; I'm surprised it works at
all and, if it does, I wouldn't rule out unexpected behaviour. Part of
the problem is from this VEP, but also the changes made in VEP002 are
responsible (and weren't reviewed properly).

This is an opportunity to correct this code. The grouping should look
like this:

* Mutually Exclusive Group
  * "View" Group
    * `--view [CONTEXT]`
    * `[--absolute]`
  * "View Staged" Group
    * `--view-staged [CONTEXT]`
    * `[--absolute]`
  * "Archival" Group
    * `[--stash]`
    * `FILE [FILE...]`

n.b., Correcting the argument parser will have repercussions on the
action selection code in `bin/vault/__init__.py`, discussed above.

## Tests

*Not reviewed*
