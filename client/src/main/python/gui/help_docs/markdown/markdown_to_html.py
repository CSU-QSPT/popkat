import os
from pathlib import Path
import subprocess

script_path = Path(os.path.realpath(__file__)).parent

pandoc = "pandoc"  # full path could go here
dest_dir = script_path.parent
src_dir = script_path / "src"
src_fmt, src_suf = "markdown", "md"
dest_fmt, dest_suf = "html", "html"
css_file = src_dir / "popkat.css"

src_files = list(src_dir.glob(f"*.{src_suf}"))

old_dest_files = list(dest_dir.glob(f"*.{dest_fmt}"))
for fl in old_dest_files:
    fl.unlink()

for doc in src_files:
    src_file = doc
    dest_file = dest_dir / Path(doc.name).with_suffix(f".{dest_suf}")
    cmd = [
        pandoc,
        str(src_file),
        "-f",
        src_fmt,
        "-t",
        dest_fmt,
        "-H",
        str(css_file),
        "-s",
        "-o",
        str(dest_file),
    ]
    subprocess.Popen(cmd)
