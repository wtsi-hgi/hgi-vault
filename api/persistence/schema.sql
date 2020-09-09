/***********************************************************************
Copyright (c) 2020 Genome Research Limited

Author: Christopher Harrison <ch12@sanger.ac.uk>

This program is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or (at your
option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
Public License for more details.

You should have received a copy of the GNU General Public License along
with this program. If not, see https://www.gnu.org/licenses/
***********************************************************************/

begin transaction;


             /*********************************************
             * NOTE This schema script MUST be idempotent *
             *********************************************/


-- Schema versioning
do $$ declare
  schema date := timestamp '2020-09-08';
  actual date;
begin
  create table if not exists __version__ (version date primary key);
  select version into actual from __version__;

  if not found then
    insert into __version__ values (schema);
    actual := schema;
  end if;

  if actual != schema then
    raise exception 'Schema mismatch! Expected %; got %', schema, actual;
  end if;
end $$;


-- Groups
-- NOTE "groups" only exists to uniquely satisfy the many-to-many
-- relationship between "files" and "group_owners".
create table if not exists groups (
  gid
    integer
    primary key
);

create table if not exists group_owners (
  gid
    integer
    not null
    references groups(gid) on delete cascade,

  owner
    integer
    not null,

  primary key (gid, owner)
);

create index if not exists group_owners_gid   on group_owners(gid);
create index if not exists group_owners_owner on group_owners(owner);


-- Files (the minimal set of metadata that we care about)
create table if not exists files (
  id
    serial
    primary key,

  device
    integer
    not null,

  inode
    integer
    not null,

  -- Source file path
  path
    text
    not null,

  -- Vault file path (can be null)
  key
    text,

  mtime
    timestamp with time zone
    not null,

  owner
    integer
    not null,

  group_id
    integer
    not null
    references groups(gid),

  size
    numeric
    not null
    check (size >= 0),

  unique (device, inode)
);

create index if not exists files_owner on files(owner);

-- TODO (if possible) A suite of rules/triggers on "files" that:
-- [x] Prevents updates
-- [ ] On insert:
--     * Inserts on no matching device-inode
--     * Does nothing on complete matching record
--     * Deletes then inserts on matching device-inode

create or replace rule no_update as
  on update to files
  do instead nothing;


-- File Status
do $$ begin
  create type state as enum ('deleted', 'staged', 'warned');
  exception
    when duplicate_object then null;
end $$;

create table if not exists status (
  id
    serial
    primary key,

  file
    integer
    not null
    references files(id) on delete cascade,

  state
    state
    not null,

  timestamp
    timestamp with time zone
    not null
    default now(),

  notified
    boolean
    not null
    default false,

  unique (id, state)
);

create index if not exists status_file      on status(file);
create index if not exists status_state     on status(state);
create index if not exists status_timestamp on status(timestamp);
create index if not exists status_notified  on status(notified);

create table if not exists warnings (
  status
    integer
    primary key
    references status(id) on delete cascade,

  -- This is a dummy field that MUST be set to "warned" to ensure it
  -- only refers to warning status records
  state
    state
    default 'warned'
    check (state = 'warned'),

  tminus
    interval hour
    not null,

  foreign key (status, state) references status(id, state)
);


-- File Stakeholders: A view of all stakeholders for the current files
create or replace view file_stakeholders as
  select id as file,
         owner as uid
  from   files

  union

  select files.id as file,
         group_owners.owner as uid
  from   files
  join   group_owners
  on     group_owners.gid = files.group_id;

-- Stakeholders: A view of all stakeholders
create or replace view stakeholders as
  select distinct uid from file_stakeholders;


-- Clean any orphaned and notified, deleted files
with deleted as (
  select file,
         notified
  from   status
  where  state = 'deleted'
),
orphaned as (
  -- Staged/warned files that are deleted, regardless of notification
  -- NOTE Staged files should never be in here
  select distinct nondeleted.file
  from   status as nondeleted
  join   deleted
  on     deleted.file = nondeleted.file
  where  nondeleted.state != 'deleted'
),
expired as (
  -- Non-staged files that have been notified, but have expired
  select distinct file
  from   status
  where  state != 'staged'
  and    age(now(), timestamp) > make_interval(days => 30)
  and    notified
),
purgeable as (
  select file from orphaned
  union
  select file from deleted where notified
  union
  select file from expired
)
delete
from   files
using  purgeable
where  files.id = purgeable.file;


commit;
vacuum;
