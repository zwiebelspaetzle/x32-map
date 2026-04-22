#!/usr/bin/env python3
"""Regenerate snapshot golden files. Run this intentionally when HTML output changes."""
import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from x32_map import parse_scene, gen_html

SCENE = Path(__file__).parent.parent / 'test_scene.scn'
SNAPSHOTS = Path(__file__).parent / 'snapshots'
HTML_OUT = SNAPSHOTS / 'test_scene.html'
HASH_OUT = SNAPSHOTS / 'test_scene.html.sha256'


def extract_db_values(html):
    return sorted(set(re.findall(r'data-db="([^"]+)"', html)))


def extract_channel_names(html):
    return sorted(set(re.findall(r'class="ch-label"[^>]*>([^<]+)<', html)))


def main():
    if not SCENE.exists():
        print(f'ERROR: {SCENE} not found', file=sys.stderr)
        sys.exit(1)

    SNAPSHOTS.mkdir(exist_ok=True)

    data = parse_scene(SCENE)
    new_html = gen_html(data)
    new_hash = hashlib.sha256(new_html.encode()).hexdigest()

    if HTML_OUT.exists():
        old_html = HTML_OUT.read_text(encoding='utf-8')
        old_dbs = extract_db_values(old_html)
        new_dbs = extract_db_values(new_html)
        old_names = extract_channel_names(old_html)
        new_names = extract_channel_names(new_html)

        added_dbs = set(new_dbs) - set(old_dbs)
        removed_dbs = set(old_dbs) - set(new_dbs)
        added_names = set(new_names) - set(old_names)
        removed_names = set(old_names) - set(new_names)

        if added_dbs or removed_dbs or added_names or removed_names:
            print('Structural diff:')
            if added_dbs:   print(f'  + db values: {sorted(added_dbs)}')
            if removed_dbs: print(f'  - db values: {sorted(removed_dbs)}')
            if added_names:   print(f'  + channels: {sorted(added_names)}')
            if removed_names: print(f'  - channels: {sorted(removed_names)}')
        else:
            print('No structural changes (channel names and db values unchanged).')
    else:
        print('Creating new snapshot.')

    HTML_OUT.write_text(new_html, encoding='utf-8')
    HASH_OUT.write_text(new_hash + '\n', encoding='utf-8')
    print(f'Wrote {HTML_OUT}')
    print(f'Wrote {HASH_OUT}  ({new_hash[:16]}...)')


if __name__ == '__main__':
    main()
