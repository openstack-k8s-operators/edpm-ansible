#!/bin/bash

set -e

# Default values
IMAGE_NAME="combined-ansibleee-runner"
IMAGE_TAG="18.0.9"
REGISTRY=""
PUSH=false

# Help message
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Build and optionally push the combined-ansibleee-runner container image.

OPTIONS:
    -r, --registry REGISTRY    Registry URL (e.g., 10.30.9.74:8787/osp18)
    -t, --tag TAG             Image tag (default: $IMAGE_TAG)
    -n, --name NAME           Image name (default: $IMAGE_NAME)
    -p, --push                Push image after build
    -h, --help                Show this help message

EXAMPLES:
    # Build only
    $0 -r 10.30.9.74:8787/osp18 -t 18.0.9

    # Build and push
    $0 -r 10.30.9.74:8787/osp18 -t 18.0.9 --push

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--registry)
            REGISTRY="$2"
            shift 2
            ;;
        -t|--tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        -n|--name)
            IMAGE_NAME="$2"
            shift 2
            ;;
        -p|--push)
            PUSH=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Construct full image name
if [ -n "$REGISTRY" ]; then
    FULL_IMAGE_NAME="${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
else
    FULL_IMAGE_NAME="${IMAGE_NAME}:${IMAGE_TAG}"
fi

# Get the repository root (3 levels up from DeploymentInstructions)
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "============================================"
echo "Build Configuration:"
echo "============================================"
echo "Repository root: $REPO_ROOT"
echo "Image name:      $FULL_IMAGE_NAME"
echo "Push to registry: $PUSH"
echo "============================================"
echo ""

# Create Containerfile in repo root
CONTAINERFILE="$REPO_ROOT/Containerfile"
echo "Creating Containerfile at repo root..."
cat > "$CONTAINERFILE" << 'EOF'
FROM quay.io/openstack-k8s-operators/openstack-ansibleee-runner:latest
COPY roles/edpm_lldp /usr/share/ansible/roles/edpm_lldp
COPY roles/edpm_neutron_opflex_agent /usr/share/ansible/roles/edpm_neutron_opflex_agent
COPY roles/edpm_cisco_opflex_agent /usr/share/ansible/roles/edpm_cisco_opflex_agent
COPY playbooks/lldp.yml /usr/share/ansible/collections/ansible_collections/osp/edpm/playbooks/
COPY playbooks/neutron_opflex_agent.yml /usr/share/ansible/collections/ansible_collections/osp/edpm/playbooks/
COPY playbooks/opflex_agent.yml /usr/share/ansible/collections/ansible_collections/osp/edpm/playbooks/
EOF

# Build container from repo root
echo "Building container image: $FULL_IMAGE_NAME"
echo "============================================"
cd "$REPO_ROOT"
podman build -t "$FULL_IMAGE_NAME" -f "$CONTAINERFILE" .

# Push if requested
if [ "$PUSH" = true ]; then
    echo ""
    echo "Pushing container image: $FULL_IMAGE_NAME"
    echo "============================================"
    podman push "$FULL_IMAGE_NAME"
    echo ""
    echo "Image successfully pushed!"
else
    echo ""
    echo "Build complete! Image not pushed (use --push to push)."
fi

echo ""
echo "============================================"
echo "Summary:"
echo "============================================"
echo "Image: $FULL_IMAGE_NAME"
if [ "$PUSH" = true ]; then
    echo "Status: Built and pushed successfully"
else
    echo "Status: Built successfully (not pushed)"
    echo ""
    echo "To push the image, run:"
    echo "  podman push $FULL_IMAGE_NAME"
    echo ""
    echo "Or rebuild with --push flag:"
    if [ -n "$REGISTRY" ]; then
        echo "  $0 -r $REGISTRY -t $IMAGE_TAG --push"
    else
        echo "  $0 -t $IMAGE_TAG --push"
    fi
fi
echo "============================================"
