# bucketize_failures.py
import re, pathlib
p = pathlib.Path("runs/dev_600")/"scot_debug.log"
log = p.read_text(errors="ignore").lower() if p.exists() else ""
buckets = {
 "no such column": len(re.findall(r"no such column", log)),
 "ambiguous column": len(re.findall(r"ambiguous column", log)),
 "syntax error": len(re.findall(r"syntax error", log)),
 "misuse of aggregate": len(re.findall(r"misuse of aggregate", log)),
 "incomplete input": len(re.findall(r"incomplete input", log)),
}
print(buckets)
