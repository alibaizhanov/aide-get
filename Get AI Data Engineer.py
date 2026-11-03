# Databricks notebook source
# MAGIC %md
# MAGIC # Get AI Data Engineer
# MAGIC
# MAGIC **1. Paste your license key between the quotes in the cell below. 2. Click Run all.** That's it: about 10 minutes,
# MAGIC and the last line prints the link to the app.
# MAGIC
# MAGIC Everything is installed into this workspace; your data never leaves it. Run as a workspace admin. To update later,
# MAGIC open this notebook and click Run all again: the key is remembered, so you can leave it empty.
# MAGIC
# MAGIC A yellow note about a changed `databricks-sdk` version during the run is expected.

# COMMAND ----------

LICENSE_KEY = ""   # paste your license key between the quotes

# Optional: your own Anthropic API key. Not needed: the model access comes with your license.
ANTHROPIC_API_KEY = ""

import json
import os

# a missing key stops here, in seconds, before anything is downloaded or installed
SCOPE = "aide"
if not LICENSE_KEY.strip():
    try:
        LICENSE_KEY = dbutils.secrets.get(SCOPE, "license-key")   # updates: the key saved by the first install
    except Exception:  # noqa: BLE001 - first install without a key
        raise ValueError("The license key is empty: paste it between the quotes in LICENSE_KEY above, then click Run all") from None
# the Python restart below clears variables: hand the keys over in a file only this user can read, deleted after use
fd = os.open("/tmp/aide_get.json", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w") as f:
    json.dump({"license_key": LICENSE_KEY.strip(), "anthropic_api_key": ANTHROPIC_API_KEY.strip()}, f)
print("License key found")

# COMMAND ----------

# MAGIC %pip install "databricks-sdk==0.156.0" "psycopg[binary]" pyyaml cryptography --quiet

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import base64
import hashlib
import io
import json
import os
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

SCOPE = "aide"
RELEASES = "https://api.github.com/repos/alibaizhanov/aide-install/zipball/main"
with open("/tmp/aide_get.json") as f:
    keys = json.load(f)
os.remove("/tmp/aide_get.json")
key, own_model_key = keys["license_key"], keys["anthropic_api_key"]

req = urllib.request.Request(RELEASES, headers={"Authorization": f"Bearer {key}", "Accept": "application/vnd.github+json",
                                                "User-Agent": "aide-get"})
try:
    data = urllib.request.urlopen(req, timeout=300).read()
except urllib.error.HTTPError as e:
    if e.code in (401, 403, 404):
        raise ValueError("The license key is not valid or has expired: contact AI Data Engineer support") from None
    raise
root = Path(tempfile.mkdtemp())
zipfile.ZipFile(io.BytesIO(data)).extractall(root)
release = next(root.iterdir())   # the archive holds one folder: install.py, sql/, release/, model-keys/
print(f"Release downloaded ({len(data) // 1024} KB)")

# the model key that comes with the license: only this license key can find and decrypt it
if own_model_key:
    os.environ["ANTHROPIC_API_KEY"] = own_model_key
else:
    from cryptography.fernet import Fernet
    sealed = release / "model-keys" / (hashlib.sha256(key.encode()).hexdigest()[:32] + ".enc")
    if sealed.exists():
        fernet = Fernet(base64.urlsafe_b64encode(hashlib.sha256(("aide-model-key:" + key).encode()).digest()))
        os.environ["ANTHROPIC_API_KEY"] = fernet.decrypt(sealed.read_bytes()).decode()

# COMMAND ----------

sys.path.insert(0, str(release))
from install import Installer, notebook_config  # noqa: E402

installer = Installer(notebook_config(lambda name: ""), release / "release", plan_only=False)
installer.run()
installer.w.secrets.put_secret(SCOPE, "license-key", string_value=key)   # updates need no key

url = installer.w.apps.get(installer.cfg["app_name"]).url
displayHTML(f"""
<div style="font-family:system-ui,sans-serif;padding:24px 0">
  <div style="font-size:20px;font-weight:600;margin-bottom:6px">AI Data Engineer is installed</div>
  <div style="color:#555;margin-bottom:18px">Open it and create your first mart. The license key is saved in this workspace,
    so you can delete it from the first cell now; updates are just Run all.</div>
  <a href="{url}" target="_blank" style="display:inline-block;background:#111;color:#fff;padding:12px 22px;border-radius:10px;
     font-size:16px;font-weight:600;text-decoration:none">Open AI Data Engineer &rarr;</a>
</div>""")
