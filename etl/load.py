"""LOAD - fill the dimensions, then the fact table.   Run:  python -m etl.load"""
from etl.extract import extract_all, RAW_DIR
from etl.transform import transform
from warehouse import fact_depression as fact
from warehouse.database import get_connection, init_warehouse, table_counts
from warehouse.dimensions import dim_student, dim_academic, dim_lifestyle, dim_mentalhealth, dim_time


def run_etl(raw_dir=RAW_DIR):
    """Full refresh: extract -> transform -> rebuild warehouse -> load."""
    clean, report = transform(extract_all(raw_dir))

    init_warehouse(reset=True)
    with get_connection() as conn:
        dim_student.load(conn, clean)
        clean["academic_id"] = dim_academic.load(conn, clean)
        clean["lifestyle_id"] = dim_lifestyle.load(conn, clean)
        clean["mentalhealth_id"] = dim_mentalhealth.load(conn, clean)
        time_map = dim_time.load(conn, clean)
        report["fact_rows"] = fact.load(conn, clean, time_map)

    report["table_counts"] = table_counts()
    return report


def print_report(report):
    print("ETL finished")
    for key, value in report.items():
        if key != "table_counts":
            print(f"  {key:38}: {value}")
    print("  table row counts:")
    for table, count in report["table_counts"].items():
        print(f"    {table:20}: {count}")


if __name__ == "__main__":
    print_report(run_etl())
