import json,subprocess,time
from pathlib import Path
ops=Path(__file__).resolve().parent
results=[]
for label,root in [("curriculum",r"C:\Users\anass\Documents\Codex\FlyCraft-curriculum"),("development",r"C:\Users\anass\Documents\FlyCraft")]:
 with (ops/(label+"_baseline_tests.txt")).open("w",encoding="utf-8") as f:
  p=subprocess.run([r"C:\Users\anass\Documents\FlyCraft\.venv\Scripts\python.exe","-m","unittest","discover","-s","tests"],cwd=root,stdout=f,stderr=subprocess.STDOUT)
 results.append(dict(checkout=label,returncode=p.returncode,finished_unix=time.time()))
 (ops/"baseline_status.json").write_text(json.dumps(results,indent=2))
 if p.returncode:break
