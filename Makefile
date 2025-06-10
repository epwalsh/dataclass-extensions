.PHONY : check
check : style lint test

.PHONY : style
style :
	black --check .
	isort --check .

.PHONY : lint
lint :
	ruff check .
	mypy .

.PHONY : test
test :
	pytest -v src/test/

.PHONY : dev-install
dev-install :
	pip install -e .[dev] --config-settings editable_mode=compat

.PHONY : build
build :
	rm -rf *.egg-info/
	python -m build
