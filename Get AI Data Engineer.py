# Databricks notebook source
# MAGIC %md
# MAGIC # Get AI Data Engineer
# MAGIC
# MAGIC Installs or updates AI Data Engineer in this workspace. **Paste your license key and click Run all.**
# MAGIC The key downloads the current release; it is then kept in this workspace's secret scope, so updates are just Run all.
# MAGIC
# MAGIC Run as a workspace admin. If the run asks for an Anthropic API key (workspaces without built-in Claude), paste it and run again.
# MAGIC Everything is installed into this workspace; your data never leaves it.

# COMMAND ----------

# MAGIC %pip install "databricks-sdk==0.156.0" "psycopg[binary]" pyyaml --quiet

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

dbutils.widgets.text("license_key", "", "1. License key (first install only)")
dbutils.widgets.text("anthropic_api_key", "", "2. Anthropic API key (only if asked)")
dbutils.widgets.dropdown("mode", "install", ["install", "plan"], "3. Mode")
dbutils.widgets.text("version", "main", "Advanced: release version")

# COMMAND ----------

import io
import os
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

SCOPE = "aide"
RELEASES = "https://api.github.com/repos/alibaizhanov/aide-install/zipball/"

key = dbutils.widgets.get("license_key").strip()
if not key:   # updates: the key saved by the first install
    try:
        key = dbutils.secrets.get(SCOPE, "license-key")
    except Exception:  # noqa: BLE001 - first install without a key
        raise ValueError("Paste your license key into the License key field at the top, then Run all") from None
req = urllib.request.Request(RELEASES + dbutils.widgets.get("version").strip(),
                             headers={"Authorization": f"Bearer {key}", "Accept": "application/vnd.github+json", "User-Agent": "aide-get"})
try:
    data = urllib.request.urlopen(req, timeout=300).read()
except urllib.error.HTTPError as e:
    if e.code in (401, 403, 404):
        raise ValueError("The license key is not valid or has expired: contact AI Data Engineer support") from None
    raise
root = Path(tempfile.mkdtemp())
zipfile.ZipFile(io.BytesIO(data)).extractall(root)
release = next(root.iterdir())   # the archive holds one folder: install.py, sql/, release/
print(f"Release downloaded ({len(data) // 1024} KB)")

# COMMAND ----------

sys.path.insert(0, str(release))
from install import Installer, notebook_config  # noqa: E402

if dbutils.widgets.get("anthropic_api_key").strip():
    os.environ["ANTHROPIC_API_KEY"] = dbutils.widgets.get("anthropic_api_key").strip()
plan_only = dbutils.widgets.get("mode") != "install"
installer = Installer(notebook_config(lambda name: ""), release / "release", plan_only=plan_only)
installer.run()
if not plan_only:   # keep the key so that updates need no fields
    installer.w.secrets.put_secret(SCOPE, "license-key", string_value=key)
