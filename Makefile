TEST_ENV_REPOSITORY := https://github.com/openstack-k8s-operators/ci-framework.git

ifndef ENV_DIR
override ENV_DIR := $(shell mktemp -d)
endif

.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: setup_test_environment
setup_test_environment: ## Setup the environment
	@if [ ! -d $(ENV_DIR) ]; then \
		git clone $(TEST_ENV_REPOSITORY) $(ENV_DIR); \
	fi
	@if ! podman image exists localhost/cfwm; then \
		make -C $(ENV_DIR) ci_ctx; \
	fi

.PHONY: execute_molecule
execute_molecule: ## Execute molecule tests
	podman run --rm -ti --security-opt label=disable \
    	   -v $(ENV_DIR):/opt/sources \
    	   -v .:/opt/edpm-ansible \
    	   cfwm:latest bash -c "make molecule_nodeps \
		   							BUILD_VENV_CTX=no \
									MOLECULE_CONFIG=.config/molecule/config_local.yml \
									ROLE_DIR=/opt/edpm-ansible/edpm_ansible/roles/ \
									TEST_ALL_ROLES=yes"

.PHONY: execute_molecule_tests ## Setup the environment and execute molecule tests
execute_molecule_tests: setup_test_environment execute_molecule
