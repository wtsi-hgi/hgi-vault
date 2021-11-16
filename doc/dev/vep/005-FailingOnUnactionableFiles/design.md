# Vault Enhancement Proposal 5: Failing on Unactionable Files

## Current Behaviour

*Originally defined in the [design document](/doc/dev/design.md).*

When the batch process is run, it will collect all the files it needs to action on, and inform the owner about the actions it is going to do, for example: soft-deleting the file.

> For each user, collate the lists of files scheduled for deletion, files deleted and files staged for archival and use them to render and send an appropriate e-mail

It is important to note that the batch process is designed to fail if anything goes wrong, to attempt to stop any unwanted data loss.

## Proposed Behaviour

### Bug

This VEP is designed to resolve the bug identified in [issue #18](https://github.com/wtsi-hgi/hgi-vault/issues/18).

Some files are owned by `root`, such as ones created by ISG.

Files in a HGI managed area on Lustre typically are properly owned by the right user and are part of the right group, however some files, such as `wrstat` files are owned by the `root` user (ID `0`). The batch process attempts to look up the user ID `0` in the LDAP records to email the right person, and can't find the user, therefore it fails.

Although ideally files shouldn't be owned by the root user, it is a possibilty we need to deal with.

### Solution

- We need Sandman to fail earlier if it comes across a file owned by root. When we first discover that a file can't be actioned on, we should issue a `CRITICAL` message, and exit. This will be a more graceful exit than just letting the process continue until it fails to find the user ID `0` in the LDAP records.
- Whether a file can be actioned on can be determined using `VaultFile.can_add`.

### Discussion

- Although this was originally an issue due to a file owned by `root`, there are other situations this could arise from - such as incorrect permissions set on the files. As `can_add` includes a variety of checks, this can work in other situations too.
- By failing earlier in the process, there is less oppurtunity for unexpected behaviour, which could include data loss.
- Failing in this instance rather than skipping the file also helps stop unexpected failures - for instance it may still delete the file without warning anybody, so this stops that.
- If Sandman fails due to a file owned by `root`, or other issues regarding file permissions/file owners, we have the oppurtunity to stop Sandman whilst we resolve these problems the proper way by changing owners/permissions.
- However, this does mean that Sandman will fail every time it is run between the first time it has to action these files and when we resolve the issue.
- Missed Sandman runs can potentially lead to data loss without the ideal amount of warning, however this can be addressed alongside [issue #6](https://github.com/wtsi-hgi/hgi-vault/issues/6).