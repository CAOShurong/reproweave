# Competitive landscape and scope decision

ReproWeave was designed after checking several mature categories. The conclusion is not that
“nobody has done reproducibility tooling.” Many strong tools exist. The narrower gap is a
dependency-free, file-native bridge between paper-level evidence, transparent reconstructability
ratings, resource constraints, and an executable replication backlog.

## Adjacent tools

| Category | Representative work | What it does well | Why ReproWeave is different |
|---|---|---|---|
| Reference management | Zotero | Libraries, metadata, annotation, citation | ReproWeave starts after selection and models claims, experiments, resources, and tasks |
| Screening automation | ASReview | Prioritizes records in systematic reviews | ReproWeave does not rank search results or learn from screening |
| Reproducibility checklists | [AAAI checklist](https://aaai.org/conference/aaai/aaai-23/reproducibility-checklist/) | Shared disclosure questions | ReproWeave stores evidence locators and converts unresolved items into a task graph |
| Reproducibility programs | [NeurIPS 2019 program report](https://www.jmlr.org/papers/v22/20-303.html) | Community process and checklist evidence | ReproWeave is a personal/lab workspace, not a venue policy |
| Evidence maps | [Systematic evidence map methodology](https://pmc.ncbi.nlm.nih.gov/articles/PMC4750281/) | Broad question-by-evidence landscapes | ReproWeave maps reconstructability at experiment and resource level |
| Evidence-and-gap maps | [Evidence and gap map methods review](https://pmc.ncbi.nlm.nih.gov/articles/PMC8428058/) | Visual inventories of available evidence and gaps | ReproWeave operates after paper selection and converts artifact gaps into candidate-specific execution decisions |
| Reproduction benchmarks | [PaperBench](https://openai.com/index/paperbench/) | Evaluates agents reproducing AI research | ReproWeave is a human-auditable planning record and does not run agents |
| Experiment tracking | MLflow | Captures runs, parameters, models, and metrics | ReproWeave begins with external literature and plans work before a local run exists |
| Data versioning | DVC | Versions data pipelines and artifacts | ReproWeave records availability and relationships; it does not transfer large data |

## Design inference

The useful open-source contribution is the composition:

```text
manual evidence locator
  + explicit unknown/no distinction
  + claim-to-experiment-to-resource graph
  + transparent rubric
  + resource-aware candidate triage
  + dependency-aware replication tasks
  + offline portable report
```

None of these individual ideas is claimed as novel. The value is a coherent, inspectable workflow
with no mandatory service, model, database, or API.

The v0.2.0 triage layer also avoids a tempting but weak design: collapsing every concern into one
“replication score.” It applies named rules in order, reports the blocking resource or task, and
keeps reconstructability coverage separate from effort. A resource override produces a scenario,
not a silent mutation of the evidence record.

## Deliberate exclusions

ReproWeave does not compete with Zotero for citation management, ASReview for search screening,
MLflow for executed runs, DVC for data transport, or PaperBench for agent evaluation. Integrations
may be useful later, but absorbing those products would weaken the tool's audit boundary.
