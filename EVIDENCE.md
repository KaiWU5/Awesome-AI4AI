# 🔬 AI4AI Stage-Ownership & Improvement-Evidence Audit

> Companion evidence artifact for *On the Eve of AI4AI*. This is an evidence-weighted 35-system sample, **not** a prevalence estimate.

**Frozen:** 2026-08-04 · **Last verified:** 2026-08-13 · **Schema:** 2.0.0

## Headline

| Systems | Goal system-owned | Execution system-owned | Repair system-owned | Feedback system-owned | Matched human evidence |
|:--:|:--:|:--:|:--:|:--:|:--:|
| **35** | **0** | **35** | **23** | **0** | **1** |

## Coding legend

- **Ownership:** Hum = human/design-time artifact, Mix = mixed, Sys = system.
- **Evidence:** G = measured gain, R = retention/compounding, H = budget-matched human comparison, T = controlled held-out transfer.
- ✅ demonstrated · ❌ explicitly tested but not demonstrated · — not reported/tested.
- **R is deliberately broad:** it can denote repeated accepted gains or an explicit capability-preservation test; R alone does not establish cross-generation RSI.

The full operational rules are stored in [`data/closure_audit.json`](data/closure_audit.json). Every row includes a primary-source locator, rationale, source tier, and confidence.

## Full audit

| System | Target | Goal | Plan | Exec | Feedback | Repair | G | R | H | T | Source | Confidence |
|:--|:--|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--|:--:|
| [STaR](https://proceedings.neurips.cc/paper_files/paper/2022/hash/639a9a172c044fbb64175b5fad42e9a5-Abstract-Conference.html) | weights | Hum | Hum | Sys | Hum | Mix | ✅ | ✅ | — | ✅ | peer-reviewed paper | high |
| [Self-Rewarding Language Models](https://proceedings.mlr.press/v235/yuan24d.html) | weights | Hum | Mix | Sys | Mix | Mix | ✅ | ✅ | — | ✅ | peer-reviewed paper | medium |
| [Self-Refine](https://proceedings.neurips.cc/paper_files/paper/2023/hash/91edff07232fb1b55a505a9e9f6c0ff3-Abstract-Conference.html) | task output (adjacent) | Hum | Hum | Sys | Mix | Mix | ✅ | ✅ | — | — | peer-reviewed paper | high |
| [Reflexion](https://proceedings.neurips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Abstract.html) | agent memory (adjacent) | Hum | Mix | Sys | Mix | Mix | ✅ | ✅ | — | — | peer-reviewed paper | high |
| [ExpeL](https://ojs.aaai.org/index.php/AAAI/article/view/29936) | harness | Hum | Mix | Sys | Hum | Mix | ✅ | ✅ | — | ✅ | peer-reviewed paper | medium |
| [SPIN](https://proceedings.mlr.press/v235/chen24j.html) | weights | Hum | Hum | Sys | Hum | Mix | ✅ | ✅ | — | — | peer-reviewed paper | medium |
| [SEAL](https://papers.nips.cc/paper_files/paper/2025/file/6b41e04c41726e2a60e456d0a2b961ab-Paper-Conference.pdf) | weights | Hum | Mix | Sys | Hum | Mix | ✅ | ✅ | — | ✅ | peer-reviewed paper | medium |
| [DataEnvGym](https://openreview.net/forum?id=00SnKBGTsz) | data/tasks | Hum | Mix | Sys | Mix | Mix | ✅ | ✅ | — | — | peer-reviewed paper | high |
| [Autodata](https://arxiv.org/abs/2606.25996) | data/tasks | Hum | Mix | Sys | Mix | Mix | ✅ | ✅ | — | ✅ | preprint | high |
| [ASI-Evolve](https://arxiv.org/abs/2603.29640) | research process | Hum | Mix | Sys | Mix | Mix | ✅ | ✅ | — | ✅ | preprint | high |
| [Frontis-MA1](https://arxiv.org/abs/2607.28568) | program/substrate | Hum | Mix | Sys | Hum | Mix | ✅ | ✅ | — | ✅ | technical report | high |
| [STOP](https://openreview.net/forum?id=VMvLRFP5R4) | harness | Hum | Sys | Sys | Hum | Sys | ✅ | ✅ | — | ✅ | peer-reviewed paper | high |
| [Gödel Agent](https://aclanthology.org/2025.acl-long.1354/) | harness | Hum | Sys | Sys | Hum | Sys | ✅ | ✅ | — | — | peer-reviewed paper | high |
| [Automated Design of Agentic Systems](https://proceedings.iclr.cc/paper_files/paper/2025/hash/36b7acf6f6010652b3f2a433774a66fe-Abstract-Conference.html) | harness | Hum | Sys | Sys | Hum | Sys | ✅ | ✅ | — | — | peer-reviewed paper | medium |
| [Darwin Gödel Machine](https://openreview.net/forum?id=pUpzQZTvGY) | harness | Hum | Sys | Sys | Hum | Sys | ✅ | ✅ | — | — | peer-reviewed paper | medium |
| [AlphaEvolve](https://arxiv.org/abs/2506.13131) | program/substrate | Hum | Sys | Sys | Hum | Sys | ✅ | ✅ | — | ✅ | technical report | high |
| [ShinkaEvolve](https://openreview.net/forum?id=lKEdGCoDNC) | program/substrate | Hum | Sys | Sys | Hum | Sys | ✅ | ✅ | — | ✅ | peer-reviewed paper | high |
| [Recursive Harness Self-Improvement](https://arxiv.org/abs/2607.15524) | harness | Hum | Sys | Sys | Mix | Sys | ✅ | ✅ | — | — | preprint | high |
| [Meta-Harness](https://arxiv.org/abs/2603.28052) | harness | Hum | Sys | Sys | Hum | Sys | ✅ | ✅ | — | ✅ | preprint | high |
| [Self-Harness](https://arxiv.org/abs/2606.09498) | harness | Hum | Sys | Sys | Mix | Sys | ✅ | ✅ | — | — | preprint | high |
| [KernelEvolve](https://doi.org/10.1109/ISCA66397.2026.00063) | program/substrate | Hum | Sys | Sys | Mix | Sys | ✅ | ✅ | — | ❌ | peer-reviewed paper | medium |
| [Bilevel Autoresearch](https://arxiv.org/abs/2603.23420) | research process | Hum | Sys | Sys | Hum | Sys | ✅ | — | — | — | preprint | high |
| [AIDE²](https://www.weco.ai/blog/first-evidence-of-recursive-self-improvement) | research process | Hum | Sys | Sys | Hum | Sys | ✅ | ✅ | — | ✅ | first-party report (unrefereed) | low |
| [AIDE](https://arxiv.org/abs/2502.13138) | data/tasks | Hum | Mix | Sys | Hum | Sys | ✅ | ✅ | ✅ | — | preprint | medium |
| [ML-Master](https://arxiv.org/abs/2506.16499) | data/tasks | Hum | Mix | Sys | Hum | Sys | ✅ | ✅ | — | — | preprint | medium |
| [ML-Master 2.0](https://arxiv.org/abs/2601.10402) | data/tasks | Hum | Sys | Sys | Mix | Sys | ✅ | ✅ | — | ✅ | preprint | high |
| [The AI Scientist v1](https://arxiv.org/abs/2408.06292) | research process | Hum | Mix | Sys | Mix | Sys | ✅ | ✅ | — | — | preprint | medium |
| [The AI Scientist-v2](https://arxiv.org/abs/2504.08066) | research process | Hum | Mix | Sys | Mix | Sys | ❌ | — | — | — | preprint | medium |
| [AiScientist](https://arxiv.org/abs/2604.13018) | program/substrate | Hum | Sys | Sys | Mix | Sys | ✅ | ✅ | — | — | preprint | high |
| [FARS](https://arxiv.org/abs/2606.31651) | research process | Hum | Mix | Sys | Mix | Sys | ✅ | ❌ | — | ✅ | preprint | medium |
| [AutoSOTA](https://arxiv.org/abs/2604.05550) | program/substrate | Hum | Mix | Sys | Mix | Sys | ✅ | ✅ | — | — | preprint | high |
| [AgentRxiv](https://arxiv.org/abs/2503.18102) | harness | Hum | Sys | Sys | Mix | Sys | ✅ | ✅ | — | — | preprint | medium |
| [DeepScientist](https://openreview.net/forum?id=cZFgsLq8Gs) | program/substrate | Hum | Sys | Sys | Mix | Mix | ✅ | ✅ | — | — | peer-reviewed paper | high |
| [AI-Researcher](https://proceedings.neurips.cc/paper_files/paper/2025/hash/0d904d300a105809a2114d727851e759-Abstract-Conference.html) | research process | Hum | Mix | Sys | Mix | Sys | — | — | — | — | peer-reviewed paper | high |
| [CodeScientist](https://aclanthology.org/2025.findings-acl.692/) | program/substrate | Hum | Mix | Sys | Mix | Sys | ✅ | ✅ | — | — | peer-reviewed paper | medium |

## Rebuild

```bash
python scripts/build_evidence.py
```

The command regenerates this page, the flat [CSV export](data/closure_audit.csv), and the [aggregate JSON](data/closure_audit_summary.json).
