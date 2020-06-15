#!/usr/bin/env bash

exec 123>.lock
flock -nx 123
locked=$?

case $1 in
  ready)  exit ${locked};;
  *)      (( locked )) && exit 1;;
esac

xargs -0 tar czf "/archive/$(date +%F).tar.gz" --remove-files
