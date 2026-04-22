import sys
import html.parser
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from x32_map import parse_scene, gen_matrix_table, gen_flow_svg, gen_html

FIXTURES = Path(__file__).parent / 'fixtures'


class TagCollector(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.errors = []
        self.ids = []
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        attrs_dict = dict(attrs)
        if 'id' in attrs_dict:
            self.ids.append(attrs_dict['id'])

    def handle_error(self, message):
        self.errors.append(message)


def parse_html(content):
    collector = TagCollector()
    collector.feed(content)
    return collector


# ── gen_matrix_table ─────────────────────────────────────────────────────────

def test_matrix_table_structure():
    data = parse_scene(FIXTURES / 'minimal.scn')
    out = gen_matrix_table(data)
    assert '<table' in out
    assert '</table>' in out


def test_matrix_table_channel_label():
    data = parse_scene(FIXTURES / 'minimal.scn')
    out = gen_matrix_table(data)
    assert '01 Kick' in out


def test_matrix_table_db_value():
    data = parse_scene(FIXTURES / 'minimal.scn')
    out = gen_matrix_table(data)
    assert 'data-db="-18.5"' in out


def test_matrix_table_fader_column():
    data = parse_scene(FIXTURES / 'minimal.scn')
    out = gen_matrix_table(data)
    assert 'col-fader' in out


def test_matrix_table_insert_column():
    data = parse_scene(FIXTURES / 'minimal.scn')
    out = gen_matrix_table(data)
    assert 'col-insert' in out


def test_matrix_table_empty_no_crash():
    data = parse_scene(FIXTURES / 'empty_scene.scn')
    out = gen_matrix_table(data)
    assert '<table' in out
    assert '</table>' in out


def test_matrix_table_dca_section_header():
    data = parse_scene(FIXTURES / 'minimal.scn')
    out = gen_matrix_table(data)
    assert 'Drums' in out


def test_matrix_table_insert_routed_label():
    data = parse_scene(FIXTURES / 'insert_routed.scn')
    out = gen_matrix_table(data)
    assert 'FX1S L' in out


def test_matrix_table_insert_unrouted_label():
    data = parse_scene(FIXTURES / 'insert_unrouted.scn')
    out = gen_matrix_table(data)
    assert 'ON/POST' in out


def test_matrix_table_pre_marker():
    data = parse_scene(FIXTURES / 'minimal.scn')
    out = gen_matrix_table(data)
    # PRE send should render a 'P' superscript marker
    assert 'pre-dot' in out


# ── gen_flow_svg ─────────────────────────────────────────────────────────────

def test_flow_svg_structure():
    data = parse_scene(FIXTURES / 'minimal.scn')
    out = gen_flow_svg(data)
    assert out.startswith('<svg')
    assert '</svg>' in out


def test_flow_svg_active_send_edge():
    data = parse_scene(FIXTURES / 'minimal.scn')
    out = gen_flow_svg(data)
    assert 'data-db=' in out


def test_flow_svg_fx_loop_arc():
    data = parse_scene(FIXTURES / 'fx_active.scn')
    out = gen_flow_svg(data)
    assert 'stroke-dasharray="5,3"' in out


def test_flow_svg_insert_badge():
    data = parse_scene(FIXTURES / 'insert_routed.scn')
    out = gen_flow_svg(data)
    assert 'insert-badge' in out


def test_flow_svg_empty_no_crash():
    data = parse_scene(FIXTURES / 'empty_scene.scn')
    out = gen_flow_svg(data)
    assert out.startswith('<svg')
    assert '</svg>' in out


# ── gen_html ─────────────────────────────────────────────────────────────────

def test_gen_html_parses():
    data = parse_scene(FIXTURES / 'minimal.scn')
    out = gen_html(data)
    collector = parse_html(out)
    assert collector.errors == []


def test_gen_html_title():
    data = parse_scene(FIXTURES / 'minimal.scn')
    out = gen_html(data)
    assert '<title>X32 Map \u2014 Minimal</title>' in out


def test_gen_html_view_buttons():
    data = parse_scene(FIXTURES / 'minimal.scn')
    out = gen_html(data)
    assert 'id="btn-matrix"' in out
    assert 'id="btn-flow"' in out


def test_gen_html_level_slider():
    data = parse_scene(FIXTURES / 'minimal.scn')
    out = gen_html(data)
    assert 'id="level-slider"' in out


def test_gen_html_dca_chip():
    data = parse_scene(FIXTURES / 'minimal.scn')
    out = gen_html(data)
    assert 'Drums' in out


def test_gen_html_has_script():
    data = parse_scene(FIXTURES / 'minimal.scn')
    out = gen_html(data)
    collector = parse_html(out)
    assert 'script' in collector.tags


def test_gen_html_doctype():
    data = parse_scene(FIXTURES / 'minimal.scn')
    out = gen_html(data)
    assert out.startswith('<!DOCTYPE html>')
