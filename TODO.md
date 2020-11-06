# To Do

Time estimates for pending work are approximate, based on one developer,
uninterrupted. Actual times will be added when available and based on
time spent (rather than wall time).

* [x] Core
  * [x] File interface
  * [x] Logging abstractions and interface
  * [x] Time interface
  * [x] Typing interface
  * [x] Utilities
    * [x] `base64` interface
    * [x] umask context manager
    * [x] Human size
    * [x] Human time
  * [x] Vault abstractions
  * [x] IdM abstractions
  * [x] Configuration abstractions and interface      <ETA: 2 days; Actual: 1 day>
  * [x] Persistence abstractions and interface        <ETA: 2 days; Actual: 2 days>
  * [x] E-mailing and templating abstractions         <ETA: 3 days; Actual: 1 day>
* [x] API
  * [x] Logging
  * [x] Vault
  * [x] IdM (LDAP)                                    <ETA: 3 days; Actual: 2 days>
  * [x] Configuration parsing (YAML)                  <ETA: 2 days; Actual: 1 day>
  * [x] Schema design and persistence engine
    * [x] Schema implementation                       <ETA: 2 days; Actual: 4 days>
    * [x] Model implementation                        <ETA: 1 day; Actual: 4 days>
    * [x] Database engine                             <ETA: 3 days; Actual: 3 days>
  * [x] E-Mail and templating                         <ETA: 3 days; Actual 2 days>
* [ ] Hot code
  * [ ] `can_delete`                                  <ETA: less than 1 day>
    * [x] Chris
    * [x] Aiden
    * [ ] Piyush
    * [x] Guillaume
    * [ ] *Others?*
* [ ] Executables and setup
  * [x] `vault`                                       <ETA: 2 days; Actual: 2 days>
  * [x] `sandman`
    * [x] Plumbing                                    <ETA: 2 days; Actual: 3 days>
    * [x] Sweep phase                                 <ETA: 3 days; Actual: 3 days>
    * [x] Drain phase                                 <ETA: 2 days; Actual: 1 day>
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
