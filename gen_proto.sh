#!/usr/bin/env bash

set -euo pipefail

PROTO_FILEPATH="${1:-}"

PROTO_DIR=$(dirname "$PROTO_FILEPATH")
PROTO_NAME=$(basename "$PROTO_FILEPATH" .proto)

echo "Generating pb2 files for $PROTO_FILEPATH ..."

python -m grpc_tools.protoc \
  -I "$PROTO_DIR" \
  --python_out="$PROTO_DIR" \
  --grpc_python_out="$PROTO_DIR" \
  "$PROTO_FILEPATH"

echo "Fixing imports in ${PROTO_NAME}_pb2_grpc.py ..."

GRPC_FILE="$PROTO_DIR/${PROTO_NAME}_pb2_grpc.py"
perl -pi -e "s|^import (${PROTO_NAME}_pb2) as |from . import \$1 as |" "$GRPC_FILE"

echo "Done."