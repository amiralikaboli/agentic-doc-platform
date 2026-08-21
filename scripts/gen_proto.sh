#!/usr/bin/env bash

set -euo pipefail

# Script to generate gRPC Python files from .proto files
# Generates pb2 files into src/generated/ matching the proto package structure
# Usage:
#   ./scripts/gen_proto.sh                    # Generate all .proto files
#   ./scripts/gen_proto.sh <path/to/file.proto>  # Generate specific .proto file

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PROTO_ROOT="$PROJECT_ROOT/proto"
GENERATED_ROOT="$PROJECT_ROOT/src/generated"

# Function to generate a single proto file
generate_proto() {
    local proto_file="$1"
    local proto_dir
    local proto_name
    local grpc_file
    local package_path
    local output_dir

    proto_dir=$(dirname "$proto_file")
    proto_name=$(basename "$proto_file" .proto)

    # Extract relative path from proto root (e.g., retrieval/v1)
    package_path="${proto_dir#$PROTO_ROOT/}"
    
    # Output directory: src/generated/retrieval/v1
    output_dir="$GENERATED_ROOT/$package_path"
    
    # Create output directory if it doesn't exist
    mkdir -p "$output_dir"

    echo "Generating pb2 files for $proto_file ..."
    echo "  Output: $output_dir"

    python3 -m grpc_tools.protoc \
        -I "$proto_dir" \
        --python_out="$output_dir" \
        --grpc_python_out="$output_dir" \
        "$proto_file"

    grpc_file="$output_dir/${proto_name}_pb2_grpc.py"
    
    if [[ -f "$grpc_file" ]]; then
        echo "Fixing imports in ${proto_name}_pb2_grpc.py ..."
        # Use sed for portability; handle both Linux and macOS
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|^import ${proto_name}_pb2 as |from . import ${proto_name}_pb2 as |" "$grpc_file" || true
#            sed -i '' "s|^from ${proto_name}|from . from ${proto_name}|g" "$grpc_file" || true
        else
            sed -i "s|^import ${proto_name}_pb2 as |from . import ${proto_name}_pb2 as |" "$grpc_file" || true
#            sed -i "s|^from ${proto_name}|from . from ${proto_name}|g" "$grpc_file" || true
        fi
    fi

    echo "✓ Generated: $proto_file -> $output_dir"
}

# Main logic
if [[ $# -gt 0 && -f "$1" ]]; then
    # Specific proto file provided
    generate_proto "$1"
else
    # Generate all .proto files in proto/ directory (recursive)
    if [[ ! -d "$PROTO_ROOT" ]]; then
        echo "Error: proto/ directory not found at $PROTO_ROOT"
        exit 1
    fi

    # Create generated root if it doesn't exist
    mkdir -p "$GENERATED_ROOT"

    proto_count=0
    while IFS= read -r proto_file; do
        if [[ -f "$proto_file" ]]; then
            generate_proto "$proto_file"
            ((proto_count++))
        fi
    done < <(find "$PROTO_ROOT" -name "*.proto" -type f) || true

    if [[ $proto_count -eq 0 ]]; then
        echo "No .proto files found in $PROTO_ROOT"
        exit 1
    fi

    echo ""
    echo "✓ Done. Generated $proto_count proto file(s) into $GENERATED_ROOT"
fi
