"""Render the actual existing-tool evolution evidence, with no result editing."""
import datetime
import hashlib
import html
import json
from pathlib import Path
import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent
E=HERE/'evidence'
R=E/'runs/engineering_policy_case_20261109T121042'
REMOTE=Path('/home/supervisor/project/sy/MedToolEvo')
read=lambda p:json.loads(p.read_text(encoding='utf-8'))


def render(md):
    def inline(s):return re.sub(r'\[([^\]]+)\]\(([^)]+)\)',r'<a href="\2">\1</a>',html.escape(s))
    parts=[];table=False;listing=False
    for line in md.splitlines():
        if line.startswith('|'):
            if not table:parts.append('<table>');table=True
            cells=[s.strip() for s in line.strip('|').split('|')]
            if all(re.fullmatch('[-:]+',s) for s in cells):continue
            parts.append('<tr>'+''.join('<td>'+inline(s)+'</td>' for s in cells)+'</tr>');continue
        if table:parts.append('</table>');table=False
        if line.startswith('- '):
            if not listing:parts.append('<ul>');listing=True
            parts.append('<li>'+inline(line[2:])+'</li>');continue
        if listing:parts.append('</ul>');listing=False
        if line.startswith('!['):parts.append('<img src="policy_evolution.png" alt="实际工具自进化结果">')
        elif line.startswith('## '):parts.append('<h2>'+inline(line[3:])+'</h2>')
        elif line.startswith('# '):parts.append('<h1>'+inline(line[2:])+'</h1>')
        elif line.strip():parts.append('<p>'+inline(line)+'</p>')
    if table:parts.append('</table>')
    if listing:parts.append('</ul>')
    return '\n'.join(parts)


def main():
    a=read(R/'case_acceptance.json');assert a['pass']
    task=read(R/'task.json');build=read(R/'builds/candidate/builder_summary.json');lineage=read(R/'builds/candidate/lineage.json')
    m=read(E/Path(a['manifest']).relative_to(REMOTE));code=E/Path(m['code_path']).relative_to(REMOTE)
    before,retry=read(R/'baseline.json'),read(R/'qwen_retry.json');repair=read(R/'original_repair.json')
    expected=read(R/'offline_oracle.json');history=build['history'];events=read(R/'state.json')['events']
    stamp=datetime.datetime.fromisoformat(events[-1]['utc']).astimezone(datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
    parent=read(R/'parent_manifest.json');assert history[0]['sha256']==a['parent_sha256']
    assert hashlib.sha256(code.read_bytes()).hexdigest()==a['new_sha256']
    assert hashlib.sha256((R/'builds/candidate/legacy_original_tests.py').read_bytes()).hexdigest()==lineage['old_test_sha256']
    def rel(p):return p.relative_to(HERE).as_posix()
    fig,(ax,bx,cx)=plt.subplots(1,3,figsize=(16,5.5),layout='constrained',gridspec_kw={'width_ratios':[1.15,1,1.15]})
    values=[a['old_tool_correct'],a['initial_Qwen_correct'],a['retry_Qwen_correct'],a['new_tool_correct'],a['after_Qwen_correct']]
    bars=ax.bar(range(5),values,color=['#a6aeb7','#718ca3','#a59a7f','#55a18c','#247b65'],width=.65)
    ax.set_xticks(range(5),['Old\ntool','Qwen\ninitial','Qwen\nretry','Updated\ntool','Qwen +\nupdate'],fontsize=9)
    ax.set_ylim(0,14);ax.set_ylabel('Fully correct policy queries');ax.set_title('Same source and Qwen annotations',fontsize=11)
    ax.spines[['top','right']].set_visible(False)
    for b,n in zip(bars,values):ax.text(b.get_x()+b.get_width()/2,n+.15,f'{n}/12',ha='center',fontsize=9)
    x=list(range(len(history)));old=[10]*len(x);new=[h['passed']-10 for h in history];failed=[h['failed'] for h in history]
    bx.bar(x,old,color='#247b65',label='Original tests:10 retained')
    bx.bar(x,new,bottom=old,color='#5f8aa8',label='New tests passed')
    bx.bar(x,failed,bottom=[i+j for i,j in zip(old,new)],color='#d99c7e',label='New tests failed')
    bx.set_xticks(x,[h['version'].rsplit('_',1)[-1] for h in history]);bx.set_ylim(0,31)
    bx.set_title('Actual inherited code -> updated code',fontsize=11);bx.set_ylabel('Immutable combined functional tests')
    bx.spines[['top','right']].set_visible(False);bx.legend(fontsize=8,loc='upper left')
    for i,h in enumerate(history):bx.text(i,22.4,f"{h['passed']}/22",ha='center',fontsize=9)
    cx.axis('off');cx.set_title('Completed DEVELOPMENT evolution',fontsize=11)
    steps=['Existing v004: original10 tests pass','Observed new-policy failure:0/12','27B Manager selected EXTEND ledger','30B changed real parent code twice','Legacy10 + new12 tests:22/22','3 legacy controls unchanged;1 registry','2 fresh reloads, including another paper']
    for i,s in enumerate(steps):cx.text(.01,.91-i*.13,'✓ '+s,fontsize=9,transform=cx.transAxes)
    fig.suptitle('MedToolEvo | third case: existing-tool evolution (one derived task,12 policy queries)',fontsize=13)
    fig.savefig(HERE/'policy_evolution.png',dpi=180);fig.savefig(HERE/'policy_evolution.svg');plt.close(fig)
    versions='| 实际版本 | 原10项回归 | 新12项测试通过 | 组合测试 |\n|---|---:|---:|---:|\n'
    for h in history:versions+=f"| {h['version'].rsplit('_',1)[-1]} | 10/10 | {h['passed']-10}/12 | {h['passed']}/22 |\n"
    c1={c['query_id']:c for c in before['evaluation']['checks']};c2={c['query_id']:c for c in retry['evaluation']['checks']}
    details='| 查询 | 参考结果（源引用ID） | 初始Qwen完整通过 | 同标注重试 | 更新后 |\n|---|---|---|---|---|\n'
    for qid,value in expected.items():
        names=', '.join(e['name'] for e in value['entities']) or '空集'
        details+=f"| {qid} | {names} | {'是' if c1[qid]['pass'] else '否'} | {'是' if c2[qid]['pass'] else '否'} | 是 |\n"
    md=f'''# 第三条闭环：已有证据台账的工具自进化

开发级完整验收通过，时间：北京时间{stamp}。Qwen3.5-27B负责标注、Executor、Manager、契约和审核；Qwen3-Coder-30B负责实际代码扩展和修复。没有训练模型权重，没有人工修改候选函数。

## 本次证明了什么

沿用此前已经存在、原10项测试通过的evidence_ledger v004。面对新的关系合取、析取、显式正负事实、排除及证据作用范围要求，旧工具只返回并集，实际12个查询0/12；Manager自主选择extend现有台账，Builder从真实父代码更新到v006，原10项回归一直保留，通过新旧22项测试后完成实际调用、开发注册和跨论文重载复用。

旧工具在原契约上正确；0/12反映新查询超出旧能力，不等于旧任务失败。父代码、旧测试及原注册文件均未改动，新版登记在本案例独立开发库。此处12个是同一个派生工程任务的条件索引请求，不是12道独立医学题，也不是BioASQ F1。

![真实结果与版本轨迹](policy_evolution.png)

## 前后结果

| 执行方式 | 完整查询通过 | 结果集合正确 |
|---|---:|---:|
| 原工具实际调用 | 0/12 | 0/12 |
| Qwen初始回答（同一标注＋旧工具观察） | 6/12 | 7/12 |
| Qwen同证据重试 | 6/12 | 7/12 |
| 更新工具实际调用 | 12/12 | 12/12 |
| Qwen读取更新工具输出 | 12/12 | 12/12 |

完整通过同时要求筛选结果、证据ID及顺序正确。初始5个查询的成员有误，另1个为证据记录错误；不是仅靠名称换写改善。所有组使用同一份Qwen源关系标注，未给工具组单独补充医学事实。该单例、单一配置结果不构成总体统计收益或临床正确性证明。

## 真正的版本继承与回归

{versions}
初始v004副本的代码SHA与既有父版本完全一致，并非人为制造的坏版本。v005完成主要扩展后还把仅有unknown事实的对象错误纳入“只排除某关系”的查询，独立测试拦截。第二次自动更新v006修复此问题。组合测试在首次代码更新前冻结，整个过程没有删改失败测试。

父代码SHA256：{a['parent_sha256']}。

新版代码SHA256：{a['new_sha256']}。

原10项测试SHA256：{lineage['old_test_sha256']}。新组合测试SHA256：{build['test_sha256']}。

## 全流程核查

- 源关系标注：主文献13组、复用文献7组，均由27B实际标注并通过预设源标注核验。
- 真实失败：旧代码在12个新policy输入上均不符合查询，全部实际调用输入/输出保留；27B自行重算和重试均6/12。
- 更新对象：Manager选择extend，target=evidence_ledger；不是重建一个无继承关系的工具。
- 测试：原10个具名测试定义和辅助逻辑保留；新增10个预设边界输入＋2个Qwen设计输入，期望值由独立规则计算，代码更新前固定，共22项。
- 真实代码更新：从父v004出发，两次30B自动更新；无人工源码补丁，完整请求和诊断反馈保留。
- 源任务修复：实际新版调用12/12；27B使用真实结果后12/12，源关系及旧能力审核通过。
- 旧能力控制：三个原文子集在无policy的旧接口上，新旧版本输出逐项相同。
- 开发注册：1件更新工具，保留parent_manifest、parent_version和parent_sha256；正式稳定注册0。
- 新进程复用：第一回合重载原任务中的两个查询组成的新批次，不能称为未见查询；第二回合在另一论文上运行两个新查询，代码保持不变，均通过。复用由控制器触发，不代表已验证开放式自主工具路由。

## 来源、构造与人工介入

主来源为DocHopQA条目9400附带的PMC11837447正文：[Accuracy of artificial intelligence in detecting tumor bone metastases: a systematic review and meta-analysis](https://pmc.ncbi.nlm.nih.gov/articles/PMC11837447/)。复用来源为条目9532、PMC11856201：[Efficacy and Safety of Celecoxib and a Korean SYSADOA (JOINS) for the Treatment of Knee Osteoarthritis: A Systematic Review and Meta-Analysis](https://pmc.ncbi.nlm.nih.gov/articles/PMC11856201/)。

源XML原样保留。引用分组及区间展开是可信机械预处理；关系语义由Qwen标注，所有对照共享。研究者预先选择来源、定义关系词表、12个查询、规则与预设标签核验、独立参考程序及验收；这些人工介入已记录，不把本例称作原DocHopQA问题或开放域自主科学发现。Builder收到通用契约、实际父代码及虚构测试反馈，没有收到真实研究ID或参考查询结果。

查询只描述当前段落的引用索引：none_of表示排除存在某显式标注的对象，不证明某研究没有实施某操作；缺失不等于负事实。原文计数与字面引用区间可能不一致，本例不替作者纠正科学结论，也不把某引用出现当作临床证据充分。

{details}

## 可复核原始文件

- [最终验收]({rel(R/'case_acceptance.json')})
- [Manager选择更新对象]({rel(R/'manager.json')})
- [父版本与代码继承记录]({rel(R/'builds/candidate/lineage.json')})
- [全部版本、测试及真实修复]({rel(R/'builds/candidate/builder_summary.json')})
- [原始旧10项测试]({rel(R/'builds/candidate/legacy_original_tests.py')})
- [完整22项组合测试]({rel(R/'builds/candidate/independent_tests.py')})
- [实际更新代码]({rel(code)})
- [前后结果和审核]({rel(R/'original_repair.json')})
- [控制结果]({rel(R/'controls.json')})
- [注册清单]({rel(E/Path(a['manifest']).relative_to(REMOTE))})
- [重载复用]({rel(R/'reuse.json')})
- [源数据和构造方式]({rel(R/'task.json')})

此前两条案例的已知问题继续保留，第三条通过不代表字符定位工具的残余缺陷已修复。三条案例仍为开发工程演示，均不替代原100题验收、不计入1130题正式结果；当前没有因此启动全量。
'''
    (HERE/'第三条_工具自进化交付.md').write_text(md,encoding='utf-8')
    page='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MedToolEvo 第三条：已有工具自进化</title><style>body{max-width:1320px;margin:30px auto;padding:0 24px;font:17px/1.75 system-ui;color:#173244;background:#f7fafb}h1,h2{line-height:1.35}table{width:100%;border-collapse:collapse;background:white;font-size:15px}td{padding:10px;border:1px solid #cfdae1}img{width:100%;height:auto}a{color:#216a85}li{margin:7px 0}p{overflow-wrap:anywhere}</style>'+render(md)+'</html>'
    (HERE/'report.html').write_text(page,encoding='utf-8')
    result={**a,'completed_beijing':stamp,'report':'report.html','run':R.name,'builder_history':history,
        'legacy_test_sha256':lineage['old_test_sha256'],'combined_test_sha256':build['test_sha256']}
    (HERE/'delivery_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['pass','completed_beijing','old_tool_correct','initial_Qwen_correct','retry_Qwen_correct','after_Qwen_correct','test_count','repair_calls']}))


if __name__=='__main__':main()
