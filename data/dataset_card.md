---
license: cc-by-4.0
task_categories:
  - translation
language:
  - ar
  - en
tags:
  - medical
  - bilingual
  - arabic
  - english
  - glossary
  - pharmaceutical
  - translation
size_categories:
  - 1K<n<10K
---

# Arabic-English Bilingual Medical Glossary

## Dataset Description

A comprehensive Arabic-English bilingual glossary focused on medical and pharmaceutical terminology. This dataset is built from multiple sources including OCR-extracted pharmaceutical leaflets, WHO essential medicines lists, curated medical phrases, and Wikipedia/Wikidata medical entities.

### Supported Tasks

- **Machine Translation** (AR ↔ EN): Training and evaluating medical translation models
- **Terminology Extraction**: Building domain-specific translation dictionaries
- **Medical NLP**: Fine-tuning language models for the medical domain in Arabic

### Languages

- **Arabic (ar)**: Modern Standard Arabic medical terminology
- **English (en)**: English medical and pharmaceutical terminology

## Dataset Structure

### Data Fields

| Field | Type | Description |
|-------|------|-------------|
| `en` | `string` | English text (term or sentence) |
| `ar` | `string` | Arabic translation |
| `source` | `string` | Data source identifier |
| `type` | `string` | `term` or `sentence` |
| `section` | `string` | Medical section/category |
| `confidence` | `string` | Translation confidence level (`very_high`, `high`, `medium`) |
| `hash` | `string` | Deduplication hash |

### Data Splits

| Split | Records | Description |
|-------|---------|-------------|
| `all_pairs.csv` | All records | Complete dataset (terms + sentences) |
| `terms.csv` | Term records only | Single-word and short-phrase terminology |
| `sentences.csv` | Sentence records only | Full-sentence translations |
| `section_headers.csv` | 35 records | Pharmaceutical leaflet section headings |

### Data Sources

| Source | Description | Count |
|--------|-------------|-------|
| `hama_pharma_ocr` | OCR-extracted from 92 Syrian pharmaceutical leaflets (Hama Pharma) | ~620 |
| `who_essential_medicines` | WHO Model List of Essential Medicines with Arabic translations | ~120 |
| `curated_medical_phrases` | Manually curated medical sentences and phrases | ~60 |
| `wikipedia_langlinks` | Wikipedia medical category EN→AR article title pairs | Variable |
| `wikidata_medical` | Wikidata medical entity EN/AR labels | Variable |
| `medlineplus` | MedlinePlus medical encyclopedia EN↔AR | Variable |

## Dataset Creation

### Source Details

1. **Hama Pharma OCR**: 92 pharmaceutical PDFs were processed using Tesseract OCR (`ara+eng`, DPI 150). Arabic text was extracted from leaflets with broken ToUnicode CMap tables. Pairs were then cleaned, deduplicated, and classified into terms vs. sentences.

2. **WHO Essential Medicines**: Standard pharmaceutical ingredient names mapped to their official Arabic translations as used in Syrian pharmaceutical regulations.

3. **Curated Medical Phrases**: Common medical instructions, warnings, and descriptions found in pharmaceutical leaflets, professionally translated.

4. **Wikipedia/Wikidata**: Medical category articles from English Wikipedia matched to their Arabic counterparts via langlinks API and Wikidata labels.

5. **MedlinePlus**: Medical encyclopedia articles from both English and Arabic MedlinePlus portals.

### Cleaning Process

- Garbled text removed via regex filtering (non-Arabic in AR field, non-Latin in EN field)
- Duplicate pairs removed using MD5 hash of normalized (lowercase EN, stripped AR)
- Classification into `term` (≤5 words) vs `sentence` (>5 words)
- Confidence scoring based on source reliability

## Usage

```python
from datasets import load_dataset

dataset = load_dataset("DrAbdulmalek/arabic-bilingual-medical-glossary")

# All pairs
print(dataset["train"][0])
# {'en': 'Composition', 'ar': 'التركيب', 'source': 'hama_pharma_ocr', ...}

# Use as translation pairs
for row in dataset["train"]:
    print(f"EN: {row['en']}  →  AR: {row['ar']}")
```

### Loading CSV Directly

```python
import pandas as pd

terms = pd.read_csv("terms.csv")
sentences = pd.read_csv("sentences.csv")
```

## Limitations

- **Domain scope**: Primarily pharmaceutical; may not cover all medical specialties equally
- **Dialect**: Modern Standard Arabic (MSA) only; no dialectal variants
- **OCR quality**: Some terms from OCR may have minor character errors despite cleaning
- **Size**: Currently ~700-1000+ pairs; this dataset is continuously being expanded

## Ethical Considerations

- This dataset is intended for research and educational purposes in medical NLP
- Pharmaceutical translations should be validated by qualified medical translators before clinical use
- No patient data or personally identifiable information is included

## License

CC-BY 4.0 — Free for research and commercial use with attribution.

## Maintenance

This dataset is updated automatically via GitHub Actions every 12 hours. Contributions and corrections are welcome via [GitHub Issues](https://github.com/DrAbdulmalek/arabic-medical-glossary/issues).