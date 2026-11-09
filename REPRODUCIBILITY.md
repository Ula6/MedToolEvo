# 核验与重放

## 1. 不需要模型或GPU的证据核验

Python 3.12或更新版本，在仓库根目录运行：

```bash
python tools/verify_evidence.py
```

该脚本核验文件SHA、候选代码/冻结测试SHA、第三条父版本继承，并用实际冻结的独立参考程序重算存储结果。它不执行生成的候选代码、不调用模型、不接触服务器或API凭据，也不独立认证医学事实。

预期：数值案例 `[0,0,4]`，定位 `[1,1,7]`，条件查询 `[6,6,12]`。定位补充检查的2/5仍作为已知失败保留。

## 2. 在原隔离方式下重放冻结功能测试

Linux、Python 3、`bubblewrap`和`timeout`可用时：

```bash
python3 tools/replay_sandbox.py --case all
```

分别重放8、13、22项原测试，生成代码只在无网络的bubblewrap进程中执行，无GPU和模型调用。脚本没有在宿主环境直接执行生成代码的回退路径。系统若禁用用户命名空间，需先解决本机bubblewrap运行条件；不要把隔离环境失败记作候选功能失败。

13项定位测试通过不否定其额外边界检查失败；22项测试通过也不证明穷尽所有有效输入。

## 3. 重现完整模型实验需要额外准备

源码里的原部署根目录是 `/home/supervisor/project/sy/MedToolEvo`，模型服务为本机端口8001，语义别名 `medtool-qa`，Builder别名 `medtool-builder`。部署分别是Qwen3.5-27B及Qwen3-Coder-30B的现有GGUF配置，具体路径、参数见冻结 `model_service.py`、协议和调用记录。

- 原部署使用Linux单GPU串行切换，不能并行启动多个GPU作业。
- 模型权重和llama.cpp构建未包含；完整原始JSON语料现已通过Git LFS补充，见`DATASETS.md`。仍需自行取得正确模型版本并配置部署路径；当前缺少通用安装器和完整环境/权重来源锁定，属于审阅事项。
- `requirements-runtime.txt`记录原服务Schema依赖版本；这不是完整CUDA/C++环境锁文件。
- 模型角色、温度、seed、上下文及请求格式以对应原始 `request.json`、协议和冻结源码为准。
- 全量BioASQ/DocHopQA与现有派生参考答案现已补充，按`DATASETS.md`下载并核验。原始答案与`references.json`仅供独立离线评分，不得送入Executor、Manager或Builder。结果快照仍为上传时90题记录，不是100题或1130题最终报告；重算分数还需正确对应原评分器、划分和已保存预测。
- 旧数据准备脚本需原数据路径。CPU核验和冻结测试重放使用仓库内的小型源快照，不需要下载完整数据集。

## 原始文件与清单

`FILE_MANIFEST.json`记录此审阅版本文件的SHA256；它本身不包含自身哈希。原始实验记录没有因整理而改写，文件中的绝对路径保持当时值。`.gitattributes`禁止自动换行转换，以保持跨系统检出后的源文件和测试哈希。
