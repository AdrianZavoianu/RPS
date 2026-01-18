"""Ensure cache debug flag wiring does not break default behavior."""

import importlib
import os


def test_cache_debug_flag_import(monkeypatch):
    monkeypatch.setenv("RPS_CACHE_DEBUG", "1")
    providers = importlib.reload(importlib.import_module("processing.result_service.providers"))
    assert providers.CACHE_DEBUG is True

    monkeypatch.setenv("RPS_CACHE_DEBUG", "0")
    providers = importlib.reload(importlib.import_module("processing.result_service.providers"))
    assert providers.CACHE_DEBUG is False
