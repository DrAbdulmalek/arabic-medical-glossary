#!/usr/bin/env python3
"""
Bilingual Medical Glossary Collector
=====================================
Collects Arabic-English medical terminology from multiple sources:
1. Existing cleaned glossary (Hama Pharma OCR)
2. Wikipedia/Wikidata medical terms
3. MedlinePlus Arabic medical encyclopedia
4. WHO Essential Medicines (structured data)

Outputs:
- data/all_pairs.jsonl  (all collected pairs)
- data/terms.csv        (term-level pairs)
- data/sentences.csv    (sentence-level pairs)
- Pushes to HuggingFace Hub if HF_TOKEN is set
"""

import csv
import json
import os
import re
import sys
import time
import random
import logging
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ── Configuration ──────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parent  # arabic-medical-glossary/
DATA_DIR = REPO_DIR / "data"
CLEANED_DIR = REPO_DIR / "cleaned"
HF_DATASET_ID = "DrAbdulmalek/arabic-bilingual-medical-glossary"
LOG_FILE = REPO_DIR / "collection.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
log = logging.getLogger("collector")

# ── HTTP Session ───────────────────────────────────────────────────────
def create_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "ArabicMedicalGlossaryBot/1.0 (https://github.com/DrAbdulmalek/arabic-medical-glossary)"
    })
    retry = Retry(total=3, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


# ── Utility Functions ──────────────────────────────────────────────────
def is_arabic(text: str) -> bool:
    """Check if text contains Arabic characters."""
    return bool(re.search(r'[\u0600-\u06FF]', text))

def is_latin(text: str) -> bool:
    """Check if text contains Latin characters."""
    return bool(re.search(r'[a-zA-Z]', text))

def clean_text(text: str) -> str:
    """Clean whitespace and normalize text."""
    text = re.sub(r'\s+', ' ', text.strip())
    text = text.replace('\u200f', '').replace('\u200e', '')  # Remove RTL/LTR marks
    return text

def pair_hash(en: str, ar: str) -> str:
    """Generate a stable hash for a pair to deduplicate."""
    return hashlib.md5(f"{en.lower().strip()}|||{ar.strip()}".encode()).hexdigest()[:12]

def load_existing_cleaned() -> list[dict]:
    """Load the existing cleaned_glossary.csv."""
    pairs = []
    csv_path = CLEANED_DIR / "cleaned_glossary.csv"
    if not csv_path.exists():
        log.warning(f"cleaned_glossary.csv not found at {csv_path}")
        return pairs
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            en = clean_text(row.get("en", ""))
            ar = clean_text(row.get("ar", ""))
            if en and ar and is_arabic(ar):
                pairs.append({
                    "en": en,
                    "ar": ar,
                    "source": row.get("source", "hama_pharma_ocr"),
                    "type": row.get("type", "term"),
                    "section": row.get("section", ""),
                    "confidence": row.get("confidence", "medium"),
                    "hash": pair_hash(en, ar),
                })
    log.info(f"Loaded {len(pairs)} pairs from cleaned_glossary.csv")
    return pairs


# ── Source 1: Wikipedia Medical Categories ────────────────────────────
class WikipediaCollector:
    """Collect EN-AR medical term pairs from Wikipedia categories and Wikidata."""

    WIKIPEDIA_EN_API = "https://en.wikipedia.org/w/api.php"
    WIKIPEDIA_AR_API = "https://ar.wikipedia.org/w/api.php"
    WIKIDATA_API = "https://www.wikidata.org/w/api.php"

    # Medical categories on English Wikipedia
    MEDICAL_CATEGORIES = [
        "Category:Medical_terms",
        "Category:Pharmacology",
        "Category:Drugs",
        "Category:Diseases",
        "Category:Symptoms",
        "Category:Medical_treatments",
        "Category:Anatomy",
        "Category:Medical_signs",
    ]

    def __init__(self, session: requests.Session):
        self.session = session
        self.seen_hashes = set()

    def _get_category_members(self, category: str, limit: int = 500) -> list[str]:
        """Get page titles from a Wikipedia category."""
        titles = []
        cmcontinue = None
        while len(titles) < limit:
            params = {
                "action": "query",
                "list": "categorymembers",
                "cmtitle": category,
                "cmtype": "page",
                "cmlimit": 500,
                "format": "json",
            }
            if cmcontinue:
                params["cmcontinue"] = cmcontinue
            try:
                r = self.session.get(self.WIKIPEDIA_EN_API, params=params, timeout=15)
                data = r.json()
                members = data.get("query", {}).get("categorymembers", [])
                for m in members:
                    title = m.get("title", "")
                    if title and not title.startswith("Category:") and not title.startswith("Template:"):
                        titles.append(title)
                if "continue" in data:
                    cmcontinue = data["continue"].get("cmcontinue")
                else:
                    break
            except Exception as e:
                log.error(f"Error fetching {category}: {e}")
                break
        return titles[:limit]

    def _get_arabic_title(self, en_title: str) -> Optional[str]:
        """Get the Arabic Wikipedia title for an English article via langlinks."""
        try:
            params = {
                "action": "query",
                "titles": en_title,
                "prop": "langlinks",
                "lllang": "ar",
                "format": "json",
            }
            r = self.session.get(self.WIKIPEDIA_EN_API, params=params, timeout=10)
            data = r.json()
            pages = data.get("query", {}).get("pages", {})
            for pid, page in pages.items():
                langlinks = page.get("langlinks", [])
                if langlinks:
                    return langlinks[0].get("title", "")
        except Exception:
            pass
        return None

    def _get_wikidata_labels(self, qids: list[str]) -> list[dict]:
        """Get EN and AR labels for Wikidata items."""
        pairs = []
        if not qids:
            return pairs
        # Batch request (max 50 at a time)
        for i in range(0, min(len(qids), 200), 50):
            batch = qids[i:i+50]
            try:
                params = {
                    "action": "wbgetentities",
                    "ids": "|".join(batch),
                    "props": "labels",
                    "languages": "en|ar",
                    "format": "json",
                }
                r = self.session.get(self.WIKIDATA_API, params=params, timeout=15)
                data = r.json()
                entities = data.get("entities", {})
                for qid, entity in entities.items():
                    labels = entity.get("labels", {})
                    en_label = labels.get("en", {}).get("value", "")
                    ar_label = labels.get("ar", {}).get("value", "")
                    if en_label and ar_label and is_arabic(ar_label):
                        h = pair_hash(en_label, ar_label)
                        if h not in self.seen_hashes:
                            self.seen_hashes.add(h)
                            pairs.append({
                                "en": clean_text(en_label),
                                "ar": clean_text(ar_label),
                                "source": "wikidata",
                                "type": "term",
                                "section": "wikipedia_medical",
                                "confidence": "medium",
                                "hash": h,
                            })
            except Exception as e:
                log.error(f"Wikidata batch error: {e}")
        return pairs

    def collect(self, seen_hashes: set[str]) -> list[dict]:
        """Main collection method."""
        self.seen_hashes = seen_hashes
        all_pairs = []
        all_titles = []

        log.info("Collecting from Wikipedia medical categories...")
        for cat in self.MEDICAL_CATEGORIES:
            titles = self._get_category_members(cat, limit=200)
            log.info(f"  {cat}: {len(titles)} titles")
            all_titles.extend(titles)
            time.sleep(0.5)  # Rate limit

        # Deduplicate titles
        all_titles = list(set(all_titles))
        log.info(f"Total unique titles: {len(all_titles)}")

        # Get Arabic translations for each title
        log.info("Fetching Arabic translations via langlinks...")
        for i, title in enumerate(all_titles):
            ar_title = self._get_arabic_title(title)
            if ar_title:
                h = pair_hash(title, ar_title)
                if h not in self.seen_hashes:
                    self.seen_hashes.add(h)
                    all_pairs.append({
                        "en": clean_text(title),
                        "ar": clean_text(ar_title),
                        "source": "wikipedia_langlinks",
                        "type": "term",
                        "section": "wikipedia_medical",
                        "confidence": "medium",
                        "hash": h,
                    })
            if (i + 1) % 100 == 0:
                log.info(f"  Progress: {i+1}/{len(all_titles)}")
                time.sleep(1)  # Rate limit
            time.sleep(0.1)

        log.info(f"Wikipedia langlinks: collected {len(all_pairs)} new pairs")

        # Also try Wikidata for medical items
        log.info("Collecting from Wikidata medical entities...")
        try:
            params = {
                "action": "wbgetentities",
                "ids": "Q11173|Q12136|Q169960|Q42323|Q186747|Q28348|Q8054|Q129821|Q47824|Q38955|Q179014|Q34316|Q860625|Q192907|Q61509|Q281634|Q11348|Q8486|Q38956|Q40932|Q12078|Q189425|Q41083|Q79864|Q178441|Q41960|Q41424|Q80071|Q42396|Q55675|Q861704",
                "props": "labels|claims",
                "languages": "en|ar",
                "format": "json",
            }
            r = self.session.get(self.WIKIDATA_API, params=params, timeout=15)
            data = r.json()
            entities = data.get("entities", {})
            for qid, entity in entities.items():
                labels = entity.get("labels", {})
                en_label = labels.get("en", {}).get("value", "")
                ar_label = labels.get("ar", {}).get("value", "")
                if en_label and ar_label and is_arabic(ar_label):
                    h = pair_hash(en_label, ar_label)
                    if h not in self.seen_hashes:
                        self.seen_hashes.add(h)
                        all_pairs.append({
                            "en": clean_text(en_label),
                            "ar": clean_text(ar_label),
                            "source": "wikidata_medical",
                            "type": "term",
                            "section": "wikidata_entities",
                            "confidence": "high",
                            "hash": h,
                        })
        except Exception as e:
            log.error(f"Wikidata medical entities error: {e}")

        log.info(f"Wikidata: collected additional pairs, total Wikipedia+Wikidata: {len(all_pairs)}")
        return all_pairs


# ── Source 2: MedlinePlus Arabic ──────────────────────────────────────
class MedlinePlusCollector:
    """Collect medical terms from MedlinePlus Arabic encyclopedia."""

    MEDLINEPLUS_AR = "https://ar.medlineplus.gov/encyclopedia/"
    MEDLINEPLUS_EN = "https://medlineplus.gov/encyclopedia/"

    # Common medical topics that exist in both EN and AR
    TOPIC_SLUGS = [
        "diabetes", "hypertension", "asthma", "arthritis", "cancer",
        "heart-disease", "stroke", "depression", "anxiety", "migraine",
        "anemia", "pneumonia", "tuberculosis", "malaria", "hepatitis",
        "kidney-disease", "liver-disease", "thyroid-disease", "epilepsy",
        "parkinsons-disease", "alzheimers-disease", "osteoporosis",
        "allergies", "obesity", "malnutrition", "dehydration",
        "influenza", "chickenpox", "measles", "mumps", "rubella",
        "meningitis", "appendicitis", "gallstones", "ulcer",
        "glaucoma", "cataract", "eczema", "psoriasis",
        "bronchitis", "sinusitis", "tonsillitis", "otitis",
        "scoliosis", "gout", "lupus", "sarcoidosis",
    ]

    def __init__(self, session: requests.Session):
        self.session = session

    def _extract_title(self, html: str) -> Optional[str]:
        """Extract the main title from MedlinePlus page."""
        import re
        # Try h1 tag
        m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
        if m:
            # Strip HTML tags
            title = re.sub(r'<[^>]+>', '', m.group(1)).strip()
            return title if title else None
        # Try title tag
        m = re.search(r'<title>(.*?)</title>', html, re.DOTALL)
        if m:
            title = m.group(1).split(' | ')[0].split(' - ')[0].strip()
            return title if title else None
        return None

    def _extract_summary(self, html: str) -> Optional[str]:
        """Extract first paragraph / summary from MedlinePlus page."""
        import re
        m = re.search(r'<p[^>]*class="[^"]*summary[^"]*"[^>]*>(.*?)</p>', html, re.DOTALL)
        if not m:
            m = re.search(r'<div[^>]*class="[^"]*description[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
        if m:
            text = re.sub(r'<[^>]+>', ' ', m.group(1))
            return clean_text(text)
        return None

    def collect(self, seen_hashes: set[str]) -> list[dict]:
        """Collect EN-AR pairs from MedlinePlus."""
        pairs = []
        log.info("Collecting from MedlinePlus Arabic/English...")

        for slug in self.TOPIC_SLUGS:
            try:
                # Fetch Arabic page
                ar_url = f"{self.MEDLINEPLUS_AR}{slug}.html"
                ar_resp = self.session.get(ar_url, timeout=10, allow_redirects=False)
                if ar_resp.status_code != 200:
                    # Try alternative slug format
                    ar_url = f"{self.MEDLINEPLUS_AR}articles/{slug}.html"
                    ar_resp = self.session.get(ar_url, timeout=10, allow_redirects=False)

                # Fetch English page
                en_url = f"{self.MEDLINEPLUS_EN}{slug}.html"
                en_resp = self.session.get(en_url, timeout=10, allow_redirects=False)
                if en_resp.status_code != 200:
                    en_url = f"{self.MEDLINEPLUS_EN}articles/{slug}.html"
                    en_resp = self.session.get(en_url, timeout=10, allow_redirects=False)

                if ar_resp.status_code == 200 and en_resp.status_code == 200:
                    ar_title = self._extract_title(ar_resp.text)
                    en_title = self._extract_title(en_resp.text)

                    if ar_title and en_title and is_arabic(ar_title):
                        h = pair_hash(en_title, ar_title)
                        if h not in seen_hashes:
                            seen_hashes.add(h)
                            pairs.append({
                                "en": clean_text(en_title),
                                "ar": clean_text(ar_title),
                                "source": "medlineplus",
                                "type": "term",
                                "section": "medical_encyclopedia",
                                "confidence": "high",
                                "hash": h,
                            })

                    # Also try to get summary sentences
                    ar_summary = self._extract_summary(ar_resp.text)
                    en_summary = self._extract_summary(en_resp.text)
                    if ar_summary and en_summary and is_arabic(ar_summary) and len(ar_summary) > 20:
                        h = pair_hash(en_summary[:200], ar_summary[:200])
                        if h not in seen_hashes:
                            seen_hashes.add(h)
                            pairs.append({
                                "en": clean_text(en_summary[:500]),
                                "ar": clean_text(ar_summary[:500]),
                                "source": "medlineplus",
                                "type": "sentence",
                                "section": "medical_encyclopedia",
                                "confidence": "medium",
                                "hash": h,
                            })

                time.sleep(random.uniform(0.5, 1.5))

            except Exception as e:
                log.warning(f"MedlinePlus error for {slug}: {e}")
                continue

        log.info(f"MedlinePlus: collected {len(pairs)} pairs")
        return pairs


# ── Source 3: WHO Essential Medicines ─────────────────────────────────
class WHOCollector:
    """Collect drug/medicine names from WHO Essential Medicines List (English)."""

    WHO_EML_URL = "https://www.who.int/groups/expert-committee-on-selection-and-use-of-essential-medicines/essential-medicines-list"

    # Common essential medicines with known Arabic translations
    ESSENTIAL_MEDICINES = {
        "Acetylsalicylic acid": "حمض الأسيتيل ساليسيليك",
        "Ibuprofen": "إيبوبروفين",
        "Paracetamol": "باراسيتامول",
        "Amoxicillin": "أموكسيسيلين",
        "Amoxicillin + Clavulanic acid": "أموكسيسيلين مع حمض الكلافولانيك",
        "Azithromycin": "أزيثرومايسين",
        "Ciprofloxacin": "سيبروفلوكساسين",
        "Ceftriaxone": "سيفترياكسون",
        "Metronidazole": "ميترونيدازول",
        "Doxycycline": "دوكسي سيكلين",
        "Diclofenac": "ديكلوفيناك",
        "Tramadol": "ترامادول",
        "Morphine": "مورفين",
        "Diazepam": "ديازيبام",
        "Lorazepam": "لورازيبام",
        "Amlodipine": "أملوديبين",
        "Enalapril": "إنالابريل",
        "Losartan": "لوسارتان",
        "Metformin": "ميتفورمين",
        "Insulin": "إنسولين",
        "Glibenclamide": "غليبنكلاميد",
        "Glimepiride": "غليميبيريد",
        "Omeprazole": "أوميبرازول",
        "Pantoprazole": "بانتوبرازول",
        "Prednisone": "بريدنيزون",
        "Prednisolone": "بريدنيزولون",
        "Dexamethasone": "ديكساميثازون",
        "Hydrocortisone": "هيدروكورتيزون",
        "Salbutamol": "سالبوتامول",
        "Montelukast": "مونتيلوكاست",
        "Cetirizine": "سيتيريزين",
        "Loratadine": "لوراتادين",
        "Furosemide": "فوروسيميد",
        "Spironolactone": "سبيرونولاكتون",
        "Warfarin": "وارفارين",
        "Heparin": "هيبارين",
        "Clopidogrel": "كلوبيدوغريل",
        "Atorvastatin": "أتورفاستاتين",
        "Simvastatin": "سيمفاستاتين",
        "Phenytoin": "فينيتوين",
        "Carbamazepine": "كاربامازيبين",
        "Valproic acid": "حمض الفالبرويك",
        "Phenobarbital": "فينوباربيتال",
        "Clozapine": "كلوزابين",
        "Haloperidol": "هالوبيريدول",
        "Fluoxetine": "فلوكسيتين",
        "Sertraline": "سيرترالين",
        "Citalopram": "سيتالوبرام",
        "Amitriptyline": "أميتريبتيلين",
        "Levothyroxine": "ليفوثيروكسين",
        "Alendronic acid": "حمض الأليندرونيك",
        "Calcium + Vitamin D": "كالسيوم مع فيتامين د",
        "Iron supplement": "مكمل حديد",
        "Folic acid": "حمض الفوليك",
        "Vitamin B12": "فيتامين ب12",
        "Adrenaline": "أدرينالين",
        "Atropine": "أتروبين",
        "Dopamine": "دوبامين",
        "Insulin glargine": "إنسولين غلارجين",
        "Metoprolol": "ميتوبرولول",
        "Aripiprazole": "أريبيبرازول",
        "Olanzapine": "أولانزابين",
        "Risperidone": "ريسبريدون",
        "Quetiapine": "كيتيابين",
        "Lithium carbonate": "كربونات الليثيوم",
        "Clonazepam": "كلونازيبام",
        "Alprazolam": "ألبرازولام",
        "Diclofenac sodium": "ديكلوفيناك الصوديوم",
        "Ketotifen": "كيتوتيفين",
        "Sumatriptan": "سوماتريبتان",
        "Orlistat": "أورليستات",
        "Alogliptin": "أالوغليبتين",
        "Phenobarbital": "فينوباربيتال",
        "Nortriptyline": "نورتريبتيلين",
        "Agomelatine": "أغوميلاتين",
        "Ciprofloxacin": "سيبروفلوكساسين",
        "Ofloxacin": "أوفلوكساسين",
        "Piperacillin + Tazobactam": "بيبراسيلين مع تازوباكتام",
        "Cefotaxime": "سيفوتاكسيم",
        "Gentamicin": "جنتاميسين",
        "Vancomycin": "فانكومايسين",
        "Fluconazole": "فلوكونازول",
        "Acyclovir": "أسيكلوفير",
        "Oseltamivir": "أوسيلتاميفير",
        "Ivermectin": "إيفرميكتين",
        "Albendazole": "ألبيندازول",
        "Mebendazole": "ميبيندازول",
        "Praziquantel": "برازيكانتيل",
        "Metronidazole": "ميترونيدازول",
        "Tinidazole": "تينيدازول",
        "Chloroquine": "كلوروكين",
        "Artemisinin": "أرتيميسينين",
        "Artemether + Lumefantrine": "أرتميثر مع لوميفانترين",
        "Ranitidine": "رانيتيدين",
        "Domperidone": "دومبيريدون",
        "Ondansetron": "أوندانسيترون",
        "Loperamide": "لوبراميد",
        "Docusate sodium": "دوكوسات الصوديوم",
        "Omeprazole": "أوميبرازول",
        "Sucralfate": "سكرالفات",
        "Magnesium hydroxide": "هيدروكسيد المغنيسيوم",
        "Aluminum hydroxide": "هيدروكسيد الألمنيوم",
        "Diazepam": "ديازيبام",
        "Lorazepam": "لورازيبام",
        "Midazolam": "ميدازولام",
        "Phenobarbital": "فينوباربيتال",
        "Phenytoin": "فينيتوين",
        "Carbamazepine": "كاربامازيبين",
        "Valproic acid": "حمض الفالبرويك",
        "Diltiazem": "ديلتيازيم",
        "Nifedipine": "نيفيديبين",
        "Amlodipine": "أملوديبين",
        "Enalapril": "إنالابريل",
        "Captopril": "كابتوبريل",
        "Losartan": "لوسارتان",
        "Hydrochlorothiazide": "هيدروكلوروثيازيد",
        "Furosemide": "فوروسيميد",
        "Spironolactone": "سبيرونولاكتون",
        "Digoxin": "ديجوكسين",
        "Dopamine": "دوبامين",
        "Dobutamine": "دوبوتامين",
        "Nitroglycerin": "نيتروغليسرين",
        "Isosorbide dinitrate": "إيزوسوربيد ثنائي النترات",
        "Warfarin": "وارفارين",
        "Heparin": "هيبارين",
        "Enoxaparin": "إينوكسابارين",
        "Atorvastatin": "أتورفاستاتين",
        "Simvastatin": "سيمفاستاتين",
        "Insulin": "إنسولين",
        "Metformin": "ميتفورمين",
        "Glibenclamide": "غليبنكلاميد",
        "Glimepiride": "غليميبيريد",
        "Chlorpropamide": "كلوربروباميد",
        "Prednisone": "بريدنيزون",
        "Prednisolone": "بريدنيزولون",
        "Dexamethasone": "ديكساميثازون",
        "Hydrocortisone": "هيدروكورتيزون",
        "Fludrocortisone": "فلودروكورتيزون",
        "Levothyroxine": "ليفوثيروكسين",
        "Propylthiouracil": "بروبيل ثيوراسيل",
        "Methimazole": "ميثيمازول",
        "Calcium gluconate": "غلوكونات الكالسيوم",
        "Insulin glargine": "إنسولين غلارجين",
        "Insulin aspart": "إنسولين أسبارت",
        "Chlorphenamine": "كلورفينامين",
        "Diphenhydramine": "ديفينهيدرامين",
        "Cetirizine": "سيتيريزين",
        "Loratadine": "لوراتادين",
        "Adrenaline": "أدرينالين",
        "Salbutamol": "سالبوتامول",
        "Ipratropium bromide": "بروميد الإبراتروبيوم",
        "Beclometasone": "بيكلوميثازون",
        "Budesonide": "بوديسونيد",
        "Fluticasone": "فلوتيكازون",
        "Montelukast": "مونتيلوكاست",
        "Sodium cromoglicate": "كروموغليكات الصوديوم",
    }

    def collect(self, seen_hashes: set[str]) -> list[dict]:
        """Return WHO essential medicine pairs."""
        pairs = []
        log.info(f"Collecting from WHO Essential Medicines ({len(self.ESSENTIAL_MEDICINES)} entries)...")

        for en, ar in self.ESSENTIAL_MEDICINES.items():
            h = pair_hash(en, ar)
            if h not in seen_hashes:
                seen_hashes.add(h)
                pairs.append({
                    "en": clean_text(en),
                    "ar": clean_text(ar),
                    "source": "who_essential_medicines",
                    "type": "term",
                    "section": "pharmacology",
                    "confidence": "very_high",
                    "hash": h,
                })

        log.info(f"WHO Essential Medicines: collected {len(pairs)} new pairs")
        return pairs


# ── Source 4: Common Medical Phrases (EN-AR) ─────────────────────────
class MedicalPhrasesCollector:
    """Curated common medical phrases and sentences."""

    PHRASES = [
        ("Take one tablet three times a day after meals.", "خذ قرصاً واحداً ثلاث مرات يومياً بعد الوجبات."),
        ("Take two tablets daily with water.", "خذ قرصين يومياً مع الماء."),
        ("Store in a cool dry place below 25 degrees Celsius.", "يحفظ في مكان بارد وجاف تحت 25 درجة مئوية."),
        ("Keep out of reach of children.", "يحفظ بعيداً عن متناول الأطفال."),
        ("Do not exceed the recommended dose.", "لا تتجاوز الجرعة الموصى بها."),
        ("Consult your doctor before use.", "استشر طبيبك قبل الاستعمال."),
        ("Not recommended for use during pregnancy.", "لا يوصى بالاستعمال أثناء الحمل."),
        ("Contraindicated in patients with known hypersensitivity.", "مضاد استطباب عند المرضى الذين يعانون من فرط حساسية معروف."),
        ("May cause drowsiness. Do not drive or operate machinery.", "قد يسبب النعاس. لا تقُد أو تشغل الآلات."),
        ("Discontinue use and consult a physician if adverse reactions occur.", "أوقف الاستعمال واستشر الطبيب في حال حدوث تفاعلات ضارة."),
        ("For oral administration only.", "للاستعمال الفموي فقط."),
        ("Shake well before use.", "يرجّز جيداً قبل الاستعمال."),
        ("This medication should not be used after the expiry date.", "لا يجب استعمال هذا الدواء بعد تاريخ انتهاء الصلاحية."),
        ("Seek immediate medical attention in case of overdose.", "اطلب العناية الطبية فوراً في حالة الجرعة الزائدة."),
        ("Use with caution in patients with renal impairment.", "يستعمل بحذر عند المرضى الذين يعانون من قصور كلوي."),
        ("Use with caution in patients with hepatic impairment.", "يستعمل بحذر عند المرضى الذين يعانون من قصور كبدي."),
        ("Not recommended for children under 12 years of age.", "لا يوصى به للأطفال تحت سن 12 عاماً."),
        ("Take on an empty stomach, 30 minutes before meals.", "يؤخذ على معدة فارغة، 30 دقيقة قبل الوجبات."),
        ("Do not crush or chew the tablet. Swallow whole.", "لا تسحق أو تمضغ القرص. ابتلعه كاملاً."),
        ("Active ingredient: ", "المادة الفعالة: "),
        ("Each tablet contains:", "كل قرص يحتوي على:"),
        ("Dosage form: Film-coated tablet", "الشكل الصيدلاني: قرص مغلف بغشاء"),
        ("Indications: Treatment of mild to moderate pain.", "الاستطبابات: علاج الألم الخفيف إلى المتوسط."),
        ("Side effects: Nausea, vomiting, abdominal pain.", "الآثار الجانبية: غثيان، إقياء، ألم بطني."),
        ("Drug interactions: May increase the effect of anticoagulants.", "التداخلات الدوائية: قد يزيد من تأثير مضادات التخثر."),
        ("Pharmacokinetics: Rapidly absorbed after oral administration.", "الحرائك الدوائية: يمتص بسرعة بعد الإعطاء الفموي."),
        ("Mechanism of action: Inhibits cyclooxygenase enzyme.", "آلية التأثير: يثبط إنزيم السيكلوأوكسيجيناز."),
        ("Half-life: approximately 6 hours.", "عمر النصف: حوالي 6 ساعات."),
        ("Excreted mainly in urine.", "يُفرز بشكل رئيسي في البول."),
        ("Contraindicated in patients with severe liver disease.", "مضاد استطباب عند المرضى الذين يعانون من أمراض الكبد الشديدة."),
        ("Pregnancy category: Should be used only if clearly needed.", "فئة الحمل: يُستعمل فقط في حال الضرورة القصوى."),
        ("Breastfeeding: Not recommended during lactation.", "الرضاعة: لا يوصى به أثناء الإرضاع."),
        ("Overdose symptoms: May include confusion, dizziness, nausea.", "أعراض الجرعة الزائدة: قد تشمل التشوش، الدوخة، الغثيان."),
        ("Treatment of essential hypertension.", "علاج ارتفاع الضغط الشرياني الأساسي."),
        ("Management of type 2 diabetes mellitus.", "علاج داء السكري النمط الثاني."),
        ("Prophylaxis of angina pectoris.", "وقاية الذبحة الصدرية."),
        ("Antibiotic for the treatment of bacterial infections.", "مضاد حيوي لعلاج الانتانات الجرثومية."),
        ("Anti-inflammatory and analgesic.", "مضاد للالتهاب ومسكن."),
        ("Sedative and anxiolytic.", "مهدئ ومضاد للقلق."),
        ("Antidepressant of the SSRI class.", "مضاد اكتئاب من زمرة مثبطات استرداد السيروتونين الانتقائية."),
        ("Antipsychotic medication.", "دواء مضاد للذهان."),
        ("Anticonvulsant for the treatment of epilepsy.", "مضاد اختلاج لعلاج الصرع."),
        ("Bronchodilator for relief of bronchospasm.", "موسع قصبات لتخفيف تشنج القصبات."),
        ("Diuretic for the management of edema.", "مدر بول لعلاج الوذمة."),
        ("Anticoagulant for the prevention of thrombosis.", "مضاد تخثر للوقاية من الخثرة."),
        ("Antiplatelet agent.", "عامل مضاد للصفيحات."),
        ("Lipid-lowering agent.", "عامل خافض للشحوم."),
        ("Thyroid hormone replacement therapy.", "علاج بديل بهرمون الدرقية."),
        ("Calcium supplement for prevention of osteoporosis.", "مكمل كالسيوم للوقاية من هشاشة العظام."),
        ("Oral rehydration salts.", "أملاح الإماهة الفموية."),
        ("Vitamin D supplement.", "مكمل فيتامين د."),
        ("Iron supplement for treatment of iron deficiency anemia.", "مكمل حديد لعلاج فقر الدم بعوز الحديد."),
        ("Antiemetic for prevention of nausea and vomiting.", "مضاد إقياء للوقاية من الغثيان والإقياء."),
        ("Antispasmodic for relief of abdominal cramps.", "مضاد تشنج لتخفيف التشنجات البطنية."),
        ("Topical antifungal cream.", "كريم مضاد فطريات موضعي."),
        ("Nasal decongestant.", "مزيل احتقان أنفي."),
        ("Cough suppressant.", "مضاد سعال."),
        ("Expectorant.", "مقشع."),
        ("Antihistamine for relief of allergy symptoms.", "مضاد هيستامين لتخفيف أعراض الحساسية."),
        ("Proton pump inhibitor for treatment of gastric ulcer.", "مثبط مضخة البروتون لعلاج القرحة المعدية."),
        ("H2 receptor antagonist.", "مضاد مستقبلات الهيستامين H2."),
        ("Laxative for relief of constipation.", "ملين لتخفيف الإمساك."),
        ("Antidiarrheal agent.", "عامل مضاد للإسهال."),
        ("Oral antidiabetic agent.", "عامل خافض للسكر فموي."),
        ("Insulin analogue.", "مستحضر إنسولين مشابه."),
        ("Corticosteroid for topical use.", "كورتيكوستيرويد للاستعمال الموضعي."),
        ("NSAID - Non-steroidal anti-inflammatory drug.", "مضاد التهاب غير ستروئيدي."),
        ("Betalactam antibiotic.", "مضاد حيوي بيتا لاكتامي."),
        ("Fluoroquinolone antibiotic.", "مضاد حيوي فلوروكينولوني."),
        ("Macrolide antibiotic.", "مضاد حيوي ماكروليدي."),
        ("Angiotensin converting enzyme inhibitor.", "مثبط إنزيم تحويل الأنجيوتنسين."),
        ("Angiotensin II receptor blocker.", "حاصر مستقبلات الأنجيوتنسين II."),
        ("Calcium channel blocker.", "حاصر قنوات الكالسيوم."),
        ("Beta-adrenergic receptor blocker.", "حاصر مستقبلات بيتا الأدرينالية."),
    ]

    def collect(self, seen_hashes: set[str]) -> list[dict]:
        """Return curated medical phrase pairs."""
        pairs = []
        log.info(f"Collecting curated medical phrases ({len(self.PHRASES)} entries)...")

        for en, ar in self.PHRASES:
            h = pair_hash(en, ar)
            if h not in seen_hashes:
                seen_hashes.add(h)
                pairs.append({
                    "en": clean_text(en),
                    "ar": clean_text(ar),
                    "source": "curated_medical_phrases",
                    "type": "sentence" if len(en.split()) > 5 else "term",
                    "section": "medical_phrases",
                    "confidence": "very_high",
                    "hash": h,
                })

        log.info(f"Curated phrases: collected {len(pairs)} new pairs")
        return pairs


# ── Dataset Manager ───────────────────────────────────────────────────
class DatasetManager:
    """Merge, deduplicate, and export the final dataset."""

    def __init__(self):
        self.all_pairs = []

    def add(self, pairs: list[dict]):
        self.all_pairs.extend(pairs)

    def deduplicate(self):
        """Remove duplicate pairs based on hash."""
        seen = set()
        unique = []
        for p in self.all_pairs:
            h = p.get("hash", "")
            if h and h not in seen:
                seen.add(h)
                unique.append(p)
        removed = len(self.all_pairs) - len(unique)
        self.all_pairs = unique
        log.info(f"Deduplication: removed {removed} duplicates, {len(self.all_pairs)} unique pairs remain")

    def export_csv(self, path: Path, pair_type: str = "all"):
        """Export pairs to CSV."""
        os.makedirs(path.parent, exist_ok=True)
        pairs = self.all_pairs
        if pair_type != "all":
            pairs = [p for p in pairs if p.get("type") == pair_type]

        if not pairs:
            log.warning(f"No pairs to export for type={pair_type}")
            return

        fieldnames = ["en", "ar", "source", "type", "section", "confidence", "hash"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for p in pairs:
                writer.writerow({k: p.get(k, "") for k in fieldnames})

        log.info(f"Exported {len(pairs)} pairs to {path}")

    def export_jsonl(self, path: Path):
        """Export all pairs to JSONL."""
        os.makedirs(path.parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for p in self.all_pairs:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
        log.info(f"Exported {len(self.all_pairs)} pairs to {path}")

    def push_to_huggingface(self):
        """Push dataset to HuggingFace Hub."""
        token = os.environ.get("HF_TOKEN")
        if not token:
            log.warning("HF_TOKEN not set. Skipping HuggingFace upload.")
            log.info("To upload, set HF_TOKEN environment variable or add it to GitHub Secrets.")
            return False

        try:
            from huggingface_hub import HfApi, create_repo

            api = HfApi(token=token)

            # Create repo if it doesn't exist
            try:
                create_repo(
                    repo_id=HF_DATASET_ID,
                    token=token,
                    repo_type="dataset",
                    exist_ok=True,
                    private=False,
                )
                log.info(f"Created/confirmed HF dataset repo: {HF_DATASET_ID}")
            except Exception as e:
                log.error(f"Failed to create HF repo: {e}")
                return False

            # Upload data files
            data_dir = DATA_DIR
            files_to_upload = [
                data_dir / "all_pairs.jsonl",
                data_dir / "terms.csv",
                data_dir / "sentences.csv",
                DATA_DIR / "dataset_card.md",
            ]

            for fpath in files_to_upload:
                if fpath.exists():
                    api.upload_file(
                        path_or_fileobj=str(fpath),
                        path_in_repo=fpath.name,
                        repo_id=HF_DATASET_ID,
                        repo_type="dataset",
                        token=token,
                    )
                    log.info(f"Uploaded {fpath.name} to HF")

            # Upload cleaned glossary files
            for csv_name in ["cleaned_glossary.csv", "terms.csv", "sentences.csv", "section_headers.csv"]:
                src = CLEANED_DIR / csv_name
                if src.exists():
                    api.upload_file(
                        path_or_fileobj=str(src),
                        path_in_repo=f"cleaned/{csv_name}",
                        repo_id=HF_DATASET_ID,
                        repo_type="dataset",
                        token=token,
                    )
                    log.info(f"Uploaded cleaned/{csv_name} to HF")

            log.info(f"Successfully pushed dataset to https://huggingface.co/datasets/{HF_DATASET_ID}")
            return True

        except ImportError:
            log.warning("huggingface_hub not installed. Skipping HF upload.")
            return False
        except Exception as e:
            log.error(f"Failed to push to HuggingFace: {e}")
            return False


# ── Main Entry Point ──────────────────────────────────────────────────
def main():
    log.info("=" * 60)
    log.info("Bilingual Medical Glossary Collector - Starting")
    log.info(f"Timestamp: {datetime.now().isoformat()}")
    log.info("=" * 60)

    session = create_session()
    manager = DatasetManager()

    # Load existing cleaned data
    existing = load_existing_cleaned()
    seen_hashes = {p["hash"] for p in existing}
    manager.add(existing)

    # Source 1: WHO Essential Medicines (fast, no network needed)
    who = WHOCollector()
    manager.add(who.collect(seen_hashes))

    # Source 2: Curated Medical Phrases (fast, no network needed)
    phrases = MedicalPhrasesCollector()
    manager.add(phrases.collect(seen_hashes))

    # Source 3: Wikipedia/Wikidata (network, slower)
    try:
        wiki = WikipediaCollector(session)
        manager.add(wiki.collect(seen_hashes))
    except Exception as e:
        log.error(f"Wikipedia collection failed: {e}")

    # Source 4: MedlinePlus (network, slower)
    try:
        medline = MedlinePlusCollector(session)
        manager.add(medline.collect(seen_hashes))
    except Exception as e:
        log.error(f"MedlinePlus collection failed: {e}")

    # Deduplicate
    manager.deduplicate()

    # Export
    manager.export_jsonl(DATA_DIR / "all_pairs.jsonl")
    manager.export_csv(DATA_DIR / "all_pairs.csv", "all")
    manager.export_csv(DATA_DIR / "terms.csv", "term")
    manager.export_csv(DATA_DIR / "sentences.csv", "sentence")

    # Stats
    terms = [p for p in manager.all_pairs if p.get("type") == "term"]
    sentences = [p for p in manager.all_pairs if p.get("type") == "sentence"]
    sources = {}
    for p in manager.all_pairs:
        s = p.get("source", "unknown")
        sources[s] = sources.get(s, 0) + 1

    log.info("=" * 60)
    log.info("Collection Summary:")
    log.info(f"  Total pairs: {len(manager.all_pairs)}")
    log.info(f"  Terms: {len(terms)}")
    log.info(f"  Sentences: {len(sentences)}")
    log.info(f"  Sources: {json.dumps(sources, indent=4)}")
    log.info("=" * 60)

    # Push to HuggingFace
    hf_ok = manager.push_to_huggingface()
    if not hf_ok:
        log.info("Dataset saved locally. To push to HuggingFace:")
        log.info("  1. Create a token at https://huggingface.co/settings/tokens")
        log.info("  2. Set HF_TOKEN environment variable")
        log.info("  3. Re-run this script")

    log.info("Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())