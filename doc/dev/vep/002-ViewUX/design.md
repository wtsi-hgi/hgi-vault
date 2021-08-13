# Vault Enhancement Proposal 2: View UX Improvements

## Current Behaviour

_Originally defined in the [design document](/doc/dev/design.md) and
[VEP001](/doc/dev/vep/001-SoftDelete/design.md)._

The `--view` options to the `vault` actions list the entire contents of
the respective branch, regardless of their location in the file
hierarchy or owner.

The `--view` option for the `recover` action normalises the output
relative to the current working directory for convenience. The other
action's `--view` outputs show absolute paths.

## Proposed Behaviour

Note: This VEP subsumes [issue #13](https://github.com/wtsi-hgi/hgi-vault/issues/13).

### Normalisation Consistency

The normalisation of annotated file paths, relative to the current
working directory, is useful for the `recover` action's view because
that style matches the expected input for the action itself, as a
convenience to the user. This style of relative path output turns out to
be easier to read, in general, so should be applied to all outputs.

However, if a user really wants absolute paths, then this can be
achieved with an optional `--absolute` flag.

### View Context

Currently, when viewing a branch's contents, it shows all files that are
annotated in that branch. For most users, this will be unhelpful, so we
should allow them to contextualise the view to their convenience. This
should be done with an optional argument to the `--view` option:

    --view [CONTEXT]

Where `CONTEXT` can be one of:

| Context | Behaviour                                                                        |
| :------ | :------------------------------------------------------------------------------- |
| `all`   | Show every file in the branch (default)                                          |
| `here`  | Show every file in the branch from the current working directory (non-recursive) |
| `mine`  | Show every file in the branch that is owned by the current user                  |

### File Expiry Time in `recover` Output

The view of the `recover` action shows files that have been
soft-deleted by Sandman. At which point, their `mtime` is reset and the
clock starts ticking before Sandman will permanently delete these files.
As Sandman may soft-delete files every time it's run, the current view
makes it impossible to tell when files will expire.

In addition to the file path, the `recover` output should be amended
with the number of hours (to one decimal place) until each file's
expiry, tab-delimited. For example:

    my-file	2.1 hours
    ../another/file	14.9 hours

The output need not be sorted, as this can be done trivially with, e.g.,
`sort`.

### Staged Files

When files are annotated for archival, Sandman will transfer them into
the `.staged` branch and remove the original copy. There will be a lag
between this happening and the file showing up in the archive, due to
the batched nature of Sandman's interface with the downstream archive
handler. This may cause unnecessary panic from users who don't realise
this, despite them receiving an e-mail notification telling them
otherwise.

To help alleviate this, the `archive` action should have an additional
`--view-staged [CONTEXT]` option, acting in the same way as described
above, with a sibling `--absolute` option, to show the current contents
of the staging queue.

Note: It won't be possible to establish when the archive will happen, as
that depends on externalities beyond our control. However, this should
be enough to reassure users that their files have not vanished.
