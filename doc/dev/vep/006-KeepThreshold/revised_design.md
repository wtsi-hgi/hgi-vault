
# Vault Enhancement Proposal 6: KeepThreshold

## Current Behaviour

Once the files are annotated for Keep, they are never deleted by our automated data deletion policy (actioned by Sandman). 

This is not desirable as this might lead to an ever increasing accumulation of Kept files by default. Files that are annotated for Keep in present might be no longer needed in future, and we would want to recover that space.


## Proposed Behaviour


This work should be done in `feature/keep-threshold` branch.

### Sandman

When Sandman sweeps the filesystem, if it comes across a file in the Keep branch whose age is more than a `Keep Threshold` (say "one year"), it will be untracked.


If the file's age is more than the `Keep Theshold`, the file's hardlink will be removed from the Keep branch (i.e. the source will be untracked. Unless re-annotated, it will be subject to Sandman's deletion policies). 

> Note: When Sandman sweeps the Keep branch, if the source is absent, it will remove the hardlink leading to permanent deletion of data. (The idea is that if the source has been deleted, then the user intended for data to be deleted.) 

> Note: Keep is not the same as "Backup"



> Suggestion from Guillaume: At the time users annotate their files, they might already have some idea of how long would they need the files for. They might want some files for a month, while others for five years. Maybe we can provide them with an argument to `vault keep` , `keep duration`, that allows them to specify the duration for which they'd keep this file. This would require storing the duration as the state of the file.
>                                                  


### Code Changes


##### Configuration

In addition to the deletion threshold, there would be a `Keep Threshold`, that will set the duration for which files are annotated as Keep. When a file's age crosses this threshold, it will be untracked.



##### Sandman Sweep

The part of the handler that would check for the Keep Threshold would be the one that walks over the source files in the filesystem (and returns its Branch status):

```
@_handler.register
    def _(self, status:Branch, vault, file):

.....


    if status == Branch.Keep:
            if _can_untrack_keep(file):
                try:
                    vault.remove(Branch.Keep, file.path)

                except VaultExc.VaultCorruption as e:
                    # Corruption detected
                    log.critical(f"Corruption detected: {e}")
                    log.info("Contact HGI to resolve this corruption")

                except VaultExc.PermissionDenied as e:
                    # User doesn't have permission to remove files
                    log.error(f"Permission denied: {e}")

                except IdM.exception.NoSuchIdentity as e:
                    # IdM doesn't know about the vault's group
                    log.critical(f"Unknown vault group: {e}")
                    log.info("Contact HGI to resolve this inconsistency")

```



##### Test

The test would look something like this:

```
    # Behavior: When a Keep file has been there for moore than keep threshold, it is unkept
    @mock.patch('api.idm.idm', new = dummy_idm)
    @mock.patch('bin.sandman.walk.idm', new = dummy_idm)
    @mock.patch('bin.vault._create_vault')
    def test_keep_threshold_passed(self, vault_mock):
        self.assertTrue(os.path.isfile(self.file_one))
        vault_file_one = self.vault.add(Branch.Keep, self.file_one)
        walk = [(self.vault, make_file_seem_old(self.file_one), Branch.Keep)]
        dummy_walker = _DummyWalker(walk)
        dummy_persistence = MagicMock()
        Sweeper(dummy_walker, dummy_persistence, True)
        self.assertTrue(os.path.isfile(self.file_one))
        self.assertFalse(os.path.isfile(vault_file_one.path))
```

----


Note on `archive --stash` (slightly unrelated):

> When a file is annotated for Keep, Archive or Archive --Stash, its mtime or atime is not changed. ctime is changed.

---

> Note: `archive --stash` is not the same as "Backup"

If a file is stashed (`vault archive --stash`), then it cannot be annotated for "Keep" until the file has been successfully archived. 

This is because there is a time lag between the following two actions:
(1) when the hardlink is created in the Stash Branch 
(2) when the hardlink is removed from the Stash branch on successful archival 

During this time lag, the file cannot have a hardlink in the Keep branch - because of the constraint (maintained in code) that there can only be one hardlink for a file in Vault at any given time. 

If the file is not subsequently annotated for Keep, it will be subject to Sandman's deletion policies and be eventually deleted when the "file age" crosses the deletion threshold. ( `archive --stash` creates a new hardlink in the stash branch, this will change the file's ctime to the latest, refreshing its age. )

The file will need to be annotated after its archival for Keep if we are to prevent its deletion.




