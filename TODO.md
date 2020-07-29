# To Do

Time estimates for pending work are approximate, based on one developer,
uninterrupted. Actual times will be added when available.

* [ ] Core
  * [x] File interface
  * [x] Logging abstractions and interface
  * [x] Time interface
  * [x] Typing interface
  * [ ] Utilities
    * [x] `base64` interface
    * [x] umask context manager
    * [ ] *Others?*
  * [x] Vault abstractions
  * [x] IdM abstractions
  * [x] Configuration abstractions and interface      <ETA: 2 days; Actual: 1 day>
  * [ ] Persistence abstractions and interface        <ETA: 2 days>
  * [ ] E-mailing and templating abstractions         <ETA: 3 days>
  * [ ] *Others?*
* [ ] API
  * [x] Logging
  * [x] Vault
  * [x] IdM (LDAP)                                    <ETA: 3 days; Actual: 2 days>
  * [x] Configuration parsing (YAML)                  <ETA: 2 days; Actual: 1 day>
  * [ ] Schema design and persistence engine          <ETA: 5 days>
  * [ ] E-Mail and templating                         <ETA: 3 days>
  * [ ] *Others?*
* [ ] Hot code
  * [ ] *Unknown*                                     <ETA: 1 day per function>
* [ ] Executables and setup
  * [x] `vault`                                       <ETA: 2 days; Actual: 2 days>
  * [ ] `sandman`
    * [ ] Plumbing                                    <ETA: 2 days>
    * [ ] Sweep phase                                 <ETA: 3 days>
    * [ ] Drain phase                                 <ETA: 2 days>
  * [ ] `setup.py`                                    <ETA: 1 day>
* [ ] Tests
  * [ ] Automated testing and certification           <ETA: *Unknown*>
  * [ ] Unit testing
    * [ ] Core                                        <ETA: 1 day per module>
    * [ ] API                                         <ETA: 3 days per module>
    * [ ] Hot code                                    <ETA: 1 day per function>
    * [ ] Executables                                 <ETA: 2 days per executable>
  * [ ] Integration testing
    * [ ] LDAP                                        <ETA: 2 days>
    * [ ] E-mail                                      <ETA: 2 days>
    * [ ] PostgreSQL                                  <ETA: 2 days>
  * [ ] User acceptance testing                       <ETA: *Unknown*>
* [ ] Documentation
  * [ ] Core and API                                  <ETA: 1 day per module pair>
  * [ ] Executables                                   <ETA: 1 day per executable>
