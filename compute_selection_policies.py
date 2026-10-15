import pickle, json, sqlite3, time, collections
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

PRED = {
    'gemini': 'predicted_scot_models_google_gemini-2.5-flash.sql',
    'gpt4o': 'predicted_scot_models_openai_gpt-4o-mini.sql',
    'llama': 'predicted_scot_models_meta-llama_llama-3.3-70b-instruct.sql',
    'haiku': 'predicted_scot_models_anthropic_claude-haiku-4.5.sql',
}

results = {}
for bkey in ['gemini', 'gpt4o', 'llama', 'haiku']:
    with open(PROJ / 'analysis_scot_diagnostics' / f'parsed_debug_{bkey}.pkl', 'rb') as f:
        records = pickle.load(f)
    by_idx = {}
    for r in records:  # keep last occurrence per idx
        by_idx[r['idx']] = r
    n = len(by_idx)
    pred_lines = (PROJ / 'runs/spider_full' / PRED[bkey]).read_text(encoding='utf-8').splitlines()
    match_final = sum(1 for idx, r in by_idx.items()
                      if idx - 1 < len(pred_lines) and pred_lines[idx - 1].strip() == r['final_sql'].strip())
    oracle = qdic = maj = selected = 0
    qdic_present = 0
    maj_tie_fb = maj_noexec_fb = 0
    for idx, r in sorted(by_idx.items()):
        i = idx - 1
        cands = r.get('cands', [])
        if eval_sql(i, r['final_sql']):
            selected += 1
        cand_ok = []
        exec_groups = collections.Counter()
        for lab, sql in cands:
            ok_p, pres = run_query(db_path_for(my_test[i]), sql.strip().rstrip(';') + ';')
            ok_g, gres = gold_result(i)
            correct = ok_g and ok_p and gres == pres
            cand_ok.append((lab, correct))
            if ok_p:
                exec_groups[str(pres)] += 1
        if any(c for _, c in cand_ok):
            oracle += 1
        qd = [(lab, c) for lab, c in cand_ok if lab == 'QD-InterCol']
        if qd:
            qdic_present += 1
            if qd[0][1]:
                qdic += 1
        if exec_groups:
            best = max(exec_groups.values())
            winners = [k for k, v in exec_groups.items() if v == best]
            if len(winners) == 1:
                ok_g, gres = gold_result(i)
                if ok_g and winners[0] == str(gres):
                    maj += 1
            else:
                maj_tie_fb += 1
                if eval_sql(i, r['final_sql']):
                    maj += 1
        else:
            maj_noexec_fb += 1
            if eval_sql(i, r['final_sql']):
                maj += 1
    results[bkey] = dict(n=n, match_final=match_final, oracle=oracle, qdic=qdic,
                         qdic_present=qdic_present, maj=maj, selected=selected,
                         maj_tie_fb=maj_tie_fb, maj_noexec_fb=maj_noexec_fb)
    print(f"{bkey}: N(unique)={n}, final_sql==predfile:{match_final}/{n} | "
          f"selected={selected/n*100:.2f}% oracle={oracle/n*100:.2f}% "
          f"alwaysQD-IC={qdic/n*100:.2f}% majvote={maj/n*100:.2f}% "
          f"(tie-fallbacks={maj_tie_fb}, noexec-fallbacks={maj_noexec_fb})")

json.dump(results, open(PROJ / 'selection_policies.json', 'w'), indent=1)
print("saved selection_policies.json")
