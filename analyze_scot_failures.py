"""Analyze divergence and pattern errors between SCoT and Standard predictions.

Adds flexibility via --run_dir argument so we can reuse for dev_500 and dev_600.
Generates a summary CSV of pattern counts:
  <run_dir>/scot_vs_standard_divergence_patterns.csv
Optionally limits printed examples.
"""

import csv
import argparse
import glob
import os

def find_file(run_dir: str, prefix: str) -> str:
    pattern = os.path.join(run_dir, f"exec_eval_report__{prefix}*.csv")
    matches = glob.glob(pattern)
    if not matches:
        raise FileNotFoundError(f"No file matching {pattern}")
    # Prefer the shortest name (without backups)
    return sorted(matches, key=len)[0]

def load_reports(run_dir: str):
    scot_file = find_file(run_dir, "predicted_scot")
    std_file = find_file(run_dir, "predicted_standard")
    with open(scot_file, newline='', encoding='utf-8') as f1, open(std_file, newline='', encoding='utf-8') as f2:
        scot_rows = list(csv.DictReader(f1))
        std_rows = list(csv.DictReader(f2))
    return scot_file, std_file, scot_rows, std_rows

def analyze(scot_rows, std_rows, limit):
    divergences = []
    for i in range(len(scot_rows)):
        if scot_rows[i].get('match') == 'False' and std_rows[i].get('match') == 'True':
            divergences.append(i)
    pattern_counts = {}
    examples = []
    for i, idx in enumerate(divergences[:limit]):
        s = scot_rows[idx]
        g = s.get('gold_sql', '')
        p = s.get('pred_sql', '')
        patterns = []
        if 'DISTINCT' in p and 'DISTINCT' not in g:
            patterns.append('Extra DISTINCT')
        if 'GROUP BY' in p and 'GROUP BY' not in g:
            patterns.append('Extra GROUP BY')
        if p.count('JOIN') > g.count('JOIN'):
            patterns.append('Extra JOINs')
        if 'ORDER BY' in g and 'ORDER BY' not in p:
            patterns.append('Missing ORDER BY')
        if 'ORDER BY' in p and 'ORDER BY' not in g:
            patterns.append('Extra ORDER BY')
        if 'HAVING' in p and 'HAVING' not in g:
            patterns.append('Extra HAVING')
        if 'NOT EXISTS' in g and 'NOT EXISTS' not in p:
            patterns.append('Missing NOT EXISTS')
        for pat in patterns:
            pattern_counts[pat] = pattern_counts.get(pat, 0) + 1
        examples.append((idx+1, s.get('question',''), patterns))
    return divergences, pattern_counts, examples

def write_pattern_csv(run_dir: str, pattern_counts: dict):
    out_path = os.path.join(run_dir, 'scot_vs_standard_divergence_patterns.csv')
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['pattern','count'])
        for k, v in sorted(pattern_counts.items(), key=lambda x: -x[1]):
            w.writerow([k, v])
    return out_path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run_dir', default='runs/dev_500', help='Directory containing exec_eval_report__*.csv files')
    ap.add_argument('--limit', type=int, default=15, help='Number of divergence examples to print')
    args = ap.parse_args()
    scot_file, std_file, scot_rows, std_rows = load_reports(args.run_dir)
    divergences, pattern_counts, examples = analyze(scot_rows, std_rows, args.limit)
    print(f"Run dir: {args.run_dir}")
    print(f"SCoT report: {scot_file}\nStandard report: {std_file}")
    print(f"Total cases where SCoT failed but Standard succeeded: {len(divergences)}")
    print(f"\nFirst {len(examples)} divergence examples:\n")
    for case_num, question, pats in examples:
        print(f"=== CASE (row {case_num}) ===")
        print(f"Q: {question}")
        if pats:
            print(f"Patterns: {', '.join(pats)}")
        print()
    out_csv = write_pattern_csv(args.run_dir, pattern_counts)
    print(f"Pattern counts written to: {out_csv}")

if __name__ == '__main__':
    main()
