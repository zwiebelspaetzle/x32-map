import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from x32_map import parse_scene

FIXTURES = Path(__file__).parent / 'fixtures'
REAL_SCENE = Path(__file__).parent.parent / 'test_scene.scn'


def test_minimal_channel():
    data = parse_scene(FIXTURES / 'minimal.scn')
    ch = data['channels'][1]
    assert ch['name'] == 'Kick'
    assert ch['color'] == 'RD'
    assert ch['fader_on'] is True
    assert ch['fader_db'] == 0.0
    assert ch['active'] is True
    assert ch['dcas'] == [1]


def test_minimal_send():
    data = parse_scene(FIXTURES / 'minimal.scn')
    send = data['channels'][1]['sends'][1]
    assert send == {'db': -18.5, 'pre': 'PRE', 'enabled': True}


def test_minimal_bus():
    data = parse_scene(FIXTURES / 'minimal.scn')
    bus = data['buses'][1]
    assert bus['name'] == 'FOH L'
    assert bus['color'] == 'GN'


def test_minimal_dca():
    data = parse_scene(FIXTURES / 'minimal.scn')
    assert data['dcas'][1]['name'] == 'Drums'


def test_minimal_output():
    data = parse_scene(FIXTURES / 'minimal.scn')
    out = data['outputs'][1]
    assert out['src_type'] == 'bus'
    assert out['src_label'] == 'MixBus 01'
    assert out['src_idx'] == 5


def test_minimal_scene_name():
    data = parse_scene(FIXTURES / 'minimal.scn')
    assert data['scene_name'] == 'Minimal'


def test_edge_names_scene_name():
    data = parse_scene(FIXTURES / 'edge_names.scn')
    assert data['scene_name'] == 'Test &amp; Scene &lt;2&gt;'


def test_edge_names_channel_escaped():
    data = parse_scene(FIXTURES / 'edge_names.scn')
    assert data['channels'][1]['name'] == 'Kick &amp; Snare'


def test_edge_names_empty_name_fallback():
    data = parse_scene(FIXTURES / 'edge_names.scn')
    # Empty quoted name "" falls back to the default 'CH02'
    assert data['channels'][2]['name'] == 'CH02'


def test_edge_names_bus_spaces():
    data = parse_scene(FIXTURES / 'edge_names.scn')
    assert data['buses'][1]['name'] == 'Bus with spaces'


def test_insert_routed():
    data = parse_scene(FIXTURES / 'insert_routed.scn')
    assert data['channels'][1]['insert'] == {'on': True, 'pos': 'PRE', 'point': 37}


def test_insert_unrouted():
    data = parse_scene(FIXTURES / 'insert_unrouted.scn')
    ins = data['channels'][1]['insert']
    assert ins['on'] is True
    assert ins['point'] == 0


def test_empty_scene_collections():
    data = parse_scene(FIXTURES / 'empty_scene.scn')
    assert data['channels'] == {}
    assert data['buses'] == {}
    assert data['dcas'] == {}
    assert data['fx_slots'] == {}


def test_empty_scene_name():
    data = parse_scene(FIXTURES / 'empty_scene.scn')
    assert data['scene_name'] == 'Empty'


def test_multi_dca_both():
    data = parse_scene(FIXTURES / 'multi_dca.scn')
    assert data['channels'][1]['dcas'] == [1, 2]


def test_multi_dca_none():
    data = parse_scene(FIXTURES / 'multi_dca.scn')
    assert data['channels'][2]['dcas'] == []


def test_multi_dca_empty_name_preserved():
    # DCA with empty name in scn keeps its default 'DCA 1'
    data = parse_scene(FIXTURES / 'multi_dca.scn')
    assert data['dcas'][1]['name'] == 'DCA 1'


def test_fx_slot():
    data = parse_scene(FIXTURES / 'fx_active.scn')
    slot = data['fx_slots'][1]
    assert slot['type_name'] == 'HALL'
    assert slot['source_l'] == 'MIX13'
    assert slot['source_r'] == 'MIX13'


def test_fxrtn_active():
    data = parse_scene(FIXTURES / 'fx_active.scn')
    assert data['fxrtns'][1]['active'] is True
    assert data['fxrtns'][2]['active'] is True


@pytest.mark.skipif(not REAL_SCENE.exists(), reason='test_scene.scn not present')
def test_real_scene_structure():
    data = parse_scene(REAL_SCENE)
    assert len(data['channels']) == 32
    assert len(data['dcas']) == 8
    assert len(data['buses']) == 16


@pytest.mark.skipif(not REAL_SCENE.exists(), reason='test_scene.scn not present')
def test_real_scene_known_values():
    data = parse_scene(REAL_SCENE)
    assert data['channels'][1]['name'] == 'Darren'
    assert data['channels'][1]['color'] == 'CYi'


@pytest.mark.skipif(not REAL_SCENE.exists(), reason='test_scene.scn not present')
def test_real_scene_fx_slot():
    data = parse_scene(REAL_SCENE)
    assert data['fx_slots'][1]['type_name'] == 'HALL'
    assert data['fx_slots'][1]['source_l'] == 'MIX13'
