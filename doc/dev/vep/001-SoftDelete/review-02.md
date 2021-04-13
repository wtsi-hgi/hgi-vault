# VEP001 Review

https://github.com/wtsi-hgi/hgi-vault/compare/9ea81e5...7a227be

## General

* Please correct the copyright dates in the following files:

  * `api/mail/notification.j2`: 2020, 2021

* I haven't been as thorough as in the first review and have focused
  mainly on key functionality.

## Implementation

### Recover Functionality

> **Important** The `recover` function is not exposed to the user and
> never actually called.

You have added a new condition in `bin/vault/__init__.py:L195-201`. This
will correctly handle the `recover` action, but note that the `else`
branch of the previous conditional (L193) will also be executed. You
definitely don't want that!

> * L122, 141-154: The `recover` and `recover_all` functions are almost
>   identical. Rather than repeating logic, increasing the scope for
>   bugs and divergence, it would be better to have this function act
>   accordingly on its input parameter(s).

You have implemented this as `recover` in `bin/vault/__init__.py`. The
signature of your function is:

```python
def recover(files: T.Optional[T.List[T.Path]]) -> None:
```

Presumably `None` maps to "recover everything" and an explicit list
means "recover these specific files." However, when you call the
function (L199 and 201), you make the "recover all" call with an empty
list. I would make the signature:

```python
def recover(files: T.Optional[T.List[T.Path]] = None) -> None:
```

Then the "recover all" call can be simply `recover()`. Indeed, this
conditional (L196-201) could be tidied up a bit. This is a personal rule
of thumb, but if you ever start writing `elif`, then think about whether
there's a clearer way to express the choice. Sometimes it's unavoidable,
but I've found that it's *incredibly* rare that I need to use `elif`
(even `else` can be quite rare). Usually I find branching patterns can
be written like this, which I personally find much clearer:

```python
if condition_for_case_a:
  do_thing_for_case_a()

if condition_for_case_b:
  do_thing_for_case_b()

# etc.

do_things_common_to_all_cases()
```

(In Python 3.10, we'll be getting structural pattern matching, which is
much better still...but that will have to wait!)

Your implementation of `recover` is basically your original `recover`
and your old `recover_all` functions mashed together with another
conditional. These two code branches are extremely similar: you should
refactor this a bit more intelligently, otherwise you open yourself up
to divergence bugs. There are a couple of specific things worth
mentioning, too:

On L129, your conditional is `if files:` to test, in your case, for an
empty list. It is clearer not to assume truthiness or otherwise and be
explicit. In your case, you should check for a non-empty list; however,
with the above change, you can do `if files is not None:`.

On L139 (and L161, because you're repeating yourself), you have used an
`else` branch to a `try...except` block. I'll be honest with you: I
never knew this was possible and having read the documentation I can see
maybe one minor use-case for it. Here it is completely unnecessary and
it forces you to increase the indentation level, which hinders
readability.

### Reset `mtime` of Limboed Files

> * **Important** This was mistakenly omitted from the "Implementation
>   Details" section of the design, but it is specified elsewhere in the
>   design and has not been implemented here:
>
>   > Reset the `mtime` of the limboed file to the current time.
>
>   Without this, hard-deletions will be due immediately whenever the
>   limbo period is less than the soft-delete period.

This is fine (`bin/sandman/sweep.py:L288-299`).

### Vault File Consistency Checks

> The `VaultFile` implementation checks for basic consistency on
> construction by [checking the number of hard
> links](https://github.com/wtsi-hgi/hgi-vault/blob/9ad9cc78509d0bcaa91e95ba72c884772eb21327/api/vault/file.py#L76-L88).
> The new "recover" action will break this assumption, so it's possible
> -- if not highly likely -- that the new functionality will run afoul
> of this. As far as I can see, your code is only using `VaultFileKey`,
> so _may_ be immune; however, other code may not be so lucky. I would
> recommend amending this consistency check to allow for single hard
> links in the limbo branch.

The implementation in `api/vault/file.py:L76-92` is fine, but the
introductory comment no longer matches (it omits the new condition).
Could you please update this?

### Updated `usage.py` for Vault

You've changed this to be very explicit, rather than using abstractions
to do the work for you. Given the context, I think this is fine. The
actions that are available may diverge more in the future and your
refactor has made that event easier to deal with. *I haven't gone
through your logic with close scrutiny, so I only assume it's all OK.*

Note, however, that this code is redundant (`bin/vault/usage.py:L167-168`):

```python
if parsed.action == "remove":
    pass
```

If it's there to serve as a signpost that there's a `remove` action and
that it hasn't been forgotten (because it doesn't have any special
control flow), then better to do this with a comment than executable
code.

(n.b., Also, "simultaneously" is spelt incorrectly, on L162.)
