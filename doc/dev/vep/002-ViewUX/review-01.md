# VEP001 Review


# General

Overall, the changes look good; you've stayed consistent with the code conventions and style, and departed minimally from the existing code.

## Implementation

* It is preferrable to use python 3's `pathlib` to the `os.path` library for operations on paths.
* Enums (instead of strings) might be better for representing `here`, `mine` and `all` options (as is the case for representing Branch (`keep`, `archive` or `limbo`)), but since the scope of use here is small enough (as of writing), strings are fine for the time being.
* Tests for `--view-staged` flag are needed (just like how tests for other argument parsing are written)


### bin/vault/__init__.py

* L66:  `os.stat(path).st_uid` could be replaced by the corresponding function from pathlib (I think its `path.owner`)
* L71-72: The Normalisation Consistency feature in the [design spec](https://github.com/wtsi-hgi/hgi-vault/blob/feature/recover-ux/doc/dev/vep/002-ViewUX/design.md) does not mention any special behavior on `--absolute` flag for `vault recover`. Ideally the behavior should remain consitent between all vault commands, which means making `--absolute` work for `recover` as well.
* L74: `os.stat(_limbo_file).st_mtime` could be replaced by the corresponding function from pathlib (I think its `_limbo_file.stat().st_mtime`)
* L81: Please change the `print` to `log.info` (This line is too long, lines should ideally be wrapped to 72 characters). 
  


> By default, print goes to stdout; whereas logs go to stderr. Rule of thumb, at least in Vault: Only print when the information would be useful for downstream processes (i.e., machine readable and actually useful to drive something)
> e.g. :
`vault keep --view | xargs stat -c %s | awk '{t+=$0} END {print t}' | numfmt --to=iec`
 will show the total size of everything in `keep` - ch12


### Commit Messages

* https://github.com/wtsi-hgi/hgi-vault/commit/7e66be80620819f8f1c2ae2fd779babfbfc0a4a8
  - Please note the vault list API  modification in this commit message

  


