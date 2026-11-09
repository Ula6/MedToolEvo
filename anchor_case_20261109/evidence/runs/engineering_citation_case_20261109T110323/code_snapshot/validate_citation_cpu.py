"""Meaningful fixed checks of the independent oracle and role schemas, CPU only."""
import json
from pathlib import Path
import sys
from schema_support import Draft202012Validator
from citation_oracle import oracle,evaluate
from citation_protocol import INPUT_SCHEMA,OUTPUT_SCHEMA


def main():
    Draft202012Validator.check_schema(INPUT_SCHEMA);Draft202012Validator.check_schema(OUTPUT_SCHEMA)
    def payload(xml,sid='S'):return {'sources':[{'source_id':sid,'xml':xml}]}
    def x(r):return '<xref ref-type="bibr" rid="'+r+'">'+r+'</xref>'
    result=oracle(payload('<p>['+x('R01')+'–'+x('R03')+','+x('R02')+']</p>'))
    assert result=={'groups':[{'source_id':'S','group_index':1,'reference_ids':['R01','R02','R03']}],
                    'unique_references':['S::R01','S::R02','S::R03']}
    common=payload('<p>['+x('A1')+']</p>')['sources'][0]
    result=oracle({'sources':[common,{**common,'source_id':'T'}]})
    assert result['unique_references']==['S::A1','T::A1']
    assert oracle(payload('<p>[<xref ref-type="table" rid="Tab1">1</xref>]</p>'))=={'groups':[],'unique_references':[]}
    assert oracle({'sources':[]})=={'groups':[],'unique_references':[]}
    invalid=[payload('<p>['+x('R4')+'–'+x('R2')+']</p>'),payload('<p>['+x('A1')+'–'+x('B3')+']</p>'),
             payload('<p>['+x('R001')+'–'+x('R03')+']</p>'),payload('<p>['+x('A1')+']'),
             payload('<p>[<xref ref-type="bibr">1</xref>]</p>'),payload('<p>'+x('A1')+'</p>'),
             {'sources':[common,common]}, {'sources':True},payload('<!DOCTYPE p><p/>')]
    for p in invalid:
        try:oracle(p)
        except ValueError:pass
        else:raise AssertionError('Oracle accepted invalid input: '+str(p))
    expected=oracle(payload('<p>['+x('A1')+','+x('A2')+']</p>'))
    missing={'groups':[{'source_id':'S','group_index':1,'reference_ids':['A1']}],'unique_references':['S::A1']}
    assert evaluate(missing,expected)['substantive_index_error'] and not evaluate(missing,expected)['pass']
    assert evaluate(expected,expected)['pass']
    task_dir=Path(sys.argv[1]);task=json.loads((task_dir/'task.json').read_text(encoding='utf-8'))
    for c in task['fixed_source_queue']:
        p={'sources':[{'source_id':c['source_id'],'xml':c['xml']}]};Draft202012Validator(INPUT_SCHEMA).validate(p);Draft202012Validator(OUTPUT_SCHEMA).validate(oracle(p))
    report={'pass':True,'fixed_valid_checks':4,'invalid_input_checks':len(invalid),
            'scoring_checks':2,'real_source_packets':len(task['fixed_source_queue']),
            'models_called':False,'scope':'Independent oracle/schema preflight only, not candidate functional tests'}
    print(json.dumps(report))


if __name__=='__main__':main()
