#!/bin/sh
set -eu
# Test-only ephemeral database inside the network-disabled sandbox. No host secrets.
export PGDATA=/tmp/pgdata
export PATH=/usr/lib/postgresql/15/bin:$PATH
initdb -D "$PGDATA" -U sandbox --auth-local=trust --auth-host=reject --no-locale --encoding=UTF8 > /tmp/pg-init.log
pg_ctl -D "$PGDATA" -l /tmp/pg.log -o "-c listen_addresses='' -c unix_socket_directories=/tmp -c shared_buffers=16MB -c max_connections=12 -c fsync=on" -w start
createdb -h /tmp -U sandbox projectforge_test
export DATABASE_URL='postgresql+psycopg://sandbox@/projectforge_test?host=/tmp'
exec /opt/entrypoint.sh "$@"
