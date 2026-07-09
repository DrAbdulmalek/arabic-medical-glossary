# أفكار ومصادر لجلب البيانات الثنائية اللغة (عربي-إنجليزي)

## مصادر ثنائية اللغة لتحميل أو إنشاء مسارد طبية

| **الموقع** | **الرابط** | **نوع المحتوى** | **طريقة الجلب** | **ملاحظات** |
|------------|------------|------------------|------------------|--------------|
| **مايوكلينيك (Arabic)** | [mayoclinic.org/arabic](https://www.mayoclinic.org/arabic) | مقالات طبية، مصطلحات، معلومات صحية | **API رسمي** (Bulk/Realtime) أو كشط | المحتوى متاح بالعربية والإنجليزية. [تفاصيل API هنا](https://gbs.mayoclinic.org/licensable-content/health-information.php) |
| **تبيب (Altibbi)** | [altibbi.com/mصطلحات-طبية](https://altibbi.com/%D9%85%D8%B5%D8%B7%D9%84%D8%AD%D8%A7%D8%AA-%D8%B7%D8%A8%D9%8A%D8%A9) | مصطلحات طبية مرتبة أبجديا (عربي-إنجليزي) | **كشط البيانات** | قائمة شاملة وسهلة التنظيم. |
| **قاموس طبي ثنائي اللغة (tbeeb.net)** | [tbeeb.net/medical-dictionary](https://www.tbeeb.net/medical-dictionary/) | ترجمة مصطلحات طبية (عربي-إنجليزي) | كشط البيانات | واجهة بسيطة للبحث عن مصطلحات. |
| **Almaany Medical Dictionary** | [almaany.com/medical](https://www.almaany.com/appendix.php?language=english&category=Medical) | فهرس مصطلحات طبية (إنجليزي-عربي) | كشط البيانات | شامل ومفهرس. |
| **موقع الترجمة الأول (translateonline.org)** | [translateonline.org/قاموس-طبي](https://translateonline.org/det.php?page=105&tit=%D9%82%D8%A7%D9%85%D9%88%D8%B3_%D8%B7%D8%A8%D9%8A_%D8%B9%D8%B1%D8%A8%D9%8A_%D8%A7%D9%86%D8%AC%D9%84%D9%8A%D8%B6%D9%8A) | قاموس طبي عربي-إنجليزي | كشط البيانات | يحتوي على شروحات مبسطة. |
| **Arabic Medical Terminology** | [arabmedicalterminology.com](https://arabmedicalterminology.com/) | مصطلحات طبية مع ترجمة فورية | كشط البيانات أو الاتصال بالموقع | متخصص في تعليم المصطلحات. |
| **MedlinePlus (NIH)** | [medlineplus.gov/arabic](https://medlineplus.gov/languages/arabic.html) | نصوص طبية ثنائية اللغة (PDF) | **تنزيل ملفات PDF** | يشمل كتيبات طبية (مثال: تطعيمات، أمراض). |
| **منظمة الصحة العالمية (WHO)** | [The Unified Medical Dictionary](https://apps.who.int/iris/handle/10665/119845) | قاموس طبي موحد (إنجليزي-عربي) | **تنزيل PDF (106.4 MB)** | [رابط مباشر للتحميل](https://apps.who.int/iris/bitstream/handle/10665/119845/dsa918.pdf) |
| **Hitti’s Medical Dictionary** | [archive.org/hitti-medical](https://archive.org/details/hittisnewmedical0000hitt) | كتاب 642 صفحة (إنجليزي-عربي + عربي-إنجليزي) | **تنزيل PDF** | شامل للمصطلحات والأختصار. |
| **Scribd** | [Arabic Medical Terms PDF](https://www.scribd.com/doc/182861843/ARABIC-MEDICAL-TERMS-IN-ENGLISH-pdf) | قائمة مصطلحات طبية (PDF) | تنزيل الملف | ملف جاهز للاستخدام. |

---

---

### **🛠 طرق جلب وإنشاء المسارد**
#### **1. استخدام API (إذا كان متاحًا)**
- **مايوكلينيك**: يوفر [API رسمي](https://gbs.mayoclinic.org/licensable-content/health-information.php) لجلب المحتوى الطبي (Bulk API وRealtime API).
  - **لغة API**: الإنجليزية.
  - **تغطية**: محتوى طبي شامل (مقالات، مصطلحات، معلومات صحية).
  - **خطوات**:
    1. تواصل مع [Mayo Clinic GBS](https://gbs.mayoclinic.org/) لطلب وصول إلى API.
    2. استخدم endpoints لجلب البيانات (مثال: `https://api.mayoclinic.org/health-information`).
    3. استخرج المصطلحات من البيانات المسترجعة.

#### **2. كشط البيانات (Web Scraping)**
- **أدوات موصى بها**:
  - **Python**: `BeautifulSoup` + `requests` (لمواقع ثابت HTML).
  - **Python**: `Scrapy` (لمواقع كبيرة أو معقدة).
  - **Node.js**: `Puppeteer` (لمواقع ديناميكية مثل JavaScript).
- **مثال لكشط مصطلحات من تبيب (Python)**:
  ```python
  import requests
  from bs4 import BeautifulSoup

  url = "https://altibbi.com/%D9%85%D8%B5%D8%B7%D9%84%D8%AD%D8%A7%D8%AA-%D8%B7%D8%A8%D9%8A%D8%A9"
  response = requests.get(url)
  soup = BeautifulSoup(response.text, 'html.parser')

  # استخراج المصطلحات (تعديل selector حسب هيكل الصفحة)
  terms = soup.select('.term-list li')  # مثال
  for term in terms:
      arabic = term.select('.arabic').text
      english = term.select('.english').text
      print(f"{arabic}: {english}")
  ```
- **ملاحظات**:
  - تحقق من **robots.txt** (مثال: `https://altibbi.com/robots.txt`) قبل الكشط.
  - احترام **شروط الاستخدام** (Rate Limiting، عدم إغراق الموقع).

#### **3. تنزيل ملفات PDF/Excel**
- **أدوات استخراج البيانات من PDF**:
  - **Python**: `PyPDF2` أو `pdfplumber` (لاستخراج النصوص).
  - **Excel**: `pandas` (للتنظيف وتنظيم البيانات).
- **مثال لاستخراج مصطلحات من PDF (Python)**:
  ```python
  import pdfplumber

  with pdfplumber.open("medical_terms.pdf") as pdf:
      for page in pdf.pages:
          text = page.extract_text()
          # استخدم regex أو تقسيم النصوص لاستخراج المصطلحات
          print(text)
  ```

#### **4. إنشاء مسارد يدويًا**
- **خطوات**:
  1. جمع المصطلحات من المواقع أو الملفات.
  2. تنظيمها في **Excel** أو **Google Sheets** (عمودين: عربي + إنجليزي).
  3. تصديرها إلى **CSV** أو **JSON** لاستخدامها في تطبيقاتك.
- **مثال تنسيق CSV**:
  ```
  arabic,english
  صداع,Headache
  سكر,Diabetes
  ضغط دم,Hypertension
  ```

---

---
---
### **⚠ تحذيرات مهمة**
1. **حقوق الملكية الفكرية**: بعض المواقع قد تمنع كشط البيانات. **اتصل بالموقع** للحصول على إذن إذا كان المحتوى محميًا.
2. **جودة البيانات**: قد تحتوي بعض المواقع على أخطاء في الترجمة. **راجع المصطلحات** مع مختصين طبية.
3. **APIs مدفوعة**: بعض APIs (مثل Mayo Clinic) قد تتطلب **دفع رسوم** للوصول الكامل.

---
---
### **📌 توصيات للبدء**
1. **للبيانات الجاهزة**:
   - حمّل **قاموس WHO الموحد** (PDF) من [هنا](https://apps.who.int/iris/bitstream/handle/10665/119845/dsa918.pdf).
   - استخدم ملف **Scribd** ([رابط](https://www.scribd.com/doc/182861843/ARABIC-MEDICAL-TERMS-IN-ENGLISH-pdf)).

2. **للأتمتة**:
   - كشط مصطلحات من **تبيب** أو **Almaany** باستخدام Python.
   - استخدم **Mayo Clinic API** إذا كنت بحاجة إلى محتوى موثوق ومحدث.

3. **للمصطلحات الصيدلانية**:
   - ابحث في **MedlinePlus** عن كتيبات الأدوية (مثال: [Vaccine Information Statements](https://medlineplus.gov/languages/arabic.html)).

---
---
### **🔗 روابط مباشرة للملفات الجاهزة**
- [قاموس WHO الموحد (PDF, 106.4 MB)](https://apps.who.int/iris/bitstream/handle/10665/119845/dsa918.pdf)
- [Arabic Medical Terms (Scribd, PDF)](https://www.scribd.com/doc/182861843/ARABIC-MEDICAL-TERMS-IN-ENGLISH-pdf)
- [Hitti’s Medical Dictionary (Internet Archive, PDF)](https://archive.org/details/hittisnewmedical0000hitt)

---
إذا كنت بحاجة إلى **كود جاهز** لكشط أحد هذه المواقع أو تنظيم البيانات، أخبرني لأعد لك مثالًا عمليًا!
**رابط تنزيل الملف مباشرة (PDF):**
📥 **[تنزيل Hitti's New Medical Dictionary (PDF, 1.3 GB)](https://archive.org/download/hittisnewmedical0000hitt/hittisnewmedical0000hitt.pdf)**

---

### **📌 روابط بديلة لتنزيل الملفات**
| **التنسيق** | **الرابط** | **الحجم** |
|-------------|------------|----------|
| **PDF** | [تنزيل](https://archive.org/download/hittisnewmedical0000hitt/hittisnewmedical0000hitt.pdf) | ~1.3 GB |
| **DJVU** | [تنزيل](https://archive.org/download/hittisnewmedical0000hitt/hittisnewmedical0000hitt.djvu) | أصغر حجمًا |
| **EPUB** | [تنزيل](https://archive.org/download/hittisnewmedical0000hitt/hittisnewmedical0000hitt.epub) | مناسب للقراءة الإلكترونية |
| **Text (NLP)** | [تنزيل](https://archive.org/download/hittisnewmedical0000hitt/hittisnewmedical0000hitt.txt) | نص عادي (لاستخراج البيانات) |

---
### **⚠ ملاحظات**
1. **الحجم كبير**: ملف PDF حجمه **1.3 GB** بسبب جودة المسح الضوئي العالية (360 DPI).
2. **بدائل أخف**: إذا كان الحجم كبيرًا، جرب **DJVU** أو **EPUB**.
3. **نص عادي**: إذا كنت تريد استخراج المصطلحات تلقائيًا، استخدم ملف **Text** أو استخرج النص من PDF باستخدام أدوات مثل `pdfplumber` (Python).

---
**هل تريد مساعدة في استخراج المصطلحات من الملف بعد تنزيله؟** (مثال: كود Python لاستخراج قائمة المصطلحات العربية-الإنجليزية)
بناءً على طلبك، قمت باستخراج الجمل والمصطلحات من الوثيقة المقدمة وتحويلها إلى مسرد وقاعدة بيانات ثنائية اللغة، مع الالتزام التام بالنص الوارد في الملف.
أولاً: المسرد الثنائي اللغة (الجمل المتقابلة)
يوضح الجدول التالي أهم الجمل الواردة في النص باللغتين الإنجليزية والعربية:
النص الإنجليزيالنص العربي المقابل 
Each film-coated tablet contains Agomelatine 25 mg.يحوي كل قرص ملبس بالفيلم على: أجوميلاتين ٢٥ ملغ. 
Agomelatine is a melatonergic agonist (MT1 and MT2 receptors) and 5-HT2C antagonist.أجوميلاتين هو شاد المستقبلات الميلاتونين MT1 و MT2 وضاد المستقبلات 5-HT2C. 
PRICKSAGE is used for the treatment of major depressive episodes in adults.يستخدم بريكسيج لمعالجة حوادث الاكتئاب الرئيسي عند البالغين. 
Hypersensitivity to the drug or its components.فرط التحس للمادة الفعالة أو أي من مكونات الدواء. 
Hepatic impairment (i.e. cirrhosis or active liver disease).لا يعطى الدواء للمرضى القصور الكبدي (المصابين بتشمع الكبد أو مرض كبدي نشط). 
The most common adverse reactions were nausea and dizziness.كانت ردود الفعل السلبية الأكثر شيوعا الغثيان والدوار. 
Agomelatine is not recommended in the treatment of depression in patients under 18 years of age.يجب عدم استعمال الدواء للمرضى الذين لم تتجاوز أعمارهم ١٨ سنة. 
Patients with depression should be treated for a sufficient period of at least 6 months.يجب أن تتم معالجة المصابين بالاكتئاب لفترة كافية من الزمن (٦ أشهر على الأقل). 
No dosage tapering is needed on treatment discontinuation.لا حاجة لتخفيض الجرعة عند التوقف عن العلاج. 
Store away from humidity and direct light, in a place of a temperature between 15 -30° C.يحفظ بعيدا عن الرطوبة والضوء المباشر في مكان لا تتجاوز حرارته ٣٠ درجة. 
ثانياً: قاعدة المصطلحات (قاموس المصطلحات)
تم استخراج هذه المصطلحات مباشرة من نص النشرة الدوائية:
المصطلحات بالإنجليزيةالمصطلحات بالعربية 
Agomelatineأجوميلاتين 
Film-Coated Tabletsأقراص ملبسة بالفيلم 
Hepatic impairmentاعتلال كبدي / قصور كبدي 
Renal impairmentاعتلال كلوي 
Contraindicationsمضادات الاستطبابات 
Side Effectsالتأثيرات الجانبية / ردود الفعل السلبية 
Major depressive episodesنوبات الاكتئاب الكبرى / حوادث الاكتئاب الرئيسي 
Suicidal thoughtsأفكار انتحارية 
Pharmacokineticsالحرائك الدوائية 
Bioavailabilityالتوافر الحيوي 
Hepatic failureفشل كبدي 
Dosage and Administrationالجرعة وطريقة الاستعمال 
Excipientsالسواغات 
Mechanism of actionآلية التأثير 
Overdosage/Toxicityفرط الجرعة / السمية
لقد قمت بالبحث في الموقع واستطعت الوصول إلى ملفات PDF الخاصة بالنشرات الدوائية. كنموذج أولي، قمت باستخراج محتوى ملف **Phenobarbital** وتحويله إلى المساردين المطلوبين تماماً كما طلبت:

### أولاً: المسرد الأساسي للنشرة الدوائية
| النص الإنجليزي | النص العربي المقابل |
|---|---|
| Phenobarbital 15, 30, 60, 100 mg (TABLETS) | فينوباربيتال ١٥، ٣٠، ٦٠، ١٠٠ ملغ (أقراص) |
| COMPOSITION: Each tablet contains: 15 mg, 30 mg, 60 mg or 100 mg of phenobarbital. | التركيب: يحوي كل قرص على: ١٥ أو ٣٠ أو ٦٠ أو ١٠٠ ملغ فينوباربيتال. |
| EXCIPIENTS: Calcium stearate, Corn starch, Anhydrous lactose, Magnesium stearate, Colloidal silicon dioxide, Microcrystalline cellulose, Sodium starch glycolate, Sodium docusate, Lactose monohydrate. | السواغات: ستيترات الكالسيوم، نشاء الذرة، لاكتوز لامائي، ستيترات المغنيسيوم، ثاني أوكسيد السيليكون الغرويدي، ميكروكريستالين سللوز، غليكوات النشاء الصودية، صوديوم دوكوسات، لاكتوز مونوهيدرات. |
| MECHANISM OF ACTION: Phenobarbital, a long-acting barbiturate, is a central nervous system depressant. In ordinary doses, the drug acts as a sedative and anticonvulsant. | آلية التأثير: فينوباربيتال مركب باربيتوري طويل المفعول مثبط للجملة العصبية المركزية. بالجرعات العادية، يعمل فينوباربيتال كمهدئ ومضاد للاختلاج. |
| PHARMACOKINETICS: Its onset of action occurs within 30 minutes, and the duration of action ranges from 5 to 6 hours. It is detoxified in the liver. | الحركية الدوائية: يبدأ عمل فينوباربيتال خلال ٣٠ دقيقة، ويستمر لفترة تتراوح بين ٥ إلى ٦ ساعات. يتم إزالة سميته في الكبد. |
| INDICATIONS: Phenobarbital Hama Pharma is indicated for use as a sedative or anticonvulsant. | الاستطبابات: يستخدم فينوباربيتال حماة فارما كمهدئ أو مضاد للاختلاج. |
| CONTRAINDICATIONS: Phenobarbital Hama Pharma is contraindicated in patients who are hypersensitive to barbiturates. | مضادات الاستطباب: يجب عدم استخدام فينوباربيتال حماة فارما في المرضى المعروفين بفرط الحساسية للباربيتورات. |
| SIDE EFFECTS: CNS Depression: Sedation, drowsiness, lethargy, and vertigo. | التأثيرات الجانبية: تثبيط الجهاز العصبي المركزي: تهدئة، نعاس، خمول، ودوار. |
| DOSAGE AND ADMINISTRATION: Oral Sedative Dose: Adults – 30 to 120 mg daily in 2 or 3 divided doses. | الجرعة وطريقة الاستعمال: الجرعة الفموية المهدئة: البالغين – ٣٠ إلى ١٢٠ ملغ يومياً على ٢ أو ٣ جرعات مقسمة. |
| OVERDOSE: The signs and symptoms of barbiturate poisoning are referable especially to the central nervous system and the cardiovascular system. | حالات فرط الجرعة: تتجلى أعراض التسمم بالباربيتورات خاصة في الجملة العصبية المركزية وفي الجملة القلبية الوعائية. |
| PRESENTATION: 3 Blisters, each contains 10 tablets of Phenobarbital Hama Pharma-15 mg. | التعبئة: ٣ أشرطة، كل شريط يحوي ١٠ أقراص من فينوباربيتال حماة فارما-١٥ ملغ. |
| STORAGE: Store at room temperature, between 20°-25°C, away from moisture and light. Keep out of reach of children. | شروط الحفظ: يحفظ في درجة حرارة الغرفة، بين ٢٠°-٢٥°، بعيداً عن الرطوبة والضوء. يحفظ بعيداً عن متناول الأطفال. |

### ثانياً: قاعدة المصطلحات (المفردات)
| المصطلح الإنجليزي | المصطلح العربي |
|---|---|
| Phenobarbital | فينوباربيتال |
| Tablets | أقراص |
| Composition | التركيب |
| Excipients | السواغات |
| Calcium stearate | ستيترات الكالسيوم |
| Corn starch | نشاء الذرة |
| Anhydrous lactose | لاكتوز لامائي |
| Magnesium stearate | ستيترات المغنيسيوم |
| Colloidal silicon dioxide | ثاني أوكسيد السيليكون الغرويدي |
| Microcrystalline cellulose | ميكروكريستالين سللوز |
| Sodium starch glycolate | غليكوات النشاء الصودية |
| Sodium docusate | صوديوم دوكوسات |
| Lactose monohydrate | لاكتوز مونوهيدرات |
| Mechanism of action | آلية التأثير |
| Long-acting barbiturate | مركب باربيتوري طويل المفعول |
| Central nervous system depressant | مثبط للجملة العصبية المركزية |
| Sedative | مهدئ |
| Anticonvulsant | مضاد للاختلاج |
| Pharmacokinetics | الحركية الدوائية |
| Onset of action | بداية التأثير |
| Duration of action | مدة التأثير |
| Liver | الكبد |
| Indications | الاستطبابات |
| Contraindications | مضادات الاستطباب |
| Hypersensitive | فرط الحساسية |
| Side effects | التأثيرات الجانبية |
| CNS Depression | تثبيط الجهاز العصبي المركزي |
| Sedation | تهدئة |
| Drowsiness | نعاس |
| Lethargy | خمول |
| Vertigo | دوار |
| Dosage and Administration | الجرعة وطريقة الاستعمال |
| Overdose | فرط الجرعة |
| Barbiturate poisoning | التسمم بالباربيتورات |
| Cardiovascular system | الجملة القلبية الوعائية |
| Presentation | التعبئة |
| Blisters | أشرطة بليستر |
| Storage | شروط الحفظ |
| Room temperature | درجة حرارة الغرفة |
| Moisture | الرطوبة |

---

الآن، بما أن الموقع يحتوي على عشرات الملفات الأخرى (مثل Linavus, Nivoltic, Triosar, Muler، وغيرها)، ولا يمكنني تحميلها وتحويلها جميعاً بشكل يدوي هنا، **كيف تظن أنه يمكننا أتمتة هذه العملية لاستخراج وتحويل جميع الملفات دفعة واحدة على جهازك الذي يعمل بنظام Linux Manjaro؟**

وما هي المكتبات البرمجية التي تفضل استخدامها في أكواد Python الخاصة بك لقراءة ملفات PDF واستخراج النصوص ثنائية اللغة (العربية والإنجليزية) منها بدقة؟ وهل تفضل استخدام مكتبات مثل `pdfplumber` أو `PyMuPDF` لمعالجة النصوص محلياً (Offline) لتجنب مشاكل الاتصال بالإنترنت؟
بالنسبة لـ **Mayo Clinic**، فهو موقع طبي أمريكي مرموق، لكنه **ليس ثنائي اللغة** بشكل رسمي. الموقع الأساسي باللغة الإنجليزية فقط، ولا يوفر نسخة عربية شاملة يمكن استخراج مسارد منها بشكل منهجي.

لكن من خلال بحثي، وجدت **مصادر طبية ثنائية اللغة ممتازة** يمكن استخراج مسارد منها:

### 1. **المعجم الطبي الموحد (UMD) - منظمة الصحة العالمية**
هذا هو **المصدر الذهبي** للمسارد الطبية ثنائية اللغة!
- متوفر بعدة صيغ: PDF, Excel, قاعدة بيانات [[19]], [[24]]
- يغطي آلاف المصطلحات الطبية بالإنجليزية والعربية (والفرنسية) [[24]]
- معيار معتمد من WHO للمنطقة الشرقية [[21]]
- يمكنك تحميله من: `https://umd.emro.who.int/WHODictionary/` [[19]]

### 2. **MedDRA - المعجم الطبي للأنشطة التنظيمية**
- قاموس طبي دولي معتمد [[13]]
- متوفر بالعربية والإنجليزية [[13]]
- يستخدم في التسجيل الدوائي والسلامة الدوائية
- متوفر كـ PDF من الموقع الرسمي [[13]]

### 3. **مواقع عربية مع محتوى طبي**
- **Altibbi (الطبي)**: أكبر منصة طبية عربية [[3]]
- **WebTeb (ويب طب)**: موقع صحي عربي كبير [[34]]
- **tbeeb.net**: قاموس طبي ثنائي اللغة [[14]]

### 4. **ملفات PDF جاهزة**
- المعجم الطبي الموحد (Khayat) على Archive.org [[15]]
- قواميس مصطلحات طبية من جامعات ومستشفيات [[16]], [[22]]

---

**الآن، كيف تريد المتابعة؟**

1. هل تريد أن أبني سكريبت Python لتحميل **المعجم الطبي الموحد (UMD)** من WHO وتحويله إلى TSV جاهز للتدريب؟
2. أم تفضل أن أبحث في مواقع شركات الأدوية العربية (مثل Hama Pharma, Ibn Al-Haytham, etc.) لاستخراج النشرات الدوائية ثنائية اللغة؟
3. أم لديك ملفات PDF طبية معينة تريد معالجتها محلياً على جهازك؟

وما هي المكتبات التي تفضل استخدامها لقراءة PDF على Linux Manjaro: `pdfplumber`, `PyMuPDF`, أم `pdfminer`؟
ممتاز! وجدت مصادر قيمة. دعني أبني لك سكريبت Python شامل يعمل على **Linux Manjaro** يقوم بكلا الخيارين:


## مصادر إضافية ممتازة


بالإضافة للسكريبت، إليك **مصادر طبية ثنائية اللغة جاهزة**:

### 1. **MedlinePlus - المكتبة الوطنية الأمريكية للطب** [[12]]
- رابط: `https://medlineplus.gov/languages/arabic.html`
- يحتوي على ملفات PDF ثنائية اللغة (عربي/إنجليزي)
- مجاني ومفتوح للاستخدام

### 2. **WHO IRIS - المستودع الرسمي** [[20]]
- رابط: `https://iris.who.int/handle/10665/119845`
- المعجم الطبي الموحد بصيغ متعددة

### 3. **Archive.org - المعجم الطبي الكامل** [[6]]
- رابط: `https://archive.org/details/umdwho`
- حجم: 1.6 GB
- يحتوي على المعجم الطبي الموحد كاملاً

---

## 🎯 الخطوات التالية