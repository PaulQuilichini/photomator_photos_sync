.PHONY: help run build installer check

help:
	@echo "PhotomatorFlagSync commands:"
	@echo "  make run        # Run the app"
	@echo "  make build      # Build standalone .app"
	@echo "  make installer  # Build installer artifact (DMG or ZIP)"
	@echo "  make check      # Run smoke/fixture checks"

run:
	./scripts/run-app.sh

build:
	./scripts/build-app.sh

installer:
	./scripts/build-installer.sh

check:
	python3 tests/smoke_check.py
	python3 tests/flag_parsing_check.py
	python3 tests/duplicate_matching_check.py
