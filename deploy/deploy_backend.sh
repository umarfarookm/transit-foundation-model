#!/bin/bash
# Deploy UmarTransit-1B API to HuggingFace Spaces
#
# Prerequisites:
#   1. huggingface-cli login (run once)
#   2. pip install huggingface-hub
#
# Usage:
#   bash deploy/deploy_backend.sh

set -e

SPACE_ID="umarfarookm/umartransit-api"
SPACE_DIR="deploy/hf-space"

echo "=== Deploying UmarTransit-1B API to HuggingFace Spaces ==="
echo "Space: https://huggingface.co/spaces/${SPACE_ID}"
echo ""

# Create the Space if it doesn't exist
echo "Creating Space (if needed)..."
python3 -c "
from huggingface_hub import HfApi
api = HfApi()
try:
    api.create_repo('${SPACE_ID}', repo_type='space', space_sdk='docker', private=False)
    print('Space created!')
except Exception as e:
    if 'already exists' in str(e).lower() or '409' in str(e):
        print('Space already exists, updating...')
    else:
        raise e
"

# Upload all files
echo "Uploading files..."
python3 -c "
from huggingface_hub import HfApi
api = HfApi()
api.upload_folder(
    folder_path='${SPACE_DIR}',
    repo_id='${SPACE_ID}',
    repo_type='space',
)
print('Files uploaded!')
"

echo ""
echo "=== Deployment started! ==="
echo "The Space will build and start automatically."
echo "Monitor at: https://huggingface.co/spaces/${SPACE_ID}"
echo ""
echo "Once running, the API will be at:"
echo "  https://${SPACE_ID/\//-}.hf.space/api/chat"
