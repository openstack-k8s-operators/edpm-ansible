##@ Build openstack-ansibleee-runner image
.PHONY: docker-build-ee
docker-build-ee:
	if [ "${EDPM_LOCAL_REPO}" != "" ] ; then \
		cd ansibleee; podman build -t ${EEIMG} . --volume ${EDPM_LOCAL_REPO}:/var/tmp/edpm-ansible:z --build-arg EDPM_LOCAL_REPO=${EDPM_LOCAL_REPO}; \
	else \
		cd ansibleee; podman build -t ${EEIMG} .; \
	fi

## Push openstack-ansible-runner image
.PHONY: docker-push-ee
docker-push-ee:
	cd ansibleee; podman push --tls-verify=${VERIFY_TLS} ${EEIMG}

##@ Deployment

ifndef ignore-not-found
  ignore-not-found = false
endif

.PHONY: install
install: CRDDESC_OVERRIDE=:maxDescLen=0
install: manifests kustomize ## Install CRDs into the K8s cluster specified in ~/.kube/config.
	$(KUSTOMIZE) build config/crd | kubectl apply -f -

.PHONY: uninstall
uninstall: manifests kustomize ## Uninstall CRDs from the K8s cluster specified in ~/.kube/config. Call with ignore-not-found=true to ignore resource not found errors during deletion.
	$(KUSTOMIZE) build config/crd | kubectl delete --ignore-not-found=$(ignore-not-found) -f -

.PHONY: deploy
deploy: CRDDESC_OVERRIDE=:maxDescLen=0
deploy: manifests kustomize ## Deploy controller to the K8s cluster specified in ~/.kube/config.
	cd config/manager && $(KUSTOMIZE) edit set image controller=${IMG}
	$(KUSTOMIZE) build config/default | kubectl apply -f -

.PHONY: undeploy
undeploy: ## Undeploy controller from the K8s cluster specified in ~/.kube/config. Call with ignore-not-found=true to ignore resource not found errors during deletion.
	$(KUSTOMIZE) build config/default | kubectl delete --ignore-not-found=$(ignore-not-found) -f -

##@ Build Dependencies

## Location to install dependencies to
LOCALBIN ?= $(shell pwd)/bin
$(LOCALBIN):
	mkdir -p $(LOCALBIN)

## Tool Binaries
KUSTOMIZE ?= $(LOCALBIN)/kustomize
CONTROLLER_GEN ?= $(LOCALBIN)/controller-gen
ENVTEST ?= $(LOCALBIN)/setup-envtest
CRD_MARKDOWN ?= $(LOCALBIN)/crd-to-markdown

## Tool Versions
KUSTOMIZE_VERSION ?= v3.8.7
CONTROLLER_TOOLS_VERSION ?= v0.10.0
CRD_MARKDOWN_VERSION ?= v0.0.3

KUSTOMIZE_INSTALL_SCRIPT ?= "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh"
.PHONY: kustomize
kustomize: $(KUSTOMIZE) ## Download kustomize locally if necessary.
$(KUSTOMIZE): $(LOCALBIN)
	rm -f $(LOCALBIN)/kustomize || true
	test -s $(LOCALBIN)/kustomize || curl -s $(KUSTOMIZE_INSTALL_SCRIPT) | bash -s -- $(subst v,,$(KUSTOMIZE_VERSION)) $(LOCALBIN)

.PHONY: controller-gen
controller-gen: $(CONTROLLER_GEN) ## Download controller-gen locally if necessary.
$(CONTROLLER_GEN): $(LOCALBIN)
	test -s $(LOCALBIN)/controller-gen || GOBIN=$(LOCALBIN) go install sigs.k8s.io/controller-tools/cmd/controller-gen@$(CONTROLLER_TOOLS_VERSION)

.PHONY: crd-to-markdown
crd-to-markdown: $(CRD_MARKDOWN) ## Download crd-to-markdown locally if necessary.
$(CRD_MARKDOWN): $(LOCALBIN)
	test -s $(LOCALBIN)/crd-to-markdown || GOBIN=$(LOCALBIN) go install github.com/clamoriniere/crd-to-markdown@$(CRD_MARKDOWN_VERSION)

.PHONY: envtest
envtest: $(ENVTEST) ## Download envtest-setup locally if necessary.
$(ENVTEST): $(LOCALBIN)
	test -s $(LOCALBIN)/setup-envtest || GOBIN=$(LOCALBIN) go install sigs.k8s.io/controller-runtime/tools/setup-envtest@latest

.PHONY: bundle
bundle: manifests kustomize ## Generate bundle manifests and metadata, then validate generated files.
	operator-sdk generate kustomize manifests -q
	cd config/manager && $(KUSTOMIZE) edit set image controller=$(IMG)
	$(KUSTOMIZE) build config/manifests | operator-sdk generate bundle $(BUNDLE_GEN_FLAGS)
	operator-sdk bundle validate ./bundle

.PHONY: bundle-build
bundle-build: ## Build the bundle image.
	podman build -f bundle.Dockerfile -t $(BUNDLE_IMG) .

.PHONY: bundle-push
bundle-push: ## Push the bundle image.
	$(MAKE) docker-push IMG=$(BUNDLE_IMG)

.PHONY: opm
OPM = ./bin/opm
opm: ## Download opm locally if necessary.
ifeq (,$(wildcard $(OPM)))
ifeq (,$(shell which opm 2>/dev/null))
	@{ \
	set -e ;\
	mkdir -p $(dir $(OPM)) ;\
	OS=$(shell go env GOOS) && ARCH=$(shell go env GOARCH) && \
	curl -sSLo $(OPM) https://github.com/operator-framework/operator-registry/releases/download/v1.26.0/$${OS}-$${ARCH}-opm ;\
	chmod +x $(OPM) ;\
	}
else
OPM = $(shell which opm)
endif
endif

# A comma-separated list of bundle images (e.g. make catalog-build BUNDLE_IMGS=example.com/operator-bundle:v0.1.0,example.com/operator-bundle:v0.2.0).
# These images MUST exist in a registry and be pull-able.
BUNDLE_IMGS ?= $(BUNDLE_IMG)

# The image tag given to the resulting catalog image (e.g. make catalog-build CATALOG_IMG=example.com/operator-catalog:v0.2.0).
CATALOG_IMG ?= $(IMAGE_TAG_BASE)-index:v$(VERSION)

# Set CATALOG_BASE_IMG to an existing catalog image tag to add $BUNDLE_IMGS to that image.
ifneq ($(origin CATALOG_BASE_IMG), undefined)
FROM_INDEX_OPT := --from-index $(CATALOG_BASE_IMG)
endif

# Build a catalog image by adding bundle images to an empty catalog using the operator package manager tool, 'opm'.
# This recipe invokes 'opm' in 'semver' bundle add mode. For more information on add modes, see:
# https://github.com/operator-framework/community-operators/blob/7f1438c/docs/packaging-operator.md#updating-your-existing-operator
.PHONY: catalog-build
catalog-build: opm ## Build a catalog image.
	$(OPM) index add --container-tool podman --mode semver --tag $(CATALOG_IMG) --bundles $(BUNDLE_IMGS) $(FROM_INDEX_OPT)

# Push the catalog image.
.PHONY: catalog-push
catalog-push: ## Push a catalog image.
	$(MAKE) docker-push IMG=$(CATALOG_IMG)

# CI tools repo for running tests
CI_TOOLS_REPO := https://github.com/openstack-k8s-operators/openstack-k8s-operators-ci
CI_TOOLS_REPO_DIR = $(shell pwd)/CI_TOOLS_REPO
.PHONY: get-ci-tools
get-ci-tools:
	if [ -d  "$(CI_TOOLS_REPO_DIR)" ]; then \
		echo "Ci tools exists"; \
		pushd "$(CI_TOOLS_REPO_DIR)"; \
		git pull --rebase; \
		popd; \
	else \
		git clone $(CI_TOOLS_REPO) "$(CI_TOOLS_REPO_DIR)"; \
	fi

# Run go fmt against code
gofmt: get-ci-tools
	GOWORK=off $(CI_TOOLS_REPO_DIR)/test-runner/gofmt.sh
	GOWORK=off $(CI_TOOLS_REPO_DIR)/test-runner/gofmt.sh ./api

# Run go vet against code
govet: get-ci-tools
	GOWORK=off $(CI_TOOLS_REPO_DIR)/test-runner/govet.sh
	GOWORK=off $(CI_TOOLS_REPO_DIR)/test-runner/govet.sh ./api

# Run go test against code
gotest: get-ci-tools
	GOWORK=off $(CI_TOOLS_REPO_DIR)/test-runner/gotest.sh
	GOWORK=off $(CI_TOOLS_REPO_DIR)/test-runner/gotest.sh ./api

# Run golangci-lint test against code
golangci: get-ci-tools
	GOWORK=off $(CI_TOOLS_REPO_DIR)/test-runner/golangci.sh
	GOWORK=off $(CI_TOOLS_REPO_DIR)/test-runner/golangci.sh ./api

# Run go lint against code
golint: get-ci-tools
	GOWORK=off PATH=$(GOBIN):$(PATH); $(CI_TOOLS_REPO_DIR)/test-runner/golint.sh
	GOWORK=off PATH=$(GOBIN):$(PATH); $(CI_TOOLS_REPO_DIR)/test-runner/golint.sh ./api

.PHONY: gowork
gowork: ## Generate go.work file to support our multi module repository
	test -f go.work || go work init
	go work use .
	go work use ./api

.PHONY: operator-lint
operator-lint: gowork ## Runs operator-lint
	GOBIN=$(LOCALBIN) go install github.com/gibizer/operator-lint@latest
	go vet -vettool=$(LOCALBIN)/operator-lint ./... ./api/...
