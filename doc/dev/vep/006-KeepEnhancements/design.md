# Vault Enhancement Proposal 6 - Keep Enhancements

## Current Behaviour

_Originally defined in the [design document](/doc/dev/design.md)._

>#### The `keep` and `archive` Actions
>
>    ```
>   vault keep --view|FILE...
>   vault archive --view|FILE...
>   ```
>
>The `keep` and `archive` actions take two forms, which perform the same
>function on the respective branch of the appropriate vaults:
>
>1. The `--view` option will list the contents of the respective branch
>of the vault relative to the current working directory ([see
>earlier](#vault-location)).
>
>2. When given a list of (at least one and no more than ten) paths to
>files, either relative or absolute, these will be hardlinked into the
>respective branch of the vault relative to each file ([see
>earlier](#vault-location)).
>
>Note that the files provided must be regular files (rather than
>directories or symlinks, etc.); non-regular files should be skipped
>over and logged as such to the user. Moreover, as the files provided
>as arguments may be arbitrary, it cannot be assumed that they belong
>in the same vault.
>
>The list of files is restricted to, at most, ten (per invocation) to
>limit "abuse"; i.e., to nudge users to be mindful of what they
>annotate, rather than using arbitrary globs.
>
>Specifically, the hardlinking function should do the following for each
>regular file provided as an argument:
>
>* If said file already exists in the vault (by virtue of matching inode
>IDs):
>
>   * Check the directory structure/file name hasn't changed in the
>    meantime:
>
>        * If it has:
>           * Correct the hardlinked name in the vault.
>           *  Log the change to the user.
>
>   * Check in which branch the hardlink exists in the vault:
>
>       * If it matches the action (`keep` or `archive`):
>           * Log to the user that no further change is necessary.
>
>       * If it differs:
>           * Move the hardlink to the opposite branch, maintaining the
>        necessary structure.
>           * Log to the user that the file's status has changed,
>        respectively. If the hardlink is moved to the archive branch,
>        log that staging will happen later and will require the file to
>        be unlocked for writing.
>
>* If it doesn't exist in the vault:
>   * Hardlink the file into the appropriate branch:
>       * Create the hierarchy needed to address the inode ID; specifically
>    its big-endian hexadecimal representation, zero-padded to a
>    multiple of 8 and broken into 8-bit words, taking all but the
>    least signficiant word to enumerate the tree.
>       * Hardlink the file into the leaf of this tree, with its name given
>    by the least significant word (from the previous step) and the
>    base64 encoding of the file's path relative to the vault location,
>    concatenated with a `-`.
>
>   * Log to the user that said file has been actioned. If the file was
>    added to the archive branch, log that staging will happen later and
>    will require the file to be unlocked for writing.
>

## Proposed Behaviour

### Keeping Directories

We allow the command

```
vault keep DIRECTORY
```
This will not work on the same level as the `.vault` file to prevent the entire project structure to be kept, which defeats the point of Vault. Only one directory can be specified at a time to also try and limit abuse.

When we run this command on a directory, Vault will walk the directory, and add every file to the Keep branch like a single file.

We also add to a file within the `.vault` called `tracking`. This will be a base-64 encoded JSON file used both here and in the section later in this document "Freezing Users". If the directory (or a parent directory) is already in here, it won't be re-added.

The structure used for "Keeping Directories" in this JSON is:
```json
[
    {
        "directory": "string",
        "exceptions": [
            "string"
        ]
    }
]
```

The field `directory` is the directory (path relative to `.vault`) being kept. The `exceptions` array is file paths **relative to the `directory`** that have since been taken out of the `keep` branch.

The batch process is likely to find inconsistencies between the `tracking` file, the directory structure and the files in the `keep` branch, for example, if a new file is added to the branch.
- If a file is in the `tracking` file `exceptions` list, but not in the directory structure, it will be removed from the `exceptions` list. This suggests it has been deleted or moved.
- If a file is in the directory, but not in the `keep` branch or `exceptions` list, it'll be added to the `exceptions` list. This suggests it is a new file added to the directory.

We will also be able to
```
vault untrack DIRECTORY...
```
to untrack everything in the directory **except** anything in the `exceptions` list, as it may have been added to the `archive` branch, which this shouldn't affect.

When the user runs
```
vault keep --view
```
anything not part of the `tracking` file will be displayed like current, however any files in the directories part of the tracking file won't be displayed, only the directory path and the number of exceptions, i.e.
```
hgi/data/ with 11 files not in the Keep branch
```

We will introduce a new ViewContext, `directory`, which will display the exceptions. It must be clear to the user that these files are **not** in the Keep branch.

```
$ vault keep --view directory

These files are NOT in the Keep branch.

hgi/data/temp_0.tsv
hgi/data/file_a.txt
...
```

The ViewContext `all` can be used to display all the files without any files being summarised as the directory they are part of. **Note:** currently the `all` ViewContext has the same behaviour as no ViewContext being provided - this changes that.

### Freezing Users

There may be times users take a leave that could stop them responding to warnings about their files being deleted. Note that this is different to scheduled downtime which affects all users - this affects a single user. This could be, for instance, for maternity leave.

We can introduce a new use case for `keep`:
```
vault keep --freeze USER
```

This would add all the user's files within the jurastiction of that `.vault` to the new Frozen branch, no matter where the command was run from.

It will also track the user and the current date in the `tracking` file (defined above in "Keeping Directories").

Files in the Frozen branch won't be deleted during the batch process, just like those in the Keep branch. However, the batch process will remove the files from the Frozen branch when a defined time period since the recorded date has passed. This time period will be defined in the Vault configuration.

After the files have been restored from the Frozen branch, it is **crucial** that the user still receives the same amount of warning of their files being deleted.

To facilitate this, the user won't be removed from the `tracking` file at the same time as the files get removed from the Frozen branch. If the batch process finds files for the user to be deleted and finds the user in the `tracking` file, the files won't be deleted, but the user will still be warned. Essentially, we are setting
```
DELETION DATE = FREEZING DATE + FROZEN PERIOD + WARNING PERIOD
```

This could provide a good baseline for implementing batch process downtime, as the issue about ensuring the user's still get the neccesary warnings is important there too.

## Discussion

The other possible way to implement these same features is with the concept of a `.vaultignore` file, however there are some limitations to that:
- It doesn't provide the same protections as `vault` commands - Vault can ensure things can only be removed from the vault by the owner or an owner of the vault, we can't ensure that with letting people just editing a text file.
- We would be tracking files in two separate ways - through the `.vault` directory and through the `.vaultignore` files. Also, we can't control where `.vaultignore` files end up.
- It would be easier for users to abuse `.vaultignore` files, and just mark all their files as Keep.

This method does introduce a new concept into Vault - the `tracking` file. This is contained within `.vault`, and in the future can be used as a place for locally storing any other metadata.

Its weakness is people tampering with it. We can ensure the errors from this are reduced by:
- Introducing error checking to the base64 encoding. Although this won't stop someone decoding it, changing it and re-encoding it (hopefully that's already not an issue by disguising it with the encoding), if someone changes some characters in the encoding, it can self-heal.
- Having fallback options for if the file is deleted, so that simply missing the file won't allow damage to be caused. For example, in the implementations in this document, the "Keeping Directories" problem is solved as it will just assume every file was added individually, and if the file is missing when the batch process finds the Frozen branch, it can recreate it based on the files in the branch, simply resetting the date to the current date.

Another potential issue is that when a user's freeze period ends, although they're files will still be given the right warning period, there may be a large number of files it is ready to delete, so the warning email may be very long and, depending on how much data is on the line, very important. Maybe it'd be a good idea to hightlight the email more to the user saying:
```
These files should have been deleted during the period your files were frozen. They will be deleted in XX hours.
```
We also need to check, (though I think it will be fine), that the time period for recovery isn't affected. I don't think it is - it is based on the `mtime` getting reset when the file is moved to the Limbo branch.

As both these features allow marking many files to be kept at the same time, we need to reduce the likelihood of it being abused and having user's just mark everything as "Keep". For example:
- limiting the `vault keep DIRECTORY` to one entry at a time
- not allowing `vault keep DIRECTORY` in the same level as the `.vault`
- logging the use of `vault keep --freeze`