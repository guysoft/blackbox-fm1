UV := artifacts/toolchain/uv-x86_64-unknown-linux-gnu/uv
PY := $(CURDIR)/.venv/bin/python
export JIELI_TOOLCHAIN ?= $(CURDIR)/artifacts/toolchain/jieli-linux-toolchains-20260730.1
export AC79_SDK ?= $(CURDIR)/artifacts/sdk
export PYTHON := $(PY)
export TMPDIR ?= $(CURDIR)/artifacts/tmp
BOARD ?= blackbox-v23
BLE ?= 0
BLE_DIAGNOSTIC ?= 0
BLE_SELFCAL ?= 0
STOCK_blackbox-v17 := artifacts/downloads/BlackBox-wayback-20250705.fwsc
STOCK_blackbox-v20 := artifacts/downloads/BlackBox_FACTORY_V20.fwsc
STOCK_blackbox-v23 := artifacts/downloads/BlackBox-current.fwsc
STOCK = $(STOCK_$(BOARD))

.PHONY: help setup baseline build test upstream-test simulate ports info monitor iterate
baseline build test upstream-test simulate: | artifacts/tmp
artifacts/tmp:
	mkdir -p artifacts/tmp

.DEFAULT_GOAL := help
help:
	@echo "blackbox-fm1: setup baseline build test upstream-test simulate ports info monitor iterate"
	@echo "Default board: $(BOARD). No default command opens MIDI or writes a device."
setup:
	python3 tools/bootstrap.py --fetch
	$(UV) sync --frozen
baseline:
	./build.sh
build:
	./build.sh --board $(BOARD) --stock $(STOCK) $(if $(filter 1,$(BLE)),--ble,) $(if $(filter 1,$(BLE_DIAGNOSTIC)),--ble-diagnostic,) $(if $(filter 1,$(BLE_SELFCAL)),--ble-selfcal,)
test:
	$(PY) -m pytest -q
upstream-test:
	PATH="$(CURDIR)/.venv/bin:$$PATH" sh tests/run_tests.sh
simulate:
	$(PY) tools/blackbox.py simulate --board $(BOARD)
ports:
	$(PY) tools/blackbox.py ports
info:
	$(PY) tools/blackbox.py info --port "$(PORT)"
monitor:
	$(PY) tools/blackbox.py monitor --port "$(PORT)" --board $(BOARD)
iterate:
	$(PY) tools/blackbox.py iterate --session "$(SESSION)" --execute
