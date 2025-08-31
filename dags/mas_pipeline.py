
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
