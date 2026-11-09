"""Private independent source-span alignment oracle; never supplied to actors."""
import unicodedata


def normalize(text):
    out=[];positions=[]
    for i,ch in enumerate(text):
        folded=unicodedata.normalize('NFKC',ch).casefold()
        for part in folded:
            if part.isspace():
                if out and out[-1]==' ':
                    positions[-1]=(positions[-1][0],i+1)
                else:out.append(' ');positions.append((i,i+1))
            else:out.append(part);positions.append((i,i+1))
    return ''.join(out),positions


def oracle(payload):
    if not isinstance(payload,dict) or set(payload)!={'sources','queries'} or not isinstance(payload['sources'],list) or not isinstance(payload['queries'],list):
        raise ValueError('Expected sources and queries lists')
    texts=[];seen=set()
    for s in payload['sources']:
        if not isinstance(s,dict) or set(s)!={'source_id','text'} or not isinstance(s['source_id'],str) or not s['source_id'] or not isinstance(s['text'],str) or s['source_id'] in seen:
            raise ValueError('Invalid or duplicate source')
        seen.add(s['source_id']);n,p=normalize(s['text']);texts.append((s,n,p))
    queries=[];unsupported=[];seen=set()
    for q in payload['queries']:
        if not isinstance(q,dict) or set(q)!={'query_id','text'} or not isinstance(q['query_id'],str) or not q['query_id'] or q['query_id'] in seen or not isinstance(q['text'],str) or not q['text'].strip():
            raise ValueError('Invalid or duplicate query')
        seen.add(q['query_id']);needle,_=normalize(q['text']);hits=[]
        for s,haystack,mapping in texts:
            cursor=0;emitted=set()
            while True:
                start=haystack.find(needle,cursor)
                if start<0:break
                cursor=start+1;end=start+len(needle)
                a,b=mapping[start][0],mapping[end-1][1];quote=s['text'][a:b]
                if normalize(quote)[0]!=needle or (a,b) in emitted:continue
                emitted.add((a,b));hits.append({'source_id':s['source_id'],'start':a,'end':b,'quote':quote})
        queries.append({'query_id':q['query_id'],'matches':hits})
        if not hits:unsupported.append(q['query_id'])
    return {'queries':queries,'unsupported_query_ids':unsupported}


def evaluate(answer,expected):
    wanted={q['query_id']:q['matches'] for q in expected['queries']}
    got={q.get('query_id'):q.get('matches') for q in answer.get('queries',[]) if isinstance(q,dict)} if isinstance(answer,dict) else {}
    checks=[{'query_id':k,'pass':got.get(k)==v} for k,v in wanted.items()]
    correct=sum(c['pass'] for c in checks);other=set(got)-set(wanted)
    exact_unsupported=isinstance(answer,dict) and answer.get('unsupported_query_ids')==expected['unsupported_query_ids']
    whole=correct==len(wanted) and not other and exact_unsupported
    return {'pass':whole,'correct_groups':correct,'content_correct_groups':correct,'total_groups':len(wanted),
            'unit':'source-alignment queries, not medical questions','unique_index_exact':exact_unsupported,
            'unexpected_groups':sorted(str(x) for x in other),'malformed':[],
            'substantive_index_error':not whole,'group_checks':checks}
