---
language:
- en
task_categories:
- question-answering
task_ids:
- open-book-qa
pretty_name: DocHopQA
license: cc-by-4.0
tags:
- multi-hop
- multi-document
- scientific
- pubmed
- tables
- layout
size_categories:
- 10K<n<100K
---
# DocHopQA Dataset
Paper: https://arxiv.org/abs/2508.15851

## Overview
We introduce **DocHop-QA**, a large-scale benchmark comprising **11,379** QA instances for **multimodal, multi-document, multi-hop question answering**. Constructed from publicly available scientific documents sourced from PubMed Central, DocHop-QA is domain-agnostic and incorporates diverse information formats, including textual passages, tables, and structural layout cues.

Unlike existing datasets, DocHop-QA does not rely on explicitly hyperlinked documents; instead, it supports open-ended reasoning through semantic similarity and layout-aware evidence synthesis. To scale realistic QA construction, we designed an LLM-driven pipeline grounded in 11 high-frequency scientific question concepts.

## Dataset Size
- Paragraph-Oriented QA: 8,547 instances  
- Table-Oriented QA: 2,812 instances  

## Data Format
Each QA instance is represented as a JSON object with the following fields:

- `id`: Unique identifier
- `task_type`: `Paragraph-Oriented` or `Table-Oriented`
- `hop_type`: `fan` or `chain`
- `question_concept_type`: One of 11 question concept categories
- `question`: Multi-hop question
- `used_doc`: `single` or `multi`
- `context_list`: list of supporting snippets, each with:
  - `pmc_id`: PMC article ID
  - `section`: Top-level section name
  - `subsection`: Subsection title
  - `type`: `text` or `table`
  - `raw_content`: Original XML-tagged content
  - `content`: Cleaned plain-text content

## Citation

If you use DocHopQA, please cite:

```bibtex
@misc{park2025dochopqamultihopreasoningmultimodal,
  title={DocHop-QA: Towards Multi-Hop Reasoning over Multimodal Document Collections},
  author={Jiwon Park and Seohyun Pyeon and Jinwoo Kim and Rina Carines Cabal and Yihao Ding and Soyeon Caren Han},
  year={2025},
  eprint={2508.15851},
  archivePrefix={arXiv},
  primaryClass={cs.CL},
  url={https://arxiv.org/abs/2508.15851}
}
```
## Usage
```python
from datasets import load_dataset

ds = load_dataset("anonymousaaai123/DocHopQA_Dataset")
print(ds)
print(ds["train"][0])
```
