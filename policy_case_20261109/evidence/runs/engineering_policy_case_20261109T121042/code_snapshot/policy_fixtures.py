"""Preset generic policy boundary inputs, frozen before any extension code."""
def entry(name='A',relation='R',polarity='positive',scope='S',eid='e',eligible=True,quote=None):
    return {'name':name,'group_id':name,'evidence_id':eid,'quote':quote or name,'eligible':eligible,
            'relation':relation,'polarity':polarity,'scope':scope}


def packet(entries,all_of=(),any_of=(),none_of=(),scope='S'):
    term=lambda v:{'relation':v[0],'polarity':v[1]} if isinstance(v,tuple) else {'relation':v,'polarity':'positive'}
    return {'evidence':[{'evidence_id':'e','text':'A B C'},{'evidence_id':'f','text':'A B C'}],
            'entries':entries,'policy':{'scope':scope,'all_of':[term(v) for v in all_of],
                                      'any_of':[term(v) for v in any_of],'none_of':[term(v) for v in none_of]}}


def fixed_inputs():
    return [
        packet([entry(),entry(relation='T'),entry('B')],all_of=['R','T']),
        packet([entry(),entry('B','T'),entry('C','U')],any_of=['R','T']),
        packet([entry(),entry(relation='T',polarity='negative'),entry('B'),entry('B','T')],all_of=['R',('T','negative')],none_of=['T']),
        packet([entry(polarity='unknown'),entry('B',polarity='negative')],all_of=[('R','negative')]),
        packet([entry(),entry(relation='T',scope='Z')],all_of=['R','T']),
        packet([entry('B','U'),entry('A','R',eid='f'),entry('B','R',eid='f'),entry('A','T'),entry('B','T'),entry('A','R',eid='f')],all_of=['R','T']),
        packet([entry(),entry('B','T'),entry('C',polarity='unknown')],none_of=['T']),
        packet([entry(),entry('B',eligible=False,quote='does not exist')],all_of=['R']),
        packet([{k:v for k,v in entry().items() if k!='relation'}],all_of=['R']),
        {'evidence':[{'evidence_id':'e','text':'A'}],'entries':[entry()],
         'policy':{'scope':'S','all_of':[{'relation':'R','polarity':'unknown'}],'any_of':[],'none_of':[]}}
    ]
