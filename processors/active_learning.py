"""
حلقة التعلم الفعّال (Active Learning Loop).
تحدد المصطلحات منخفضة الثقة والمكررات وتعرضها للمراجعة البشرية.
"""

import json
import os
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass, asdict, field

logger = __import__("logging").getLogger(__name__)


@dataclass
class ReviewItem:
    """عنصر بانتظار المراجعة."""
    term_hash: str
    term: str
    definition: str
    source: str
    confidence: float
    reason: str             # low_confidence | duplicate | ambiguous
    suggested_correction: Optional[str] = None
    reviewed: bool = False
    reviewed_at: Optional[str] = None
    reviewer: Optional[str] = None


class ActiveLearningManager:
    """
    إدارة دورة المراجعة البشرية:
    1. تحديد المصطلحات المنخفضة الثقة
    2. تحديد المكررات المحتملة
    3. عرض قائمة الانتظار
    4. تسجيل التصحيحات
    5. تطبيقها على المسرد
    """

    def __init__(self, review_file: str = "data/review/pending.json"):
        self.review_file = review_file
        os.makedirs(os.path.dirname(review_file), exist_ok=True)
        self.pending_items: List[ReviewItem] = self._load()

    # ─── التخزين ───────────────────────────────────────────────

    def _load(self) -> List[ReviewItem]:
        if not os.path.exists(self.review_file):
            return []
        try:
            with open(self.review_file, 'r', encoding='utf-8') as f:
                return [ReviewItem(**item) for item in json.load(f)]
        except Exception:
            return []

    def _save(self):
        with open(self.review_file, 'w', encoding='utf-8') as f:
            json.dump(
                [asdict(i) for i in self.pending_items],
                f, ensure_ascii=False, indent=2,
            )

    # ─── التحديد ───────────────────────────────────────────────

    def identify_low_confidence(
        self,
        glossary_path: str = "data/merged/glossary_master.json",
        threshold: float = 0.7,
    ) -> int:
        """تحديد المصطلحات ذات الثقة المنخفضة."""
        if not os.path.exists(glossary_path):
            return 0

        with open(glossary_path, 'r', encoding='utf-8') as f:
            terms = json.load(f).get("terms", {})

        existing_hashes = {i.term_hash for i in self.pending_items}
        new = 0

        for h, td in terms.items():
            if h in existing_hashes:
                continue
            if td.get("confidence", 1.0) < threshold:
                self.pending_items.append(ReviewItem(
                    term_hash=h,
                    term=td.get("term", ""),
                    definition=td.get("definition", ""),
                    source=td.get("source", ""),
                    confidence=td.get("confidence", 0),
                    reason="low_confidence",
                ))
                new += 1

        self._save()
        return new

    def identify_duplicates(
        self,
        glossary_path: str = "data/merged/glossary_master.json",
    ) -> int:
        """تحديد المكررات المحتملة (نفس المصطلح، مصادر مختلفة)."""
        if not os.path.exists(glossary_path):
            return 0

        with open(glossary_path, 'r', encoding='utf-8') as f:
            terms = json.load(f).get("terms", {})

        # تجميع حسب المصطلح (normalized)
        groups: Dict[str, list] = {}
        for h, td in terms.items():
            key = td.get("term", "").lower().strip()
            groups.setdefault(key, []).append((h, td))

        existing_hashes = {i.term_hash for i in self.pending_items}
        new = 0

        for term, group in groups.items():
            if len(group) <= 1:
                continue
            # الأقدم (أعلى ثقة) يبقى، الباقي يُراجَع
            group.sort(key=lambda x: x[1].get("confidence", 0), reverse=True)
            for h, td in group[1:]:
                if h in existing_hashes:
                    continue
                self.pending_items.append(ReviewItem(
                    term_hash=h,
                    term=td.get("term", ""),
                    definition=td.get("definition", ""),
                    source=td.get("source", ""),
                    confidence=td.get("confidence", 0),
                    reason="duplicate",
                ))
                new += 1

        self._save()
        return new

    def identify_ambiguous(
        self,
        glossary_path: str = "data/merged/glossary_master.json",
        min_sources: int = 2,
    ) -> int:
        """تحديد المصطلحات المبهمة (تظهر في مصادر متعددة بتعريفات مختلفة)."""
        if not os.path.exists(glossary_path):
            return 0

        with open(glossary_path, 'r', encoding='utf-8') as f:
            terms = json.load(f).get("terms", {})

        groups: Dict[str, list] = {}
        for h, td in terms.items():
            key = td.get("term", "").lower().strip()
            groups.setdefault(key, []).append((h, td))

        existing_hashes = {i.term_hash for i in self.pending_items}
        new = 0

        for term, group in groups.items():
            if len(group) < min_sources:
                continue
            # فحص التعريفات المختلفة
            definitions = {td.get("definition", "") for _, td in group}
            if len(definitions) <= 1:
                continue
            for h, td in group:
                if h in existing_hashes:
                    continue
                self.pending_items.append(ReviewItem(
                    term_hash=h,
                    term=td.get("term", ""),
                    definition=td.get("definition", ""),
                    source=td.get("source", ""),
                    confidence=td.get("confidence", 0),
                    reason="ambiguous",
                ))
                new += 1

        self._save()
        return new

    # ─── المراجعة ──────────────────────────────────────────────

    def get_pending(
        self, limit: int = 50, reason: Optional[str] = None,
    ) -> List[ReviewItem]:
        """جلب العناصر بانتظار المراجعة (الأقل ثقة أولاً)."""
        items = [i for i in self.pending_items if not i.reviewed]
        if reason:
            items = [i for i in items if i.reason == reason]
        items.sort(key=lambda i: i.confidence)
        return items[:limit]

    def review(
        self,
        term_hash: str,
        action: str,       # approve | correct | remove
        correction: Optional[str] = None,
        reviewer: Optional[str] = None,
    ):
        """تسجيل قرار المراجعة."""
        for item in self.pending_items:
            if item.term_hash == term_hash:
                item.reviewed = True
                item.reviewed_at = datetime.now().isoformat()
                item.reviewer = reviewer
                if action == "correct" and correction:
                    item.suggested_correction = correction
                elif action == "remove":
                    item.suggested_correction = "__REMOVE__"
                break
        self._save()

    def apply_corrections(
        self,
        glossary_path: str = "data/merged/glossary_master.json",
    ) -> int:
        """تطبيق التصحيحات المعتمدة على المسرد."""
        if not os.path.exists(glossary_path):
            return 0

        with open(glossary_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        terms = data.get("terms", {})
        applied = 0

        for item in self.pending_items:
            if not item.reviewed or item.suggested_correction is None:
                continue
            if item.term_hash not in terms:
                continue

            if item.suggested_correction == "__REMOVE__":
                del terms[item.term_hash]
            else:
                terms[item.term_hash]["definition"] = item.suggested_correction
            applied += 1

        data["terms"] = terms
        data["metadata"]["total_terms"] = len(terms)
        data["metadata"]["last_corrected"] = datetime.now().isoformat()

        with open(glossary_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # إزالة العناصر المُطبَّقة
        self.pending_items = [
            i for i in self.pending_items
            if not (i.reviewed and i.suggested_correction)
        ]
        self._save()
        return applied

    # ─── الإحصائيات ────────────────────────────────────────────

    def get_stats(self) -> Dict:
        total = len(self.pending_items)
        reviewed = sum(1 for i in self.pending_items if i.reviewed)
        pending = total - reviewed
        by_reason: Dict[str, dict] = {}

        for item in self.pending_items:
            r = item.reason
            if r not in by_reason:
                by_reason[r] = {"total": 0, "reviewed": 0}
            by_reason[r]["total"] += 1
            if item.reviewed:
                by_reason[r]["reviewed"] += 1

        return {
            "total": total,
            "reviewed": reviewed,
            "pending": pending,
            "by_reason": by_reason,
        }


# ─── CLI ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    mgr = ActiveLearningManager()
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""

    if cmd == "identify":
        g = sys.argv[2] if len(sys.argv) > 2 else "data/merged/glossary_master.json"
        lc = mgr.identify_low_confidence(g)
        dup = mgr.identify_duplicates(g)
        amb = mgr.identify_ambiguous(g)
        print(f"✅ منخفضة الثقة: {lc} | مكررات: {dup} | مبهمة: {amb}")

    elif cmd == "list":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        items = mgr.get_pending(n)
        print(f"\n📋 عناصر بانتظار المراجعة ({len(items)}):\n")
        for i in items:
            print(f"  [{i.reason.upper()}] {i.term}  (ثقة: {i.confidence:.2f})")
            print(f"    التعريف: {i.definition[:80]}...")
            print()

    elif cmd == "stats":
        s = mgr.get_stats()
        print(f"\n📊 المراجعة: {s['reviewed']}/{s['total']} مُراجَع، {s['pending']} بانتظار")
        for reason, d in s["by_reason"].items():
            print(f"    {reason}: {d['reviewed']}/{d['total']}")

    elif cmd == "apply":
        n = mgr.apply_corrections()
        print(f"✅ تم تطبيق {n} تصحيح")

    else:
        print("الاستخدام:")
        print("  python -m processors.active_learning identify [مسار_المسرد]")
        print("  python -m processors.active_learning list [عدد]")
        print("  python -m processors.active_learning stats")
        print("  python -m processors.active_learning apply")