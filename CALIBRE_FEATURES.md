# نظام إدارة المسارد الطبية المتقدم — مستوحى من Calibre

> نظام شامل لإدارة المصطلحات الطبية العربية-الإنجليزية، مبني بأسلوب Calibre لإدارة الكتب الإلكترونية.
> يوفر 15 ميزة رئيسية تغطي قاعدة البيانات، التنظيف، الدمج، التصدير، الفحص، والإحصاءات.

---

## جدول الميزات الرئيسية

| # | الميزة | الملف المصدر | الوصف |
|---|--------|-------------|-------|
| 1 | قاعدة بيانات SQLite + FTS5 | `src/db_manager.py` | تخزين مهيكل مع بحث نصي كامل عربي-إنجليزي |
| 2 | تنظيف البيانات | `src/data_cleaner.py` | تطبيع النصوص العربية والإنجليزية وإزالة الضوضاء |
| 3 | دمج المصادر | `src/source_merger.py` | 5 استراتيجيات لدمج المسارد المتعددة |
| 4 | تصدير متعدد الصيغ | `src/exporter.py` | دعم 9 صيغ تصدير مختلفة |
| 5 | فحص الجودة | `src/quality_checker.py` | 11 فحصاً تلقائياً لضمان صحة البيانات |
| 6 | الإحصائيات والتقارير | `src/statistics.py` | تقارير مفصلة عن حالة قاعدة البيانات |
| 7 | النسخ الاحتياطي | `src/backup_system.py` | إنشاء واستعادة وتدوير النسخ الاحتياطية |
| 8 | الاستيعاب التلقائي | `src/auto_ingestion.py` | مراقبة المجلدات وإضافة المسارد تلقائياً |
| 9 | نظام الإضافات | `src/plugin_manager.py` | بنية قابلة للتوسيع عبر إضافات خارجية |
| 10 | تتبع الأصل (Provenance) | `src/provenance.py` | تسجيل تاريخ كل مصطلح وتغييراته |
| 11 | تحويل الصيغ | `src/format_converter.py` | تحويل بين صيغ الملفات المختلفة |
| 12 | واجهة CLI | `src/cli.py` | 8 أوامر سطرية لإدارة النظام كاملاً |
| 13 | بناء قاعدة البيانات | `scripts/build_database.py` | سكريبت لإنشاء قاعدة البيانات من المصادر |
| 14 | الاختبارات | `tests/` | 47 اختباراً يشمل الوحدات والتكامل |
| 15 | التوثيق المرتبط | `glossary-api/` | REST API منفصل للاستعلام عن المصطلحات |

---

## هيكل المشروع

```
arabic-medical-glossary/
├── src/                          ← النظام المتقدم (14 وحدة)
│   ├── __init__.py
│   ├── db_manager.py             ← قاعدة البيانات + FTS5
│   ├── data_cleaner.py           ← تنظيف البيانات
│   ├── source_merger.py          ← دمج المصادر
│   ├── exporter.py               ← التصدير متعدد الصيغ
│   ├── quality_checker.py        ← فحص الجودة
│   ├── statistics.py             ← الإحصائيات
│   ├── backup_system.py          ← النسخ الاحتياطي
│   ├── auto_ingestion.py         ← الاستيعاب التلقائي
│   ├── plugin_manager.py         ← نظام الإضافات
│   ├── provenance.py             ← تتبع الأصل
│   ├── format_converter.py       ← تحويل الصيغ
│   └── cli.py                    ← واجهة سطر الأوامر
├── tests/                        ← 47 اختباراً
│   ├── test_db_manager.py
│   ├── test_data_cleaner.py
│   ├── test_source_merger.py
│   ├── test_exporter.py
│   ├── test_quality_checker.py
│   ├── test_statistics.py
│   ├── test_backup_system.py
│   ├── test_auto_ingestion.py
│   ├── test_plugin_manager.py
│   ├── test_provenance.py
│   ├── test_format_converter.py
│   └── test_cli.py
├── scripts/
│   ├── build_database.py         ← بناء قاعدة البيانات
│   ├── bilingual_collector.py
│   ├── build_local.py
│   └── upload_to_hf.py
├── glossaries/                   ← المسارد الخام
├── terms/                        ← قواعد المصطلحات
├── cleaned/                      ← البيانات المنظفة
├── data/                         ← البيانات المجمعة
└── CALIBRE_FEATURES.md           ← هذا الملف
```

---

## تفاصيل الميزات الرئيسية

### 1. قاعدة بيانات SQLite + FTS5 — `db_manager.py`

نظام تخزين مهيكل يستخدم SQLite مع محرك البحث النصي الكامل FTS5، يدعم البحث بالعربية والإنجليزية مع تجاهل التشكيل.

**Schema الأساسي:**

```sql
CREATE TABLE terms (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    english     TEXT NOT NULL,
    arabic      TEXT NOT NULL,
    category    TEXT,
    source      TEXT,
    confidence  REAL DEFAULT 1.0,
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now'))
);

CREATE VIRTUAL TABLE terms_fts USING fts5(
    english, arabic, category,
    content='terms', content_rowid='id'
);
```

**أمثلة البحث:**

```python
from src.db_manager import DatabaseManager

db = DatabaseManager("glossary.db")

# بحث نصي كامل بالعربية
results = db.search("ضغط الدم", language="arabic")

# بحث بالإنجليزية
results = db.search("hypertension", language="english")

# إضافة مصطلح جديد
db.add_term(
    english="hypertension",
    arabic="ارتفاع ضغط الدم",
    category="diagnosis",
    source="WHO-ICD10"
)
```

---

### 2. تنظيف البيانات — `data_cleaner.py`

وحدة متخصصة لتنظيف وتطبيع النصوص الطبية ثنائية اللغة، تتضمن معالجة خاصة للحروف العربية.

```python
from src.data_cleaner import DataCleaner

cleaner = DataCleaner()

# تنظيف النص الإنجليزي
cleaner.clean_english("  Hypertension  (high  blood pressure)  ")
# → "hypertension (high blood pressure)"

# تنظيف النص العربي مع إزالة التشكيل
cleaner.clean_arabic("ارتفاعُ ضغطِ الدمِ")
# → "ارتفاع ضغط الدم"

# تطبيع شامل
cleaner.normalize(text, language="arabic")
# → إزالة التشكيل، توحيد الألف/الياء، إزالة المسافات الزائدة
```

**العمليات المتضمنة:**
- `clean_english()`: تحويل لحالة صغيرة، إزالة المسافات الزائدة، تنظيف علامات الترقيم
- `clean_arabic()`: إزالة التشكيل (tashkeel)، توحيد الهمزات، توحيد الألف المقصورة
- `normalize()`: تطبيق سلسلة كاملة من عمليات التنظيف

---

### 3. دمج المصادر — `source_merger.py`

5 استراتيجيات متقدمة لدمج المسارد المتعددة مع التعامل مع التعارضات:

| الاستراتيجية | الوصف | الاستخدام |
|-------------|-------|-----------|
| `keep_first` | الاحتفاظ بالمصطلح من أول مصدر | مسارد مترتبة حسب الأهمية |
| `keep_best` | اختيار الأفضل حسب置信اء (confidence) | مصادر متفاوتة الجودة |
| `merge_all` | دمج جميع الترجمات لكل مصطلح | بناء مسرد شامل |
| `vote` | التصويت الأغلبية بين المصادر | عدة مصادر متكافئة |
| `custom` | استراتيجية مخصصة عبر callable | حالات خاصة |

```python
from src.source_merger import SourceMerger

merger = SourceMerger(db)
merger.add_source("terms/medical_terms_basic.csv")
merger.add_source("terms/hama_pharma_master.csv")
merger.add_source("glossaries/")

# دمج باستخدام استراتيجية التصويت
merger.merge(strategy="vote", conflict_resolution="majority")

# دمج مع استراتيجية مخصصة
def custom_strategy(entries):
    return max(entries, key=lambda e: len(e["arabic"]))

merger.merge(strategy="custom", resolver=custom_strategy)
```

---

### 4. التصدير متعدد الصيغ — `exporter.py`

تصدير قاعدة البيانات إلى 9 صيغ مختلفة:

| الصيغة | الامتداد | الوصف |
|--------|---------|-------|
| CSV | `.csv` | جدول بيانات مفصول بفواصل |
| TSV | `.tsv` | جدول بيانات مفصول بتابات |
| JSON | `.json` | بيانات مهيكلة |
| JSONL | `.jsonl` | سطور JSON (كل سطر كائن مستقل) |
| Excel | `.xlsx` | ملف إكسل متعدد الأوراق |
| SQLite | `.db` | قاعدة بيانات مستقلة |
| TMX | `.tmx` | صيغة ترجمة الذاكرة (XML) |
| Markdown | `.md` | جدول Markdown |
| HTML | `.html` | صفحة ويب منظمة |

```python
from src.exporter import GlossaryExporter

exporter = GlossaryExporter(db)

# تصدير إلى CSV
exporter.export("output/glossary.csv", format="csv")

# تصدير إلى Excel بأوراق متعددة
exporter.export("output/glossary.xlsx", format="xlsx", 
                sheets_by_category=True)

# تصدير إلى JSONL
exporter.export("output/glossary.jsonl", format="jsonl")

# تصدير شامل — جميع الصيغ دفعة واحدة
exporter.export_all("output/", formats=["csv", "json", "xlsx", "tmx"])
```

---

### 5. فحص الجودة — `quality_checker.py`

11 فحصاً تلقائياً لضمان جودة البيانات:

| # | الفحص | الوصف | الخطورة |
|---|-------|-------|---------|
| 1 | `empty_fields` | حقول فارغة (عربي/إنجليزي) | حرجة |
| 2 | `duplicates` | مصطلحات مكررة | حرجة |
| 3 | `inconsistent_categories` | تصنيفات غير متسقة | متوسطة |
| 4 | `invalid_unicode` | أحرف Unicode غير صالحة | حرجة |
| 5 | `mixed_script` | خلط غير متوقع بين الكتابات | متوسطة |
| 6 | `suspicious_whitespace` | مسافات بيضاء مشبوهة | منخفضة |
| 7 | `orphaned_terms` | مصطلحات بدون مصدر | منخفضة |
| 8 | `confidence_anomaly` | قيم ثقة غير طبيعية | متوسطة |
| 9 | `encoding_issues` | مشاكل الترميز | حرجة |
| 10 | `length_anomalies` | أطوال نصية غير طبيعية | متوسطة |
| 11 | `cross_source_conflict` | تعارضات بين المصادر | متوسطة |

```python
from src.quality_checker import QualityChecker

checker = QualityChecker(db)
report = checker.run_all_checks()

# عرض النتائج
print(f"الاجمالي: {report.total_issues} مشكلة")
print(f"حرجة: {report.critical_count}")
print(f"تم الإصلاح تلقائياً: {report.auto_fixed_count}")

# فحص محدد
duplicates = checker.check("duplicates")
```

---

### 6. الإحصائيات والتقارير — `statistics.py`

```python
from src.statistics import Statistics

stats = Statistics(db)

# تقرير شامل
report = stats.generate_report()
# → {total_terms, by_category, by_source, coverage, ...}

# تصدير التقرير
stats.export_report("report.json", format="json")
```

---

### 7. النسخ الاحتياطي — `backup_system.py`

```python
from src.backup_system import BackupSystem

backup = BackupSystem(db_path="glossary.db", backup_dir="backups/")

# إنشاء نسخة احتياطية
backup.create(description="قبل التحديث الكبير")
# → backups/glossary_20260715_143022_before_update.db

# استعادة من نسخة
backup.restore("glossary_20260715_143022_before_update.db")

# تدوير النسخ — الاحتفاظ بآخر 10 فقط
backup.rotate(keep=10)
```

---

### 8. الاستيعاب التلقائي — `auto_ingestion.py`

```python
from src.auto_ingestion import AutoIngestion

ingestion = AutoIngestion(
    db=db,
    watch_dirs=["glossaries/", "terms/"],
    patterns=["*.csv", "*.json", "*.jsonl"]
)

# مراقبة مستمرة (بخلفية)
ingestion.watch()

# فحص لمرة واحدة
ingestion.scan_once()
```

---

### 9. نظام الإضافات — `plugin_manager.py`

```python
from src.plugin_manager import PluginManager

pm = PluginManager(plugins_dir="plugins/")

# إنشاء إضافة جديدة
pm.create_plugin(
    name="terminology_validator",
    description="التحقق من صحة المصطلحات الطبية"
)
# → ينشئ plugins/terminology_validator/ بهيكل قياسي

# تحميل وتفعيل
pm.load_plugin("terminology_validator")
pm.enable("terminology_validator")

# قائمة الإضافات
pm.list_plugins()
```

---

### 10. تتبع الأصل (Provenance) — `provenance.py`

```python
from src.provenance import ProvenanceTracker

tracker = ProvenanceTracker(db)

# تسجيل إضافة مصطلح
tracker.log(
    term_id=42,
    action="add",
    source="hama_pharma_master.csv",
    details={"row": 15, "original": "Hypertension - ارتفاع ضغط الدم"}
)

# عرض تاريخ مصطلح
history = tracker.get_history(term_id=42)
# → [AddEvent, UpdateEvent, MergeEvent, ...]
```

---

### 11. تحويل الصيغ — `format_converter.py`

```python
from src.format_converter import FormatConverter

converter = FormatConverter()

# تحويل من CSV إلى JSON
converter.convert("input.csv", "output.json")

# تحويل من JSONL إلى TMX
converter.convert("data.jsonl", "output.tmx")

# الصيغ المدعومة: csv, tsv, json, jsonl, xlsx, tmx, md, html
```

---

### 12. واجهة CLI — `src/cli.py`

8 أوامر سطرية لإدارة النظام بالكامل:

| الأمر | الوصف | مثال |
|-------|-------|------|
| `search` | بحث في المصطلحات | `cli search "ضغط الدم"` |
| `add` | إضافة مصطلح | `cli add -e "hypertension" -a "ارتفاع ضغط الدم" -c diagnosis` |
| `import` | استيراد ملف | `cli import terms.csv --format csv` |
| `export` | تصدير البيانات | `cli export --format xlsx -o output.xlsx` |
| `check` | فحص الجودة | `cli check --fix` |
| `stats` | عرض الإحصائيات | `cli stats --json` |
| `backup` | النسخ الاحتياطي | `cli backup create --desc "daily"` |
| `merge` | دمج المصادر | `cli merge --strategy vote` |

```bash
# أمثلة استخدام
python -m src.cli search "hypertension" --lang en
python -m src.cli import glossaries/ --watch
python -m src.cli export --all --dir output/
python -m src.cli check --severity critical --fix
python -m src.cli stats
```

---

### 13. بناء قاعدة البيانات — `scripts/build_database.py`

```bash
# بناء قاعدة البيانات من جميع المصادر
python scripts/build_database.py --sources glossaries/ terms/ --output glossary.db

# إعادة البناء بالكامل
python scripts/build_database.py --rebuild --clean
```

### 14. الاختبارات — `tests/` (47 اختباراً)

```bash
# تشغيل جميع الاختبارات
python -m pytest tests/ -v

# تشغيل اختبار وحدة محددة
python -m pytest tests/test_db_manager.py -v

# مع تغطية الكود
python -m pytest tests/ --cov=src --cov-report=term-missing
```

---

## الروابط بين المستودعات

| المستودع | الوصف | الرابط |
|----------|-------|--------|
| `arabic-medical-glossary` | المسارد الطبية + نظام الإدارة المتقدم | `./` (المستودع الحالي) |
| `glossary-api` | REST API منفصل للاستعلام | `../glossary-api/` |

- النظام المتقدم (Calibre-inspired) يدير البيانات في هذا المستودع
- `glossary-api` يوفر واجهة REST للقراءة والبحث عن المصطلحات
- كلا المستودعين يشتركان في نفس قاعدة البيانات (SQLite)

---

## البدء السريع

```bash
# 1. بناء قاعدة البيانات
python scripts/build_database.py --sources glossaries/ terms/

# 2. فحص الجودة
python -m src.cli check --fix

# 3. تصدير إلى Excel
python -m src.cli export --format xlsx -o glossary.xlsx

# 4. البحث
python -m src.cli search "ارتفاع ضغط الدم"

# 5. تشغيل الاختبارات
python -m pytest tests/ -v
```

---

*آخر تحديث: 2026-07-15 — الإصدار 2.0*