.DEFAULT_GOAL := init
.PHONY: prepare-dev install-dev data help lint tests coverage upload-prod-pypi upload-test-pypi pyclean doc doc-pdf visu-doc-pdf visu-doc tox licences
VENV = ".planetary_fetch"

define PROJECT_HELP_MSG

Usage:\n
	\n
    make help\t\t\t             show this message\n
	\n
	-------------------------------------------------------------------------\n
	\t\tInstallation\n
	-------------------------------------------------------------------------\n
	make\t\t\t\t                Install planetary_fetch in the system (root)\n
	make user\t\t\t 			Install planetary_fetch for non-root usage\n
	\n
	-------------------------------------------------------------------------\n
	\t\tDevelopment\n
	-------------------------------------------------------------------------\n
	make prepare-dev\t\t 		Prepare Development environment\n
	make install-dev\t\t 		Install COTS and planetary_fetch for development purpose\n
	make tests\t\t\t             Run units and integration tests\n
	\n
	make release\t\t\t 			Release the package as tar.gz\n
	\n
	\n
	make pyclean\t\t\t		Clean .pyc files and __pycache__ directories\n
	\n
	-------------------------------------------------------------------------\n
	\t\tOthers\n
	-------------------------------------------------------------------------\n
	make version\t\t\t		Display the version\n
	make coverage\t\t\t 	Coverage\n
	make lint\t\t\t			Lint\n
	make tox\t\t\t 			Run all tests\n

endef
export PROJECT_HELP_MSG


#Show help
#---------
help:
	echo $$PROJECT_HELP_MSG


#
# Sotware Installation in the system (need root access)
# -----------------------------------------------------
#
init:
	uv tool install .

#
# Sotware Installation for user
# -----------------------------
# This scheme is designed to be the most convenient solution for users
# that don’t have write permission to the global site-packages directory or
# don’t want to install into it.
#
user:
	uv tool install .

prepare-dev:
	cp .pypirc ~${USER} && git init && echo "python3 -m venv planetary_fetch-env && export PYTHONPATH=. && export PATH=`pwd`/planetary_fetch-env/bin:"${PATH}"" > ${VENV} && echo "source \"`pwd`/planetary_fetch-env/bin/activate\"" >> ${VENV} && scripts/install-hooks.bash && echo "\nnow source this file: \033[31msource ${VENV}\033[0m"

install-dev:
	uv sync && uv run pre-commit install && uv run pre-commit autoupdate && git config commit.template .gitmessage

coverage:  ## Run tests with coverage
	uv run coverage erase
	uv run coverage run --include=planetary_fetch/* -m pytest -ra
	uv run coverage report -m

lint:  ## Lint and static-check
	uv run flake8 --ignore=E203,E266,E501,W503,F403,F401 --max-line-length=79 --max-complexity=18 --select=B,C,E,F,W,T4,B9 planetary_fetch
	uv run pylint planetary_fetch
	uv run mypy planetary_fetch

tests:  ## Run tests
	uv run pytest -ra

tox:
	uv run tox -e py311

release:
	uv build

version:
	uv version --short

pyclean:
	find . -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete
