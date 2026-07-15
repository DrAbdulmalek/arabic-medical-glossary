# State of Truth — المسارد الطبية العربية

> **الإصدار:** 2.0  
> **آخر تحديث:** 2026-07-15  
> **الغرض:** نقطة مرجعية وحيدة (single source of truth) لفهم حالة المستودع الحالية، بدون الحاجة لقراءة كل الملفات.

---

## هيكل المستودع

| المسار | الوصف | الملفات الرئيسية |
|--------|-------|-----------------|
| `glossaries/` | مسارد الجمل والعبارات المتقابلة (phrase-level) | `*.csv` (~80 ملف) |
| `terms/` | قواعد المصطلحات المفردية (term-level) | `*.csv` (~30 ملف) |
| `cleaned/` | البيانات المنظفة والموحدة | `cleaned_glossary.csv`, `comprehensive_glossary.csv` |
| `data/` | البيانات المجمعة للنشر | `all_pairs.csv`, `all_pairs.jsonl`, `terms.csv`, `sentences.csv` |
| `ocr_output/` | مخرجات OCR من النشرات الدوائية | `*.txt` (~90 ملف) |
| `src/` | نظام الإدارة المتقدم (Calibre-inspired) — 14 وحدة برمجية | `db_manager.py`, `data_cleaner.py`, `source_merger.py`, `exporter.py`, `quality_checker.py`, `statistics.py`, `backup_system.py`, `auto_ingestion.py`, `plugin_manager.py`, `provenance.py`, `format_converter.py`, `cli.py` |
| `tests/` | 47 اختبار | `test_db_manager.py`, `test_data_cleaner.py`, `test_source_merger.py`, `test_exporter.py`, `test_quality_checker.py`, `test_statistics.py`, `test_backup_system.py`, `test_auto_ingestion.py`, `test_plugin_manager.py`, `test_provenance.py`, `test_format_converter.py`, `test_cli.py` |
| `scripts/` | أدوات البناء والنشر | `build_database.py`, `bilingual_collector.py`, `build_local.py`, `upload_to_hf.py` |

---

## المحتوى الحالي

- **المصادر:** مسارد مستخلصة من نشرات Hama Pharma ومنتجاتها الدوائية (~80 منتج)
- **المستوى:** term-level + phrase-level
- **اللغات:** عربي ↔ إنجليزي
- **التصنيفات:** مصطلحات طبية، أسماء أدوية، تفاعلات، موانع استعمال، جرعات، آثار جانبية، محاذير، مؤشرات استعمال، التركيب، حركية الدواء

---

## آخر التغييرات الجوهرية

| # | الـ Commit | التاريخ | الوصف |
|---|-----------|---------|-------|
| 1 | `calibre-v2` | 2026-07-15 | إضافة نظام إدارة متقدم مستوحى من Calibre — 15 ميزة، 14 وحدة، 47 اختبار، مستودع API منفصل |

---

## ملاحظات للنماذج الذكية

1. هذا مستودع **مصطلحات طبية عربية-إنجليزية** مستخلصة من نشرات دوائية حقيقية
2. كل مصطلح/عبارة يجب أن يكون **ثنائي اللغة** — سطر عربي وآخر إنجليزي
3. لا تُضف مصطلحات من خارج المصادر الموجودة
4. المسارد في `glossaries/` هي عبارات وجمل متقابلة (phrase-level)
5. المصطلحات في `terms/` هي كلمات مفردة (term-level)
6. البيانات المُنظفة النهائية في `cleaned/` و `data/`
7. النظام المتقدم متاح في `src/` — اقرأ `CALIBRE_FEATURES.md` للتفاصيل الكاملة
8. REST API منفصل في `../glossary-api/`

---

## المستودعات المرتبطة

| المستودع | الرابط | الوصف |
|----------|--------|-------|
| `arabic-medical-glossary` | `./` (الحالي) | المسارد الطبية + نظام الإدارة المتقدم (Calibre-inspired) |
| `glossary-api` | `../glossary-api/` | REST API منفصل للاستعلام عن المصطلحات |