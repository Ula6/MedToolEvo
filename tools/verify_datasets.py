"""Verify complete dataset bytes, record counts and existing derived input files."""
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def main():
    manifest = json.loads((ROOT / 'DATASETS_MANIFEST.json').read_text(encoding='utf-8'))
    for row in manifest['files']:
        path = ROOT / row['path']
        if not path.is_file():
            raise SystemExit('Missing dataset file: ' + row['path'])
        if path.stat().st_size != row['bytes'] or digest(path) != row['sha256']:
            raise SystemExit('Dataset content mismatch; run git lfs pull if this is a pointer: ' + row['path'])
    results = []
    for row in manifest['original_datasets']:
        data = json.loads((ROOT / row['path']).read_text(encoding='utf-8-sig'))
        rows = data['questions'] if isinstance(data, dict) else data
        key = 'type' if isinstance(data, dict) else 'task_type'
        assert len(rows) == row['records']
        assert len(set(str(r['id']) for r in rows)) == row['unique_ids']
        assert dict(collections.Counter(r[key] for r in rows)) == row['type_counts']
        results.append({'path':row['path'],'records':len(rows),'sha256':row['sha256']})
    print(json.dumps({'verified_data_files':len(manifest['files']),
                      'original_datasets':results,'model_calls':0},indent=2))


if __name__ == '__main__':
    main()
