import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from x32_map import parse_db, decode_source, decode_dca_mask, tokenize, level_color, scribble_colors, decode_insert_point


@pytest.mark.parametrize("token,expected", [
    ('+0.0',   0.0),
    ('-50',    -50.0),
    ('+5.3',   5.3),
    ('0.0',    0.0),
    ('-oo',    None),
    ('garbage', None),
])
def test_parse_db(token, expected):
    assert parse_db(token) == expected


@pytest.mark.parametrize("idx,expected_type,expected_label", [
    (0,  'off',     'Off'),
    (1,  'main',    'Main L'),
    (2,  'main',    'Main R'),
    (3,  'main',    'M/C'),
    (4,  'unknown', 'Src 4'),      # gap — nothing maps to 4
    (5,  'bus',     'MixBus 01'),
    (20, 'bus',     'MixBus 16'),
    (21, 'matrix',  'Matrix 01'),
    (26, 'matrix',  'Matrix 06'),
    (32, 'local',   'Local In 01'),
    (63, 'local',   'Local In 32'),
    (64, 'aux',     'Aux In 01'),
    (71, 'aux',     'Aux In 08'),
    (100,'unknown', 'Src 100'),
])
def test_decode_source(idx, expected_type, expected_label):
    t, l = decode_source(idx)
    assert t == expected_type
    assert l == expected_label


@pytest.mark.parametrize("mask,expected", [
    ('%00000001', [1]),
    ('%00000010', [2]),
    ('%00000011', [1, 2]),
    ('%00000000', []),
    ('%11111111', [1, 2, 3, 4, 5, 6, 7, 8]),
    ('%10000000', [8]),
    ('%01000000', [7]),
])
def test_decode_dca_mask(mask, expected):
    assert decode_dca_mask(mask) == expected


@pytest.mark.parametrize("line,expected_key,expected_tokens", [
    ('/ch/01/config "Kick Drum" 1 RD 1', '/ch/01/config', ['"Kick Drum"', '1', 'RD', '1']),
    ('',              None, []),
    ('# comment',     None, []),
    ('/key',          '/key', []),
    ('/key val1 val2','/key', ['val1', 'val2']),
    ('/key "quoted with spaces"', '/key', ['"quoted with spaces"']),
])
def test_tokenize(line, expected_key, expected_tokens):
    key, tokens = tokenize(line)
    assert key == expected_key
    assert tokens == expected_tokens


@pytest.mark.parametrize("db,expected_bg", [
    (None,   '#ffffff'),
    (0.0,    '#166534'),
    (1.0,    '#166534'),
    (-5.0,   '#22c55e'),
    (-10.0,  '#22c55e'),  # boundary: >= -10
    (-10.1,  '#86efac'),
    (-20.0,  '#86efac'),  # boundary: >= -20
    (-20.1,  '#fef08a'),
    (-30.0,  '#fef08a'),  # boundary: >= -30
    (-30.1,  '#fed7aa'),
    (-50.0,  '#fed7aa'),  # boundary: >= -50
    (-50.1,  '#e2e8f0'),
    (-70.0,  '#e2e8f0'),  # boundary: >= -70
    (-70.1,  '#f8fafc'),
    (-90.0,  '#f8fafc'),
])
def test_level_color(db, expected_bg):
    bg, _ = level_color(db)
    assert bg == expected_bg


@pytest.mark.parametrize("code,expected_bg", [
    ('RD',      '#dc2626'),
    ('GN',      '#16a34a'),
    ('CY',      '#0e7490'),
    ('CYi',     '#1e293b'),
    ('WH',      '#e2e8f0'),
    ('OFF',     '#374151'),
    ('OFFi',    '#1e293b'),
    (None,      '#e2e8f0'),  # None -> defaults to WH
    ('UNKNOWN', '#475569'),  # fallback
])
def test_scribble_colors(code, expected_bg):
    bg, _ = scribble_colors(code)
    assert bg == expected_bg


@pytest.mark.parametrize("point,expected", [
    (0,   'Off'),
    (1,   'OUT 01'),
    (16,  'OUT 16'),
    (17,  'AES 01'),
    (22,  'AES 06'),
    (23,  'P16 01'),
    (30,  'P16 08'),
    (31,  'AUX 01'),
    (36,  'AUX 06'),
    (37,  'FX1S L'),
    (38,  'FX1S R'),
    (39,  'FX2S L'),
    (44,  'FX4S R'),
    (100, 'Pt 100'),
])
def test_decode_insert_point(point, expected):
    assert decode_insert_point(point) == expected
