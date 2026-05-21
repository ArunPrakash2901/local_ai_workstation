from pathlib import Path
from .paths import quant_path

def get_raw_dataset_path(source_name: str, symbol: str) -> Path:
    return quant_path("data", "quant", "raw", source_name, f"{symbol}.parquet")

def get_clean_dataset_path(symbol: str) -> Path:
    return quant_path("data", "quant", "clean", f"{symbol}.parquet")

def get_feature_dataset_path(symbol: str, feature_set_id: str) -> Path:
    return quant_path("data", "quant", "features", symbol, f"{feature_set_id}.parquet")

def get_experiment_manifest_path(experiment_id: str) -> Path:
    return quant_path("experiments", "quant", "manifests", f"{experiment_id}.yaml")

def get_experiment_result_path(experiment_id: str) -> Path:
    return quant_path("experiments", "quant", "results", f"{experiment_id}.json")

def get_report_path(report_id: str) -> Path:
    return quant_path("reports", "quant", f"{report_id}.md")
