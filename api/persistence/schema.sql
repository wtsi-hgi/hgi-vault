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


commit;
