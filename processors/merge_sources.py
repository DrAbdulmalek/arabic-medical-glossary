"""
Merge all source glossaries into a master file with deduplication.
"""

import json
import os
from datetime import datetime
from collections import defaultdict


def merge_all_sources():
    """دمج جميع المصادر في ملف رئيسي"""
    sources_dir = os.path.join("data", "sources")
    merged_dir = os.path.join("data", "merged")
    os.makedirs(merged_dir, exist_ok=True)

    master = {
        "metadata": {
            "created": datetime.now().isoformat(),
            "sources": []
        },
        "terms": {},
        "by_language": {"ar": [], "en": []},
        "by_source": defaultdict(list)
    }

    if not os.path.exists(sources_dir):
        print("⚠️ لا توجد مصادر بعد")
        return master

    for filename in os.listdir(sources_dir):
        if not filename.endswith('.json'):
            continue

        source_name = filename.replace('.json', '')
        filepath = os.path.join(sources_dir, filename)

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        source_terms = 0
        for term_hash, term_data in data.get("terms", {}).items():
            if term_hash not in master["terms"]:
                master["terms"][term_hash] = term_data
                source_terms += 1

            lang = term_data.get("language", "unknown")
            if lang in master["by_language"]:
                master["by_language"][lang].append(term_hash)

            master["by_source"][source_name].append(term_hash)

        master["metadata"]["sources"].append({
            "name": source_name,
            "terms_count": source_terms,
            "file": filename
        })

    master["metadata"]["total_terms"] = len(master["terms"])

    merged_file = os.path.join(merged_dir, "glossary_master.json")
    with open(merged_file, 'w', encoding='utf-8') as f:
        json.dump(master, f, ensure_ascii=False, indent=2)

    print(f"✅ تم دمج {len(master['terms'])} مصطلح من {len(master['metadata']['sources'])} مصدر")
    return master


if __name__ == "__main__":
    merge_all_sources()
