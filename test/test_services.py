# -*- coding: utf-8 -*-
"""Regression tests for Xiaomi Home service registration."""
import ast
from pathlib import Path

import pytest


@pytest.mark.github
def test_async_setup_registers_services() -> None:
    """Ensure async_setup registers Xiaomi Home services."""
    init_path = Path(__file__).parent.parent / (
        'custom_components/xiaomi_home/__init__.py')
    tree = ast.parse(init_path.read_text(encoding='utf-8'))

    async_setup = next(
        node for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef)
        and node.name == 'async_setup')

    calls = [
        node for node in ast.walk(async_setup)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == 'async_setup_services'
    ]

    assert len(calls) == 1
    assert len(calls[0].args) == 1
    assert isinstance(calls[0].args[0], ast.Name)
    assert calls[0].args[0].id == 'hass'
