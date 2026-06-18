import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from google.cloud import bigquery
import pandas as pd
from pydantic import BaseModel

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
    
# Rota 1: Busca metadados estruturais e colunas elegíveis para filtro de data (Custo Zero)
@app.get("/api/table-metadata/{dataset_id}/{table_id}")
def get_table_metadata(dataset_id: str, table_id: str):
    try:
        table_ref = f"{PROJECT_ID}.{dataset_id}.{table_id}"
        table = bq_client.get_table(table_ref)
        
        # Filtra apenas colunas temporais elegíveis para o dropdown de filtro D-X
        date_columns = [
            field.name for field in table.schema 
            if field.field_type in ["DATE", "DATETIME", "TIMESTAMP"] and field.mode != "REPEATED"
        ]
        
        schema_info = [
            {"name": field.name, "type": field.field_type, "mode": field.mode}
            for field in table.schema
        ]
        
        return {
            "table_id": table_id,
            "table_type": table.table_type,  # TABLE, VIEW, EXTERNAL
            "schema": schema_info,
            "date_columns": date_columns,
            "total_rows": table.num_rows
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao capturar metadados: {str(e)}")


# Rota 2: Executa Simulação FinOps (Dry Run) ou o Profiling Estatístico Real
@app.get("/api/table-profiling-run/{dataset_id}/{table_id}")
def run_table_profiling(
    dataset_id: str, 
    table_id: str, 
    dry_run: bool = True,
    sample_percent: Optional[float] = 100.0,
    date_column: Optional[str] = None,
    days_lookback: Optional[int] = None,
    exact_distinct: bool = False
):
    try:
        table_ref = f"{PROJECT_ID}.{dataset_id}.{table_id}"
        table = bq_client.get_table(table_ref)
        is_view = table.table_type == "VIEW"
        
        # Define dinamicamente o sufixo do alias para não confundir o usuário engenheiro
        uniqueness_suffix = "__exact_distinct" if exact_distinct else "__approx_distinct"
        
        # Início da montagem dinâmica da query analítica baseada em FinOps
        select_clauses = ["COUNT(*) AS _total_sampled_rows"]
        
        for field in table.schema:
            # Ignora estruturas complexas ou aninhadas para prevenir falhas de agregação
            if field.field_type in ["RECORD", "STRUCT"] or field.mode == "REPEATED":
                continue
            
            escaped_col = f"`{field.name}`"
            # Auxiliares para cálculo de Completude
            select_clauses.append(f"COUNT({escaped_col}) AS {field.name}__count_filled")
            
            # Alternância algorítmica injetando o alias correto correspondente
            if exact_distinct:
                select_clauses.append(f"COUNT(DISTINCT {escaped_col}) AS {field.name}{uniqueness_suffix}")
            else:
                select_clauses.append(f"APPROX_COUNT_DISTINCT({escaped_col}) AS {field.name}{uniqueness_suffix}")
            
            # Habilita MIN/MAX para tipos textuais (STRING) e booleanos, além de numéricos/temporais
            if field.field_type in ["INTEGER", "FLOAT", "NUMERIC", "BIGNUMERIC", "INT64", "FLOAT64", "DATE", "DATETIME", "TIMESTAMP", "STRING", "BOOLEAN"]:
                select_clauses.append(f"MIN({escaped_col}) AS {field.name}__min")
                select_clauses.append(f"MAX({escaped_col}) AS {field.name}__max")
        
        from_clause = f"`{table_ref}`"
        # Injeta TABLESAMPLE apenas se for tabela física nativa
        if not is_view and sample_percent and sample_percent < 100:
            from_clause += f" TABLESAMPLE SYSTEM ({sample_percent} PERCENT)"
            
        where_clauses = []
        if date_column and days_lookback is not None:
            target_field = next((f for f in table.schema if f.name == date_column), None)
            if target_field:
                if target_field.field_type == "DATE":
                    where_clauses.append(f"`{date_column}` >= DATE_SUB(CURRENT_DATE(), INTERVAL {days_lookback} DAY)")
                elif target_field.field_type in ["TIMESTAMP", "DATETIME"]:
                    where_clauses.append(f"`{date_column}` >= {target_field.field_type}_SUB(CURRENT_{target_field.field_type}(), INTERVAL {days_lookback} DAY)")
                else:
                    where_clauses.append(f"`{date_column}` >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days_lookback} DAY)")
                
        query = f"SELECT {', '.join(select_clauses)} FROM {from_clause}"
        if where_clauses:
            query += f" WHERE {' AND '.join(where_clauses)}"
            
        # Configuração do Job do BigQuery de acordo com a intenção do clique
        job_config = bigquery.QueryJobConfig(dry_run=dry_run, use_query_cache=True)
        query_job = bq_client.query(query, job_config=job_config)
        
        if dry_run:
            bytes_scanned = query_job.total_bytes_processed
            # Conversão: Proporção baseada em 1 TB = 10^12 Bytes no modelo On-Demand do BQ
            cost_usd = (bytes_scanned / (10**12)) * 6.25
            return {
                "dry_run": True,
                "bytes_scanned": bytes_scanned,
                "cost_usd": cost_usd,
                "query_generated": query
            }
        
        # Execução Analítica Efetiva
        df = query_job.to_dataframe()
        if df.empty:
            raise HTTPException(status_code=404, detail="Nenhum registro encontrado para amostragem.")
            
        row = df.iloc[0]
        total_sampled_rows = int(row["_total_sampled_rows"])
        
        columns_profiling = []
        for field in table.schema:
            if field.field_type in ["RECORD", "STRUCT"] or field.mode == "REPEATED":
                columns_profiling.append({
                    "name": field.name, "type": field.field_type, "mode": field.mode, "status": "unsupported"
                })
                continue
                
            count_filled = int(row.get(f"{field.name}__count_filled", 0))
            approx_distinct = int(row.get(f"{field.name}{uniqueness_suffix}", 0))
            
            completeness = (count_filled / total_sampled_rows * 100) if total_sampled_rows > 0 else 0
            uniqueness = (approx_distinct / count_filled * 100) if count_filled > 0 else 0
            
            # Solução de Contenção Estatística: Limita o teto da aproximação do HyperLogLog a 100%
            uniqueness_capped = min(uniqueness, 100.0)
            
            min_val = row.get(f"{field.name}__min")
            max_val = row.get(f"{field.name}__max")
            
            if pd.notnull(min_val) and hasattr(min_val, 'strftime'):
                min_val = min_val.strftime('%Y-%m-%d %H:%M:%S')
            if pd.notnull(max_val) and hasattr(max_val, 'strftime'):
                max_val = max_val.strftime('%Y-%m-%d %H:%M:%S')
                
            columns_profiling.append({
                "name": field.name,
                "type": field.field_type,
                "mode": field.mode,
                "status": "profiled",
                "completeness_percent": round(completeness, 2),
                "approx_distinct_count": approx_distinct,
                "uniqueness_percent": round(uniqueness_capped, 2),
                "min": str(min_val) if pd.notnull(min_val) else None,
                "max": str(max_val) if pd.notnull(max_val) else None
            })
            
        return {
            "dry_run": False,
            "table_id": table_id,
            "total_rows": table.num_rows,
            "sampled_rows": total_sampled_rows,
            "columns": columns_profiling,
            "query_generated": query
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dataset-health/{dataset_id}")
def get_dataset_health(dataset_id: str):
    try:
        # Busca metadados do Dataset (como Região/Location)
        ds_ref = bq_client.get_dataset(dataset_id)
        location = ds_ref.location or "US"

        # Solução FinOps: LEFT JOIN com INFORMATION_SCHEMA.COLUMNS para contagem gratuita de colunas
        query_metadata = f"""
        WITH table_base AS (
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
        ),
        col_counts AS (
            SELECT table_name, COUNT(1) AS column_count
            FROM `{PROJECT_ID}.{dataset_id}.INFORMATION_SCHEMA.COLUMNS`
            GROUP BY table_name
        )
        SELECT 
            t.*,
            COALESCE(c.column_count, 0) AS column_count
        FROM table_base t
        LEFT JOIN col_counts c ON t.table_id = c.table_name
        ORDER BY t.table_id ASC
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

        df['location'] = location

        oldest_created_row = df.loc[df['created_time'].idxmin()] if not df['created_time'].isnull().all() else None
        newest_created_row = df.loc[df['created_time'].idxmax()] if not df['created_time'].isnull().all() else None
        oldest_modified_row = df.loc[df['modified_time'].idxmin()] if not df['modified_time'].isnull().all() else None
        newest_modified_row = df.loc[df['modified_time'].idxmax()] if not df['modified_time'].isnull().all() else None

        def format_kpi_string(row, time_col):
            if row is None or pd.isna(row[time_col]): return "-"
            return f"{row['table_id']} ({row[time_col].strftime('%Y-%m-%d %H:%M:%S')})"

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