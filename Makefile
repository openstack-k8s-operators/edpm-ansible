TEST_ENV_REPOSITORY := https://github.com/openstack-k8s-operators/ci-framework.git
IMAGE_TAG_BASE ?= quay.io/openstack-k8s-operators/openstack-ansibleee-runner
IMG ?= $(IMAGE_TAG_BASE):latest

ifndef ENV_DIR
override ENV_DIR := $(shell mktemp -d)/ci-framework
endif

TEST_VERBOSITY := '-vvv'

.PHONY: help
help: ## Display this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: setup_test_environment
setup_test_environment: ## Setup the test environment
	@if [ ! -d $(ENV_DIR) ]; then \
		git clone $(TEST_ENV_REPOSITORY) $(ENV_DIR); \
	fi
	@if ! podman image exists localhost/cifmw; then \
		make -C $(ENV_DIR) ci_ctx; \
	fi

.PHONY: execute_molecule
execute_molecule: setup_test_environment ## Setup the test environment and execute molecule tests
	podman run --rm -ti --security-opt label=disable \
		-v $(ENV_DIR):/opt/ci_framework \
		-v .:/opt/edpm-ansible \
		-e ANSIBLE_LOCAL_TMP=/tmp \
		-e ANSIBLE_REMOTE_TMP=/tmp \
		-e HOME=/tmp \
		-e MOLECULE_CONFIG=.config/molecule/config_local.yml \
		-e TEST_ALL_ROLES=yes \
		-e TEST_VERBOSITY=$(TEST_VERBOSITY) \
		--user root \
		cifmw:latest bash -c "/opt/ci_framework/scripts/run_molecule \
		/opt/edpm-ansible/roles/"

.PHONY: openstack_ansibleee_build
openstack_ansibleee_build: ## Build the openstack-ansibleee-runner image
	podman build . -f openstack_ansibleee/Dockerfile -t ${IMG}

.PHONY: openstack_ansibleee_push
openstack_ansibleee_push: ## Push the openstack-ansibleee-runner image
	podman push ${IMG}

.PHONY: linters
linters: ## Execute pre-commit linters
	pre-commit run -a

.PHONY: html_docs
html_docs: ## build HTML docs
	docs/build-docs.sh
