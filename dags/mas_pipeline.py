from dataclasses import dataclass, asdict
import re, json, hashlib
from pathlib import Path

@dataclass
class Clause:
    id: str
    doc_id: str
    page: int
    section_path: list[str]     # ["Energy","Solar", "Eligibility criteria"]
    kind: str                   # "criterion" | "threshold" | "definition" | "dns_h" | "safeguard" | "note"
    text: str
    refs: dict                  # {"doc":"MAS SAT v1.0","page":12}

def clean_text(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip()

def make_id(doc_id, page, text):
    h = hashlib.sha1(text.encode()).hexdigest()[:8]
    return f"{doc_id}-p{page}-{h}"

def pdf_to_markdown(pdf_path: Path) -> list[dict]:
    import pdfplumber
    md = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            txt = page.extract_text() or ""
            md.append({"page": i, "text": txt})
    return md

def detect_section_lines(text: str) -> list[str]:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return lines

def classify_kind(line: str) -> str:
    l = line.lower()
    if any(k in l for k in ["must", "shall", "required", "eligibility"]): return "criterion"
    if any(k in l for k in ["threshold", "intensity", "gco2", "capex","<",">","≤","≥"]): return "threshold"
    if any(k in l for k in ["do no significant harm","dnsh"]): return "dns_h"
    if any(k in l for k in ["minimum safeguards","governance","social"]): return "safeguard"
    if any(k in l for k in ["definition", "means", "refers to"]): return "definition"
    return "note"

def parse_pdf_to_clauses(pdf_path: str, doc_id: str, taxonomy_name="MAS SAT") -> list[Clause]:
    md_pages = pdf_to_markdown(Path(pdf_path))
    clauses = []
    section_stack = []
    for pg in md_pages:
        lines = detect_section_lines(pg["text"])
        for line in lines:
            kind = classify_kind(line)
            cid = make_id(doc_id, pg["page"], line[:160])
            clause = Clause(
                id=cid, doc_id=doc_id, page=pg["page"],
                section_path=section_stack[-3:] if section_stack else [],
                kind=kind, text=clean_text(line),
                refs={"doc": taxonomy_name, "page": pg["page"]}
            )
            clauses.append(clause)
    return clauses

def dump_clauses(clauses, out_path: str):
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump([asdict(c) for c in clauses], f, ensure_ascii=False, indent=2)


from __future__ import annotations
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable

# Task callables
from tasks.ingest_docs import run as ingest_docs
from tasks.chunk_docs import run as chunk_docs
from tasks.build_index import run as build_index
from tasks.classify_actions import run as classify_actions
from tasks.generate_report import run as generate_report

CFG = Variable.get("MAS_PIPELINE_CFG", default_var="configs/pipeline.yaml")

with DAG(
    dag_id="mas_esg_agentic_pipeline",
    description="Ingest MAS/GFIT docs -> Chunk -> Index -> Classify -> Report",
    start_date=datetime(2025, 8, 1),
    schedule="@daily",
    catchup=False,
    max_active_runs=1,
    default_args={"owner": "esg-agent", "retries": 1},
    tags=["mas","esg","taxonomy"],
) as dag:
    t1 = PythonOperator(task_id="ingest_docs", python_callable=ingest_docs, op_kwargs={"pipeline_cfg": CFG})
    t2 = PythonOperator(task_id="chunk_docs", python_callable=chunk_docs, op_kwargs={"pipeline_cfg": CFG})
    t3 = PythonOperator(task_id="build_index", python_callable=build_index, op_kwargs={"pipeline_cfg": CFG})
    t4 = PythonOperator(task_id="classify_actions", python_callable=classify_actions, op_kwargs={"pipeline_cfg": CFG})
    t5 = PythonOperator(task_id="generate_report", python_callable=generate_report, op_kwargs={"pipeline_cfg": CFG})
    t1 >> t2 >> t3 >> t4 >> t5
