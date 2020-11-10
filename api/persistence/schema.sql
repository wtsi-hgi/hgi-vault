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
  schema date := timestamp '2020-11-10';
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
-- NOTE Records in this table must NEVER be updated; if a change is
-- required, then the record MUST be deleted and reinserted
create table if not exists files (
  id
    serial
    primary key,

  device
    numeric
    not null,

  inode
    numeric
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

  unique (id, state)
);

create index if not exists status_file      on status(file);
create index if not exists status_state     on status(state);
create index if not exists status_timestamp on status(timestamp);

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


-- Notifications
create table if not exists notifications (
  status
    integer
    references status(id) on delete cascade,

  stakeholder
    integer
    not null,

  primary key (status, stakeholder)
);


-- File Stakeholders: A view of all stakeholders for the current files
create or replace view file_stakeholders as
  select id as file,
         owner as stakeholder
  from   files

  union

  select files.id as file,
         group_owners.owner as stakeholder
  from   files
  join   group_owners
  on     group_owners.gid = files.group_id;


-- Stakeholders: A view of all stakeholders
create or replace view stakeholders as
  select distinct stakeholder from file_stakeholders;


-- Stakeholder Notification State: A view of file status notifications
-- by stakeholder
create or replace view stakeholder_notified as
  select    status.*,
            file_stakeholders.stakeholder,
            notifications.status is not null as notified
  from      status
  join      file_stakeholders
  on        file_stakeholders.file    = status.file
  left join notifications
  on        notifications.status      = status.id
  and       notifications.stakeholder = file_stakeholders.stakeholder;


-- General Notification State: A view of file status notifications
-- FIXME? This query seems inelegant; there must be a better way...
create or replace view status_notified as
  select   id, file, state, timestamp,
           every(notified) as notified
  from     stakeholder_notified
  group by id, file, state, timestamp; -- PG can't infer that id is the PK


-- Clean orphaned states: When a file has been deleted, clear up any
-- other, now redundant states to avoid erroneous notifications
with orphaned as (
  select distinct nondeleted.id
  from   status as nondeleted
  join   status_notified as deleted
  on     deleted.file = nondeleted.file
  where  nondeleted.state = 'deleted'
  and    deleted.state   != 'deleted'
)
delete
from   status
using  orphaned
where  status.id = orphaned.id;


-- Clean fully notified, deleted files and expired states
with expired as (
  -- Non-staged files that have been notified, but have expired
  select   file
  from     status_notified
  where    state != 'staged'
  and      notified
  group by file
  having   every(age(now(), timestamp) > make_interval(days => 90))
),
purgeable as (
  select file
  from   status_notified
  where  state = 'deleted'
  and    notified

  union

  select file
  from   expired
)
delete
from   files
using  purgeable
where  files.id = purgeable.file;


commit;
