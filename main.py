from dotenv import load_dotenv
from databricks.sdk import WorkspaceClient

import os
import json

load_dotenv()

DATABRICKS_HOST = os.getenv("DATABRICKS_HOST")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
UC_CATALOG_NAME = os.getenv("UC_CATALOG_NAME")
UC_SCHEMA_NAME = os.getenv("UC_SCHEMA_NAME")

w = WorkspaceClient(
  host  = DATABRICKS_HOST,
  token = DATABRICKS_TOKEN
)

for c in w.catalogs.list():
  print(c.full_name)


for t in w.tables.list(catalog_name=UC_CATALOG_NAME, schema_name=UC_SCHEMA_NAME):
  print(json.dumps(t.as_dict(), indent=4))

