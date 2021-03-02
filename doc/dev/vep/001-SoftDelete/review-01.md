# VEP001 Review

## General

* Please amend the commit messages of the following commits so they
  conform to the template:

  * `5a49baa`
  * `074efb8`
  * `b004b69`
  * `c80be20`

  Feel free to squash smaller commits together, where it makes sense.

* Please add your name to the list of authors in the following files:

  * `api/vault/common.py`
  * `api/vault/file.py`
  * `bin/vault/usage.py`

* Please correct the copyright dates in the following files:

  * `api/config.py`: 2020, 2021
  * `api/mail/notification.j2`: 2020, 2021
  * `api/vault/common.py`: 2020, 2021
  * `api/vault/file.py`: 2020, 2021
  * `bin/vault/recover.py`: 2021
  * `bin/vault/usage.py`: 2020, 2021
  * `core/file.py`: 2020, 2021
  * `test/api/test_config.py`: 2020, 2021
  * `test/bin/test_recover.py`: 2021
  * `test/core/test_file.py`: 2020, 2021

* The `VaultFile` implementation checks for basic consistency on
  construction by [checking the number of hard
  links](https://github.com/wtsi-hgi/hgi-vault/blob/9ad9cc78509d0bcaa91e95ba72c884772eb21327/api/vault/file.py#L76-L88).
  The new "recover" action will break this assumption, so it's possible
  -- if not highly likely -- that the new functionality will run afoul
  of this. As far as I can see, your code is only using `VaultFileKey`,
  so _may_ be immune; however, other code may not be so lucky. I would
  recommend amending this consistency check to allow for single hard
  links in the limbo branch.

* Please restructure `test/bin`, such that `test_recover.py` is under
  `test/bin/vault` (i.e., preparing `test/bin` for future tests).

* Please check off all implemented functionality in
  `doc/dev/vep/001-SoftDelete/design.md`.

* I haven't enumerated the instances of this, but you often have very
  long lines in your code, which are hard to read unless wrapping is
  explicitly turned on (usually not appropriate for code). This is
  particularly prevalent in comments or documentation; ideally these
  should be wrapped to 72 characters, to match the other comments. All
  instances can be seen clearly in the [branch diff](https://github.com/wtsi-hgi/hgi-vault/compare/c53ef2a...9ad9cc7#files_bucket).

* This is a minor stylistic point, so can be ignored, but ideally:

  * Don't leave dangling whitespace at the ends of lines and files.

  * Between "related" functions/definitions, leave one empty line (e.g.,
    between class methods).

  * Between "unrelated" definitions, leave two empty lines.

  * Try not to let code lines (as opposed to comments or documentation)
    exceed 100 characters. Sometimes this isn't possible, or doing so
    would look uglier than leaving the long line; it's a somewhat
    subjective thing.

  As I say, style isn't of crucial importance, but it helps with the
  long-term maintenance of code, which should be written mostly for the
  benefit of another (human) reader who isn't necessarily familiar with
  any context.

## Implementation

### Core

> Method to update a file's `mtime` (`core/file.py`, tests in
> `test/core/test_file.py`).

The implementation is fine. A few minor points:

* `dt` is not a descriptive name for the argument; `mtime` would be
  clearer.

* You use `dt.timestamp()` to get the Unix time. This is fine, but it
  breaks the dependency inversion. Instead, you could implement a new
  function in `core.time` that takes a `DateTime` and returns its Unix
  timestamp (thus centralising your `to_utc` and casting logic):

  ```python
  timestamp = lambda dt: int(to_utc(dt).timestamp())
  ```

  Note: Similar code was removed in `b26d3f1` as it was no longer
  needed, at the time. This usage makes the case to reinstate it.

* If you make the above change, you can then use `core.time.timestamp`
  in your tests.

### API

> Update the configuration schema to include `deletion.limbo`
> (`api/config.py`, tests in `test/api/test_config.py`).

This is fine.

> Add `.limbo` branch (`api/vault/common.py`).

This is fine.

> Change text of notification e-mail (`api/mail/notification.js`).

This is fine.

### Vault

> Method that canonicalises a Vault path (which is relative to the Vault
> root), such that it is also relative to any directory under the Vault
> root, both up and down the tree.

`bin/vault/recover.py`:

* L20: You don't use `os`, so no need to import it.

* L23: You don't use `VaultFileKey`, so no need to import it.

* L26: `vault_relative_to_wd_relative` is a bit of a mouthful. Can it be
  made shorter and clearer?

`test/bin/test_recover.py:L37-62`:

* L39-45: This comment is meaningless without more explanation; it is
  also indented incorrectly.

* L48, 57: The code for these tests are clear enough, so these comments
  (which aren't very clear) should either be removed or annotated.

> Method that takes a canonicalised Vault path, relative to some
> directory under the Vault root, and converts it back to a "full" Vault
> path (i.e., the inverse of the above).

`bin/vault/recover.py`:

* L40: `wd_relative_to_vault_relative` is even more cryptic than and, at
  the same time, too close to `vault_relative_to_wd_relative`. Please
  consider clearer names.

* L49: Your example omits the vault root.

* L52-56: I'm not sure if your algorithm is the same, but this is my
  thought process:

  ```
  Vault root:         /path/to/vault/root
  Working directory:  some/subdirectory
  Relative path:      ../other/subdirectory/some/file

  Returns:            some/other/subdirectory/some/file
  ```

  You need the Vault root because the relative path may contain `..`
  parents and `pathlib.Path.resolve()` will get the absolute path
  relative to the current working directory, not some arbitrary working
  directory. So I _think_ the algorithm should be:

  ```python
  # NOTE vault_root should always be an absolute path
  full_path = (vault_root / working_directory / path).resolve()
  return full_path.relative_to(vault_root)
  ```

  You _might_ even be able to get away with this, if you always assume
  that `working_directory` and `path` have the same parent (i.e.,
  `vault_root`, which would thus not even be needed):

  ```python
  return T.Path(os.path.normpath(working_directory / path))
  ```

  Your algorithm may be correct, but I'm not convinced. That said, you
  have tests which are passing...

`test/bin/test_recover.py:L65-84`:

...Your tests are passing and the code for which is clear. However, the
implementation of `wd_relative_to_vault_relative` is hard to follow and
doesn't seem to be doing anything different to the simpler algorithms I
present above. Also, your tests assume a `vault_path` of `.`, on L71 and
81, rather than the reality of an absolute path: Does this matter? I
can't say with any certainty when reading your implementation. I would
therefore recommend simplifying the algorithm for this function in
`bin/vault/recover.py`.

* L68, 78: The code for these tests are clear enough, so these comments
  (which aren't very clear) should either be removed or annotated.

> Update command line argument parser to accept new subcommand and its
> options (`bin/vault/usage.py`), with appropriate help text.

The following changes to `bin/vault/usage.py` may seem trivial, but as
part of the user-facing interface, it's important to polish:

* L41: Change the help text to just "file recovery operations" and the
  view help text to "view recoverable files". Align the view help text
  beneath the help text in the code (see other actions as an example).

* L78: `--all` flag:

  * Change the help text to "recover all recoverable files".

  * `--view` and `--all` (and `FILES`) are mutually exclusive. Your
    change to the argument parser would allow both. It should raise an
    error if you attempt to provide both.

* L65: This is my code to add a special usage string for commands that
  support `--view`. `recover` is the new such command, but it also
  supports `--all`, which won't be shown in the help. You will need to
  add a special case for the `recover` command. Something like:

  ```python
  action_level["recover"].usage = "%(prog)s [-h] (--view | --all | FILE [FILE...])"
  ```

* L93: The error message in my code is no longer true, for the `recover`
  command, as you now also have `--all` in this case. This is a similar
  special case to the above, so it may be better to solve these with
  abstraction, rather than conditions all over the place.

* L95-97: The design mentions that the 10 file limit does not apply for
  the recovery operation:

  > Note: Unlike `keep` and `archive`, the list of paths will not be
  > limited to ten, but must be at least one.

> Method that recovers a file from the `.limbo` branch, per the steps
> outlined [in the design].

`bin/vault/recover.py:L59-74`:

* L60: Please include full function documentation, with parameters
  outlined. Also note that your code is general (a good thing) and
  doesn't actually refer to the limbo branch. i.e., There's no need to
  mention this in the comment, as it implies functionality that's not
  there; but this is because it's not relevant, rather than overlooked.

* L64-66: You check for the case that the destination's parent directory
  doesn't exist, but what about the case when the destination itself
  _does_ exist? You don't want a recovery operation to overwrite a file
  that has come into existence in the meantime with the same name.

* L63, 66: Rather than logging and returning `None` in these error
  instances, it might be useful to raise a custom exception so that the
  upstream code has a better idea of what's going on.

* L68: Whilst this is how it was specified in the design -- an oversight
  on my part -- it would probably be better to simply move the file from
  the limbo branch to its recovery target. One probably-atomic
  filesystem operation (move) would be safer than two (link and unlink),
  which are together not atomic by definition.

`test/bin/test_recover.py:L89-125`:

* L107, 115, 121: The code for these tests are clear enough, so these
  comments (which aren't very clear) should either be removed or
  annotated.

* L118-119, 124-125: You're not testing anything here. Your
  implementation returns `None` in these failure modes, but it also
  returns `None` when it succeeds. You've commented out the assertion
  that the failure mode should raise an exception: Stick with that and
  update your implementation such that the appropriate exceptions are
  raised (per my comment, above).

> Expose `--view` option, wrapped in the aforementioned canonicalisation
> method with respect to the current working directory.

`bin/vault/__init__.py`:

* L46-60:

  * You have changed this function to return a list of paths, but
    have not changed the type signature.

  * If you need the list of paths, then better to yield them (i.e., as a
    generator) than return a list.

  * You don't need the list of paths and, indeed, never use it. Please
    revert this function to its original state, plus the logic to show
    relative paths for the limbo branch.

`test/bin/test_recover.py:L253-299`:

Ah, so you return the list of paths because you've written a test for
the view. However, again, you don't actually use the return value. You
do not need to write a test for the exposed `view` function, because it
is just a thin wrapper over `api.vault.vault.Vault.list`, which has its
own test. You can remove this code.

* L291-299: Moreover, these tests aren't actually testing anything!

> Expose `FILE...` recovery option, wrapped in the aforementioned
> inverse canonicalisation method with respect to the current working
> directory.

`bin/vault/__init__.py`:

* L122, 141-154: The `recover` and `recover_all` functions are almost
  identical. Rather than repeating logic, increasing the scope for bugs
  and divergence, it would be better to have this function act
  accordingly on its input parameter(s).

* L123-125: Please tidy-up the formatting of the function documentation.

* L131, 152: `project_files` and `project_source` are curious names. Do
  you mean "project" as in the verb? In which case, `projected` would be
  a clearer prefix; or something else entirely to remove the ambiguity.

* L135: You reconstruct the Vault key non-defensively. What happens if
  an errant file is hit in this walk? It _shouldn't_ be, but it's a good
  idea to guard against such a possibility.

* L139: The logging is done by the `hardlink_and_remove` function, which
  makes it opaque to this code (where it actually counts). It would be
  better if the logging was done here based on the return value or
  exception from `hardlink_and_remove` (as described elsewhere).

**Important** The `recover` function is not exposed to the user and
never actually called.

* L167: The "recover" action diverges enough from "keep" and "archive"
  that it would make more sense to separate it out as its own branch in
  this conditional. That would help you solve the above important
  omission more clearly.

`test/bin/test_recover.py:L128-251`:

* L130-137: This comment is meaningless without more explanation; it is
  also indented incorrectly.

* L141-159, 173-194: The set up for the test is very opaque and also
  spread over two functions (the actual set up and the test). I
  appreciate that setting up the desired state for this test is
  necessarily going to be verbose, but how it's currently written is
  very hard to follow. For example, you `chmod` files on L153-157, but
  it's not clear why some get `0o660` and another `0o664`, etc. The
  state should be the absolute minimum to get the test done and, in
  cases where its non-trivial, such as this, should be adequately
  documented.

> Expose `--all` option, as a special case of the above two.

`bin/vault/__init__.py`:

* L141-154: Per above, consolidate this function into the `recover`
  function, with appropriate behaviour predicated on its input
  parameter(s).

* L171-172: You recover everything if you do the "recover" action and
  `--view` isn't passed. This is not the expected behaviour. (See the
  above comment about separating the "recover" action's logic into a
  separate branch.)

`test/bin/test_recover.py:L211-251`:

This test is, unsurprisingly, effectively the same as the test for
`recover`. You should consolidate `recover` and `recover_all`, then you
will be able to remove this near-duplicated test.

### Sandman

`bin/sandman/sweep.py:L52-56`:

* Splitting into `can_soft_delete` and `can_permanently_delete` is a
  good idea.

> Update the untracked file sweeper handler to soft-delete files that
> have exceeded their maximum age, rather than hard-delete them
> (`bin/sandman/sweep.py`).

`bin/sandman/sweep.py:L263-312`:

* L265-271: Update function's documentation to refer to soft-deletion,
  rather than permanent deletion.

* L288-289: The `limboed` variable is never used, so you might as well
  drop it. Note also that these two lines should probably be moved out
  of the `try` block, as that only exists to check that the deletion
  operation succeeded (or otherwise). Something like:

  ```python
  vault.add(Branch.Limbo, file.path)
  assert hardlinks(file.path) > 1
  try:
      # etc.
  ```

* L291, 294, 297: In the logging output, always use the term
  "soft-delete" or "soft-deletion", rather than just "delete", and don't
  refer to "limbo" as that is internal only.

* L300: I agree with your comment, but we want to avoid changing the
  database model at all costs. In my opinion, while true, this comment
  is best removed to avoid any potential confusion.

* **Important** This was mistakenly omitted from the "Implementation
  Details" section of the design, but it is specified elsewhere in the
  design and has not been implemented here:

  > Reset the `mtime` of the limboed file to the current time.

  Without this, hard-deletions will be due immediately whenever the
  limbo period is less than the soft-delete period.

> Update the branch sweeper handler to hard-delete limboed files that
> have exceeded their grace age (`bin/sandman/sweep.py`).

`bin/sandman/sweep.py:L215-258`:

* L217-222: Update function's documentation to refer to the
  hard-deletion that now may take place here.

* L251: I agree with your comment, but we want to avoid changing the
  database model at all costs. In my opinion, while true, this comment
  is best removed to avoid any potential confusion.
