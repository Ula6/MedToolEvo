"""Offline reference for explicitly annotated evidence policies, never medical inference."""


def base(payload):
    if not isinstance(payload,dict) or not isinstance(payload.get('evidence'),list) or not isinstance(payload.get('entries'),list):
        raise ValueError('Evidence and entries must be lists')
    evidence={}
    for item in payload['evidence']:
        if not isinstance(item,dict) or not isinstance(item.get('evidence_id'),str) or not item['evidence_id'].strip() or not isinstance(item.get('text'),str) or item['evidence_id'] in evidence:
            raise ValueError('Invalid evidence')
        evidence[item['evidence_id']]=item['text']
    for e in payload['entries']:
        if not isinstance(e,dict) or any(not isinstance(e.get(k),str) or not e[k].strip() for k in ['name','group_id','evidence_id','quote']) or not isinstance(e.get('eligible'),bool):
            raise ValueError('Invalid entry')
        if e['evidence_id'] not in evidence or e['quote'] not in evidence[e['evidence_id']]:
            raise ValueError('Unbound source quote')
    return payload['entries']


def oracle(payload):
    entries=base(payload)
    policy=payload.get('policy')
    if 'policy' not in payload:
        names={};groups={}
        for e in entries:
            if e['group_id'] in names and names[e['group_id']]!=e['name']:raise ValueError('Inconsistent group names')
            names[e['group_id']]=e['name']
        for e in entries:
            if e['eligible']:groups.setdefault(e['group_id'],[]).append(e)
        return {'entities':[{'name':es[0]['name'],'evidence_ids':list(dict.fromkeys(e['evidence_id'] for e in es))} for es in groups.values()],
                'unique_entity_count':len(groups)}
    if not isinstance(policy,dict) or set(policy)!={'scope','all_of','any_of','none_of'} or not isinstance(policy['scope'],str) or not policy['scope'].strip():
        raise ValueError('Invalid policy')
    rules={}
    for kind in ['all_of','any_of','none_of']:
        if not isinstance(policy[kind],list):raise ValueError('Invalid rule list')
        values=set()
        for r in policy[kind]:
            if not isinstance(r,dict) or set(r)!={'relation','polarity'} or not isinstance(r['relation'],str) or not r['relation'].strip() or r['polarity'] not in ['positive','negative']:
                raise ValueError('Invalid signed relation')
            values.add((r['relation'],r['polarity']))
        rules[kind]=values
    names={};groups={}
    for e in entries:
        if any(not isinstance(e.get(k),str) or not e[k].strip() for k in ['relation','scope']) or e.get('polarity') not in ['positive','negative','unknown']:
            raise ValueError('Policy entries need explicit relation, polarity and scope')
        key=(e['scope'],e['group_id'])
        if key in names and names[key]!=e['name']:raise ValueError('Inconsistent names inside one scoped group')
        names[key]=e['name']
        if e['eligible'] and e['scope']==policy['scope'] and e['polarity']!='unknown':groups.setdefault(key,[]).append(e)
    selected=[]
    for es in groups.values():
        facts={(e['relation'],e['polarity']) for e in es}
        if not rules['all_of']<=facts or (rules['any_of'] and not rules['any_of']&facts) or rules['none_of']&facts:continue
        needed=rules['all_of']|rules['any_of']
        support=[e for e in es if not needed or (e['relation'],e['polarity']) in needed]
        selected.append({'name':es[0]['name'],'evidence_ids':list(dict.fromkeys(e['evidence_id'] for e in support))})
    return {'entities':selected,'unique_entity_count':len(selected)}


def evaluate(answer,expected):
    answers=answer.get('answers',[]) if isinstance(answer,dict) else []
    observed={r.get('query_id'):r.get('result') for r in answers if isinstance(r,dict)}
    checks=[{'query_id':key,'pass':observed.get(key)==value,
             'member_set_pass':isinstance(observed.get(key),dict) and
                {e.get('name') for e in observed[key].get('entities',[])}=={e['name'] for e in value['entities']}}
            for key,value in expected.items()]
    correct=sum(c['pass'] for c in checks)
    return {'pass':correct==len(checks) and len(answers)==len(checks),'correct':correct,'total':len(checks),
            'member_sets_correct':sum(c['member_set_pass'] for c in checks),'checks':checks,
            'unit':'policy query with exact source provenance; not independent medical questions'}
