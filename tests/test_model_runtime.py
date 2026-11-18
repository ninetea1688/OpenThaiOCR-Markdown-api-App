"""Contracts for the upstream 2.1 output; no model weights or GPU needed.

API-only installations skip these tests. scripts/install.sh installs the runtime.
"""
from importlib.metadata import PackageNotFoundError, version

import pytest
from PIL import Image

try:
    runtime = version('nemotron-parse')
except PackageNotFoundError:
    runtime = None
pytestmark = pytest.mark.skipif(runtime != '3.5.0.post8', reason='Requires the pinned OpenThai 2.1 runtime')


def test_standard_output_normalizes_sara_am_and_preserves_merged_cells():
    from nemotron_parse.postprocessing import standard_text

    text = '<table><tr><td rowspan="1" colspan="2">ประจํา</td><td colspan="1">งาน</td></tr></table>'
    out = standard_text(text)
    assert 'ประจำ' in out
    assert 'rowspan="1"' not in out and 'colspan="1"' not in out
    assert 'colspan="2"' in out


def test_blank_page_skips_generation_and_returns_empty_document():
    from nemotron_parse.inference import DocumentParser

    def backend(*args, **kwargs):
        pytest.fail('Blank pages must not invoke model generation')

    parser = DocumentParser(backend=backend, skip_blank=True, dewarp=False)
    result = parser.parse(Image.new('RGB', (200, 300), 'white'), mode='single')
    assert result['markdown'] == ''
    assert result['blocks'] == []


def test_new_markdown_defaults():
    from nemotron_parse.postprocessing import PostprocessOptions

    options = PostprocessOptions()
    assert options.keep_page_headers_footers is False
    assert options.formula_display_dollars is True
    assert options.standard_output is True
