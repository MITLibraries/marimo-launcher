SHELL=/bin/bash
DATETIME:=$(shell date -u +%Y%m%dT%H%M%SZ)
### This is the Terraform-generated header for marimo-launcher-dev.     ###
ECR_NAME_DEV:=marimo-launcher-dev
ECR_URL_DEV:=222053980223.dkr.ecr.us-east-1.amazonaws.com/marimo-launcher-dev
### End of Terraform-generated header                                   ###

help: # Preview Makefile commands
	@awk 'BEGIN { FS = ":.*#"; print "Usage:  make <target>\n\nTargets:" } \
/^[-_[:alpha:]]+:.?*#/ { printf "  %-15s%s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# ensure OS binaries aren't called if naming conflict with Make recipes
.PHONY: help dist-dev publish-dev dist-stage publish-stage venv install update test coveralls lint black mypy ruff safety lint-apply black-apply ruff-apply

##############################################
# Python Environment and Dependency commands
##############################################

install: .venv .git/hooks/pre-commit # Install Python dependencies and create virtual environment if not exists
	uv sync --dev

.venv: # Creates virtual environment if not found
	@echo "Creating virtual environment at .venv..."
	uv venv .venv

.git/hooks/pre-commit: # Sets up pre-commit hook if not setup
	@echo "Installing pre-commit hooks..."
	uv run pre-commit install

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
# Code quality and safety commands
####################################

lint: black mypy ruff safety # Run linters

black: # Run 'black' linter and print a preview of suggested changes
	uv run black --check --diff .

mypy: # Run 'mypy' linter
	uv run mypy .

ruff: # Run 'ruff' linter and print a preview of errors
	uv run ruff check .

safety: # Check for security vulnerabilities
	uv run pip-audit

lint-apply: black-apply ruff-apply # Apply changes with 'black' and resolve 'fixable errors' with 'ruff'

black-apply: # Apply changes with 'black'
	uv run black .

ruff-apply: # Resolve 'fixable errors' with 'ruff'
	uv run ruff check --fix .


####################################
# CLI
####################################
cli-test-inline-run:
	uv run python -m launcher.cli \
    run \
    --mount=tests/fixtures/inline_deps

cli-test-reqs-txt-run:
	uv run python -m launcher.cli \
    run \
    --mount=tests/fixtures/static_deps_reqs_txt \
    --requirements=requirements.txt

cli-test-token-authenticated:
	uv run python -m launcher.cli \
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
	-e NOTEBOOK_MOUNT="/tmp/fixtures" \
	-e NOTEBOOK_PATH="helloworld.py" \
	marimo-launcher:latest \
	run

####################################
# Terraform
####################################

### Terraform-generated Developer Deploy Commands for Dev environment           ###
dist-dev: ## Build docker container (intended for developer-based manual build)
	docker build --platform linux/amd64 \
	    -t $(ECR_URL_DEV):latest \
		-t $(ECR_URL_DEV):`git describe --always` \
		-t $(ECR_NAME_DEV):latest .

publish-dev: dist-dev ## Build, tag and push (intended for developer-based manual publish)
	docker login -u AWS -p $$(aws ecr get-login-password --region us-east-1) $(ECR_URL_DEV)
	docker push $(ECR_URL_DEV):latest
	docker push $(ECR_URL_DEV):`git describe --always`

### Terraform-generated manual shortcuts for deploying to Stage. This requires  ###
###   that ECR_NAME_STAGE, ECR_URL_STAGE, and FUNCTION_STAGE environment        ###
###   variables are set locally by the developer and that the developer has     ###
###   authenticated to the correct AWS Account. The values for the environment  ###
###   variables can be found in the stage_build.yml caller workflow.            ###
dist-stage: ## Only use in an emergency
	docker build --platform linux/amd64 \
	    -t $(ECR_URL_STAGE):latest \
		-t $(ECR_URL_STAGE):`git describe --always` \
		-t $(ECR_NAME_STAGE):latest .

publish-stage: ## Only use in an emergency
	docker login -u AWS -p $$(aws ecr get-login-password --region us-east-1) $(ECR_URL_STAGE)
	docker push $(ECR_URL_STAGE):latest
	docker push $(ECR_URL_STAGE):`git describe --always`
