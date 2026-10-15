import pickle, json, sqlite3, time, collections, math
from pathlib import Path

PROJ = Path(__file__).parent.resolve()
my_test = json.loads((PROJ / 'runs/spider_full/my_test_set.json').read_text(encoding='utf-8'))
OLD_PREFIX = "C:\\Users\\Pathao Ltd\\Desktop\\Text_to_SQL-main"

def db_path_for(ex):
    p = ex['db_path'].replace(OLD_PREFIX, str(PROJ))
    if not Path(p).exists():
        p = str(PROJ / 'data' / 'spider' / 'database' / ex['db_id'] / f"{ex['db_id']}.sqlite")
    return p

def norm_cell(x) -> str:
    try:
        if x is None:
            return ""
        s = str(x).strip()
        try:
            float(s)
            return s
        except ValueError:
            return s.lower()
    except Exception:
        return str(x)

def run_query(db_path, sql):
    try:
        con = sqlite3.connect(db_path)
        start = time.monotonic()
        def _t():
            return 1 if time.monotonic() - start > 10 else 0
        con.set_progress_handler(_t, 1000)
        cur = con.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        cur.close()
        con.close()
        norm = [tuple(norm_cell(c) for c in r) for r in rows]
        norm.sort()
        return True, norm
    except Exception:
        return False, None

gold_cache = {}
def gold_result(i):
    if i not in gold_cache:
        ex = my_test[i]
        gsql = ex['gold_query'].strip().rstrip(';') + ';'
        gold_cache[i] = run_query(db_path_for(ex), gsql)
    return gold_cache[i]

def eval_sql(i, sql):
    ok_p, pres = run_query(db_path_for(my_test[i]), sql.strip().rstrip(';') + ';')
    ok_g, gres = gold_result(i)
    return ok_g and ok_p and gres == pres

def mcnemar_exact(b, c):
    n = b + c
    if n == 0:
        return 1.0
    p = 0.0
    for k in range(min(b, c) + 1):
        p += math.comb(n, k)
    p *= (0.5 ** n)
    return min(1.0, 2 * p)

LABELS = ['SCoT-Native', 'QD-InterCol', 'Standard']
out_rows = []
per_backend = {}
for bkey in ['gemini', 'gpt4o', 'llama', 'haiku']:
    with open(PROJ / 'analysis_scot_diagnostics' / f'parsed_debug_{bkey}.pkl', 'rb') as f:
        records = pickle.load(f)
    by_idx = {}
    for r in records:
        by_idx[r['idx']] = r
    n = len(by_idx)
    sel = {}
    orc = {}
    maj = {}
    lab_ok = {L: {} for L in LABELS}
    for idx, r in sorted(by_idx.items()):
        i = idx - 1
        cands = r.get('cands', [])
        sel[i] = eval_sql(i, r['final_sql'])
        any_ok = False
        exec_groups = collections.Counter()
        for lab, sql in cands:
            ok = eval_sql(i, sql)
            any_ok = any_ok or ok
            if lab in lab_ok:
                lab_ok[lab][i] = ok
            ok_p, pres = run_query(db_path_for(my_test[i]), sql.strip().rstrip(';') + ';')
            if ok_p:
                exec_groups[str(pres)] += 1
        orc[i] = any_ok
        if exec_groups:
            best = max(exec_groups.values())
            winners = [k for k, v in exec_groups.items() if v == best]
            if len(winners) == 1:
                ok_g, gres = gold_result(i)
                maj[i] = bool(ok_g and winners[0] == str(gres))
            else:
                maj[i] = sel[i]
        else:
            maj[i] = sel[i]

    def pct(d):
        return sum(d.values()) / n * 100

    row = {'backend': bkey, 'n': n,
           'selected': pct(sel), 'oracle': pct(orc), 'majority_vote': pct(maj)}
    for L in LABELS:
        row[f'always_{L}'] = pct(lab_ok[L]) if lab_ok[L] else None
    # McNemar: majority vote vs selected
    b = sum(1 for i in sel if maj[i] and not sel[i])
    c = sum(1 for i in sel if sel[i] and not maj[i])
    row['maj_vs_sel_b'] = b
    row['maj_vs_sel_c'] = c
    row['maj_vs_sel_p'] = mcnemar_exact(b, c)
    # McNemar: oracle vs selected (context)
    b2 = sum(1 for i in sel if orc[i] and not sel[i])
    c2 = sum(1 for i in sel if sel[i] and not orc[i])
    row['orc_vs_sel_b'] = b2
    row['orc_vs_sel_c'] = c2
    row['orc_vs_sel_p'] = mcnemar_exact(b2, c2)
    out_rows.append(row)
    per_backend[bkey] = row
    print(f"{bkey}: N={n} | selected={row['selected']:.2f}% oracle={row['oracle']:.2f}% "
          f"majvote={row['majority_vote']:.2f}% | always: " +
          " ".join(f"{L}={row[f'always_{L}']:.2f}%" for L in LABELS) +
          f" | maj-vs-sel: b={b} c={c} p={row['maj_vs_sel_p']:.2e}")

import csv
with open(PROJ / 'selection_policies_full.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
    w.writeheader()
    w.writerows(out_rows)
print("saved selection_policies_full.csv")
