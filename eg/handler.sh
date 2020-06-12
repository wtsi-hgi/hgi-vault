#!/usr/bin/env bash

exec 123>".lock"

if [[ "$1" == "ready" ]]; then
  flock -nx 123
  exit $?
fi

flock -x 123
xargs -0 tar czf "/archive/$(date +%F).tar.gz" --remove-files
