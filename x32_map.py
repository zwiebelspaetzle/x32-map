#!/usr/bin/env python3
"""Behringer X32 scene file → interactive routing diagram (HTML).

Usage: python3 x32_routing.py "test_scene.scn"
"""
import re, sys, json, html
from pathlib import Path


# ── Parsing helpers ───────────────────────────────────────────────────────────

def parse_db(token):
    if token == '-oo': return None
    try: return float(token.replace('+', ''))
    except ValueError: return None

def decode_source(idx):
    idx = int(idx)
    if idx == 0: return ('off', 'Off')
    if idx == 1: return ('main', 'Main L')
    if idx == 2: return ('main', 'Main R')
    if idx == 3: return ('main', 'M/C')
    if 5 <= idx <= 20:  return ('bus',    f'MixBus {idx-4:02d}')
    if 21 <= idx <= 26: return ('matrix', f'Matrix {idx-20:02d}')
    if 32 <= idx <= 63: return ('local',  f'Local In {idx-31:02d}')
    if 64 <= idx <= 71: return ('aux',    f'Aux In {idx-63:02d}')
    return ('unknown', f'Src {idx}')

def decode_dca_mask(s):
    bits = s.lstrip('%')
    return [i+1 for i, c in enumerate(reversed(bits)) if c == '1']

def tokenize(line):
    line = line.strip()
    if not line or line.startswith('#'): return None, []
    parts = re.findall(r'"[^"]*"|\S+', line)
    return (parts[0], parts[1:]) if parts else (None, [])


# ── Scene parser ──────────────────────────────────────────────────────────────

def new_ch(num, prefix='CH'):
    return {'name': f'{prefix}{num:02d}', 'color': 'WH', 'fader_on': True, 'fader_db': 0.0,
            'sends': {}, 'dcas': [], 'active': False}

def parse_scene(path):
    data = {
        'scene_name': 'X32', 'channels': {}, 'auxins': {}, 'fxrtns': {},
        'buses': {}, 'matrices': {},
        'main_st': {'name': 'Main L/R', 'color': 'WH', 'fader_on': True, 'fader_db': 0.0, 'sends_to_matrix': {}},
        'dcas': {}, 'outputs': {}, 'p16_outputs': {}, 'aux_outputs': {}, 'routing_in': [],
        'fx_slots': {},   # 1-8: {type_name, source_l, source_r}
    }

    def ch(d, num, pfx='CH'):
        if num not in d: d[num] = new_ch(num, pfx)
        return d[num]
    def bus(num):
        if num not in data['buses']:
            data['buses'][num] = {'name': f'Bus {num:02d}', 'color': 'WH', 'fader_on': True,
                                  'fader_db': 0.0, 'sends_to_matrix': {}}
        return data['buses'][num]
    def mtx(num):
        if num not in data['matrices']:
            data['matrices'][num] = {'name': f'Mtx {num:02d}', 'color': 'WH', 'fader_on': True, 'fader_db': 0.0}
        return data['matrices'][num]
    def dca(num):
        if num not in data['dcas']:
            data['dcas'][num] = {'name': f'DCA {num}', 'color': 'WH', 'fader_on': True, 'fader_db': 0.0}
        return data['dcas'][num]

    PATS = [
        (re.compile(r'^/ch/(\d+)/config$'),       'ch_cfg'),
        (re.compile(r'^/ch/(\d+)/mix$'),           'ch_mix'),
        (re.compile(r'^/ch/(\d+)/mix/(\d+)$'),     'ch_send'),
        (re.compile(r'^/ch/(\d+)/grp$'),           'ch_grp'),
        (re.compile(r'^/auxin/(\d+)/config$'),      'ax_cfg'),
        (re.compile(r'^/auxin/(\d+)/mix/(\d+)$'),  'ax_send'),
        (re.compile(r'^/auxin/(\d+)/grp$'),         'ax_grp'),
        (re.compile(r'^/fxrtn/(\d+)/config$'),      'fx_cfg'),
        (re.compile(r'^/fxrtn/(\d+)/mix/(\d+)$'),  'fx_send'),
        (re.compile(r'^/bus/(\d+)/config$'),        'bus_cfg'),
        (re.compile(r'^/bus/(\d+)/mix$'),           'bus_mix'),
        (re.compile(r'^/bus/(\d+)/mix/(\d+)$'),     'bus_send'),
        (re.compile(r'^/mtx/(\d+)/config$'),        'mtx_cfg'),
        (re.compile(r'^/mtx/(\d+)/mix$'),           'mtx_mix'),
        (re.compile(r'^/main/st/config$'),          'mst_cfg'),
        (re.compile(r'^/main/st/mix$'),             'mst_mix'),
        (re.compile(r'^/main/st/mix/(\d+)$'),       'mst_send'),
        (re.compile(r'^/dca/(\d+)/config$'),        'dca_cfg'),
        (re.compile(r'^/dca/(\d+)$'),               'dca_fdr'),
        (re.compile(r'^/outputs/main/(\d+)$'),      'out_main'),
        (re.compile(r'^/outputs/p16/(\d+)$'),       'out_p16'),
        (re.compile(r'^/outputs/aux/(\d+)$'),       'out_aux'),
        (re.compile(r'^/config/routing/IN$'),       'rt_in'),
        (re.compile(r'^/fx/(\d+)$'),               'fx_type'),
        (re.compile(r'^/fx/(\d+)/source$'),         'fx_src'),
    ]

    lines = Path(path).resolve().read_text(encoding='utf-8', errors='replace').splitlines()
    if lines:
        m = re.match(r'#[\d.]+#\s*"([^"]*)"', lines[0])
        if m: data['scene_name'] = html.escape(m.group(1))

    for line in lines[1:]:
        key, tok = tokenize(line)
        if not key: continue
        for pat, tag in PATS:
            m = pat.match(key)
            if not m: continue
            g = m.groups()

            if tag == 'ch_cfg':
                c = ch(data['channels'], int(g[0]))
                if tok: c['name'] = html.escape(tok[0].strip('"')) or c['name']
                if len(tok) >= 3: c['color'] = tok[2]
            elif tag == 'ch_mix':
                c = ch(data['channels'], int(g[0]))
                if len(tok) >= 2: c['fader_on'] = tok[0]=='ON'; c['fader_db'] = parse_db(tok[1])
            elif tag == 'ch_send':
                c = ch(data['channels'], int(g[0])); bnum = int(g[1])
                if len(tok) >= 2:
                    db = parse_db(tok[1])
                    pre = tok[3] if len(tok) >= 4 else None
                    c['sends'][bnum] = {'enabled': tok[0]=='ON', 'db': db, 'pre': pre}
                    if db is not None: c['active'] = True
            elif tag == 'ch_grp':
                c = ch(data['channels'], int(g[0]))
                if tok: c['dcas'] = decode_dca_mask(tok[0])
            elif tag == 'ax_cfg':
                c = ch(data['auxins'], int(g[0]), 'AuxIn')
                if tok: c['name'] = html.escape(tok[0].strip('"')) or c['name']
                if len(tok) >= 3: c['color'] = tok[2]
            elif tag == 'ax_send':
                c = ch(data['auxins'], int(g[0]), 'AuxIn'); bnum = int(g[1])
                if len(tok) >= 2:
                    db = parse_db(tok[1])
                    c['sends'][bnum] = {'enabled': tok[0]=='ON', 'db': db, 'pre': None}
                    if db is not None: c['active'] = True
            elif tag == 'ax_grp':
                c = ch(data['auxins'], int(g[0]), 'AuxIn')
                if tok: c['dcas'] = decode_dca_mask(tok[0])
            elif tag == 'fx_cfg':
                c = ch(data['fxrtns'], int(g[0]), 'FXRtn')
                if tok: c['name'] = html.escape(tok[0].strip('"')) or c['name']
                if len(tok) >= 3: c['color'] = tok[2]
            elif tag == 'fx_send':
                c = ch(data['fxrtns'], int(g[0]), 'FXRtn'); bnum = int(g[1])
                if len(tok) >= 2:
                    db = parse_db(tok[1])
                    c['sends'][bnum] = {'enabled': tok[0]=='ON', 'db': db, 'pre': None}
                    if db is not None: c['active'] = True
            elif tag == 'bus_cfg':
                b = bus(int(g[0]))
                if tok: b['name'] = html.escape(tok[0].strip('"')) or b['name']
                if len(tok) >= 3: b['color'] = tok[2]
            elif tag == 'bus_mix':
                b = bus(int(g[0]))
                if len(tok) >= 2: b['fader_on'] = tok[0]=='ON'; b['fader_db'] = parse_db(tok[1])
            elif tag == 'bus_send':
                b = bus(int(g[0])); mnum = int(g[1])
                if len(tok) >= 2:
                    db = parse_db(tok[1])
                    b['sends_to_matrix'][mnum] = {'enabled': tok[0]=='ON', 'db': db}
            elif tag == 'mtx_cfg':
                mt = mtx(int(g[0]))
                if tok: mt['name'] = html.escape(tok[0].strip('"')) or mt['name']
                if len(tok) >= 3: mt['color'] = tok[2]
            elif tag == 'mtx_mix':
                mt = mtx(int(g[0]))
                if len(tok) >= 2: mt['fader_on'] = tok[0]=='ON'; mt['fader_db'] = parse_db(tok[1])
            elif tag == 'mst_cfg':
                if tok: data['main_st']['name'] = html.escape(tok[0].strip('"')) or 'Main L/R'
                if len(tok) >= 3: data['main_st']['color'] = tok[2]
            elif tag == 'mst_mix':
                if len(tok) >= 2:
                    data['main_st']['fader_on'] = tok[0]=='ON'
                    data['main_st']['fader_db'] = parse_db(tok[1])
            elif tag == 'mst_send':
                mnum = int(g[0])
                if len(tok) >= 2:
                    db = parse_db(tok[1])
                    data['main_st']['sends_to_matrix'][mnum] = {'enabled': tok[0]=='ON', 'db': db}
            elif tag == 'dca_cfg':
                d = dca(int(g[0]))
                if tok: d['name'] = html.escape(tok[0].strip('"')) or d['name']
                if len(tok) >= 3: d['color'] = tok[2]
            elif tag == 'dca_fdr':
                d = dca(int(g[0]))
                if len(tok) >= 2: d['fader_on'] = tok[0]=='ON'; d['fader_db'] = parse_db(tok[1])
            elif tag == 'out_main':
                num = int(g[0])
                if tok:
                    st, sl = decode_source(tok[0])
                    data['outputs'][num] = {'src_idx': int(tok[0]), 'src_type': st, 'src_label': sl}
            elif tag == 'out_p16':
                num = int(g[0])
                if tok:
                    st, sl = decode_source(tok[0])
                    data['p16_outputs'][num] = {'src_idx': int(tok[0]), 'src_type': st, 'src_label': sl}
            elif tag == 'out_aux':
                num = int(g[0])
                if tok:
                    st, sl = decode_source(tok[0])
                    data['aux_outputs'][num] = {'src_idx': int(tok[0]), 'src_type': st, 'src_label': sl}
            elif tag == 'rt_in':
                data['routing_in'] = tok
            elif tag == 'fx_type':
                num = int(g[0])
                if num not in data['fx_slots']:
                    data['fx_slots'][num] = {'type_name': '', 'source_l': '', 'source_r': ''}
                if tok: data['fx_slots'][num]['type_name'] = html.escape(tok[0])
            elif tag == 'fx_src':
                num = int(g[0])
                if num not in data['fx_slots']:
                    data['fx_slots'][num] = {'type_name': '', 'source_l': '', 'source_r': ''}
                if len(tok) >= 1: data['fx_slots'][num]['source_l'] = html.escape(tok[0])
                if len(tok) >= 2: data['fx_slots'][num]['source_r'] = html.escape(tok[1])
            break

    return data


# ── Colour helpers ────────────────────────────────────────────────────────────

def level_color(db):
    """(bg_hex, text_hex)"""
    if db is None:       return ('#ffffff', '#ffffff')
    if db >= 0:          return ('#166534', '#ffffff')
    if db >= -10:        return ('#22c55e', '#052e16')
    if db >= -20:        return ('#86efac', '#052e16')
    if db >= -30:        return ('#fef08a', '#422006')
    if db >= -50:        return ('#fed7aa', '#431407')
    if db >= -70:        return ('#e2e8f0', '#475569')
    return                      ('#f8fafc', '#94a3b8')

X32_COLORS = {
    'OFF':  ('#374151', '#d1d5db'), 'OFFi': ('#1e293b', '#9ca3af'),
    'RD':   ('#dc2626', '#fff'),    'RDi':  ('#1e293b', '#f87171'),
    'GN':   ('#16a34a', '#fff'),    'GNi':  ('#1e293b', '#4ade80'),
    'YE':   ('#b45309', '#fff'),    'YEi':  ('#1e293b', '#fbbf24'),
    'BL':   ('#1d4ed8', '#fff'),    'BLi':  ('#1e293b', '#60a5fa'),
    'MG':   ('#7c3aed', '#fff'),    'MGi':  ('#1e293b', '#c084fc'),
    'CY':   ('#0e7490', '#fff'),    'CYi':  ('#1e293b', '#22d3ee'),
    'WH':   ('#e2e8f0', '#1e293b'), 'WHi':  ('#1e293b', '#e2e8f0'),
}

def scribble_colors(code):
    """Return (bg_hex, fg_hex) for an X32 color code such as 'CYi' or 'RD'."""
    return X32_COLORS.get(code or 'WH', ('#475569', '#fff'))

BUS_TYPE_COLOR = {
    'foh':  '#3b82f6',
    'mon':  '#22c55e',
    'iem':  '#f97316',
    'fx':   '#a855f7',
    'misc': '#6b7280',
}

def bus_type(num):
    if num in (1, 2):        return 'foh'
    if 3 <= num <= 11:       return 'mon'
    if num == 12:            return 'iem'
    if 13 <= num <= 16:      return 'fx'
    return 'misc'

def fmt_db(db):
    if db is None: return ''
    if db > 0:     return f'+{db:.1f}'
    return f'{db:.1f}'

FX_TYPE_NAMES = {
    'HALL': 'Hall Reverb',    'ROOM': 'Room Reverb',     'PLATE': 'Plate Reverb',
    'AMBIENCE': 'Ambience',   'COMB': 'Comb Filter',     'ALLPASS': 'Allpass',
    'DELAY': 'Delay',         '2TAPDELAY': '2-Tap Delay', 'TRIPLEDELAY': 'Triple Delay',
    'MODDELAY': 'Mod Delay',  'STEREOANALG': 'Stereo Analogue Delay',
    'TREM/AUTOPAN': 'Tremolo/Autopan', 'VIBRATO': 'Vibrato', 'FLANGER': 'Flanger',
    'CHORUS': 'Chorus',       'MODFX': 'Mod FX',          'PITCH': 'Pitch Shifter',
    'PITCH2': 'Pitch Shifter 2', 'HARMONIZER': 'Harmonizer',
    'DES': 'De-esser',        'DES2': 'De-esser 2',       'DENOISER': 'Noise Reducer',
    'VRM': 'Virtual Room Mon.', 'GEQ': 'Graphic EQ',     'GEQ2': 'Stereo Graphic EQ',
    'MULTITAP': 'Multitap Delay',
}

def decode_mix_source(src_str):
    """'MIX13' → 13"""
    m = re.match(r'MIX(\d+)', src_str or '')
    return int(m.group(1)) if m else None


# ── Matrix table ──────────────────────────────────────────────────────────────

def gen_matrix_table(data):
    buses  = data['buses']
    dcas   = data['dcas']
    bus_nums = list(range(1, 17))

    # Build ordered channel list grouped by DCA
    # Group: (dca_num_or_0, [channels])
    by_dca = {}
    for num in sorted(data['channels']):
        c = data['channels'][num]
        primary_dca = c['dcas'][0] if c['dcas'] else 0
        by_dca.setdefault(primary_dca, []).append((num, c))

    rows = []

    def th(text, cls='', style='', colspan=1):
        cs = f' colspan="{colspan}"' if colspan > 1 else ''
        return f'<th class="mat-hdr {cls}"{cs} style="{style}">{text}</th>'

    # Header row
    header = '<tr><th class="mat-corner">CH / Bus</th>'
    for bn in bus_nums:
        b = buses.get(bn, {})
        bname = b.get('name', f'Bus {bn:02d}')
        bg, fg = scribble_colors(b.get('color', 'WH'))
        header += f'<th class="mat-hdr" style="background:{bg};color:{fg}" title="{bname}">'
        header += f'<span class="bus-num">{bn:02d}</span><br><span class="bus-name">{bname}</span></th>'
    header += '</tr>'
    rows.append(header)

    def channel_row(num, c, section):
        dcas_list = c['dcas']
        bg, fg = scribble_colors(c.get('color', 'WH'))
        label = f'{num:02d} {c["name"]}'
        row = (f'<tr class="ch-row" data-dcas=\'{json.dumps(dcas_list)}\' '
               f'data-section="{section}">')
        row += (f'<td class="ch-label" style="background:{bg};color:{fg}" '
                f'title="DCA: {", ".join(str(d) for d in dcas_list) or "—"}">'
                f'{label}</td>')
        for bn in bus_nums:
            send = c['sends'].get(bn, {})
            db   = send.get('db')
            pre  = send.get('pre')
            bg, fg = level_color(db)
            db_str = fmt_db(db)
            pre_dot = '<sup class="pre-dot">P</sup>' if pre == 'PRE' and db is not None else ''
            db_num  = '' if db is None else f'data-db="{db}"'
            row += (f'<td class="mat-cell" {db_num} style="background:{bg};color:{fg}" '
                    f'title="Bus {bn:02d}: {db_str if db_str else "—"}">'
                    f'{db_str}{pre_dot}</td>')
        row += '</tr>'
        return row

    def section_header(label, color='#334155'):
        return (f'<tr class="sec-hdr"><td colspan="{len(bus_nums)+1}" '
                f'style="background:{color};color:#fff;padding:4px 8px;font-weight:700;'
                f'font-size:0.8em;text-transform:uppercase;letter-spacing:.05em">{label}</td></tr>')

    # Channels by DCA group
    dca_order = sorted(by_dca.keys(), key=lambda x: (x == 0, x))
    for dca_num in dca_order:
        items = by_dca[dca_num]
        if dca_num == 0:
            label = 'Ungrouped channels'
            color = '#475569'
        else:
            d = dcas.get(dca_num, {})
            dname = d.get('name', f'DCA {dca_num}')
            label = f'DCA {dca_num}: {dname}'
            color, _ = scribble_colors(d.get('color', 'WH'))
        rows.append(section_header(label, color))
        for num, c in items:
            rows.append(channel_row(num, c, f'dca{dca_num}'))

    # AuxIns
    if data['auxins']:
        rows.append(section_header('Aux Inputs', '#0f172a'))
        for num in sorted(data['auxins']):
            rows.append(channel_row(num, data['auxins'][num], 'auxin'))

    # FX Returns (only active ones)
    active_fx = [(n, c) for n, c in data['fxrtns'].items() if c['active']]
    if active_fx:
        rows.append(section_header('FX Returns', '#0f172a'))
        for num, c in sorted(active_fx):
            rows.append(channel_row(num, c, 'fxrtn'))

    return '<table class="routing-matrix">' + '\n'.join(rows) + '</table>'


# ── Signal flow SVG ───────────────────────────────────────────────────────────

def gen_flow_svg(data):
    buses    = data['buses']
    outputs  = data['outputs']
    matrices = data['matrices']

    FX_LOOP_X                          = 30   # leftmost x for FX return arc
    CH_X, BUS_X, MTX_X, OUT_X         = 150, 460, 760, 1060
    NODE_W_CH, NODE_W_BUS              = 140, 140
    NODE_W_MTX, NODE_W_OUT             = 130, 165
    CH_H, BUS_H, MTX_H, OUT_H         = 20, 34, 28, 22
    MTX_COLOR                          = '#5b21b6'
    FX_COLOR                           = '#b45309'   # amber-700

    # Build channel list (active only), with section gaps tracked
    ch_items  = []
    gap_before = set()   # indices where extra vertical gap is inserted

    for num in sorted(data['channels']):
        c = data['channels'][num]
        if c['active']:
            ch_items.append(('ch', num, c))

    active_aux = [num for num in sorted(data['auxins']) if data['auxins'][num]['active']]
    if active_aux:
        gap_before.add(len(ch_items))
        for num in active_aux:
            ch_items.append(('aux', num, data['auxins'][num]))

    active_fx = sorted(num for num, c in data['fxrtns'].items() if c['active'])
    if active_fx:
        gap_before.add(len(ch_items))
        for num in active_fx:
            ch_items.append(('fx', num, data['fxrtns'][num]))

    SVG_PAD    = 30
    ch_spacing = max(CH_H + 4, 24)
    bus_spacing = max(BUS_H + 6, 40)

    # Channel Y positions (with extra gap at section boundaries)
    ch_y = {}
    y = SVG_PAD + CH_H // 2
    for i, (kind, num, _) in enumerate(ch_items):
        if i in gap_before:
            y += ch_spacing           # one extra slot of space between sections
        ch_y[(kind, num)] = y
        y += ch_spacing

    # Bus Y positions (centred on channel column height)
    bus_nums    = list(range(1, 17))
    total_bus_h = (len(bus_nums) - 1) * bus_spacing
    total_ch_h  = max(ch_y.values()) if ch_y else 400
    bus_start   = max(SVG_PAD, (total_ch_h - total_bus_h) // 2)
    bus_y       = {}
    for i, bn in enumerate(bus_nums):
        bus_y[bn] = bus_start + i * bus_spacing + BUS_H // 2

    # Main L/R Y position (above first bus)
    main_y = max(SVG_PAD + BUS_H, bus_start - bus_spacing)

    # Matrix node Y positions (centred on bus span)
    mtx_nums = sorted(matrices.keys()) or list(range(1, 7))
    mtx_spacing = max(MTX_H + 10, 52)
    mtx_total_h = (len(mtx_nums) - 1) * mtx_spacing
    bus_mid     = (bus_y[bus_nums[0]] + bus_y[bus_nums[-1]]) // 2
    mtx_start   = bus_mid - mtx_total_h // 2
    mtx_y       = {}
    for i, mn in enumerate(mtx_nums):
        mtx_y[mn] = mtx_start + i * mtx_spacing + MTX_H // 2

    # Output Y positions (centred on matrix span)
    out_nums    = sorted(outputs.keys())
    out_spacing = max(OUT_H + 4, 28)
    total_out_h = (len(out_nums) - 1) * out_spacing
    out_mid     = (mtx_y[mtx_nums[0]] + mtx_y[mtx_nums[-1]]) // 2 if mtx_y else bus_mid
    out_start   = max(SVG_PAD, out_mid - total_out_h // 2)
    out_y       = {}
    for i, on in enumerate(out_nums):
        out_y[on] = out_start + i * out_spacing + OUT_H // 2

    SVG_H = max(
        (max(ch_y.values())  if ch_y  else 0) + SVG_PAD + CH_H,
        (max(bus_y.values()) if bus_y else 0) + SVG_PAD + BUS_H,
        (max(mtx_y.values()) if mtx_y else 0) + SVG_PAD + MTX_H,
        (max(out_y.values()) if out_y else 0) + SVG_PAD + OUT_H,
        300
    )
    SVG_W = OUT_X + NODE_W_OUT + SVG_PAD

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" '
             f'width="{SVG_W}" height="{SVG_H}" '
             f'style="font-family:system-ui,sans-serif;font-size:11px">']
    parts.append('<defs><style>.fe{transition:opacity .2s}.fe.dim{opacity:.08}'
                 '.fn{transition:opacity .2s}.fn.dim{opacity:.2}</style></defs>')

    def bezier(x1, y1, x2, y2):
        cx = x1 + (x2 - x1) * 0.5
        return f'M{x1},{y1} C{cx},{y1} {cx},{y2} {x2},{y2}'

    # ── Edges: channel → bus ──────────────────────────────────────────────────
    for kind, num, c in ch_items:
        cy = ch_y[(kind, num)]
        dcas_list = c['dcas']
        dca_cls = ' '.join(f'dca-{d}' for d in dcas_list) if dcas_list else 'dca-0'
        for bn, send in c['sends'].items():
            db = send.get('db')
            if db is None or bn not in bus_y: continue
            by = bus_y[bn]
            color = BUS_TYPE_COLOR[bus_type(bn)]
            sw = max(0.6, min(3.0, 3.0 + db * 0.08))
            parts.append(
                f'<path class="fe {dca_cls}" d="{bezier(CH_X+NODE_W_CH, cy, BUS_X, by)}" '
                f'fill="none" stroke="{color}" stroke-width="{sw:.1f}" opacity="0.35" '
                f'data-db="{db}" data-dcas=\'{json.dumps(dcas_list)}\'>'
                f'<title>{"CH" if kind=="ch" else "AuxIn"}{num:02d} {c["name"]} → '
                f'Bus {bn:02d} {buses.get(bn,{}).get("name","")} ({fmt_db(db)} dB)</title>'
                f'</path>'
            )

    # ── Edges: FX bus → (processor) → FX returns  (loop arcs) ───────────────
    for fx_num, fx_info in sorted(data.get('fx_slots', {}).items()):
        src_bus = decode_mix_source(fx_info.get('source_l', ''))
        if not src_bus or src_bus not in bus_y: continue
        rtn_l, rtn_r = 2*fx_num - 1, 2*fx_num
        fy_l = ch_y.get(('fx', rtn_l))
        fy_r = ch_y.get(('fx', rtn_r))
        if fy_l is None and fy_r is None: continue
        fy_mid = (fy_l + fy_r) // 2 if (fy_l and fy_r) else (fy_l or fy_r)
        by = bus_y[src_bus]
        # Arc: left edge of FX bus → swing left past channel column → FXRtn right edge
        cx = CH_X + NODE_W_CH
        path = f'M{BUS_X},{by} C{FX_LOOP_X},{by} {FX_LOOP_X},{fy_mid} {cx},{fy_mid}'
        fx_type = fx_info.get('type_name', f'FX{fx_num}')
        parts.append(
            f'<path class="fe" d="{path}" fill="none" stroke="{FX_COLOR}" '
            f'stroke-width="1.5" stroke-dasharray="5,3" opacity="0.85">'
            f'<title>FX {fx_num} {FX_TYPE_NAMES.get(fx_type, fx_type)}: '
            f'Bus {src_bus:02d} → FXRtn {rtn_l:02d}/{rtn_r:02d}</title>'
            f'</path>'
        )
        # Rotated type label on the arc's vertical segment
        lx, ly = FX_LOOP_X + 9, (by + fy_mid) // 2
        parts.append(
            f'<text x="{lx}" y="{ly}" fill="{FX_COLOR}" font-size="8.5" font-weight="700" '
            f'text-anchor="middle" transform="rotate(-90,{lx},{ly})">'
            f'FX{fx_num} {fx_type}</text>'
        )

    # ── Edges: bus → matrix ───────────────────────────────────────────────────
    for bn in bus_nums:
        b = buses.get(bn, {})
        for mn, send in b.get('sends_to_matrix', {}).items():
            db = send.get('db')
            if db is None or mn not in mtx_y: continue
            by = bus_y[bn]
            my = mtx_y[mn]
            color = BUS_TYPE_COLOR[bus_type(bn)]
            parts.append(
                f'<path class="fe" d="{bezier(BUS_X+NODE_W_BUS, by, MTX_X, my)}" '
                f'fill="none" stroke="{color}" stroke-width="2" opacity="0.55">'
                f'<title>Bus {bn:02d} {b.get("name","")} → Matrix {mn:02d} '
                f'{matrices.get(mn,{}).get("name","")} ({fmt_db(db)} dB)</title>'
                f'</path>'
            )

    # ── Edges: main L/R → matrix ──────────────────────────────────────────────
    ms = data['main_st']
    for mn, send in ms.get('sends_to_matrix', {}).items():
        db = send.get('db')
        if db is None or mn not in mtx_y: continue
        my = mtx_y[mn]
        parts.append(
            f'<path class="fe" d="{bezier(BUS_X+NODE_W_BUS, main_y, MTX_X, my)}" '
            f'fill="none" stroke="#64748b" stroke-width="2" opacity="0.55">'
            f'<title>{ms["name"]} → Matrix {mn:02d} '
            f'{matrices.get(mn,{}).get("name","")} ({fmt_db(db)} dB)</title>'
            f'</path>'
        )

    # ── Edges: matrix → output ────────────────────────────────────────────────
    for on, out_info in outputs.items():
        if on not in out_y: continue
        oy = out_y[on]
        sl, st = out_info.get('src_label',''), out_info.get('src_type','')
        if st == 'matrix':
            bm = re.search(r'(\d+)', sl)
            if bm:
                mn = int(bm.group(1))
                if mn in mtx_y:
                    my = mtx_y[mn]
                    parts.append(
                        f'<path class="fe" d="{bezier(MTX_X+NODE_W_MTX, my, OUT_X, oy)}" '
                        f'fill="none" stroke="{MTX_COLOR}" stroke-width="2" opacity="0.6">'
                        f'<title>Matrix {mn:02d} {matrices.get(mn,{}).get("name","")} → OUT {on:02d}</title>'
                        f'</path>'
                    )
        elif st == 'bus':
            bm = re.search(r'(\d+)', sl)
            if bm:
                bn = int(bm.group(1))
                if bn in bus_y:
                    by = bus_y[bn]
                    color = BUS_TYPE_COLOR[bus_type(bn)]
                    parts.append(
                        f'<path class="fe" d="{bezier(BUS_X+NODE_W_BUS, by, OUT_X, oy)}" '
                        f'fill="none" stroke="{color}" stroke-width="2" opacity="0.6">'
                        f'<title>Bus {bn:02d} {buses.get(bn,{}).get("name","")} → OUT {on:02d}</title>'
                        f'</path>'
                    )
        elif st == 'main':
            parts.append(
                f'<path class="fe" d="{bezier(BUS_X+NODE_W_BUS, main_y, OUT_X, oy)}" '
                f'fill="none" stroke="#64748b" stroke-width="2" opacity="0.6">'
                f'<title>{sl} → OUT {on:02d}</title>'
                f'</path>'
            )

    # ── Channel / AuxIn / FXRtn nodes ────────────────────────────────────────
    for kind, num, c in ch_items:
        cy = ch_y[(kind, num)]
        dcas_list = c['dcas']
        if kind == 'fx':
            fx_slot = (num + 1) // 2
            fx_type = data['fx_slots'].get(fx_slot, {}).get('type_name', '')
            bg, fg  = FX_COLOR, '#fff'
            label   = f'↩ FX{fx_slot} {"L" if num%2==1 else "R"} ({fx_type})'
            dca_cls = 'dca-0'
        else:
            bg, fg  = scribble_colors(c.get('color', 'WH'))
            dca_cls = ' '.join(f'dca-{d}' for d in dcas_list) if dcas_list else 'dca-0'
            label   = f'{"" if kind=="ch" else "⎙ "}{num:02d} {c["name"]}'
        parts.append(
            f'<g class="fn {dca_cls}" data-dcas=\'{json.dumps(dcas_list)}\'>'
            f'<rect x="{CH_X}" y="{cy-CH_H//2}" width="{NODE_W_CH}" height="{CH_H}" '
            f'rx="3" fill="{bg}"/>'
            f'<text x="{CH_X+6}" y="{cy+4}" fill="{fg}" font-size="10" font-weight="600">{label}</text>'
            f'</g>'
        )

    # ── Bus nodes ─────────────────────────────────────────────────────────────
    for bn in bus_nums:
        by = bus_y[bn]
        b = buses.get(bn, {})
        label = f'{bn:02d} {b.get("name", f"Bus {bn:02d}")}'
        bg, fg = scribble_colors(b.get('color', 'WH'))
        parts.append(
            f'<g class="fn">'
            f'<rect x="{BUS_X}" y="{by-BUS_H//2}" width="{NODE_W_BUS}" height="{BUS_H}" '
            f'rx="3" fill="{bg}"/>'
            f'<text x="{BUS_X+6}" y="{by+4}" fill="{fg}" font-size="11" font-weight="600">{label}</text>'
            f'</g>'
        )

    # ── Main L/R node ─────────────────────────────────────────────────────────
    ms_bg, ms_fg = scribble_colors(ms.get('color', 'WH'))
    parts.append(
        f'<g class="fn">'
        f'<rect x="{BUS_X}" y="{main_y-BUS_H//2}" width="{NODE_W_BUS}" height="{BUS_H}" '
        f'rx="3" fill="{ms_bg}"/>'
        f'<text x="{BUS_X+6}" y="{main_y+4}" fill="{ms_fg}" font-size="11" font-weight="600">'
        f'{ms["name"]}</text>'
        f'</g>'
    )

    # ── Matrix nodes ──────────────────────────────────────────────────────────
    for mn in mtx_nums:
        my = mtx_y[mn]
        mt = matrices.get(mn, {})
        mname = mt.get('name') or f'Mtx {mn:02d}'
        label = f'{mn:02d} {mname}'
        parts.append(
            f'<g class="fn">'
            f'<rect x="{MTX_X}" y="{my-MTX_H//2}" width="{NODE_W_MTX}" height="{MTX_H}" '
            f'rx="3" fill="{MTX_COLOR}"/>'
            f'<text x="{MTX_X+6}" y="{my+4}" fill="#fff" font-size="11" font-weight="600">{label}</text>'
            f'</g>'
        )

    # ── Output nodes ──────────────────────────────────────────────────────────
    bg_map = {'bus': '#1e40af', 'main': '#374151', 'local': '#065f46',
              'matrix': '#4c1d95', 'off': '#d1d5db', 'unknown': '#9ca3af'}
    for on in out_nums:
        oy = out_y[on]
        out_info = outputs.get(on, {})
        sl = out_info.get('src_label', '?')
        st = out_info.get('src_type', 'unknown')
        bg = bg_map.get(st, '#9ca3af')
        parts.append(
            f'<g class="fn">'
            f'<rect x="{OUT_X}" y="{oy-OUT_H//2}" width="{NODE_W_OUT}" height="{OUT_H}" '
            f'rx="3" fill="{bg}"/>'
            f'<text x="{OUT_X+6}" y="{oy+4}" fill="#fff" font-size="10">'
            f'OUT {on:02d} → {sl}</text>'
            f'</g>'
        )

    # ── Column labels ─────────────────────────────────────────────────────────
    def col_label(x, w, text):
        return (f'<text x="{x + w//2}" y="14" text-anchor="middle" '
                f'fill="#475569" font-size="9" font-weight="700" letter-spacing=".06em">'
                f'{text}</text>')

    parts.append(col_label(CH_X,  NODE_W_CH,  'CHANNELS / FX RETURNS'))
    parts.append(col_label(BUS_X, NODE_W_BUS, 'MIX BUSES'))
    parts.append(col_label(MTX_X, NODE_W_MTX, 'MATRIX'))
    parts.append(col_label(OUT_X, NODE_W_OUT, 'XLR OUTPUTS'))

    parts.append('</svg>')
    return '\n'.join(parts)


# ── Bus → Matrix routing table ────────────────────────────────────────────────

def gen_matrix_routing_table(data):
    buses    = data['buses']
    matrices = data['matrices']
    main_st  = data['main_st']

    mtx_nums = sorted(matrices.keys())
    if not mtx_nums:
        return ''

    # Collect sources that have at least one active matrix send
    sources = []
    for bn in sorted(buses):
        b = buses[bn]
        if any(s.get('db') is not None for s in b['sends_to_matrix'].values()):
            sources.append(('bus', bn, b))
    if any(s.get('db') is not None for s in main_st['sends_to_matrix'].values()):
        sources.append(('main', 0, main_st))

    if not sources:
        return '<p style="color:#64748b;font-size:.85rem;margin-top:8px">No active bus→matrix sends in this scene.</p>'

    rows = ['<table class="routing-matrix">']

    # Header row
    hdr = '<tr><th class="mat-corner">Source / Matrix Out</th>'
    for mn in mtx_nums:
        mname = matrices[mn].get('name') or f'Mtx {mn:02d}'
        hdr += (f'<th class="mat-hdr" style="background:#5b21b6;color:#fff">'
                f'<span class="bus-num">{mn:02d}</span>'
                f'<br><span class="bus-name">{mname}</span></th>')
    hdr += '</tr>'
    rows.append(hdr)

    for src_type, src_num, src in sources:
        if src_type == 'bus':
            label = f'{src_num:02d} {src["name"]}'
        else:
            label = src['name']
        bg, fg = scribble_colors(src.get('color', 'WH'))

        row = (f'<tr class="ch-row" data-dcas="[]">'
               f'<td class="ch-label" style="background:{bg};color:{fg}">{label}</td>')
        for mn in mtx_nums:
            send = src['sends_to_matrix'].get(mn, {})
            db   = send.get('db')
            bg_c, fg_c = level_color(db)
            db_str = fmt_db(db)
            db_attr = f'data-db="{db}"' if db is not None else ''
            row += (f'<td class="mat-cell" {db_attr} style="background:{bg_c};color:{fg_c}" '
                    f'title="→ Matrix {mn:02d}: {db_str or "—"}">{db_str}</td>')
        row += '</tr>'
        rows.append(row)

    rows.append('</table>')
    return '\n'.join(rows)


# ── FX summary table ──────────────────────────────────────────────────────────

def gen_fx_summary_table(data):
    fx_slots = data.get('fx_slots', {})
    buses    = data['buses']
    fxrtns   = data['fxrtns']

    active = []
    for num in sorted(fx_slots):
        slot  = fx_slots[num]
        rtn_l = fxrtns.get(2*num - 1, {})
        rtn_r = fxrtns.get(2*num,     {})
        if rtn_l.get('active') or rtn_r.get('active'):
            active.append((num, slot, rtn_l, rtn_r))

    if not active:
        return '<p style="color:#64748b;font-size:.85rem">No active FX return loops found.</p>'

    rows = ['<table class="out-table"><thead><tr>'
            '<th>Slot</th><th>Type</th><th>Source Bus</th>'
            '<th>Returns</th><th>Feeds Into</th>'
            '</tr></thead><tbody>']

    for num, slot, rtn_l, rtn_r in active:
        fx_type   = slot.get('type_name', '')
        type_name = FX_TYPE_NAMES.get(fx_type, fx_type) if fx_type else '—'
        src_bus_n = decode_mix_source(slot.get('source_l', ''))
        if src_bus_n:
            b = buses.get(src_bus_n, {})
            src_label = f'{src_bus_n:02d} {b.get("name","")}'
        else:
            src_label = slot.get('source_l') or '—'

        rtn_nums = f'{2*num-1:02d} / {2*num:02d}'

        # Aggregate destination buses from both L and R returns
        dest = {}
        for rtn in (rtn_l, rtn_r):
            for bn, send in rtn.get('sends', {}).items():
                db = send.get('db')
                if db is not None:
                    dest[bn] = max(dest.get(bn, -999), db)

        if dest:
            chips = []
            for bn in sorted(dest):
                b  = buses.get(bn, {})
                bt = bus_type(bn)
                bg = BUS_TYPE_COLOR[bt]
                chips.append(
                    f'<span style="background:{bg};color:#fff;padding:1px 6px;'
                    f'border-radius:3px;font-size:.78em;margin-right:3px">'
                    f'{bn:02d} {b.get("name","")} ({fmt_db(dest[bn])} dB)</span>'
                )
            dest_html = ''.join(chips)
        else:
            dest_html = '—'

        rows.append(
            f'<tr>'
            f'<td class="out-num">FX {num}</td>'
            f'<td><strong>{type_name}</strong></td>'
            f'<td style="font-family:monospace">{src_label}</td>'
            f'<td style="font-family:monospace">FXRtn {rtn_nums}</td>'
            f'<td>{dest_html}</td>'
            f'</tr>'
        )

    rows.append('</tbody></table>')
    return '\n'.join(rows)


# ── Output assignments table ──────────────────────────────────────────────────

def gen_outputs_table(data):
    buses = data['buses']
    rows = ['<table class="out-table"><thead><tr>'
            '<th>XLR Out</th><th>Source</th>'
            '<th>P16 Out</th><th>Source</th>'
            '</tr></thead><tbody>']
    out_nums = range(1, 17)
    for i in out_nums:
        out = data['outputs'].get(i, {})
        p16 = data['p16_outputs'].get(i, {})
        o_label = out.get('src_label', '—')
        p_label = p16.get('src_label', '—')
        o_type  = out.get('src_type', '')
        p_type  = p16.get('src_type', '')
        type_bg = {'bus': '#dbeafe', 'main': '#f1f5f9', 'local': '#dcfce7',
                   'matrix': '#ede9fe', 'off': '#f1f5f9'}
        rows.append(
            f'<tr>'
            f'<td class="out-num">OUT {i:02d}</td>'
            f'<td style="background:{type_bg.get(o_type,"#fff")}">{o_label}</td>'
            f'<td class="out-num">P16 {i:02d}</td>'
            f'<td style="background:{type_bg.get(p_type,"#fff")}">{p_label}</td>'
            f'</tr>'
        )
    rows.append('</tbody></table>')
    return '\n'.join(rows)


# ── HTML assembly ─────────────────────────────────────────────────────────────

CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: system-ui, -apple-system, sans-serif; background: #0f172a; color: #e2e8f0; }
.header { padding: 16px 20px; background: #1e293b; border-bottom: 1px solid #334155; position: sticky; top: 0; z-index: 100; }
.header h1 { font-size: 1.1rem; font-weight: 700; margin-bottom: 10px; color: #f1f5f9; }
.controls { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }
.view-toggle button { padding: 5px 14px; border: 1px solid #475569; background: #1e293b;
  color: #94a3b8; cursor: pointer; border-radius: 4px; font-size: 0.85rem; }
.view-toggle button.active { background: #3b82f6; border-color: #3b82f6; color: #fff; }
.dca-filters { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.dca-filters label.head { color: #94a3b8; font-size: 0.8rem; margin-right: 2px; }
.dca-chip { display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px;
  border-radius: 12px; font-size: 0.78rem; cursor: pointer; user-select: none; }
.dca-chip input { width: 12px; height: 12px; cursor: pointer; }
.level-filter { display: flex; align-items: center; gap: 8px; font-size: 0.82rem; color: #94a3b8; }
.level-filter input[type=range] { width: 120px; }
.view { display: none; padding: 16px; overflow: auto; }
.view.active { display: block; }

/* Matrix */
.routing-matrix { border-collapse: collapse; font-size: 0.75rem; }
.routing-matrix th, .routing-matrix td { border: 1px solid #1e293b; }
.mat-corner { background: #1e293b; min-width: 120px; padding: 4px 6px; position: sticky; left: 0; z-index: 10; }
.mat-hdr { padding: 4px 3px; text-align: center; min-width: 52px; position: sticky; top: 0; }
.bus-num { font-size: 0.9em; font-weight: 700; display: block; }
.bus-name { font-size: 0.7em; opacity: .85; display: block; white-space: nowrap; overflow: hidden; max-width: 50px; }
.ch-label { padding: 2px 6px; white-space: nowrap; position: sticky; left: 0; z-index: 5; font-weight: 600; }
.sec-hdr td { font-size: 0.72rem; }
.mat-cell { text-align: center; padding: 1px 2px; font-size: 0.72rem; min-width: 52px; white-space: nowrap; }
.mat-cell.hidden-cell { background: #fff !important; color: #fff !important; }
.pre-dot { font-size: 0.6em; color: #6366f1; margin-left: 1px; }

/* Flow SVG container */
.flow-wrap { overflow: auto; padding-bottom: 16px; }
.flow-wrap svg { display: block; }

/* Outputs table */
.out-table { border-collapse: collapse; font-size: 0.82rem; margin-top: 20px; }
.out-table th { background: #1e293b; padding: 6px 12px; text-align: left; color: #94a3b8; }
.out-table td { padding: 4px 12px; border-bottom: 1px solid #1e293b; }
.out-num { font-weight: 700; color: #94a3b8; font-family: monospace; }

/* Legend */
.legend { display: flex; flex-wrap: wrap; gap: 8px; padding: 10px 0; font-size: 0.75rem; }
.legend-item { display: flex; align-items: center; gap: 4px; }
.legend-swatch { width: 16px; height: 16px; border-radius: 3px; }
"""

JS = """
const btns = { matrix: document.getElementById('btn-matrix'), flow: document.getElementById('btn-flow') };
const views = { matrix: document.getElementById('view-matrix'), flow: document.getElementById('view-flow') };

function switchView(name) {
  Object.entries(btns).forEach(([k,b]) => b.classList.toggle('active', k===name));
  Object.entries(views).forEach(([k,v]) => v.classList.toggle('active', k===name));
}
btns.matrix.addEventListener('click', () => switchView('matrix'));
btns.flow.addEventListener('click', () => switchView('flow'));

const activeDCAs = new Set();
document.querySelectorAll('.dca-cb').forEach(cb => cb.addEventListener('change', applyFilters));

function applyFilters() {
  activeDCAs.clear();
  document.querySelectorAll('.dca-cb:checked').forEach(c => activeDCAs.add(+c.value));
  const showAll = activeDCAs.size === 0;

  // Matrix rows
  document.querySelectorAll('tr.ch-row').forEach(tr => {
    const dcas = JSON.parse(tr.dataset.dcas || '[]');
    tr.style.display = (showAll || dcas.some(d => activeDCAs.has(d))) ? '' : 'none';
  });

  // SVG: dim non-matching nodes and edges
  ['fe','fn'].forEach(cls => {
    document.querySelectorAll('.' + cls + '[data-dcas]').forEach(el => {
      const dcas = JSON.parse(el.dataset.dcas || '[]');
      const match = showAll || dcas.some(d => activeDCAs.has(d));
      el.classList.toggle('dim', !match);
    });
  });
}

const slider = document.getElementById('level-slider');
const levelSpan = document.getElementById('level-val');
slider.addEventListener('input', () => {
  const t = +slider.value;
  levelSpan.textContent = t <= -90 ? '−∞' : t + ' dB';
  document.querySelectorAll('td.mat-cell[data-db]').forEach(td => {
    td.classList.toggle('hidden-cell', +td.dataset.db < t);
  });
  document.querySelectorAll('.fe[data-db]').forEach(el => {
    el.style.opacity = +el.dataset.db < t ? '0' : '';
  });
});
"""

def gen_html(data):
    scene = data['scene_name']
    dcas  = data['dcas']

    dca_chips = '<label class="head">DCA:</label>'
    for num in sorted(dcas):
        d = dcas[num]
        bg, fg = scribble_colors(d.get('color', 'WH'))
        dca_chips += (
            f'<label class="dca-chip" style="background:{bg};color:{fg}">'
            f'<input type="checkbox" class="dca-cb" value="{num}"> {d["name"] or f"DCA {num}"}'
            f'</label>'
        )

    legend_items = [
        ('#166534', 'white', '≥ 0 dB'),
        ('#22c55e', 'dark',  '0 to −10'),
        ('#86efac', 'dark',  '−10 to −20'),
        ('#fef08a', 'dark',  '−20 to −30'),
        ('#fed7aa', 'dark',  '−30 to −50'),
        ('#e2e8f0', 'dark',  '−50 to −70'),
        ('#f8fafc', 'dark',  '< −70 dB'),
    ]
    legend_html = '<div class="legend">' + ''.join(
        f'<div class="legend-item">'
        f'<div class="legend-swatch" style="background:{bg};border:1px solid #e2e8f0"></div>'
        f'<span style="color:#94a3b8">{label}</span>'
        f'</div>'
        for bg, _, label in legend_items
    ) + '</div>'

    matrix   = gen_matrix_table(data)
    flow     = gen_flow_svg(data)
    outs     = gen_outputs_table(data)
    mtx_tbl  = gen_matrix_routing_table(data)
    fx_tbl   = gen_fx_summary_table(data)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>X32 Map — {scene}</title>
<style>{CSS}</style>
</head>
<body>
<div class="header">
  <h1>X32 Map — {scene}</h1>
  <div class="controls">
    <div class="view-toggle">
      <button id="btn-matrix" class="active">Matrix View</button>
      <button id="btn-flow">Signal Flow</button>
    </div>
    <div class="dca-filters">{dca_chips}</div>
    <div class="level-filter">
      Min level: <strong id="level-val">−∞</strong>
      <input type="range" id="level-slider" min="-90" max="0" value="-90" step="5">
    </div>
  </div>
</div>

<div id="view-matrix" class="view active">
  {legend_html}
  <div style="overflow:auto">{matrix}</div>
  <h2 style="margin-top:24px;font-size:.9rem;color:#94a3b8;font-weight:700">OUTPUT ASSIGNMENTS</h2>
  {outs}
  <h2 style="margin-top:28px;font-size:.9rem;color:#94a3b8;font-weight:700">BUS → MATRIX SENDS</h2>
  {mtx_tbl}
  <h2 style="margin-top:28px;font-size:.9rem;color:#94a3b8;font-weight:700">FX LOOPS</h2>
  {fx_tbl}
</div>

<div id="view-flow" class="view">
  <p style="color:#64748b;font-size:.8rem;margin-bottom:8px">
    Edges show active sends only (level &gt; −∞). Use DCA filter to highlight groups.
  </p>
  <div class="flow-wrap">{flow}</div>
</div>

<script>{JS}</script>
</body>
</html>"""


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print('Usage: python3 x32_routing.py <scene_file.scn>', file=sys.stderr)
        sys.exit(1)

    scene_path = Path(sys.argv[1]).resolve()
    out_path   = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else \
                 scene_path.with_suffix('.html')

    print(f'Parsing {scene_path}...')
    data = parse_scene(scene_path)

    print(f'Scene: "{data["scene_name"]}"')
    print(f'  Channels: {len(data["channels"])} ({sum(1 for c in data["channels"].values() if c["active"])} active)')
    print(f'  AuxIns:   {len(data["auxins"])}')
    print(f'  Buses:    {len(data["buses"])}')
    print(f'  DCAs:     {len(data["dcas"])}')
    print(f'  Outputs:  {len(data["outputs"])} XLR, {len(data["p16_outputs"])} P16')

    html = gen_html(data)
    out_path.write_text(html, encoding='utf-8')
    print(f'Written: {out_path}')


if __name__ == '__main__':
    main()
