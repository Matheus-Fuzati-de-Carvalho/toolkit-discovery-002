import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from google.cloud import bigquery
import pandas as pd

app = FastAPI(title="Data Catalog - Dataset Viewer")

# Configuração GCP Inteligente (Autodescoberta)
try:
    bq_client = bigquery.Client()
    PROJECT_ID = bq_client.project
except Exception as e:
    print(f"Aviso na inicialização do GCP: {e}")
    PROJECT_ID = "toolkit-discovery-001"

@app.get("/api/datasets")
def list_datasets():
    try:
        datasets = list(bq_client.list_datasets())
        return [{"dataset_id": d.dataset_id} for d in datasets]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar Datasets: {str(e)}")

@app.get("/api/dataset-health/{dataset_id}")
def get_dataset_health(dataset_id: str):
    try:
        # Busca metadados do Dataset (como Região/Location)
        ds_ref = bq_client.get_dataset(dataset_id)
        location = ds_ref.location or "US"

        query_metadata = f"""
        SELECT
            table_id,
            row_count,
            size_bytes,
            CASE 
                WHEN type = 1 THEN 'TABLE' 
                WHEN type = 2 THEN 'VIEW' 
                ELSE 'EXTERNAL' 
            END as table_type,
            TIMESTAMP_MILLIS(creation_time) as created_time,
            TIMESTAMP_MILLIS(last_modified_time) as modified_time,
            TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), TIMESTAMP_MILLIS(last_modified_time), HOUR) as freshness_hours
        FROM `{PROJECT_ID}.{dataset_id}.__TABLES__`
        ORDER BY table_id ASC
        """
        df = bq_client.query(query_metadata).to_dataframe()
        
        if df.empty:
            return {
                "status": "empty",
                "location": location,
                "kpis": {
                    "total_tables": 0, "total_size_bytes": 0, "total_rows": 0, "empty_tables": 0,
                    "h12": 0, "h24": 0, "h48": 0, "w1": 0, "m1": 0, "old": 0
                },
                "tables_detailed": []
            }

        # Injeta a região em cada linha da tabela para exibição no grid
        df['location'] = location

        # Identificação de Linhagem Temporal (Mais antigas e mais recentes)
        oldest_created_row = df.loc[df['created_time'].idxmin()] if not df['created_time'].isnull().all() else None
        newest_created_row = df.loc[df['created_time'].idxmax()] if not df['created_time'].isnull().all() else None
        oldest_modified_row = df.loc[df['modified_time'].idxmin()] if not df['modified_time'].isnull().all() else None
        newest_modified_row = df.loc[df['modified_time'].idxmax()] if not df['modified_time'].isnull().all() else None

        def format_kpi_string(row, time_col):
            if row is None or pd.isna(row[time_col]): return "-"
            return f"{row['table_id']} ({row[time_col].strftime('%Y-%m-%d %H:%M:%S')})"

        # Formatação das strings de data para o JSON final
        df['created_time'] = df['created_time'].dt.strftime('%Y-%m-%d %H:%M:%S')
        df['modified_time'] = df['modified_time'].dt.strftime('%Y-%m-%d %H:%M:%S')
        df = df.where(pd.notnull(df), None)

        return {
            "status": "success",
            "location": location,
            "kpis": {
                "total_tables": len(df),
                "total_size_bytes": int(df["size_bytes"].sum()),
                "total_rows": int(df["row_count"].sum()),
                "empty_tables": int((df["row_count"] == 0).sum()),
                "oldest_created": format_kpi_string(oldest_created_row, 'created_time'),
                "newest_created": format_kpi_string(newest_created_row, 'created_time'),
                "oldest_modified": format_kpi_string(oldest_modified_row, 'modified_time'),
                "newest_modified": format_kpi_string(newest_modified_row, 'modified_time'),
                # Janelas temporais solicitadas
                "h12": int((df["freshness_hours"] <= 12).sum()),
                "h24": int(((df["freshness_hours"] > 12) & (df["freshness_hours"] <= 24)).sum()),
                "h48": int(((df["freshness_hours"] > 24) & (df["freshness_hours"] <= 48)).sum()),
                "w1": int(((df["freshness_hours"] > 48) & (df["freshness_hours"] <= 168)).sum()),
                "m1": int(((df["freshness_hours"] > 168) & (df["freshness_hours"] <= 720)).sum()),
                "old": int((df["freshness_hours"] > 720).sum())
            },
            "tables_detailed": df.to_dict(orient="records")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

app.mount("/", StaticFiles(directory="static", html=True), name="static")