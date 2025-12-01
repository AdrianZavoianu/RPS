"""Tests for ProjectController utilities."""

from __future__ import annotations

import types

from gui.controllers.project_controller import ProjectController


def test_build_runtime_passes_through(monkeypatch):
    controller = ProjectController()
    context = object()
    fake_runtime = object()

    called = {}

    def fake_builder(ctx):
        called["context"] = ctx
        return fake_runtime

    monkeypatch.setattr(
        "gui.controllers.project_controller.build_project_runtime",
        fake_builder,
    )

    assert controller.build_runtime(context) is fake_runtime
    assert called["context"] is context


def test_list_summaries_uses_service(monkeypatch):
    controller = ProjectController()
    fake_summaries = ["s1", "s2"]

    monkeypatch.setattr(
        "gui.controllers.project_controller.list_project_summaries",
        lambda: fake_summaries,
    )

    assert controller.list_summaries() == fake_summaries
