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
/* TODO Uncomment this for production **********************************
do $$ declare
  schema date := timestamp '2020-08-04';
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
***********************************************************************/


-- Groups
create table if not exists groups (
  gid
    integer,

  owner
    integer
    not null,

  primary key (gid, owner)
);

create index if not exists groups_gid on groups(gid);
create index if not exists groups_owner on groups(owner);


-- Files
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

  group
    integer
    not null
    references groups(gid),

  size
    numeric
    not null
    check (size >= 0)
);

create index if not exists files_owner on files(owner);


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
         groups.owner as uid
  from   files
  join   groups
  on     groups.gid = files.group;


-- All Stakeholders: A view of all stakeholders
create or replace view stakeholders as
  select distinct uid from file_stakeholders;


commit;
