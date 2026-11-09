# 完整数据集与实验输入

本次补充上传的是用户已有原始文件，逐字节复制，未删减、改写或重新生成问答。两个大文件使用Git LFS，原始README和引用信息一并保留。数据仍受各自原始条款约束，本项目不为其重新授权。

| 数据 | 完整文件 | 实际记录数 | 大小（字节） |
|---|---|---:|---:|
| BioASQ 14b | [training14b.json](BioASQ-training14b/training14b.json) | 5729 | 57109878 |
| DocHopQA | [DocHopQA_Dataset.json](DocHopQA/DocHopQA_Dataset.json) | 11379 | 196084332 |

BioASQ包含1130道list、1695道factoid、1541道yesno、1363道summary。当前正式实验目标1130题指其中全部list题，并非5729题所有题型。

DocHopQA原始JSON包含8567条Paragraph-Oriented、2812条Table-Oriented。其上游README写8547条段落型，与原始JSON存在20条差异；此处按文件实数报告，保留原始README和JSON，不替上游修改。

## 下载完整文件

有此私有仓库读取权限且已安装Git LFS时：

```bash
git lfs install
git clone https://github.com/Ula6/MedToolEvo.git
cd MedToolEvo
git lfs pull
python tools/verify_datasets.py
python tools/verify_evidence.py
```

已克隆仓库则先`git pull --ff-only`，再`git lfs pull`。GitHub显示大文件时可使用其下载原始文件入口。若下载ZIP或跳过LFS下载，可能只得到小型指针；核验脚本会明确报错，不能将指针当成完整数据集。

## 派生数据与评分隔离

- `data/formal_list_v1/list/`：只读复制自实际服务器输入目录，含全部1130道list题，以及development_seen、discovery、admission、evaluation的任务与离线参考文件。已核对与本地历史同名划分逐文件SHA256一致。
- `formal_20261106/data/`：历史正式数据准备产物，含all/list两种范围及其划分。目录中的all输入并不说明所有题型已按对应官方指标完成实验。
- `data_format_20261109/original_public_tasks.json`、`formatted_public_tasks.json`：固定100题的原公开输入与无损重排输入。重排版本没有替换冻结实验输入，也没有单独取得模型收益结果。
- `data/smoke20/`：原小规模开发输入与离线参考。
- `formal_snapshot/`：仍保留北京时间2026-11-09 21:29:48的90/100结果快照。该快照内“未包含完整数据”等字段描述当时快照，不因后来补充语料而改写。此次数据上传不代表新增或完成实验。

**完整原始文件本身含答案。** BioASQ的`exact_answer`、`ideal_answer`及派生`references.json`等只供独立离线评价。Executor、Manager、Builder应读取去答案的公开`tasks.json`；不要把原始完整文件直接作为模型输入。

`DATASETS_MANIFEST.json`记录实际条数、分类统计、文件大小和原文件SHA256。`FILE_MANIFEST.json`为本次提交的全仓库工作树字节清单，其中LFS文件的哈希指实际JSON内容，不是Git中的指针。

## 原始来源说明

BioASQ的用途、版本更新及引用见[原始README](BioASQ-training14b/README)，数据说明站点为原README提供的[BioASQ Task14b](http://participants-area.bioasq.org/general_information/Task14b/)。

DocHopQA的CC-BY-4.0声明、论文引用及原获取方式见[原始README](DocHopQA/README.md)，其中记录的数据发布入口为`anonymousaaai123/DocHopQA_Dataset`。没有另外打包PMC完整文章PDF或图片；工程案例所用源片段已在案例证据目录中保存。
