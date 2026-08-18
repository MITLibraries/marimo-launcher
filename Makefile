SHELL=/bin/bash
DATETIME:=$(shell date -u +%Y%m%dT%H%M%SZ)
### This is the Terraform-generated header for marimo-launcher-dev.     ###
ECR_NAME_DEV := marimo-launcher-dev
ECR_URL_DEV := 222053980223.dkr.ecr.us-east-1.amazonaws.com/marimo-launcher-dev
CPU_ARCH ?= $(shell cat .aws-architecture 2>/dev/null || echo "linux/amd64")
### End of Terraform-generated header                                   ###

CPU_ARCH ?= $(shell cat .aws-architecture 2>/dev/null || echo "linux/amd64")

help: # Preview Makefile commands
	@awk 'BEGIN { FS = ":.*#"; print "Usage:  make <target>\n\nTargets:" } \
/^[-_[:alpha:]]+:.?*#/ { printf "  %-15s%s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# ensure OS binaries aren't called if naming conflict with Make recipes
.PHONY: help dist-dev publish-dev dist-stage publish-stage venv install update test coveralls lint lint-fix security check-arch docker-clean marimo-launcher mypy ruff

##############################################
# Python Environment and Dependency commands
##############################################

install: .venv .git/hooks/pre-commit .git/hooks/pre-push # Install Python dependencies and create virtual environment if not exists
	uv sync --dev

.venv: # Creates virtual environment if not found
	@echo "Creating virtual environment at .venv..."
	uv venv .venv

.git/hooks/pre-commit: # Sets up pre-commit commit hooks if not setup
	@echo "Installing pre-commit commit hooks..."
	uv run pre-commit install --hook-type pre-commit

.git/hooks/pre-push: # Sets up pre-commit push hooks if not setup
	@echo "Installing pre-commit push hooks..."
	uv run pre-commit install --hook-type pre-push

venv: .venv # Create the Python virtual environment

update: # Update Python dependencies
	uv lock --upgrade
	uv sync --dev

######################
# Unit test commands
######################

test: # Run tests and print a coverage report
	uv run coverage run --source=launcher -m pytest -vv
	uv run coverage report -m

coveralls: test # Write coverage data to an LCOV report
	uv run coverage lcov -o ./coverage/lcov.info

####################################
# Code linting and formatting
####################################

lint: # Run linting, alerts only, no code changes
	uv run ruff format --diff
	uv run mypy .
	uv run ruff check .

lint-fix: # Run linting, auto fix behaviors where supported
	uv run ruff format .
	uv run ruff check --fix .

mypy: # Run 'mypy' type checker
	uv run mypy .

ruff: # Run 'ruff' linter and print a preview of errors
	uv run ruff check .

security: # Run security / vulnerability checks
	uv run pip-audit


####################################
# CLI
####################################
marimo-launcher: # CLI without any arguments, utilizing uv script entrypoint
	uv run marimo-launcher

cli-test-inline-run:
	uv run marimo-launcher \
    run \
    --mount=tests/fixtures/inline_deps

cli-test-reqs-txt-run:
	uv run marimo-launcher \
    run \
    --mount=tests/fixtures/static_deps_reqs_txt \
    --requirements=requirements.txt

cli-test-token-authenticated:
	uv run marimo-launcher \
    run \
    --mount=tests/fixtures/inline_deps \
    --token="iamsecret"

####################################
# Docker
####################################
docker-build: # Build local image for testing
	docker build -t marimo-launcher:latest .

docker-shell: # Shell into local container for testing
	docker run -it --entrypoint='bash' marimo-launcher:latest

docker-test-run: # Test local docker container with test fixture notebook
	docker run \
	-p "2718:2718" \
	-v "$(CURDIR)/tests/fixtures:/tmp/fixtures" \
	-e NOTEBOOK_MOUNT="/tmp/fixtures/inline_deps" \
	marimo-launcher:latest

####################################
# Terraform
####################################

### Terraform-generated Developer Deploy Commands for Dev environment           ###
check-arch: # Validate CPU_ARCH and write .arch_tag
	@if [[ "$(CPU_ARCH)" != "linux/amd64" && "$(CPU_ARCH)" != "linux/arm64" ]]; then \
		echo "Invalid CPU_ARCH: $(CPU_ARCH)"; exit 1; \
	fi; \
	if [[ -f .aws-architecture ]]; then \
		echo "latest-$$(echo $(CPU_ARCH) | cut -d'/' -f2)" > .arch_tag; \
	else \
		echo "latest" > .arch_tag; \
	fi

dist-dev: check-arch ## Build docker container (intended for developer-based manual build)
	docker buildx inspect $(ECR_NAME_DEV) >/dev/null 2>&1 || docker buildx create --name $(ECR_NAME_DEV) --use
	docker buildx use $(ECR_NAME_DEV)
	docker buildx build --platform $(CPU_ARCH) \
		--load \
		-t $(ECR_URL_DEV):latest \
		-t $(ECR_URL_DEV):`git describe --always` \
		-t $(ECR_NAME_DEV):latest .

publish-dev: dist-dev ## Build, tag and push (intended for developer-based manual publish)
	aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $(ECR_URL_DEV)
	docker push $(ECR_URL_DEV):latest
	docker push $(ECR_URL_DEV):`git describe --always`

### Terraform-generated manual shortcuts for deploying to Stage. This requires  ###
###   that ECR_NAME_STAGE, ECR_URL_STAGE, and FUNCTION_STAGE environment        ###
###   variables are set locally by the developer and that the developer has     ###
###   authenticated to the correct AWS Account. The values for the environment  ###
###   variables can be found in the stage_build.yml caller workflow.            ###
dist-stage: ## Only use in an emergency
	docker buildx build --platform $(CPU_ARCH) \
		--load \
	    -t $(ECR_URL_STAGE):latest \
		-t $(ECR_URL_STAGE):`git describe --always` \
		-t $(ECR_NAME_STAGE):latest .

publish-stage: ## Only use in an emergency
	aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $(ECR_URL_STAGE)
	docker push $(ECR_URL_STAGE):latest
	docker push $(ECR_URL_STAGE):`git describe --always`

docker-clean: # Clean up Docker detritus
	docker rmi -f $(ECR_URL_DEV):latest || true
	docker rmi -f $(ECR_URL_DEV):`git describe --always` || true
	docker rmi -f $(ECR_NAME_DEV):latest || true
	docker buildx rm $(ECR_NAME_DEV) || true
	@rm -rf .arch_tag
