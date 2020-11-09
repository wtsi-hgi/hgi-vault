# Deployment Planning

## Dog Fooding and Hot Fixing

Once the application code is complete, it can be deployed in a sandboxed
environment that contains nothing of value. This environment can be a
duplicated subset of a team/project directory, with modification times
artificially wound forwards and the owners set to current HGI members;
alternatively, random state can be created.

This will allow:

* To uncover any immediate problems in the code (such as syntax errors,
  typos, etc.);
* To uncover any obvious mistakes and/or deviations from expectations
  while running in a controlled way.

The state (as in, the data over which we will be testing) should be
reproducible, such that we can restore a known initial state quickly and
easily.

When this sandboxed environment has passed its usefulness (i.e., when
we're satisfied HGI Vault is working as intended), it should be retired
and HGI Vault should be pointed at the live HGI team directory. All team
members must unanimously agree to this.

## Formal Testing

The above will probably raise issues mostly at the start, before
tapering into a tail. As such, meanwhile, work can continue on writing
formal tests (unit and integration tests) to ensure that the codebase
reaches our certification criteria. Any issue that is uncovered in this
process must be documented as a GitHub issue and, ultimately, resolved.

The unit testing methodology should focus more on behavioural testing.
This should facilitate high coverage, without coupling tests closely to
their respective feature implementations. Integration testing should be
automated -- in the sense that it is defined in code -- but needn't run
on external CI services (such as Travis CI) for simplicity's sake.

## Documentation Writing

Full documentation should be written for both the Vault and Sandman
entry-points. A Sanger-specific quick reference should also be produced
that outlines Vault usage, pitfalls and specifics of the data retention
policy defined in configuration.

## Phased Production Deployment

When all the above are completed, HGI Vault can begin its production
roll out.

### Phase 1: Guinea Pigs

To control for scale, it should be deployed across no more than five
project directories at first. These projects must satisfy:

* Relatively new projects (no more than two years old), which are still
  in active use;
* Small-to-medium in size (say, up to 10TiB).

Note that all groups that fall under the production run must have at
least two, human owners (as well as `mercury`); one of whom *may* be the
PI.

This phase will allow fine-tuning of the specifics of the data retention
policy, while keeping the support/maintenance requirements minimal and
scale controlled if problems arise.

### Phase 2: Team Groups

Team groups (across all volumes) can be added to the production
deployment, piecemeal, allowing for individual group training and
support, at a rate of no more than five groups per month.

Again, groups must have at least two, human owners (as well as
`mercury`); one of whom *must* be the PI.

This phase, once complete, will spread the deployment across the
programme, bringing it to all teams' awareness. This will allow final
tuning of the data retention policy, plus ironing out of any support
issues and proposed enhancements.

### Phase 3: Project Groups

The remaining project groups can now be brought into the production
deployment, piecemeal, at a rate of no more than eight projects per
month. No/minimal additional training or tweaking of the data retention
policy is anticipated in this phase. Groups should be prioritised on
activity and size.

Again, groups must have at least two, human owners (as well as
`mercury`); one of whom *may* be the PI.
