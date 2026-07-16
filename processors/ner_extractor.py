"""
استخراج الكيانات الطبية المسماة (Medical NER).
يجمع بين المطابقة القائمة على الأنماط والمطابقة مع المسرد.
"""

import re
import json
import os
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ExtractedEntity:
    """كيان طبي مُستخرج"""
    text: str
    label: str          # DISEASE, SYMPTOM, DRUG, PROCEDURE, ANATOMY, BODY_FUNCTION
    confidence: float
    start: int
    end: int
    context: str = ""
    source: str = "pattern"  # pattern | glossary | ner


class MedicalNERExtractor:
    """
    مستخرج الكيانات الطبية — يدمج بين:
    1. أنماط Regex للأمراض والأعراض والأدوية (عربي + إنجليزي)
    2. مطابقة مباشرة مع المسرد الرئيسي (21,120+ مصطلح)
    """

    def __init__(self, glossary_path: str = "data/merged/glossary_master.json"):
        self._glossary_terms: Dict[str, dict] = {}
        self._glossary_loaded = False
        self._glossary_path = glossary_path
        self._compiled = self._compile_patterns()

    # ─── أنماط الأمراض والأعراض والأدوية ─────────────────────

    _PATTERNS = {
        "DISEASE": [
            # English
            r"\b(diabetes\s?(mellitus|type\s?\d|insipidus)?)\b",
            r"\b(hypertension|high\s+blood\s+pressure)\b",
            r"\b(heart\s+disease|coronary\s+artery\s+disease|cardiovascular)\b",
            r"\b(chronic\s+(kidney|obstructive\s+pulmonary)\s+disease)\b",
            r"\b(hepatitis\s?[ABC]?)\b",
            r"\b(tuberculosis|pneumonia|asthma|bronchitis)\b",
            r"\b(anemia|leukemia|lymphoma|sarcoma|melanoma)\b",
            r"\b(osteoporosis|arthritis|arthritis|rheumatoid)\b",
            r"\b(thyroiditis|hypothyroidism|hyperthyroidism)\b",
            r"\b(alzheimer|parkinson|epilepsy|sclerosis)\b",
            # Arabic
            r"\b(السكري|مرض السكري|داء السكري)\b",
            r"\b(ارتفاع\s?(ضغط\s?الدم|الضغط))\b",
            r"\b(السرطان|الأورام|الورم)\b",
            r"\b(الربو|الالتهاب\s?الرئوي)\b",
            r"\b(التهاب\s?الكبد|التهاب\s?الكلى)\b",
            r"\b(فقر\s?الدم|الأنيميا)\b",
            r"\b(هشاشة\s?العظام|التهاب\s?المفاصل)\b",
            r"\b(القلب|الكبد|الرئة|الكلية)\b",
        ],
        "SYMPTOM": [
            r"\b(fever|high\s+temperature|hyperthermia)\b",
            r"\b(cough|dry\s+cough|chronic\s+cough)\b",
            r"\b(headache|migraine|head\s+pain)\b",
            r"\b(nausea|vomiting|diarrhea|constipation)\b",
            r"\b(fatigue|weakness|malaise|lethargy)\b",
            r"\b(chest\s+pain|abdominal\s+pain|back\s+pain)\b",
            r"\b(dyspnea|shortness\s+of\s+breath|tachypnea)\b",
            r"\b(حمى|سعال|صداع|غثيان|قيء|إسهال)\b",
            r"\b(إرهاق|ضعف|ألم|تعب|دوار)\b",
            r"\b(ضيق\s?التنفس|ألم\s?الصدر|ألم\s?البطن)\b",
        ],
        "DRUG": [
            r"\b(aspirin|ibuprofen|acetaminophen|paracetamol)\b",
            r"\b(amoxicillin|azithromycin|ciprofloxacin|metronidazole)\b",
            r"\b(metformin|insulin|glimepiride|sitagliptin)\b",
            r"\b(amlodipine|losartan|atenolol|captopril)\b",
            r"\b(omeprazole|pantoprazole|ranitidine)\b",
            r"\b(أسبرين|إيبوبروفين|باراسيتامول|أموكسيسيلين)\b",
            r"\b(ميتفورمين|إنسولين|أملوديبين|لوسارتان)\b",
        ],
        "PROCEDURE": [
            r"\b(surgery|operation|biopsy|transplant|dialysis)\b",
            r"\b(chemotherapy|radiation\s+therapy|immunotherapy)\b",
            r"\b(CT\s+scan|MRI|X-?ray|ultrasound|endoscopy)\b",
            r"\b(جراحة|عملية|خزعة|زراعة?|غسيل\s?كلوى)\b",
            r"\b(علاج\s?كيماوي|أشعة|علاج\s?طبيعي)\b",
        ],
        "ANATOMY": [
            r"\b(heart|liver|kidney|brain|lung|stomach|intestine)\b",
            r"\b(pancreas|spleen|gallbladder|bladder|thyroid)\b",
            r"\b(femur|tibia|humerus|spine|vertebra)\b",
            r"\b(القلب|الكبد|الكلية|الدماغ|الرئة|المعدة)\b",
            r"\b(البنكرياس|الطحال|المرارة|المثانة|الغدة)\b",
            r"\b(العظم|العمود\s?الفقري|العضلات?|الأعصاب)\b",
        ],
        "BODY_FUNCTION": [
            r"\b(heart\s+rate|blood\s+pressure|respiratory\s+rate)\b",
            r"\b(renal\s+function|liver\s+function|thyroid\s+function)\b",
            r"\b(معدل\s?النبض|ضغط\s?الدم|معدل\s?التنفس)\b",
            r"\b(وظيفة\s?الكبد|وظيفة\s?الكلى)\b",
        ],
    }

    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """تجميع الأنماط مرة واحدة."""
        compiled = {}
        for label, patterns in self._PATTERNS.items():
            compiled[label] = [re.compile(p, re.IGNORECASE) for p in patterns]
        return compiled

    # ─── تحميل المسرد ──────────────────────────────────────────

    def _ensure_glossary(self):
        """تحميل المسرد بكسل (مرة واحدة فقط)."""
        if self._glossary_loaded:
            return
        self._glossary_loaded = True
        if not os.path.exists(self._glossary_path):
            return
        try:
            with open(self._glossary_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for hash_key, td in data.get("terms", {}).items():
                term = td.get("term", "").strip().lower()
                if len(term) < 2:
                    continue
                self._glossary_terms[term] = td
        except Exception as e:
            logger.error(f"فشل تحميل المسرد للـ NER: {e}")

    # ─── الاستخراج ──────────────────────────────────────────────

    def extract(self, text: str) -> List[ExtractedEntity]:
        """
        استخراج الكيانات الطبية من النص.
        يجمع بين المطابقة بالأنماط والمطابقة مع المسرد.
        """
        results: List[ExtractedEntity] = []
        seen_spans = set()  # لمنع التداخل

        # 1. مطابقة الأنماط
        for label, patterns in self._compiled.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    span = (match.start(), match.end())
                    if self._overlaps(span, seen_spans):
                        continue
                    seen_spans.add(span)

                    ctx_start = max(0, match.start() - 60)
                    ctx_end = min(len(text), match.end() + 60)
                    results.append(ExtractedEntity(
                        text=match.group(),
                        label=label,
                        confidence=0.85,
                        start=match.start(),
                        end=match.end(),
                        context=text[ctx_start:ctx_end],
                        source="pattern",
                    ))

        # 2. مطابقة المسرد (فقط الأطول أولاً لتجنب التداخل)
        self._ensure_glossary()
        sorted_terms = sorted(
            self._glossary_terms.keys(),
            key=len, reverse=True
        )
        text_lower = text.lower()
        for term in sorted_terms:
            if len(term) < 3:
                continue
            for m in re.finditer(re.escape(term), text_lower):
                span = (m.start(), m.end())
                if self._overlaps(span, seen_spans):
                    continue
                seen_spans.add(span)

                td = self._glossary_terms[term]
                ctx_start = max(0, m.start() - 60)
                ctx_end = min(len(text), m.end() + 60)
                results.append(ExtractedEntity(
                    text=text[m.start():m.end()],
                    label="MEDICAL_TERM",
                    confidence=td.get("confidence", 0.9),
                    start=m.start(),
                    end=m.end(),
                    context=text[ctx_start:ctx_end],
                    source=f"glossary:{td.get('source', '')}",
                ))

        # ترتيب حسب الموقع في النص
        results.sort(key=lambda e: e.start)
        return results

    def extract_with_translations(self, text: str) -> List[Dict]:
        """
        استخراج مع ترجمة تلقائية إن وُجدت في المسرد.
        يُرجع قواميس بدلاً من كائنات.
        """
        entities = self.extract(text)
        enriched = []

        for ent in entities:
            item = {
                "entity": ent.text,
                "label": ent.label,
                "confidence": ent.confidence,
                "context": ent.context,
                "source": ent.source,
            }

            # محاولة إيجاد ترجمة في المسرد
            self._ensure_glossary()
            term_lower = ent.text.strip().lower()
            td = self._glossary_terms.get(term_lower)
            if td:
                item["definition"] = td.get("definition", "")
                item["glossary_source"] = td.get("source", "")
                item["language"] = td.get("language", "")

            enriched.append(item)
        return enriched

    @staticmethod
    def _overlaps(span: tuple, existing: set) -> bool:
        """فحص تداخل الفترات."""
        s, e = span
        for (es, ee) in existing:
            if s < ee and e > es:
                return True
        return False


# ─── CLI ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("الاستخدام: python -m processors.ner_extractor \"النص الطبي\"")
        sys.exit(1)

    text = " ".join(sys.argv[1:])
    extractor = MedicalNERExtractor()
    entities = extractor.extract_with_translations(text)

    print(f"\nتم العثور على {len(entities)} كيان طبي:\n")
    for ent in entities:
        print(f"  [{ent['label']}] {ent['entity']}  "
              f"(ثقة: {ent['confidence']:.2f} | المصدر: {ent['source']})")
        if "definition" in ent:
            print(f"    الترجمة: {ent['definition']}")
        if ent.get("context"):
            print(f"    السياق: ...{ent['context']}...")
        print()