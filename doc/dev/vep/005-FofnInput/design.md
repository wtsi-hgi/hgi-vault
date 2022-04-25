# Vault Enhancement Proposal 5: Fofn Input

## Current Behaviour

_Originally defined in the [design document](/doc/dev/design.md)._

A file is added to a branch  of a vault (`keep` or `archive` or `stash`) or recovered from `limbo` branch or untracked using the following command:

    vault ACTION FILE(s)..

where ACTION could be `keep` or `archive` or `archive --stash` or `recover` or `untrack`.


The FILE(s) argument must satisfy the following:

* At least one file path must be passed.
* The number of paths in the list can be at most 10 if ACTION is `keep` or `archive`
* The paths can be either relative to the current working directory or absolute. 
* The files in the paths should be regular files (i.e. they cannot be directories or symlinks). 
* Users are advised to be mindful of what they annotate and do it explicitly. While passing a glob file pattern as an argument is allowed, however, if the glob evaluates to more than 10 files the annotation will fail as the number of paths in the list are limited to 10 (`keep` or `archive`)



## Proposed Behaviour


This work should be done in `feature/fofn-input` branch.

In all those instances where vault takes as input a filepath (or a list of file paths), it will take an additional, optional flag  `--fofn` that will take a fofn filepath as argument.

Example:

```
vault keep --help
                | --view [CONTEXT] [--absolute]
                | FILE [FILE(s)...] 
                | --fofn FOFN          
```

```
vault archive --help
                | --view [CONTEXT] [--absolute]
                | --view-staged [CONTEXT] [--absolute]
                | [--stash] FILE [FILE(s)...] 
                | [--stash]  --fofn FOFN       
```

```
vault recover --help
                | --view  [CONTEXT] [--absolute] 
                | --all 
                | FILE [FILE(s)...]    
                | --fofn FOFN      
```

```
vault untrack --help
                | FILE(s)...  
                | --fofn FOFN
```

