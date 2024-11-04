#!/bin/bash
set -e

# Ensure we're using a login shell to activate conda
exec /bin/bash --login -c "$*"
