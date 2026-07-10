#!/usr/bin/env python3
"""Quick local test - only WHO + Curated + Existing (no network)."""
import csv, json, os, re, sys, hashlib, time
from pathlib import Path
from datetime import datetime

REPO_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_DIR / "data"
CLEANED_DIR = REPO_DIR / "cleaned"
os.makedirs(DATA_DIR, exist_ok=True)

def is_arabic(t): return bool(re.search(r'[\u0600-\u06FF]', t))
def clean_text(t): return re.sub(r'\s+', ' ', t.replace('\u200f','').replace('\u200e','').strip())
def pair_hash(en, ar): return hashlib.md5(f"{en.lower().strip()}|||{ar.strip()}".encode()).hexdigest()[:12]

seen = set()
all_pairs = []

# 1) Load existing cleaned glossary
print("Loading existing cleaned glossary...")
csv_path = CLEANED_DIR / "cleaned_glossary.csv"
if csv_path.exists():
    with open(csv_path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            en, ar = clean_text(row.get("en","")), clean_text(row.get("ar",""))
            if en and ar and is_arabic(ar):
                h = pair_hash(en, ar)
                if h not in seen:
                    seen.add(h)
                    all_pairs.append({"en":en,"ar":ar,"source":row.get("source","hama_pharma_ocr"),"type":row.get("type","term"),"section":row.get("section",""),"confidence":row.get("confidence","medium"),"hash":h})
print(f"  Loaded {len(all_pairs)} pairs")

# 2) WHO Essential Medicines
WHO = {
"Acetylsalicylic acid":"حمض الأسيتيل ساليسيليك","Ibuprofen":"إيبوبروفين","Paracetamol":"باراسيتامول",
"Amoxicillin":"أموكسيسيلين","Azithromycin":"أزيثرومايسين","Ciprofloxacin":"سيبروفلوكساسين",
"Ceftriaxone":"سيفترياكسون","Metronidazole":"ميترونيدازول","Doxycycline":"دوكسي سيكلين",
"Diclofenac":"ديكلوفيناك","Tramadol":"ترامادول","Morphine":"مورفين","Diazepam":"ديازيبام",
"Lorazepam":"لورازيبام","Amlodipine":"أملوديبين","Enalapril":"إنالابريل","Losartan":"لوسارتان",
"Metformin":"ميتفورمين","Insulin":"إنسولين","Glibenclamide":"غليبنكلاميد","Glimepiride":"غليميبيريد",
"Omeprazole":"أوميبرازول","Pantoprazole":"بانتوبرازول","Prednisone":"بريدنيزون","Prednisolone":"بريدنيزولون",
"Dexamethasone":"ديكساميثازون","Hydrocortisone":"هيدروكورتيزون","Salbutamol":"سالبوتامول",
"Montelukast":"مونتيلوكاست","Cetirizine":"سيتيريزين","Loratadine":"لوراتادين","Furosemide":"فوروسيميد",
"Spironolactone":"سبيرونولاكتون","Warfarin":"وارفارين","Heparin":"هيبارين","Clopidogrel":"كلوبيدوغريل",
"Atorvastatin":"أتورفاستاتين","Simvastatin":"سيمفاستاتين","Phenytoin":"فينيتوين",
"Carbamazepine":"كاربامازيبين","Valproic acid":"حمض الفالبرويك","Phenobarbital":"فينوباربيتال",
"Clozapine":"كلوزابين","Haloperidol":"هالوبيريدول","Fluoxetine":"فلوكسيتين","Sertraline":"سيرترالين",
"Citalopram":"سيتالوبرام","Amitriptyline":"أميتريبتيلين","Levothyroxine":"ليفوثيروكسين",
"Alendronic acid":"حمض الأليندرونيك","Folic acid":"حمض الفوليك","Vitamin B12":"فيتامين ب12",
"Adrenaline":"أدرينالين","Atropine":"أتروبين","Dopamine":"دوبامين","Insulin glargine":"إنسولين غلارجين",
"Metoprolol":"ميتوبرولول","Aripiprazole":"أريبيبرازول","Olanzapine":"أولانزابين",
"Risperidone":"ريسبريدون","Quetiapine":"كيتيابين","Lithium carbonate":"كربونات الليثيوم",
"Clonazepam":"كلونازيبام","Alprazolam":"ألبرازولام","Ketotifen":"كيتوتيفين",
"Sumatriptan":"سوماتريبتان","Orlistat":"أورليستات","Alogliptin":"أالوغليبتين",
"Nortriptyline":"نورتريبتيلين","Agomelatine":"أغوميلاتين","Ofloxacin":"أوفلوكساسين",
"Cefotaxime":"سيفوتاكسيم","Gentamicin":"جنتاميسين","Vancomycin":"فانكومايسين",
"Fluconazole":"فلوكونازول","Acyclovir":"أسيكلوفير","Oseltamivir":"أوسيلتاميفير",
"Ivermectin":"إيفرميكتين","Albendazole":"ألبيندازول","Mebendazole":"ميبيندازول",
"Ranitidine":"رانيتيدين","Domperidone":"دومبيريدون","Ondansetron":"أوندانسيترون",
"Loperamide":"لوبراميد","Diltiazem":"ديلتيازيم","Nifedipine":"نيفيديبين",
"Captopril":"كابتوبريل","Hydrochlorothiazide":"هيدروكلوروثيازيد","Digoxin":"ديجوكسين",
"Dobutamine":"دوبوتامين","Nitroglycerin":"نيتروغليسرين","Enoxaparin":"إينوكسابارين",
"Chlorphenamine":"كلورفينامين","Diphenhydramine":"ديفينهيدرامين",
"Ipratropium bromide":"بروميد الإبراتروبيوم","Beclometasone":"بيكلوميثازون",
"Budesonide":"بوديسونيد","Fluticasone":"فلوتيكازون","Sodium cromoglicate":"كروموغليكات الصوديوم",
}
print("Adding WHO Essential Medicines...")
who_count = 0
for en, ar in WHO.items():
    h = pair_hash(en, ar)
    if h not in seen:
        seen.add(h)
        all_pairs.append({"en":en,"ar":ar,"source":"who_essential_medicines","type":"term","section":"pharmacology","confidence":"very_high","hash":h})
        who_count += 1
print(f"  Added {who_count} WHO terms")

# 3) Curated medical phrases
PHRASES = [
("Take one tablet three times a day after meals.","خذ قرصاً واحداً ثلاث مرات يومياً بعد الوجبات."),
("Take two tablets daily with water.","خذ قرصين يومياً مع الماء."),
("Store in a cool dry place below 25 degrees Celsius.","يحفظ في مكان بارد وجاف تحت 25 درجة مئوية."),
("Keep out of reach of children.","يحفظ بعيداً عن متناول الأطفال."),
("Do not exceed the recommended dose.","لا تتجاوز الجرعة الموصى بها."),
("Consult your doctor before use.","استشر طبيبك قبل الاستعمال."),
("Not recommended for use during pregnancy.","لا يوصى بالاستعمال أثناء الحمل."),
("Contraindicated in patients with known hypersensitivity.","مضاد استطباب عند المرضى الذين يعانون من فرط حساسية معروف."),
("May cause drowsiness. Do not drive or operate machinery.","قد يسبب النعاس. لا تقُد أو تشغل الآلات."),
("Discontinue use and consult a physician if adverse reactions occur.","أوقف الاستعمال واستشر الطبيب في حال حدوث تفاعلات ضارة."),
("For oral administration only.","للاستعمال الفموي فقط."),
("Shake well before use.","يرجّز جيداً قبل الاستعمال."),
("This medication should not be used after the expiry date.","لا يجب استعمال هذا الدواء بعد تاريخ انتهاء الصلاحية."),
("Seek immediate medical attention in case of overdose.","اطلب العناية الطبية فوراً في حالة الجرعة الزائدة."),
("Use with caution in patients with renal impairment.","يستعمل بحذر عند المرضى الذين يعانون من قصور كلوي."),
("Use with caution in patients with hepatic impairment.","يستعمل بحذر عند المرضى الذين يعانون من قصور كبدي."),
("Not recommended for children under 12 years of age.","لا يوصى به للأطفال تحت سن 12 عاماً."),
("Take on an empty stomach, 30 minutes before meals.","يؤخذ على معدة فارغة، 30 دقيقة قبل الوجبات."),
("Do not crush or chew the tablet. Swallow whole.","لا تسحق أو تمضغ القرص. ابتلعه كاملاً."),
("Each tablet contains:","كل قرص يحتوي على:"),
("Dosage form: Film-coated tablet","الشكل الصيدلاني: قرص مغلف بغشاء"),
("Side effects: Nausea, vomiting, abdominal pain.","الآثار الجانبية: غثيان، إقياء، ألم بطني."),
("Drug interactions: May increase the effect of anticoagulants.","التداخلات الدوائية: قد يزيد من تأثير مضادات التخثر."),
("Pharmacokinetics: Rapidly absorbed after oral administration.","الحرائك الدوائية: يمتص بسرعة بعد الإعطاء الفموي."),
("Mechanism of action: Inhibits cyclooxygenase enzyme.","آلية التأثير: يثبط إنزيم السيكلوأوكسيجيناز."),
("Half-life: approximately 6 hours.","عمر النصف: حوالي 6 ساعات."),
("Excreted mainly in urine.","يُفرز بشكل رئيسي في البول."),
("Contraindicated in patients with severe liver disease.","مضاد استطباب عند المرضى الذين يعانون من أمراض الكبد الشديدة."),
("Pregnancy category: Should be used only if clearly needed.","فئة الحمل: يُستعمل فقط في حال الضرورة القصوى."),
("Breastfeeding: Not recommended during lactation.","الرضاعة: لا يوصى به أثناء الإرضاع."),
("Treatment of essential hypertension.","علاج ارتفاع الضغط الشرياني الأساسي."),
("Management of type 2 diabetes mellitus.","علاج داء السكري النمط الثاني."),
("Antibiotic for the treatment of bacterial infections.","مضاد حيوي لعلاج الانتانات الجرثومية."),
("Anti-inflammatory and analgesic.","مضاد للالتهاب ومسكن."),
("Sedative and anxiolytic.","مهدئ ومضاد للقلق."),
("Antidepressant of the SSRI class.","مضاد اكتئاب من زمرة مثبطات استرداد السيروتونين الانتقائية."),
("Antipsychotic medication.","دواء مضاد للذهان."),
("Anticonvulsant for the treatment of epilepsy.","مضاد اختلاج لعلاج الصرع."),
("Bronchodilator for relief of bronchospasm.","موسع قصبات لتخفيف تشنج القصبات."),
("Diuretic for the management of edema.","مدر بول لعلاج الوذمة."),
("Anticoagulant for the prevention of thrombosis.","مضاد تخثر للوقاية من الخثرة."),
("Antiplatelet agent.","عامل مضاد للصفيحات."),
("Lipid-lowering agent.","عامل خافض للشحوم."),
("Thyroid hormone replacement therapy.","علاج بديل بهرمون الدرقية."),
("Iron supplement for treatment of iron deficiency anemia.","مكمل حديد لعلاج فقر الدم بعوز الحديد."),
("Antiemetic for prevention of nausea and vomiting.","مضاد إقياء للوقاية من الغثيان والإقياء."),
("Antispasmodic for relief of abdominal cramps.","مضاد تشنج لتخفيف التشنجات البطنية."),
("Topical antifungal cream.","كريم مضاد فطريات موضعي."),
("Nasal decongestant.","مزيل احتقان أنفي."),
("Cough suppressant.","مضاد سعال."),
("Expectorant.","مقشع."),
("Antihistamine for relief of allergy symptoms.","مضاد هيستامين لتخفيف أعراض الحساسية."),
("Proton pump inhibitor for treatment of gastric ulcer.","مثبط مضخة البروتون لعلاج القرحة المعدية."),
("Laxative for relief of constipation.","ملين لتخفيف الإمساك."),
("Antidiarrheal agent.","عامل مضاد للإسهال."),
("Oral antidiabetic agent.","عامل خافض للسكر فموي."),
("NSAID - Non-steroidal anti-inflammatory drug.","مضاد التهاب غير ستروئيدي."),
("Betalactam antibiotic.","مضاد حيوي بيتا لاكتامي."),
("Fluoroquinolone antibiotic.","مضاد حيوي فلوروكينولوني."),
("Macrolide antibiotic.","مضاد حيوي ماكروليدي."),
("Angiotensin converting enzyme inhibitor.","مثبط إنزيم تحويل الأنجيوتنسين."),
("Angiotensin II receptor blocker.","حاصر مستقبلات الأنجيوتنسين II."),
("Calcium channel blocker.","حاصر قنوات الكالسيوم."),
("Beta-adrenergic receptor blocker.","حاصر مستقبلات بيتا الأدرينالية."),
("Indications: Treatment of mild to moderate pain.","الاستطبابات: علاج الألم الخفيف إلى المتوسط."),
("Overdose symptoms: May include confusion, dizziness, nausea.","أعراض الجرعة الزائدة: قد تشمل التشوش، الدوخة، الغثيان."),
]
print("Adding curated medical phrases...")
ph_count = 0
for en, ar in PHRASES:
    h = pair_hash(en, ar)
    if h not in seen:
        seen.add(h)
        ptype = "sentence" if len(en.split()) > 5 else "term"
        all_pairs.append({"en":en,"ar":ar,"source":"curated_medical_phrases","type":ptype,"section":"medical_phrases","confidence":"very_high","hash":h})
        ph_count += 1
print(f"  Added {ph_count} phrases")

# Export
print(f"\nTotal: {len(all_pairs)} pairs")
terms = [p for p in all_pairs if p["type"]=="term"]
sentences = [p for p in all_pairs if p["type"]=="sentence"]
print(f"  Terms: {len(terms)}, Sentences: {len(sentences)}")

fields = ["en","ar","source","type","section","confidence","hash"]
for name, data in [("all_pairs.csv", all_pairs), ("terms.csv", terms), ("sentences.csv", sentences)]:
    with open(DATA_DIR / name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(data)
    print(f"  Saved {name} ({len(data)} rows)")

with open(DATA_DIR / "all_pairs.jsonl", "w", encoding="utf-8") as f:
    for p in all_pairs:
        f.write(json.dumps(p, ensure_ascii=False) + "\n")

# Stats
sources = {}
for p in all_pairs:
    s = p["source"]
    sources[s] = sources.get(s, 0) + 1
print(f"\nSources: {json.dumps(sources, indent=2)}")
print(f"Files saved to: {DATA_DIR}")
print("Done!")