# HGI Vault

<!-- TODO Change these to the "release" branch when available -->
[![Build Status](https://travis-ci.com/wtsi-hgi/hgi-vault.svg?branch=develop)](https://travis-ci.com/wtsi-hgi/hgi-vault)
[![Coverage Status](https://codecov.io/github/wtsi-hgi/hgi-vault/coverage.svg?branch=develop)](https://codecov.io/github/wtsi-hgi/hgi-vault?branch=develop)

Data retention policy tools.

## Installation

You will need to create an exclusive Python 3.8 (or later) virtual
environment. For example:

    python -m venv .venv
    source .venv/bin/activate

Then, to install HGI Vault:

    pip install git+https://github.com/wtsi-hgi/hgi-vault.git

It is not recommended to install HGI Vault globally or in a shared
virtual environment due to the risk of namespace collision.

## Usage

See the [documentation](/doc) directory for full instructions.
Specifically:

* [End-user documentation](/doc/vault.md)
* [Administrative documentation](/doc/sandman.md)
* [Developer documentation](/doc/dev)
