"""Smoke test: the package imports and the scaffold is where config expects it."""

import harborfund
from harborfund import config


def test_import():
    assert harborfund.__version__


def test_data_folders_exist():
    for d in (config.RAW_DIR, config.PROCESSED_DIR, config.REFERENCE_DIR):
        assert d.is_dir(), d


def test_constants():
    assert config.BASE_YEAR == 2025
    assert config.fiscal_year(2024, 10) == 2025
    assert config.fiscal_year(2025, 9) == 2025
