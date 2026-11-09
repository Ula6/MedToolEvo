"""Render the archived successful engineering run without modifying raw evidence."""
import datetime
import html
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE / 'evidence'
RUN = EVIDENCE / 'runs/engineering_weighted_case_20261109T095954'
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
acceptance = read(RUN / 'case_acceptance.json')
assert acceptance['pass']
baseline, retry = read(RUN / 'baseline.json'), read(RUN / 'qwen_retry.json')
repair = read(RUN / 'original_repair.json')
builder = read(RUN / 'builds/candidate/builder_summary.json')
controls, reuse = read(RUN / 'controls.json'), read(RUN / 'reuse.json')
events = read(RUN / 'state.json')['events']
stamp = datetime.datetime.fromisoformat(events[-1]['utc']).astimezone(datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
manifest_path = RUN / 'development_registry/weighted_statistical_summaries.json'
manifest = read(manifest_path)
code_path = EVIDENCE / Path(manifest['code_path']).relative_to('/home/supervisor/project/sy/MedToolEvo')
repair_component = EVIDENCE / 'runs/auto_open_deterministic_canonicalize_and_filter_25f7d831_20261109T084823Z_30646e/summary.json'
component = read(repair_component)
keys = list(baseline['evaluation']['checks'])
chinese = ['加权均值', '组均值的加权总体方差', '组均值的加权总体标准差', '加权几何均值']
english = ['Weighted mean', 'Weighted variance\nof group means', 'Weighted SD\nof group means', 'Weighted\ngeometric mean']
fig, (left, right) = plt.subplots(1, 2, figsize=(13.5, 6), gridspec_kw={'width_ratios': [1.2, 1]}, layout='constrained')
errors = [baseline['evaluation']['checks'][k]['absolute_error'] for k in keys]
after_errors = [repair['after_evaluation']['checks'][k]['absolute_error'] for k in keys]
left.bar(range(4), errors, width=.5, label='Initial Executor', color='#55799b')
left.scatter(range(4), after_errors, marker='D', color='#21856a', s=60, label='After generated tool', zorder=4)
left.axhline(5e-7, color='#bd863b', linestyle='--', label='Acceptance tolerance: 5e-7')
left.set_yscale('symlog', linthresh=1e-6)
left.set_xticks(range(4), english, fontsize=9)
left.set_ylabel('Absolute error against independent arithmetic reference')
left.set_title('One derived task: 0/4 correct -> 4/4 correct', fontsize=12)
left.spines[['top', 'right']].set_visible(False)
left.grid(axis='y', alpha=.2)
left.legend(fontsize=8, loc='upper left')
left.set_ylim(-2e-7, 6)
for i, error in enumerate(errors):
    left.text(i, error * 1.35, f'{error:.6f}', ha='center', fontsize=8)
right.set_xlim(0, 1)
right.set_ylim(-.7, 8)
right.axis('off')
right.set_title('Completed DEVELOPMENT lifecycle', fontsize=12)
steps = [
    ('Real source', 'Published Table3: 12 rows, total weight3020'),
    ('Observed failure', 'Fixed Qwen Executor: 0/4; same-input retry: 0/4'),
    ('Diagnosis and construction', 'Qwen3.5-27B Manager + Qwen3-Coder-30B'),
    ('Independent functional tests', '8/8 passed at v001; no main-case repair needed'),
    ('Actual original-task repair', '4/4 numerical outputs correct; source binding checked'),
    ('Development admission', '3 source controls: Qwen baseline4/4, code4/4 each'),
    ('Development registration', '1 generated tool; code and tests retained with SHA256'),
    ('Fresh-process reload and reuse', 'Original input + different4-row input; both correct')]
for i, (title, text) in enumerate(steps):
    y = 7.15 - i
    right.add_patch(FancyBboxPatch((.02, y), .96, .73, boxstyle='round,pad=.015', facecolor='#edf5f1', edgecolor='#4b8e7a'))
    right.text(.055, y + .46, title, fontsize=9.5, weight='bold')
    right.text(.055, y + .18, text, fontsize=8)
    if i < len(steps) - 1:
        right.annotate('', xy=(.5, y - .20), xytext=(.5, y - .02), arrowprops={'arrowstyle': '->', 'color': '#718494'})
fig.suptitle('MedToolEvo | real-source derivative engineering demonstration (n=1 task)', fontsize=13)
fig.savefig(HERE / 'engineering_result.png', dpi=180)
fig.savefig(HERE / 'engineering_result.svg')
plt.close(fig)


def relative(path):
    return str(path.relative_to(HERE)).replace('\\', '/')


table = '| 数值指标 | 初始Executor | 同证据Qwen重试 | 工具后Executor | 独立参考值 |\n|---|---:|---:|---:|---:|\n'
table_html = ''
for label, key in zip(chinese, keys):
    values = [baseline['answer'][key], retry['answer'][key], repair['after'][key], baseline['evaluation']['checks'][key]['expected']]
    table += '| ' + label + ' | ' + ' | '.join(f'{v:.6f}' for v in values) + ' |\n'
    table_html += '<tr><td>' + label + '</td>' + ''.join(f'<td>{v:.6f}</td>' for v in values) + '</tr>'

md = f'''# MedToolEvo 本周工程闭环交付

**结论：按用户明确选定的开发级工程标准，已完整通过一条真实来源派生案例。** 验收完成时间：北京时间{stamp}，原始报告case_acceptance.json的pass=true。

数据来自[真实论文Table3](https://pmc.ncbi.nlm.nih.gov/articles/PMC11835903/#Tab3)：*Evaluating the impact of the Radiomics Quality Score: a systematic review and meta-analysis*，DOI10.1007/s00330-024-11341-y。使用DocHopQA条目9990附带的原始表格快照，选取System/body location下全部12行，权重合计3020。公开页面元数据已核对，冻结表格及哈希一并提供。

**这是研究者构造的问题，不是DocHopQA原题或BioASQ原题。** 四个输出是对已公布舍入数值的指定数学运算，用来验证工具流程；不作为原论文发现、RQS汇总方法推荐或患者层面的总体估计。4/4表示单个问题的4个数值正确，不是4道独立问题，也不计入BioASQ正式结果。

## 前后指标

{table}
初始0/4，同证据重试0/4，实际使用生成工具后4/4。固定绝对误差门槛为5×10⁻⁷，题目和精度在首次模型作答前固定。离线参考采用Decimal60位计算，并事先与NumPy独立核对；参考结果没有发送给初始Executor、Manager、Compiler或Builder。工具后Executor收到的是实际生成代码的运行输出。

![数值误差与完整开发闭环](engineering_result.png)

## 流程证据

| 环节 | 实际结果 |
|---|---|
| 源证据 | 原始XML保留，BeautifulSoup与ElementTree两套解析一致，12/12行 |
| 初始失败 | Qwen3.5-27B正常作答，4个数值均未达到门槛；输出未经改写 |
| 缺口诊断 | Qwen3.5-27B选择创建可复用的加权数值计算能力 |
| 工具生成 | Qwen3-Coder-30B从通用规格生成weighted_statistical_summaries |
| 独立测试 | Qwen独立提出合成测试，可信算术预检，8/8通过 |
| 实际调用和原题修复 | 真实沙箱调用，4/4；Qwen审核确认数值修复和源操作数支持 |
| 开发准入 | 3个同源单行控制输入：模型基线逐个4/4，工具输出逐个4/4，数值不退步；未额外运行控制输入的工具后Executor |
| 开发注册 | 1件工具，持久化manifest及代码/测试哈希 |
| 重载复用 | 新进程PID1836435重跑原输入，PID1836441计算另一组4行输入，均通过；固定Qwen读取真实输出后也均4/4 |

主例代码版本v001即通过8/8，**主例代码自动修复次数为0，没有人为制造错误**。自动修复组件另有真实候选复测：初版2/7，经固定Qwen诊断、Qwen3-Coder-30B一次自动代码修复后7/7；同一套独立测试未修改。该记录属于另一个候选的工程恢复复测，不合并成主例的修复次数，也不称为该候选医学问答已通过。

## 模型、人工介入和边界

语义、诊断、契约编译、测试提案、执行结果整理及审核均使用现有固定Qwen3.5-27B部署；候选代码和代码修复使用Qwen3-Coder-30B。未训练或替换权重。

人工预先确定：来源表格和选取段落、派生问题与数学定义、固定数值I/O、精度和独立参考程序、控制输入、复用输入、沙箱和控制器。数据准备是可信解析，源码由Coder生成，未手写或修改候选函数。此前上下文和诊断传输修正发生在此工程运行开始前；主例从首次作答至完成连续自动运行。

复用由控制器触发，验证持久化和新进程调用；不宣称已验证开放式任意工具发明、自主跨论文选工具、临床可靠性或总体统计收益。开发注册为development_registry，不替代正式稳定注册；原100题与1130题门槛保持独立。本例没有通过100题验收，也不授权启动全量。

借鉴论文的重点是明确可执行对象、真实运行反馈、独立准入和持久复用，可参见[MedRSI作者实现](https://github.com/ImprintLab/MedRSI/blob/d453b7047275a62b3dc92020f1c959b384982f61/medrsi/evolve.py)。九篇论文及实现的核对记录见项目repair2_20261109/修复依据与验收_20261109.md；本例不宣称复现论文指标。

## 可核查文件

- [原始数据集逐字来源核查](data_provenance_verification.json)
- [最终验收JSON]({relative(RUN / 'case_acceptance.json')})
- [原始模型回答和数值评价]({relative(RUN / 'baseline.json')})
- [原题修复、同证据对照与Qwen审核]({relative(RUN / 'original_repair.json')})
- [实际生成的工具源码]({relative(code_path)})
- [独立测试与版本轨迹]({relative(RUN / 'builds/candidate/builder_summary.json')})
- [开发注册manifest]({relative(manifest_path)})
- [新进程重载复用记录]({relative(RUN / 'reuse.json')})
- [真实自动代码修复组件记录]({relative(repair_component)})
- [原始问题构造及完整数据来源]({relative(RUN / 'task.json')})
- [事件时间线]({relative(RUN / 'events.jsonl')})

工具代码SHA256：{manifest['sha256']}。
独立测试SHA256：{builder['test_sha256']}。
来源表格SHA256：{acceptance['source']['source_sha256']}。
归档中的JSON和源码保留原始内容；远程路径按原样保留，本报告链接指向本地归档副本。
'''
(HERE / '本周交付_真实表格工程闭环.md').write_text(md, encoding='utf-8')
links = ''.join(f'<li><a href="{relative(p)}">{html.escape(label)}</a></li>' for label, p in [
    ('最终验收JSON', RUN / 'case_acceptance.json'), ('生成的工具源码', code_path),
    ('原题修复与独立评价', RUN / 'original_repair.json'), ('开发注册', manifest_path),
    ('重载复用', RUN / 'reuse.json'), ('独立自动修复组件证据', repair_component)])
page = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>MedToolEvo 工程闭环已通过</title>
<style>body{{font:16px/1.75 system-ui;background:#eef3f6;color:#183447;max-width:1280px;margin:auto;padding:25px}}section{{background:white;border-radius:12px;padding:24px;margin:18px 0}}h1{{font-size:30px}}.cards{{display:flex;gap:12px;flex-wrap:wrap}}.cards div{{background:#e7f3ec;border-radius:10px;padding:14px 22px}}strong{{color:#176849}}table{{width:100%;border-collapse:collapse}}td,th{{text-align:left;padding:12px;border-bottom:1px solid #dce4e9}}img{{max-width:100%}}a{{color:#126ca0}}small{{color:#617687}}</style>
<h1>MedToolEvo：真实表格派生工程闭环已通过</h1><p>北京时间{stamp}，验收pass=true。</p>
<section><div class="cards"><div>初始数值正确 <b>0/4</b></div><div>工具后 <b>4/4</b></div><div>功能测试 <b>8/8</b></div><div>控制输入 <b>3/3</b></div><div>开发注册 <b>1</b></div><div>新进程复用 <b>2</b></div></div>
<p><strong>单个问题的4个数值，不是4道独立问题。</strong> 数值来自真实论文Table3的12组数据；问题、数学定义及验收规则为研究者构造。不计入BioASQ正式结果。语义Qwen3.5-27B；代码Qwen3-Coder-30B。</p></section>
<section><img src="engineering_result.png" alt="实际数值误差和已完成的开发闭环"><p>源码初版8/8，无需代码修复；自动修复组件另有真实2/7→一次自动修复→7/7记录，分别核算。</p></section>
<section><h2>同题前后数值</h2><table><tr><th>指标</th><th>初始Executor</th><th>同证据重试</th><th>工具后</th><th>独立参考值</th></tr>{table_html}</table><p>绝对误差门槛5×10⁻⁷。参考程序在离线验收中使用，未把参考结果交给初始解题器、Manager或Builder。</p></section>
<section><h2>来源与介入记录</h2><p><a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC11835903/#Tab3">真实论文及Table3</a>，DocHopQA条目9990附带原始表格快照。选取System/body location全部12行，权重合计3020。计算对象为给定组均值的数学汇总，不是患者层面的总体估计或原文结论。</p><p>人为设定派生问题、I/O、公式、精度、独立参考、控制及复用输入；未改写初始输出或手写候选代码。控制器触发复用。开发注册和正式稳定注册分别核算，100题与全量门槛未变。</p></section>
<section><h2>可核查证据</h2><ul>{links}</ul><p><a href="本周交付_真实表格工程闭环.md">完整周报Markdown</a> · <a href="engineering_result.svg">导出矢量图</a></p><small>归档原始数据未修改；这是带时间的已完成工程结果，不是实时全量看板。</small></section></html>'''
(HERE / 'report.html').write_text(page, encoding='utf-8')
print(json.dumps({'pass': True, 'completed_beijing': stamp, 'html': str(HERE / 'report.html'),
                  'markdown': str(HERE / '本周交付_真实表格工程闭环.md')}, ensure_ascii=True))
