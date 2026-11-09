"""Offline structural oracle. Never supplied to actors or generated candidates."""
import re
import xml.etree.ElementTree as ET


def expand(left, right):
    a, b = re.fullmatch(r'(.*?)([0-9]+)', left), re.fullmatch(r'(.*?)([0-9]+)', right)
    if not a or not b or a[1] != b[1]:
        raise ValueError('Range endpoints need identical prefixes and numeric suffixes')
    lo, hi = int(a[2]), int(b[2])
    if hi < lo or hi-lo > 500:
        raise ValueError('Invalid bounded ascending range')
    padded = len(a[2]) > 1 and a[2].startswith('0')
    if padded and len(a[2]) != len(b[2]):
        raise ValueError('Inconsistent zero padding')
    return [a[1]+(str(n).zfill(len(a[2])) if padded else str(n)) for n in range(lo, hi+1)]


def oracle(payload):
    if not isinstance(payload, dict) or set(payload) != {'sources'} or not isinstance(payload['sources'], list):
        raise ValueError('Expected sources list')
    groups, unique, seen, source_ids = [], [], set(), set()
    for source in payload['sources']:
        if not isinstance(source, dict) or set(source) != {'source_id','xml'}:
            raise ValueError('Malformed source')
        sid, xml = source['source_id'], source['xml']
        if not isinstance(sid,str) or not sid or '::' in sid or sid in source_ids or not isinstance(xml,str):
            raise ValueError('Invalid source ID/XML')
        source_ids.add(sid)
        if '<!DOCTYPE' in xml.upper() or '<!ENTITY' in xml.upper() or '<<C' in xml:
            raise ValueError('Unsupported declarations/marker')
        try:
            root = ET.fromstring('<root>'+xml+'</root>')
        except ET.ParseError as exc:
            raise ValueError('Malformed XML') from exc
        tokens = []
        def flatten(node):
            if node.tag == 'xref' and node.get('ref-type') == 'bibr':
                rid = node.get('rid','').split()
                if not rid or any(not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.:-]*', r) for r in rid):
                    raise ValueError('Missing/invalid bibliography ID')
                tokens.append(rid)
                return '<<C%d>>' % (len(tokens)-1)
            return (node.text or '') + ''.join(flatten(c)+(c.tail or '') for c in node)
        flat = flatten(root)
        counter = 0
        covered = set()
        for bracket in re.finditer(r'\[([^\[\]]*)\]',flat):
            inside=bracket[1]
            mentions=list(re.finditer(r'<<C([0-9]+)>>',inside))
            if not mentions:
                continue
            counter += 1
            refs=[]
            previous=None
            for match in mentions:
                index=int(match[1]); current=tokens[index]; covered.add(index)
                if previous is not None:
                    connector=inside[previous.end():match.start()]
                    if re.fullmatch(r'\s*[-\u2010-\u2014]\s*',connector):
                        left=tokens[int(previous[1])]
                        if len(left)!=1 or len(current)!=1:
                            raise ValueError('Range endpoint must have one ID')
                        current=expand(left[0],current[0])
                for ref in current:
                    if ref not in refs:
                        refs.append(ref)
                    key=sid+'::'+ref
                    if key not in seen:
                        seen.add(key); unique.append(key)
                previous=match
            groups.append({'source_id':sid,'group_index':counter,'reference_ids':refs})
        if covered != set(range(len(tokens))):
            raise ValueError('Every bibliography xref must occur inside square brackets')
    return {'groups':groups,'unique_references':unique}


def evaluate(answer, expected):
    wanted={(g['source_id'],g['group_index']):g['reference_ids'] for g in expected['groups']}
    got={}
    malformed=[]
    if not isinstance(answer,dict):
        answer={}
    for g in answer.get('groups',[]):
        try:
            key=(g['source_id'],g['group_index'])
            if key in got:malformed.append('duplicate group')
            got[key]=g['reference_ids']
        except (KeyError,TypeError):malformed.append('malformed group')
    correct=sum(got.get(k)==v for k,v in wanted.items())
    content_correct=sum(isinstance(got.get(k),list) and set(got[k])==set(v) for k,v in wanted.items())
    unexpected=[str(k) for k in got if k not in wanted]
    exact_unique=answer.get('unique_references')==expected['unique_references']
    whole=correct==len(wanted) and exact_unique and not unexpected and not malformed
    substantive=content_correct<len(wanted) or set(answer.get('unique_references',[]))!=set(expected['unique_references']) or bool(unexpected)
    return {'pass':whole,'correct_groups':correct,'content_correct_groups':content_correct,
            'total_groups':len(wanted),'unique_index_exact':exact_unique,
            'unexpected_groups':unexpected,'malformed':malformed,
            'substantive_index_error':substantive,
            'group_checks':[{'source_id':k[0],'group_index':k[1],
                             'pass':got.get(k)==v} for k,v in wanted.items()]}
