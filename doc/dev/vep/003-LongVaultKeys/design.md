# Vault Enhancement Proposal 3: Long Vault Keys

## Current Behaviour

_Originally defined in the [design document](/doc/dev/design.md)._

When files are annotated in a vault, their inode ID and filename are
used to form what is known internally as the "Vault key". This is the
filename of the hardlink to the original file and defined as such:

> * The big-endian hexadecimal representation of their inode ID will be
>   broken out into 8-bit words (padded, if necessary). All but the
>   least significant word will be used to make a hierarchy of
>   directories, if they don't already exist. (If the inode ID is less
>   than 256, then no hierarchy need be created.)
>
> * In the lowest child directory, the file will be hardlinked, having a
>   filename equal to the least significant word, concatenated
>   (delimited with a `-`) with the base64 encoding of the marked file's
>   path, relative to the vault's location, at the time of marking.

## Proposed Behaviour

### Bug

Note: This VEP is designed to resolve the bug identified in
[issue #17](https://github.com/wtsi-hgi/hgi-vault/issues/17).

A filename's maximum length, in POSIX systems, is defined by the
`NAME_MAX` value, which is typically 255 bytes. Given the prefixed inode
LSB and delimiter, that only leaves 252 bytes to play with. Base64
encoding has an overhead of 33%, meaning we could only ever store
relative paths up to 189 bytes in length. That is not enough.

### Filesystem Introspection

The `NAME_MAX` of a filesystem can be found in Python with:

    os.pathconf("/path/to/file/on/filesystem/you/care/about", "PC_NAME_MAX")

It should not be assumed to be 255 bytes, nor should it be assumed to be
equal on all filesystems.

**Note** `PATH_MAX` (accessible via `os.pathconf` with `PC_PATH_MAX`) is
a similar limit we should be wary of. It is the character limit for full
paths, including the directory separators; it is usually 4KB, but again,
we should not assume this.

### Solution

The original file's relative path will remain base64 encoded. However,
if its length exceeds `NAME_MAX - 3` bytes, on the filesystem in
question, the remainder will be broken into `NAME_MAX` byte chunks.
These chunks will go on to form a hierarchy of directories, with the
hardlink appearing (with the final chunk as its name), as before, at the
leaf position.

#### Example

Let's say the inode ID is 123456 and the base64 encoding of the filename
is 268 bytes long, on a filesystem whose `NAME_MAX` is 255 bytes:

    01/e2/40-XXXXXXXX...XXXXXXXX
             |<-- 268 bytes -->|

This would be unrepresentable with the current schema. With the proposed
solution, this would change to:

    01/e2/40-XXXXXXXX...XXXXXXXX/XXXXXXXXXXXXXXXX
             |<-- 252 bytes -->| |<- 16 bytes ->|
          \_____ directory ____/ \____ link ____/

i.e., The first chunk becomes a directory, holding the leaf chunk which
is named with the remaining 16 bytes of the encoded filename.

As many levels of `NAME_MAX` hierarchy will be used, as needed.

### Discussion

This proposal has two advantages:

1. It maintains backwards compatibility with keys for files whose
   encoding does not exceed the limit. This will allow the software to
   be deployed against an existing vault, without having to redo any
   annotations.

2. It maintains the obfuscation of annotated files, designed to
   discourage end users from poking around in the vault.

**However, the scope of this change should not be underestimated.**

The main implementation is in `api.vault.key.VaultFileKey`, which has
tests in `test.api.vault.test_key`.

Files tracked by the vault have their keys automatically corrected when
reannotated and a filename change is detected. This becomes a little
more challenging when a hierarchy of directories is involved.

The key is persisted into the tracking database, used for notifications
and maintaining the archive staging queue. The `File` model is an
abstraction which contains no logic for the key encoding -- i.e., it's
generic -- so oughtn't require code changes. Nonetheless, care should be
taken.

The end user interface uses the key when viewing the contents of a
vault. The decoding, however, is done further upstream, so oughtn't
require code changes this close to the edge. Nonetheless, care should be
taken.

The key is used by external systems. At time of writing:

* The staging queue (a list of keys) is drained to the archive handler.
  In production, this is [Crook](https://github.com/wtsi-hgi/crook) and
  the [Crook-fork of Shepherd](https://github.com/wtsi-hgi/shepherd/tree/crook-shepherd).
  These will need to be updated to understand the change.

* [Lurge](https://github.com/wtsi-hgi/lurge) and
  [Weaver](https://github.com/wtsi-hgi/weaver) work together to present
  views of any vaults that are on disk. These will need to be updated to
  understand the change.
