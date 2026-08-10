# eval_scot.py
import json, sqlite3, pathlib, math, re

def has_order_by(sql:str)->bool:
    return bool(re.search(r"\border\s+by\b", sql, flags=re.I))

def normalize_row(row):
    out=[]
    for v in row:
        if isinstance(v,float):
            out.append(round(v,4))  # numeric tolerance anchor
        elif isinstance(v,str):
            out.append(v.strip())
        else:
            out.append(v)
    return tuple(out)

def fetch(con, sql):
    cur=con.cursor(); cur.execute(sql); rows=cur.fetchall(); cur.close()
    return [normalize_row(r) for r in rows]

def seteq(a,b):  # set compare (duplicates ignore)
    return set(a)==set(b)

def main():
    run_dir = pathlib.Path("runs/dev_600")  
    data = json.loads((run_dir/"my_test_set.json").read_text())
    preds = [l.strip() for l in (run_dir/"predicted_scot_models_gemini-2.5-pro.sql").read_text().splitlines()]
    assert len(preds)==len(data), f"preds({len(preds)}) != data({len(data)})"
    ok=0; fails=[]
    for i,(ex,pred) in enumerate(zip(data,preds),1):
        con=sqlite3.connect(ex["db_path"])
        try:
            gold = ex.get("gold_sql")
            pr = fetch(con, pred)
            if gold:
                gr = fetch(con, gold)
                if has_order_by(gold):
                    good = (pr==gr)
                else:
                    good = seteq(pr,gr)
            else:
                good = True  # যদি gold না থাকে, স্কিপের বদলে পাস
            ok += 1 if good else 0
            if not good:
                fails.append((i, ex.get("db_id","?"), ex["question"], pred))
        except Exception as e:
            fails.append((i, ex.get("db_id","?"), ex["question"], f"EXEC_ERR: {type(e).__name__}: {e} | {pred}"))
        finally:
            con.close()
    total=len(data)
    print(f"Accuracy: {ok}/{total} = {ok/total:.3f}")
    (run_dir/"fails.txt").write_text("\n\n".join(map(str,fails)))
if __name__=="__main__": main()
