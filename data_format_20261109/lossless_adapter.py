"""Experimental transport layout only; no medical inference or answer rewriting."""
import copy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def encode(task):
    task = copy.deepcopy(task)
    evidence = task.pop('evidence')
    columns = list(dict.fromkeys(key for row in evidence for key in row))
    sources, source_indexes, rows, missing = [], {}, [], []
    for original in evidence:
        row = []
        missing.append([i for i, key in enumerate(columns) if key not in original])
        for key in columns:
            value = original.get(key)
            if key == 'source' and key in original:
                lookup = canonical(value)
                if lookup not in source_indexes:
                    source_indexes[lookup] = len(sources)
                    sources.append(value)
                value = source_indexes[lookup]
            row.append(value)
        rows.append(row)
    task['evidence_table'] = {'columns':columns, 'rows':rows,
                              'sources':sources, 'missing_columns':missing}
    return task


def decode(task):
    task = copy.deepcopy(task)
    table = task.pop('evidence_table')
    evidence = []
    for row, missing in zip(table['rows'], table['missing_columns'], strict=True):
        record = {}
        for i, (key, value) in enumerate(zip(table['columns'], row, strict=True)):
            if i in missing:
                continue
            record[key] = table['sources'][value] if key == 'source' else value
        evidence.append(record)
    task['evidence'] = evidence
    return task


def main():
    data = json.loads((HERE/'original_public_tasks.json').read_text(encoding='utf-8'))
    tasks = data['tasks']
    assert len(tasks) == len({t['id'] for t in tasks}) == 100
    assert [t['id'] for t in tasks] == data['pilot_ids']
    formatted = [encode(task) for task in tasks]
    restored = [decode(task) for task in formatted]
    assert canonical(restored) == canonical(tasks), 'Lossless roundtrip failed'
    forbidden = {'exact_answer','ideal_answer','gold','reference','references','answer'}
    assert all(not (set(t) & forbidden) for t in tasks)
    texts = [e['text'] for t in tasks for e in t['evidence']]
    assert texts == [e['text'] for t in restored for e in t['evidence']]
    original_bytes = len(canonical(tasks).encode())
    formatted_bytes = len(canonical(formatted).encode())
    report = {
        'purpose':'Lossless layout validation, not a model performance experiment',
        'source_run':data['run'], 'task_count':len(tasks),
        'roundtrip_equal_tasks':sum(a == b for a,b in zip(tasks,restored,strict=True)),
        'fixed_ids_and_order_preserved':True, 'original_texts_exactly_preserved':True,
        'evidence_count':len(texts), 'reference_files_read':False,
        'medical_annotation_added':False, 'model_or_gpu_calls':0,
        'original_canonical_sha256':hashlib.sha256(canonical(tasks).encode()).hexdigest(),
        'restored_canonical_sha256':hashlib.sha256(canonical(restored).encode()).hexdigest(),
        'compact_utf8_bytes_before':original_bytes,
        'compact_utf8_bytes_after':formatted_bytes,
        'byte_reduction_fraction':1-formatted_bytes/original_bytes,
        'byte_counts_are_not_model_token_counts':True,
        'limitations':['New layout requires a matching consumer adapter or prompt.',
                       'No answer quality, failure repair or tool registration improvement measured.',
                       'No frozen pilot files or metrics modified.']}
    (HERE/'formatted_public_tasks.json').write_text(json.dumps(
        {'format_version':'evidence-table-layout-v1','source_run':data['run'],
         'source_files':data['source_files'],'tasks':formatted},ensure_ascii=False,indent=2),encoding='utf-8')
    (HERE/'format_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    sample = {'note':'Layout illustration only; first two original evidence segments.',
              'before':{**tasks[0],'evidence':tasks[0]['evidence'][:2]}}
    sample['after'] = encode(sample['before'])
    (HERE/'format_sample.json').write_text(json.dumps(sample,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True))


if __name__ == '__main__':
    main()
