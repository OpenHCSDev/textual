"""Captured stderr must not leak an invalid descriptor into process startup."""

from io import UnsupportedOperation
from unittest.mock import Mock

import pytest

from textual.app import _PrintCapture


def test_capture_has_no_os_descriptor():
    capture = _PrintCapture(Mock(), stderr=True)
    with pytest.raises(UnsupportedOperation):
        capture.fileno()
