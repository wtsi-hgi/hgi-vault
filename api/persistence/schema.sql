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
  schema date := timestamp '2020-08-10';
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
    references groups(gid),

  owner
    integer
    not null,

  primary key (gid, owner)
);

create index if not exists group_owners_gid   on group_owners(gid);
create index if not exists group_owners_owner on group_owners(owner);


-- Files (inode, plus the minimal set of metadata that we care about)
create table if not exists files (
  inode
    integer
    primary key,

  path
    text
    not null,

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
    check (size >= 0)
);

create index if not exists files_owner on files(owner);

-- TODO (if possible) A suite of rules/triggers on `files` that:
-- [x] Prevents updates
-- [ ] On insert:
--     * Inserts on no matching inode
--     * Does nothing on complete matching record
--     * Deletes then inserts on matching inode

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

  inode
    integer
    not null
    references files(inode) on delete cascade,

  state
    state
    not null,

  notified
    boolean
    not null
    default false,

  unique (id, state)
);

create index if not exists status_inode    on status(inode);
create index if not exists status_state    on status(state);
create index if not exists status_notified on status(notified);

create table if not exists warnings (
  status
    integer
    primary key
    references status(id) on delete cascade,

  -- This is a dummy field that MUST be set to `warned` to ensure it
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


-- File Stakeholders: A view of all stakeholders of a file (i.e., the
-- file owner and its group owners)
create or replace view file_stakeholders as
  select files.inode,
         files.owner as uid
  from   files

  -- "Union" (rather than "union all") because files may be owned by
  -- group owners and we don't want duplicates
  union

  select files.inode,
         group_owners.owner as uid
  from   files
  join   group_owners
  on     group_owners.gid = files.group_id;


-- All Stakeholders: A view of all stakeholders
create or replace view stakeholders as
  select distinct uid from file_stakeholders;


-- Warnings: A view of warned files with their status
create or replace view file_warnings as
  select status.inode,
         warning.tminus,
         status.notified
  from   status
  join   warnings
  on     warnings.status = status.id
  where  status.state = 'warned';


-- Clean any notified, deleted files
-- TODO Also delete warnings for deleted files
delete
from   files
using  status
where  files.inode  = status.inode
and    status.state = 'deleted'
and    status.notified;


commit;
