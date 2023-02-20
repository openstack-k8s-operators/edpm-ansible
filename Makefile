ROLE_LIST := ./edpm_ansible/roles/*

.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: setup_env
setup_env: ## Setup the environment
	bash scripts/setup_env

.PHONY: molecule
molecule: setup_env molecule_nodeps ## Run molecule tests with dependencies install

.PHONY: molecule_nodeps
molecule_nodeps: ## Run molecule without installing dependencies
	for role in ${ROLE_LIST}; do \
		bash scripts/run-local-test "$$(basename $${role})" ; \
	done
