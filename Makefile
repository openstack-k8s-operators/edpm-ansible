TEST_ENV_REPOSITORY := https://github.com/openstack-k8s-operators/ci-framework.git
IMAGE_TAG_BASE ?= quay.io/openstack-k8s-operators/openstack-ansibleee-runner
IMG ?= $(IMAGE_TAG_BASE):latest

ifndef ENV_DIR
override ENV_DIR := $(shell mktemp -d)/ci-framework
endif

.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: setup_test_environment
setup_test_environment: ## Setup the environment
	@if [ ! -d $(ENV_DIR) ]; then \
		git clone $(TEST_ENV_REPOSITORY) $(ENV_DIR); \
	fi
	@if ! podman image exists localhost/cifmw-build; then \
		make -C $(ENV_DIR) ci_ctx; \
	fi

.PHONY: execute_molecule
execute_molecule: ## Execute molecule tests
	podman run --rm -ti --security-opt label=disable \
    	   -v $(ENV_DIR):/opt/sources \
    	   -v .:/opt/edpm-ansible \
    	   cifmw-build:latest bash -c "cd /opt/sources/ && make molecule \
		   							BUILD_VENV_CTX=no \
									MOLECULE_CONFIG=.config/molecule/config_local.yml \
									ROLE_DIR=/opt/edpm-ansible/roles/ \
									TEST_ALL_ROLES=yes"

.PHONY: execute_molecule_tests ## Setup the environment and execute molecule tests
execute_molecule_tests: setup_test_environment execute_molecule

.PHONY: openstack_ansibleee_build ## Build the openstack-ansibleee-runner image
openstack_ansibleee_build:
	podman build . -f openstack_ansibleee/Dockerfile -t ${IMG}

.PHONY: openstack_ansibleee_push ## Push the openstack-ansibleee-runner image
openstack_ansibleee_push:
	podman push ${IMG}
