import sys

from google.cloud import bigquery
from google.cloud.exceptions import NotFound

from .schema import SCHEMA_CONFIG


def run_setup():
    project_id = sys.argv[1] if len(sys.argv) > 1 else None
    region = sys.argv[2] if len(sys.argv) > 2 else None

    if not project_id or not region:
        print("❌ USAGE: python3 -m bigquery.setup_table <PROJECT_ID> <REGION>\n")
        sys.exit(1)

    client = bigquery.Client(project=project_id)
    print(f"🚀 Running Setup Start | Project: {project_id} | Region: {region}")

    for dataset_id, table_modules in SCHEMA_CONFIG.items():
        dataset_ref = f"{project_id}.{dataset_id}"

        # 1. Check Dataset Existence & Create if Not Exists
        try:
            client.get_dataset(dataset_ref)
            print(f"✅ Dataset Exists: {dataset_id}")
        except NotFound:
            new_dataset = bigquery.Dataset(dataset_ref)
            new_dataset.location = region
            client.create_dataset(new_dataset)
            print(f"✨ Created Dataset: '{dataset_id}' in {region}")

        # 2. Loop through Tables in Dataset
        for table_module in table_modules:
            table_name = table_module.TABLE_NAME
            table_ref = f"{dataset_ref}.{table_name}"

            try:
                existing_table = client.get_table(table_ref)
                existing_table.schema = table_module.SCHEMA
                update_fields = ["schema"]

                if hasattr(table_module, "CLUSTERING_FIELDS"):
                    existing_table.clustering_fields = table_module.CLUSTERING_FIELDS
                    update_fields.append("clustering_fields")

                if hasattr(table_module, "TIME_PARTITIONING"):
                    existing_table.time_partitioning = table_module.TIME_PARTITIONING
                    update_fields.append("time_partitioning")

                client.update_table(existing_table, update_fields)
                print(f"✅ Update Table: {table_name}")
            except NotFound:
                new_table = bigquery.Table(table_ref, schema=table_module.SCHEMA)

                partition_msg = ""
                if hasattr(table_module, "TIME_PARTITIONING"):
                    new_table.time_partitioning = table_module.TIME_PARTITIONING
                    partition_msg += (
                        f" (PARTITIONED BY {table_module.TIME_PARTITIONING.field})"
                    )

                if hasattr(table_module, "CLUSTERING_FIELDS"):
                    new_table.clustering_fields = table_module.CLUSTERING_FIELDS
                    partition_msg += (
                        f" (CLUSTERED BY {', '.join(table_module.CLUSTERING_FIELDS)})"
                    )

                client.create_table(new_table)
                print(f"✅ Create Table: {table_ref} {partition_msg}")


if __name__ == "__main__":
    run_setup()
