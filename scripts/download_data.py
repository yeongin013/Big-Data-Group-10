"""Download UCI Online Retail II (CC BY 4.0) into data/raw/.

Usage: python scripts/download_data.py
"""
import hashlib
import io
import ssl
import urllib.request
import zipfile
from pathlib import Path

URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"
NAME = "online_retail_II.xlsx"
SHA256 = "bcbe73b35f5b7babf197fb0cb983a11f5d9ff929078d4aa53d171b1f2df2e980"
OUT = Path(__file__).resolve().parent.parent / "data" / "raw" / NAME

try:  # certifi comes with requirements.txt; python.org Python on macOS has no CA store.
    import certifi
    CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:  # standard library only: system CA store
    CONTEXT = None


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    if OUT.exists() and sha256(OUT.read_bytes()) == SHA256:
        print(f"Already present: {OUT}")
        return
    print(f"Downloading {URL}")
    try:
        with urllib.request.urlopen(URL, context=CONTEXT) as r:
            archive = zipfile.ZipFile(io.BytesIO(r.read()))
    except urllib.error.URLError as e:
        if "CERTIFICATE_VERIFY_FAILED" in str(e):
            raise SystemExit(
                "SSL certificate error. Run 'pip install -r requirements.txt' first (certifi), "
                "or on macOS with python.org Python run "
                "'Install Certificates.command' in /Applications/Python 3.x/, "
                "or retry with SSL_CERT_FILE=/etc/ssl/cert.pem."
            )
        raise
    data = archive.read(NAME)
    if sha256(data) != SHA256:
        raise SystemExit("Checksum mismatch: the file differs from the expected version.")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(data)
    print(f"Saved {OUT} ({len(data):,} bytes)")


if __name__ == "__main__":
    main()
