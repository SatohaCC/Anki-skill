"""
Anki Card Duplication & Similarity Audit Script
Analyzes Anki export/import files (.txt) in an output folder for:
1. Format parity & card count alignment between 一問一答 and 4択
2. Duplicate or near-duplicate questions (text similarity via n-gram & SequenceMatcher)
3. Concept clustering (cards testing the exact same term/answer repeatedly)
4. Conflicting questions (nearly identical question stems but different answers)
5. Cross-chapter duplicate concepts
"""

import os
import sys
import csv
import re
import html
import json
import argparse
from collections import defaultdict
from difflib import SequenceMatcher

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def clean_html(text):
    text = re.sub(r'<script.*?</script>', '', text, flags=re.DOTALL)
    text = re.sub(r'<ol\s+class=["\']anki-shuffle["\'].*?</ol>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_primary_answer(text):
    text = re.sub(r'<ul\s+class=["\']abbreviation-expansions["\'].*?</ul>', '', text, flags=re.DOTALL)
    text = re.sub(r'<div><strong>略語のフルスペル：</strong></div>', '', text)
    m = re.search(r'<(div|li)>(.*?)</\1>', text, flags=re.DOTALL)
    first_part = m.group(2) if m else text
    first_part = re.sub(r'<[^>]+>', ' ', first_part)
    first_part = html.unescape(first_part)
    first_part = re.sub(r'^正解：', '', first_part.strip())
    return first_part.strip()

def clean_full_answer(text):
    text = re.sub(r'<ul\s+class=["\']abbreviation-expansions["\'].*?</ul>', '', text, flags=re.DOTALL)
    text = re.sub(r'<div><strong>略語のフルスペル：</strong></div>', '', text)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html.unescape(text)
    text = re.sub(r'^正解：', '', text.strip())
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_choices(text):
    ol = re.search(r'<ol\s+class=["\']anki-shuffle["\']>(.*?)</ol>', text, flags=re.DOTALL)
    if not ol:
        return []
    lis = re.findall(r'<li>(.*?)</li>', ol.group(1), flags=re.DOTALL)
    return [re.sub(r'<[^>]+>', '', html.unescape(li)).strip() for li in lis]

def parse_anki_file(path):
    headers = []
    cards = []
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        row_idx = 0
        for r in reader:
            if not r:
                continue
            if r[0].startswith('#'):
                headers.append(r[0])
                continue
            row_idx += 1
            if len(r) < 3:
                continue
            guid = r[0]
            q_raw = r[1]
            a_raw = r[2]
            q_stem = clean_html(q_raw)
            # Remove trailing choice indicators from stem
            q_clean_stem = re.sub(r'（[1１一]つ選択）.*', '', q_stem).strip()
            q_clean_stem = re.sub(r'(として)?正しい(もの|説明|記述|選択肢)を([1１一]つ)?選んでください[。]?$', '', q_clean_stem).strip()
            q_clean_stem = re.sub(r'について正しい(もの|説明|記述)を.*$', '', q_clean_stem).strip()
            a_primary = extract_primary_answer(a_raw)
            a_full = clean_full_answer(a_raw)
            choices = extract_choices(q_raw)
            cards.append({
                'index': row_idx,
                'guid': guid,
                'q_stem': q_stem,
                'q_clean_stem': q_clean_stem,
                'a_primary': a_primary,
                'a_full': a_full,
                'choices': choices,
                'q_raw': q_raw,
                'a_raw': a_raw
            })
    return headers, cards

def ngrams(text, n=2):
    return set(text[i:i+n] for i in range(len(text)-n+1))

def jaccard_similarity(a, b, n=2):
    ng_a = ngrams(a, n)
    ng_b = ngrams(b, n)
    if not ng_a or not ng_b:
        return 0.0
    return len(ng_a & ng_b) / len(ng_a | ng_b)

def seq_ratio(a, b):
    return SequenceMatcher(None, a, b).ratio()

def audit_directory(target_dir):
    txt_files = [f for f in os.listdir(target_dir) if f.endswith('.txt')]
    if not txt_files:
        print(f"No .txt files found in {target_dir}")
        return {}

    # Group by chapter/range
    # Filename convention: <slug>_<range>_<type>_<timestamp>_Anki.txt
    range_groups = defaultdict(dict)
    for fname in txt_files:
        path = os.path.join(target_dir, fname)
        m = re.match(r'^(.*?)_(.*?)_(一問一答|4択)_(.*?)_Anki\.txt$', fname)
        if m:
            slug, crange, ftype, ts = m.groups()
            key = f"{slug}_{crange}"
            # Keep latest if multiple timestamps
            if ftype not in range_groups[key] or ts > range_groups[key][ftype]['ts']:
                range_groups[key][ftype] = {'file': fname, 'path': path, 'ts': ts}
        else:
            range_groups['other'][fname] = {'file': fname, 'path': path, 'ts': ''}

    audit_results = {
        'ranges': {},
        'cross_range_similarities': []
    }

    all_decks = {}

    for rkey, types in sorted(range_groups.items()):
        range_report = {'files': {}, 'parity': {}, 'concept_clusters': [], 'similar_pairs': []}
        for ftype, finfo in types.items():
            headers, cards = parse_anki_file(finfo['path'])
            range_report['files'][ftype] = {
                'filename': finfo['file'],
                'card_count': len(cards),
                'headers': headers
            }
            all_decks[f"{rkey}_{ftype}"] = cards

        # Parity check between 一問一答 and 4択
        if '一問一答' in types and '4択' in types:
            qa_cards = all_decks[f"{rkey}_一問一答"]
            fc_cards = all_decks[f"{rkey}_4択"]
            qa_count = len(qa_cards)
            fc_count = len(fc_cards)
            range_report['parity']['count_match'] = (qa_count == fc_count)
            range_report['parity']['qa_count'] = qa_count
            range_report['parity']['fc_count'] = fc_count

            # Check 1-to-1 question stem alignment
            stem_mismatches = []
            max_len = min(qa_count, fc_count)
            for i in range(max_len):
                q1 = qa_cards[i]['q_clean_stem']
                q2 = fc_cards[i]['q_clean_stem']
                sim = seq_ratio(q1, q2)
                if sim < 0.65:
                    stem_mismatches.append({
                        'index': i + 1,
                        'qa_stem': q1,
                        'fc_stem': q2,
                        'similarity': round(sim, 3)
                    })
            range_report['parity']['mismatches'] = stem_mismatches

        # Concept clustering (cards with same primary answer keyword)
        primary_deck_key = f"{rkey}_一問一答" if f"{rkey}_一問一答" in all_decks else list(types.keys())[0]
        deck = all_decks[primary_deck_key]
        ans_groups = defaultdict(list)
        for c in deck:
            p_ans = c['a_primary'].split('。')[0].split(' ')[0]
            if len(p_ans) >= 2:
                ans_groups[p_ans].append(c)

        for p_ans, group in ans_groups.items():
            if len(group) > 1:
                range_report['concept_clusters'].append({
                    'keyword': p_ans,
                    'count': len(group),
                    'cards': [{'index': c['index'], 'guid': c['guid'], 'q': c['q_stem'], 'a': c['a_full']} for c in group]
                })

        # Intra-deck text similarity pairs
        n = len(deck)
        for i in range(n):
            for j in range(i + 1, n):
                c1 = deck[i]
                c2 = deck[j]
                q_seq = seq_ratio(c1['q_clean_stem'], c2['q_clean_stem'])
                q_jac = jaccard_similarity(c1['q_clean_stem'], c2['q_clean_stem'])
                a_seq = seq_ratio(c1['a_full'], c2['a_full'])
                a_jac = jaccard_similarity(c1['a_full'], c2['a_full'])

                # Flag if question stems are very similar, or both questions & answers are moderately similar
                if q_seq >= 0.65 or q_jac >= 0.5 or (q_seq >= 0.55 and a_seq >= 0.5):
                    is_conflicting = (q_seq >= 0.6 and a_seq < 0.3)
                    range_report['similar_pairs'].append({
                        'card1': c1['index'],
                        'card2': c2['index'],
                        'guid1': c1['guid'],
                        'guid2': c2['guid'],
                        'q1': c1['q_stem'],
                        'q2': c2['q_stem'],
                        'a1': c1['a_full'],
                        'a2': c2['a_full'],
                        'q_similarity': round(q_seq, 3),
                        'a_similarity': round(a_seq, 3),
                        'is_conflicting': is_conflicting
                    })

        range_report['similar_pairs'].sort(key=lambda x: x['q_similarity'], reverse=True)
        audit_results['ranges'][rkey] = range_report

    # Cross-range similarities
    range_keys = list(range_groups.keys())
    for r_idx1 in range(len(range_keys)):
        for r_idx2 in range(r_idx1 + 1, len(range_keys)):
            k1 = range_keys[r_idx1]
            k2 = range_keys[r_idx2]
            d1_key = f"{k1}_一問一答" if f"{k1}_一問一答" in all_decks else None
            d2_key = f"{k2}_一問一答" if f"{k2}_一問一答" in all_decks else None
            if not d1_key or not d2_key:
                continue
            d1 = all_decks[d1_key]
            d2 = all_decks[d2_key]
            for c1 in d1:
                for c2 in d2:
                    q_seq = seq_ratio(c1['q_clean_stem'], c2['q_clean_stem'])
                    a_seq = seq_ratio(c1['a_full'], c2['a_full'])
                    if q_seq >= 0.6 or (q_seq >= 0.5 and a_seq >= 0.55):
                        audit_results['cross_range_similarities'].append({
                            'range1': k1,
                            'card1': c1['index'],
                            'q1': c1['q_stem'],
                            'a1': c1['a_full'],
                            'range2': k2,
                            'card2': c2['index'],
                            'q2': c2['q_stem'],
                            'a2': c2['a_full'],
                            'q_similarity': round(q_seq, 3),
                            'a_similarity': round(a_seq, 3)
                        })

    audit_results['cross_range_similarities'].sort(key=lambda x: x['q_similarity'], reverse=True)
    return audit_results

def print_audit_summary(results):
    print("=" * 70)
    print("           ANKI CARD DUPLICATION & SIMILARITY AUDIT REPORT           ")
    print("=" * 70)
    for rkey, rdata in results.get('ranges', {}).items():
        print(f"\n[Chapter Range: {rkey}]")
        for ftype, finfo in rdata.get('files', {}).items():
            print(f"  - {ftype}: {finfo['filename']} ({finfo['card_count']} cards)")

        parity = rdata.get('parity', {})
        if parity:
            if parity.get('count_match'):
                print(f"  * Parity Status: OK (Both formats have {parity['qa_count']} cards)")
            else:
                print(f"  * Parity Status: MISMATCH! 一問一答={parity.get('qa_count')} vs 4択={parity.get('fc_count')}")

            mismatches = parity.get('mismatches', [])
            if mismatches:
                print(f"  * Question Stem Desynchronization ({len(mismatches)} mismatches detected):")
                for m in mismatches[:3]:
                    print(f"      Row {m['index']}: QA='{m['qa_stem'][:40]}' vs FC='{m['fc_stem'][:40]}' (sim={m['similarity']})")

        clusters = rdata.get('concept_clusters', [])
        if clusters:
            print(f"  * Concept Clusters ({len(clusters)} repeated answer terms):")
            for cl in clusters:
                print(f"      Term '{cl['keyword']}': {cl['count']} cards")
                for c in cl['cards']:
                    print(f"        #{c['index']:02d}: Q: {c['q'][:60]} | A: {c['a'][:40]}")

        sim_pairs = rdata.get('similar_pairs', [])
        conflicting = [p for p in sim_pairs if p.get('is_conflicting')]
        if conflicting:
            print(f"  * Conflicting/Ambiguous Questions ({len(conflicting)} pairs - similar stem, different answers):")
            for p in conflicting[:3]:
                print(f"      Card #{p['card1']:02d} vs #{p['card2']:02d} (stem sim: {p['q_similarity']}):")
                print(f"        Q1: {p['q1'][:60]} -> A1: {p['a1'][:40]}")
                print(f"        Q2: {p['q2'][:60]} -> A2: {p['a2'][:40]}")

    cross = results.get('cross_range_similarities', [])
    if cross:
        print(f"\n[Cross-Chapter Overlaps ({len(cross)} pairs)]")
        for cp in cross[:5]:
            print(f"  * {cp['range1']} #{cp['card1']} vs {cp['range2']} #{cp['card2']} (stem sim: {cp['q_similarity']}):")
            print(f"      Q1: {cp['q1'][:55]}")
            print(f"      Q2: {cp['q2'][:55]}")
    else:
        print("\n[Cross-Chapter Overlaps: None detected]")
    print("=" * 70)

def main():
    parser = argparse.ArgumentParser(description="Audit Anki export files for duplicate and similar questions.")
    parser.add_argument("target_dir", help="Path to the directory containing Anki txt files (e.g. target-folder/<slug>/output)")
    parser.add_argument("--json", dest="json_path", help="Path to save JSON audit report", default=None)
    args = parser.parse_args()

    if not os.path.exists(args.target_dir):
        print(f"Error: Directory not found: {args.target_dir}")
        sys.exit(1)

    results = audit_directory(args.target_dir)
    print_audit_summary(results)

    if args.json_path:
        with open(args.json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"Saved JSON report to {args.json_path}")

if __name__ == '__main__':
    main()
