# VEP001 Review

https://github.com/wtsi-hgi/hgi-vault/compare/4b54cc3...7502a11

## `bin/sandman/sweep.py:L184-191`

This is where you do the hard-delete of limboed files. Limboed files
should only have one hardlink; I think it would be useful to output a
warning logging message if >1 are detected.

## `bin/sandman/sweep.py:L193`

Personally, I feel this should be an `else` clause, rather than a new
`if` statement; which would then need a nested `if` to check number of
hardlinks. Obviously it's semantically identical, but I feel it's easier
to read that way. (I realise this is entirely subjective!)

## `bin/vault/__init__.py:L133,144`

If you use a dictionary comprehension, rather than a list comprehension,
you'll get O(1) lookup -- rather than O(n) -- in your recovery loop.

## `bin/vault/__init__.py:L177-180`

I don't think you want `if` on L177, but `else`. You can replace those
four lines with something like:

  else:
      recover(None if args.all else args.files)

...maybe even terser, depending on those `args.*` values.

There are two other bugs in your `main` function:

1. If you do `recover --view`, `branch` is not declared in the call to
   `view`.
2. The "remove" action will be triggered whenever the action isn't
   "recover". That's not good if you want to keep/archive something.

The correct logic is something like:

```python
def main(argv:T.List[str] = sys.argv) -> None:
    args = usage.parse_args(argv[1:])

    if args.action in ["keep", "archive", "recover"]:
        branch = _action_to_branch[args.action]
        if args.view:
            view(branch)
        else:
            if args.action == "recover":
                recover(None if args.all else args.files)
            else:
                add(branch, args.files)
    else:
        remove(args.files)
```

## `test/bin/sandman/test_sweep.py:TestSweeper`

You are using functions from `os.path` a lot (here and elsewhere).
Again, that's fine, but for consistency with the rest of the code, a lot
of that functionality is available from the
[pathlib library](https://docs.python.org/3.8/library/pathlib.html?#correspondence-to-tools-in-the-os-module),
which we use heavily.

## Copyright Dates that Need Correcting

| File                             | Correct Copyright Dates |
| :------------------------------- | :---------------------- |
| `test/api/test_mail.py`          | 2021                    |
| `test/api/vault/test_vault.py`   | 2020, 2021              |
| `test/bin/sandman/test_sweep.py` | 2021                    |
| `test/bin/sandman/test_walk.py`  | 2021                    |

## Commit Messages that Need Correcting (i.e., to Template)

* `c335ea5`
