"""Self-contained, offline HTML evidence report."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .audit import audit_workspace
from .constants import ASSESSMENT_DIMENSIONS
from .graph import build_evidence_graph
from .planning import build_replication_plan, readiness_backlog
from .scoring import assess_workspace, evidence_matrix
from .seal import build_seal
from .triage import build_replication_triage
from .util import html_escape
from .workspace import Workspace


def _json_script(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True).replace("</", "<\\/")


def _rating_cells(row: dict[str, Any]) -> str:
    labels = {"yes": "Yes", "partial": "Partial", "no": "No", "unknown": "?", "missing": "—"}
    return "".join(
        f'<td><span class="rating {html_escape(row[dimension])}">'
        f"{labels.get(row[dimension], html_escape(row[dimension]))}</span></td>"
        for dimension in ASSESSMENT_DIMENSIONS
    )


def _paper_rows(assessment: dict[str, Any], matrix: dict[str, Any]) -> str:
    scores = {item["paper_id"]: item for item in assessment["papers"]}
    rows = []
    for row in matrix["rows"]:
        result = scores.get(row["paper_id"], {})
        score = result.get("score", 0)
        rows.append(
            f'<tr data-score="{score}" data-search="{html_escape((row["title"] + " " + row["paper_id"]).lower())}">'
            f'<td><div class="paper-title">{html_escape(row["title"])}</div>'
            f"<code>{html_escape(row['paper_id'])}</code></td>"
            f"<td>{row['year']}</td><td><strong>{score:.1f}</strong></td>"
            f"{_rating_cells(row)}</tr>"
        )
    return "\n".join(rows)


def _claim_cards(workspace: Workspace) -> str:
    papers = workspace.index("paper")
    cards = []
    for claim in workspace.all("claim"):
        cards.append(
            '<article class="claim-card">'
            f'<span class="eyebrow">{html_escape(claim.get("type", "empirical"))}</span>'
            f"<h3>{html_escape(claim['statement'])}</h3>"
            f"<p>{html_escape(papers.get(claim['paper_id'], {}).get('title', claim['paper_id']))}</p>"
            f'<div class="locator">{html_escape(claim["evidence_locator"])}</div>'
            f'<span class="confidence {html_escape(claim.get("confidence", "reported"))}">'
            f"{html_escape(claim.get('confidence', 'reported'))}</span></article>"
        )
    return "\n".join(cards) or '<p class="empty">No claims recorded.</p>'


def _task_rows(plan: dict[str, Any]) -> str:
    rows = []
    for wave in plan["waves"]:
        for task in wave["parallel_tasks"]:
            dependencies = ", ".join(task.get("depends_on", [])) or "—"
            rows.append(
                "<tr>"
                f"<td>{wave['wave'] + 1}</td><td><strong>{html_escape(task['title'])}</strong>"
                f"<br><code>{html_escape(task['id'])}</code></td>"
                f'<td><span class="state {html_escape(task.get("state", "ready"))}">'
                f"{html_escape(task.get('state', 'ready'))}</span></td>"
                f"<td>{html_escape(task.get('priority', 'medium'))}</td>"
                f"<td>{task.get('estimate_hours', 0):g}h</td>"
                f"<td>{html_escape(dependencies)}</td></tr>"
            )
    return "\n".join(rows)


def _gap_bars(summary: dict[str, Any]) -> str:
    count = max(summary["assessed_count"], 1)
    return (
        "\n".join(
            '<div class="gap-row">'
            f"<span>{html_escape(item['dimension'])}</span>"
            f'<div class="bar"><i style="width:{100 * item["count"] / count:.1f}%"></i></div>'
            f"<strong>{item['count']}</strong></div>"
            for item in summary["common_gaps"]
        )
        or '<p class="empty">No unresolved gaps.</p>'
    )


def _triage_rows(triage: dict[str, Any]) -> str:
    rows = []
    for rank, candidate in enumerate(triage["candidates"], start=1):
        score = candidate["reconstructability_score"]
        score_text = f"{score:.1f}" if score is not None else "—"
        resources = ", ".join(candidate["unresolved_resource_ids"]) or "—"
        rows.append(
            "<tr>"
            f"<td>{rank}</td>"
            f"<td><strong>{html_escape(candidate['title'])}</strong>"
            f"<br><code>{html_escape(candidate['paper_id'])}</code></td>"
            f'<td><span class="decision {html_escape(candidate["status"])}">'
            f"{html_escape(candidate['status'].replace('_', ' '))}</span></td>"
            f"<td>{score_text}</td>"
            f"<td>{candidate['remaining_effort_hours']:g}h</td>"
            f"<td>{html_escape(resources)}</td>"
            f"<td>{html_escape(candidate['next_action'])}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def build_report(workspace: Workspace, output: str | Path) -> Path:
    """Generate one portable HTML file with embedded data, styles, and interactions."""
    workspace.require()
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest = workspace.manifest()
    assessment = assess_workspace(workspace)
    matrix = evidence_matrix(workspace)
    plan = build_replication_plan(workspace)
    audit = audit_workspace(workspace)
    graph = build_evidence_graph(workspace)
    backlog = readiness_backlog(workspace)
    triage = build_replication_triage(workspace)
    seal = build_seal(workspace)
    summary = assessment["summary"]
    audit_class = "verified" if audit["status"] == "pass" else "failed"
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="generator" content="ReproWeave 0.2.0">
<title>{html_escape(manifest["title"])} · ReproWeave evidence report</title>
<style>
:root{{--ink:#202a32;--muted:#68747b;--paper:#f4f1e9;--panel:#fffef9;--burgundy:#873e4a;
--sage:#667968;--gold:#a9813d;--blue:#60798a;--line:#cec8ba;--navy:#243744}}
*{{box-sizing:border-box}} html{{scroll-behavior:smooth}} body{{margin:0;background:var(--paper);
color:var(--ink);font:15px/1.58 ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif}}
a{{color:inherit}} code{{font:12px/1.4 ui-monospace,SFMono-Regular,Consolas,monospace;color:#566c79}}
.top{{background:#f4f1e9e8;border-bottom:1px solid var(--navy);padding:14px max(24px,calc((100vw - 1240px)/2));
display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:5;backdrop-filter:blur(10px)}}
.brand{{font:700 15px Georgia,serif;letter-spacing:.12em}} .brand b{{color:var(--burgundy)}} nav a{{margin-left:22px;
font-size:12px;text-decoration:none;color:#4f5f68}} main{{max-width:1240px;margin:auto;padding:58px 24px 84px}}
.hero{{display:grid;grid-template-columns:1.45fr .85fr;gap:48px;align-items:end;margin-bottom:38px;
border-top:4px solid var(--navy);padding-top:38px}}
.kicker,.eyebrow{{font-size:10px;letter-spacing:.18em;text-transform:uppercase;font-weight:800;color:var(--burgundy)}}
h1{{font:700 clamp(40px,6vw,72px)/1.02 Georgia,serif;letter-spacing:-.025em;margin:12px 0 20px;max-width:880px}}
.question{{font-size:18px;max-width:760px;color:#4f5c63}} .seal{{border:1px solid var(--line);border-top:4px solid var(--sage);
background:var(--panel);padding:21px;color:#435158}}
.seal .status{{display:inline-block;color:#405b49;font-weight:900;border-bottom:2px solid #77917a;padding:2px 0;
font-size:10px;letter-spacing:.12em}} .seal code{{display:block;margin-top:13px;overflow-wrap:anywhere}}
.stats{{display:grid;grid-template-columns:repeat(5,1fr);border:1px solid var(--line);margin:24px 0 56px;background:var(--panel)}}
.stat{{padding:20px;border-right:1px solid var(--line)}} .stat:last-child{{border-right:0}}
.stat strong{{font:700 30px/1 Georgia,serif;display:block;color:var(--navy)}} .stat span{{font-size:11px;color:var(--muted)}}
section{{margin-top:62px}} .section-head{{display:flex;justify-content:space-between;align-items:end;
border-bottom:2px solid var(--navy);padding-bottom:10px;margin-bottom:18px}} h2{{font:700 29px/1.15 Georgia,serif;margin:0}}
.section-head p{{margin:0;max-width:620px;color:var(--muted);font-size:12px;text-align:right}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:16px}} .panel{{background:var(--panel);border:1px solid var(--line);
padding:22px;overflow:hidden}} .panel h3{{margin:0 0 14px;font:700 15px Georgia,serif}}
.score{{font:700 62px/1 Georgia,serif;color:var(--burgundy)}} .score small{{font:13px system-ui;color:var(--muted)}}
.gap-row{{display:grid;grid-template-columns:90px 1fr 25px;gap:10px;align-items:center;margin:9px 0;font-size:12px}}
.bar{{height:6px;background:#e2ded4;overflow:hidden}} .bar i{{display:block;height:100%;background:var(--gold)}}
.table-wrap{{overflow:auto;border:1px solid var(--line);background:var(--panel)}}
table{{width:100%;border-collapse:collapse;min-width:1040px}} th,td{{padding:11px;border-bottom:1px solid #dfdbd0;text-align:left;
vertical-align:top}} th{{font-size:9px;letter-spacing:.1em;text-transform:uppercase;background:#eae6dc;position:sticky;top:49px}}
.paper-title{{font-weight:700;min-width:230px}} .rating,.state,.confidence,.decision{{display:inline-block;padding:2px 6px;
border:1px solid currentColor;font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:.04em}}
.rating.yes,.state.done,.decision.complete,.decision.run_now{{color:#4c6f57;background:#edf3ec}}
.rating.partial,.state.in_progress,.decision.prepare{{color:#846627;background:#f7f1df}}
.rating.no,.state.blocked,.decision.evidence_first{{color:#873e4a;background:#f6e9e9}}
.rating.unknown,.rating.missing,.state.ready,.decision.needs_planning{{color:#596b76;background:#edf0f1}}
.controls{{display:flex;gap:10px;margin:0 0 15px}} input,select{{border:1px solid var(--line);
background:var(--panel);padding:9px 11px;color:var(--ink);border-radius:0}} input{{min-width:280px}}
.claims{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}} .claim-card{{position:relative;
background:var(--panel);border:1px solid var(--line);border-top:3px solid var(--blue);padding:19px;min-height:190px}}
.claim-card h3{{font:700 17px/1.35 Georgia,serif}} .claim-card p{{color:var(--muted);font-size:12px}}
.locator{{font:12px ui-monospace,monospace;border-left:2px solid var(--burgundy);padding-left:9px;margin:16px 0}}
.confidence{{color:#566c79;background:#edf0f1}} .footer-note{{margin-top:54px;padding:18px 20px;border-left:4px solid var(--gold);
background:#ebe7dd;color:var(--muted)}} .warning{{color:#765a28}} .empty{{color:var(--muted);font-style:italic}}
.legend{{display:flex;gap:14px;flex-wrap:wrap;font-size:10px;color:var(--muted);margin-top:10px}}
@media(max-width:850px){{.hero,.grid2{{grid-template-columns:1fr}}.stats{{grid-template-columns:repeat(2,1fr)}}
.stat{{border-bottom:1px solid var(--line)}}.claims{{grid-template-columns:1fr}}nav{{display:none}}
.section-head{{display:block}}.section-head p{{text-align:left;margin-top:8px}}}}
@media print{{.top,.controls{{display:none}}body{{background:white}}main{{max-width:none;padding:20px}}section{{break-inside:avoid}}}}
</style>
</head>
<body>
<header class="top"><div class="brand">REPRO<b>WEAVE</b></div><nav>
<a href="#triage">Triage</a><a href="#matrix">Evidence matrix</a><a href="#claims">Claims</a><a href="#plan">Plan</a><a href="#audit">Audit</a>
</nav></header>
<main>
<div class="hero"><div><div class="kicker">Local-first research evidence map</div>
<h1>{html_escape(manifest["title"])}</h1><div class="question">{html_escape(manifest["research_question"])}</div>
</div><aside class="seal"><span class="status {audit_class}">{audit["status"].upper()}</span>
<p><strong>{audit["counts"]["errors"]} errors</strong> and {audit["counts"]["warnings"]} review warnings.
The source set is content-addressed below.</p><code>{html_escape(seal["root"])}</code></aside></div>
<div class="stats">
<div class="stat"><strong>{summary["paper_count"]}</strong><span>Papers mapped</span></div>
<div class="stat"><strong>{workspace.counts()["claim"]}</strong><span>Claims anchored</span></div>
<div class="stat"><strong>{summary["mean_score"]:.1f}</strong><span>Mean coverage / 100</span></div>
<div class="stat"><strong>{plan["summary"]["task_count"]}</strong><span>Replication tasks</span></div>
<div class="stat"><strong>{plan["summary"]["blocked_count"]}</strong><span>Current blockers</span></div>
</div>
<section id="triage"><div class="section-head"><h2>Replication candidate triage</h2>
<p>A rule-based queue combines evidence gaps, required resources, task dependencies, and remaining effort. No hidden composite score.</p></div>
<div class="table-wrap"><table><thead><tr><th>Rank</th><th>Candidate</th><th>Decision</th>
<th>Coverage</th><th>Effort</th><th>Unresolved resources</th><th>Next action</th></tr></thead>
<tbody>{_triage_rows(triage)}</tbody></table></div>
<p class="footer-note">{html_escape(triage["interpretation"])}</p></section>
<section><div class="section-head"><h2>What can actually be rebuilt?</h2>
<p>A weighted summary of documented reconstructability. The score is a navigation aid, never a verdict on research quality.</p></div>
<div class="grid2"><div class="panel"><h3>Assessment coverage</h3><div class="score">{summary["mean_score"]:.1f}
<small>/ 100 mean</small></div><p>{summary["assessed_count"]} of {summary["paper_count"]} papers have explicit cards.</p>
<p class="warning">{html_escape(assessment["warning"])}</p></div>
<div class="panel"><h3>Recurring evidence gaps</h3>{_gap_bars(summary)}</div></div></section>
<section id="matrix"><div class="section-head"><h2>Evidence matrix</h2>
<p>Every cell comes from an evidence locator, not a model-generated guess.</p></div>
<div class="controls"><input id="search" type="search" placeholder="Filter by title or ID">
<select id="threshold"><option value="0">All scores</option><option value="50">50+</option>
<option value="75">75+</option><option value="90">90+</option></select></div>
<div class="table-wrap"><table><thead><tr><th>Paper</th><th>Year</th><th>Score</th>
{"".join(f'<th title="{html_escape(meta["question"])}">{html_escape(meta["label"])}</th>' for meta in ASSESSMENT_DIMENSIONS.values())}
</tr></thead><tbody id="paperRows">{_paper_rows(assessment, matrix)}</tbody></table></div>
<div class="legend"><span>YES = sufficiently documented</span><span>PARTIAL = usable with assumptions</span>
<span>NO = explicitly unavailable</span><span>? = not yet established</span></div></section>
<section id="claims"><div class="section-head"><h2>Claim anchors</h2>
<p>Statements are linked to page, figure, table, appendix, or repository evidence supplied by the reviewer.</p></div>
<div class="claims">{_claim_cards(workspace)}</div></section>
<section id="plan"><div class="section-head"><h2>Replication execution plan</h2>
<p>Dependency waves expose what can run in parallel and which missing artifact blocks later work.</p></div>
<div class="table-wrap"><table><thead><tr><th>Wave</th><th>Task</th><th>State</th><th>Priority</th>
<th>Estimate</th><th>Dependencies</th></tr></thead><tbody>{_task_rows(plan)}</tbody></table></div>
<p class="footer-note">{html_escape(plan["assumption"])}</p></section>
<section id="audit"><div class="section-head"><h2>Audit boundary</h2>
<p>Machine checks validate structure and references. They cannot establish truth, fairness, statistical validity, or author intent.</p></div>
<div class="grid2"><div class="panel"><h3>Structural result</h3><div class="score">{audit["status"].upper()}</div>
<p>{audit["counts"]["artifacts"]} artifacts · {len(graph["nodes"])} graph nodes · {len(graph["edges"])} graph edges ·
{seal["file_count"]} sealed files.</p></div><div class="panel"><h3>Actionable backlog</h3>
<p><strong>{len(backlog)}</strong> partial, missing, or unknown evidence items remain.</p>
<p>Open the JSON source to see the exact evidence, next action, and human-entered decision behind every cell.</p></div></div></section>
<div class="footer-note"><strong>Interpretation boundary.</strong> This report is a structured reading aid.
It measures documented reconstructability, not scientific quality. It does not execute external code,
verify experimental claims, rank scientific merit, or infer missing facts.
The embedded dataset lets you inspect the exact generated state offline.</div>
</main>
<script id="reproweave-data" type="application/json">{_json_script({"manifest": manifest, "assessment": assessment, "matrix": matrix, "triage": triage, "plan": plan, "audit": audit, "graph": graph, "backlog": backlog, "seal": seal})}</script>
<script>
const search=document.querySelector("#search"), threshold=document.querySelector("#threshold");
function filterRows(){{const query=search.value.trim().toLowerCase(), min=Number(threshold.value);
document.querySelectorAll("#paperRows tr").forEach(row=>{{row.hidden=!(row.dataset.search.includes(query)&&Number(row.dataset.score)>=min)}})}}
search.addEventListener("input",filterRows);threshold.addEventListener("change",filterRows);
</script>
</body></html>
"""
    destination.write_text(html, encoding="utf-8", newline="\n")
    return destination
