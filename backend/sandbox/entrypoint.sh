#!/bin/sh
set -eu
cp -R /source /tmp/workspace
chmod -R u+w /tmp/workspace
if [ -d /tmp/workspace/frontend ]; then
    ln -s /opt/frontend/node_modules /tmp/workspace/frontend/node_modules
fi
cd /tmp/workspace
exec "$@"
