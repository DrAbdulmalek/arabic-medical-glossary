"""
Collect medical terms from ICF (International Classification of Functioning, Disability and Health).
Developed by WHO to provide a unified and standard language for functioning and disability.

⚠️ ملاحظة:
ICF لا يوفر REST API مباشر. يجب تحميل ملفات من:
https://www.who.int/standards/classifications/international-classification-of-functioning-disability-and-health

يتطلب حساباً مسجلاً (مجاني) للوصول للملفات.

هذا المجمع يدعم:
1. قراءة ملف CSV/Excel محلي
2. إنشاء بيانات نموظية للاختبار
"""

import os
import json
from collectors.base import BaseCollector, TermEntry


class ICFCollector(BaseCollector):
    """
    مجمع مصطلحات من ICF (WHO)
    يتطلب تحميل ملف يدوي
    """

    def __init__(self, config: dict = None):
        super().__init__(
            "ICF",
            "https://www.who.int/standards/classifications/international-classification-of-functioning-disability-and-health",
            config
        )

        self.download_dir = os.path.join("data", "icf")
        self.local_json = os.path.join(self.download_dir, "icf_index.json")
        os.makedirs(self.download_dir, exist_ok=True)

    def collect(self) -> int:
        """
        جمع المصطلحات من ICF
        يحاول قراءة ملف محلي ثم يحاول إنشاء بيانات نموظية
        """
        new_count = 0

        # محاولة 1: قراءة ملف JSON محلي
        if os.path.exists(self.local_json):
            self.logger.info("📄 تم العثور على ملف JSON محلي")
            new_count = self._parse_json_file()
            return new_count

        # محاولة 2: إنشاء بيانات نموظية
        self.logger.warning(
            "⚠️ لم يتم العثور على ملف ICF.\n"
            "الرجاء:\n"
            "1. التسجيل في https://www.who.int/standards/classifications/\n"
            "2. تحميل ملف ICF (CSV/Excel)\n"
            "3. وضعه في data/icf/\n"
            "4. أو استخدام create_sample_data()"
        )

        return 0

    def _parse_json_file(self) -> int:
        """قراءة ملف JSON محلي"""
        new_count = 0

        try:
            with open(self.local_json, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for item in data:
                code = item.get("code", "")
                title = item.get("title", "")
                domain = item.get("domain", "")

                if not code or not title:
                    continue

                entry = TermEntry(
                    term=title,
                    definition=f"ICF Code: {code} ({domain})",
                    source="ICF",
                    language="en",
                    confidence=0.95,
                    tags=["icf", code, domain.lower().replace(" ", "_")]
                )

                if self.add_term(entry):
                    new_count += 1

            self.logger.info(f"✅ ICF JSON: {new_count} مصطلح")

        except Exception as e:
            self.logger.error(f"❌ خطأ في قراءة JSON: {e}")

        return new_count

    def create_sample_data(self) -> int:
        """
        إنشاء بيانات نموظية للاختبار
        """
        sample_data = [
            # Body Functions (b)
            {"code": "b1", "title": "Mental functions", "domain": "Body Functions"},
            {"code": "b110", "title": "Consciousness functions", "domain": "Body Functions"},
            {"code": "b114", "title": "Orientation functions", "domain": "Body Functions"},
            {"code": "b117", "title": "Intellectual functions", "domain": "Body Functions"},
            {"code": "b122", "title": "Global psychosocial functions", "domain": "Body Functions"},
            {"code": "b126", "title": "Temperament and personality functions", "domain": "Body Functions"},
            {"code": "b130", "title": "Energy and drive functions", "domain": "Body Functions"},
            {"code": "b134", "title": "Sleep functions", "domain": "Body Functions"},
            {"code": "b140", "title": "Attention functions", "domain": "Body Functions"},
            {"code": "b144", "title": "Memory functions", "domain": "Body Functions"},
            {"code": "b152", "title": "Emotional functions", "domain": "Body Functions"},
            {"code": "b156", "title": "Perceptual functions", "domain": "Body Functions"},
            {"code": "b160", "title": "Thought functions", "domain": "Body Functions"},
            {"code": "b164", "title": "Higher-level cognitive functions", "domain": "Body Functions"},
            {"code": "b167", "title": "Mental functions of language", "domain": "Body Functions"},
            {"code": "b172", "title": "Calculation functions", "domain": "Body Functions"},
            {"code": "b176", "title": "Mental function of sequencing complex movements", "domain": "Body Functions"},
            {"code": "b180", "title": "Experience of self and time functions", "domain": "Body Functions"},
            {"code": "b2", "title": "Sensory functions and pain", "domain": "Body Functions"},
            {"code": "b210", "title": "Seeing functions", "domain": "Body Functions"},
            {"code": "b230", "title": "Hearing functions", "domain": "Body Functions"},
            {"code": "b235", "title": "Vestibular functions", "domain": "Body Functions"},
            {"code": "b255", "title": "Temperature and other sensory functions", "domain": "Body Functions"},
            {"code": "b260", "title": "Proprioceptive function", "domain": "Body Functions"},
            {"code": "b265", "title": "Touch function", "domain": "Body Functions"},
            {"code": "b280", "title": "Pain", "domain": "Body Functions"},
            {"code": "b3", "title": "Voice and speech functions", "domain": "Body Functions"},
            {"code": "b310", "title": "Voice functions", "domain": "Body Functions"},
            {"code": "b320", "title": "Articulation functions", "domain": "Body Functions"},
            {"code": "b330", "title": "Fluency and rhythm of speech functions", "domain": "Body Functions"},
            {"code": "b4", "title": "Functions of the cardiovascular, haematological, immunological and respiratory systems", "domain": "Body Functions"},
            {"code": "b410", "title": "Heart functions", "domain": "Body Functions"},
            {"code": "b420", "title": "Blood pressure functions", "domain": "Body Functions"},
            {"code": "b430", "title": "Haematological system functions", "domain": "Body Functions"},
            {"code": "b435", "title": "Immunological system functions", "domain": "Body Functions"},
            {"code": "b440", "title": "Respiration functions", "domain": "Body Functions"},
            {"code": "b5", "title": "Functions of the digestive, metabolic and endocrine systems", "domain": "Body Functions"},
            {"code": "b510", "title": "Ingestion functions", "domain": "Body Functions"},
            {"code": "b520", "title": "Assimilation functions", "domain": "Body Functions"},
            {"code": "b530", "title": "Weight maintenance functions", "domain": "Body Functions"},
            {"code": "b540", "title": "General metabolic functions", "domain": "Body Functions"},
            {"code": "b555", "title": "Endocrine gland functions", "domain": "Body Functions"},
            {"code": "b6", "title": "Genitourinary and reproductive functions", "domain": "Body Functions"},
            {"code": "b620", "title": "Urination functions", "domain": "Body Functions"},
            {"code": "b640", "title": "Sexual functions", "domain": "Body Functions"},
            {"code": "b7", "title": "Neuromusculoskeletal and movement-related functions", "domain": "Body Functions"},
            {"code": "b710", "title": "Mobility of joint functions", "domain": "Body Functions"},
            {"code": "b730", "title": "Muscle power functions", "domain": "Body Functions"},
            {"code": "b740", "title": "Muscle endurance functions", "domain": "Body Functions"},
            {"code": "b750", "title": "Motor reflex functions", "domain": "Body Functions"},
            {"code": "b760", "title": "Control of voluntary movement functions", "domain": "Body Functions"},
            {"code": "b770", "title": "Gait pattern functions", "domain": "Body Functions"},
            {"code": "b8", "title": "Functions of the skin and related structures", "domain": "Body Functions"},
            {"code": "b810", "title": "Protective functions of the skin", "domain": "Body Functions"},
            {"code": "b820", "title": "Repair functions of the skin", "domain": "Body Functions"},
            {"code": "b830", "title": "Sensation related to the skin", "domain": "Body Functions"},
            # Activities and Participation (d)
            {"code": "d1", "title": "Learning and applying knowledge", "domain": "Activities and Participation"},
            {"code": "d110", "title": "Watching", "domain": "Activities and Participation"},
            {"code": "d115", "title": "Listening", "domain": "Activities and Participation"},
            {"code": "d120", "title": "Other purposeful sensing", "domain": "Activities and Participation"},
            {"code": "d130", "title": "Copying", "domain": "Activities and Participation"},
            {"code": "d135", "title": "Rehearsing", "domain": "Activities and Participation"},
            {"code": "d140", "title": "Learning to read", "domain": "Activities and Participation"},
            {"code": "d145", "title": "Learning to write", "domain": "Activities and Participation"},
            {"code": "d150", "title": "Learning to calculate", "domain": "Activities and Participation"},
            {"code": "d155", "title": "Acquiring skills", "domain": "Activities and Participation"},
            {"code": "d160", "title": "Focusing attention", "domain": "Activities and Participation"},
            {"code": "d163", "title": "Thinking", "domain": "Activities and Participation"},
            {"code": "d166", "title": "Reading", "domain": "Activities and Participation"},
            {"code": "d170", "title": "Writing", "domain": "Activities and Participation"},
            {"code": "d172", "title": "Calculating", "domain": "Activities and Participation"},
            {"code": "d175", "title": "Solving problems", "domain": "Activities and Participation"},
            {"code": "d177", "title": "Making decisions", "domain": "Activities and Participation"},
            {"code": "d2", "title": "General tasks and demands", "domain": "Activities and Participation"},
            {"code": "d210", "title": "Undertaking a single task", "domain": "Activities and Participation"},
            {"code": "d220", "title": "Undertaking multiple tasks", "domain": "Activities and Participation"},
            {"code": "d230", "title": "Carrying out daily routine", "domain": "Activities and Participation"},
            {"code": "d240", "title": "Handling stress and other psychological demands", "domain": "Activities and Participation"},
            {"code": "d3", "title": "Communication", "domain": "Activities and Participation"},
            {"code": "d310", "title": "Communicating with - receiving - spoken messages", "domain": "Activities and Participation"},
            {"code": "d315", "title": "Communicating with - receiving - nonverbal messages", "domain": "Activities and Participation"},
            {"code": "d320", "title": "Communicating with - receiving - formal sign language messages", "domain": "Activities and Participation"},
            {"code": "d325", "title": "Communicating with - receiving - written messages", "domain": "Activities and Participation"},
            {"code": "d330", "title": "Speaking", "domain": "Activities and Participation"},
            {"code": "d335", "title": "Producing nonverbal messages", "domain": "Activities and Participation"},
            {"code": "d340", "title": "Producing formal sign language messages", "domain": "Activities and Participation"},
            {"code": "d345", "title": "Writing messages", "domain": "Activities and Participation"},
            {"code": "d350", "title": "Conversation", "domain": "Activities and Participation"},
            {"code": "d355", "title": "Discussion", "domain": "Activities and Participation"},
            {"code": "d360", "title": "Using communication devices and techniques", "domain": "Activities and Participation"},
            {"code": "d4", "title": "Mobility", "domain": "Activities and Participation"},
            {"code": "d410", "title": "Changing basic body position", "domain": "Activities and Participation"},
            {"code": "d415", "title": "Maintaining a body position", "domain": "Activities and Participation"},
            {"code": "d420", "title": "Transferring oneself", "domain": "Activities and Participation"},
            {"code": "d430", "title": "Lifting and carrying objects", "domain": "Activities and Participation"},
            {"code": "d435", "title": "Moving objects with lower extremities", "domain": "Activities and Participation"},
            {"code": "d440", "title": "Fine hand use", "domain": "Activities and Participation"},
            {"code": "d445", "title": "Hand and arm use", "domain": "Activities and Participation"},
            {"code": "d450", "title": "Walking", "domain": "Activities and Participation"},
            {"code": "d455", "title": "Moving around", "domain": "Activities and Participation"},
            {"code": "d460", "title": "Moving around in different locations", "domain": "Activities and Participation"},
            {"code": "d465", "title": "Moving around using equipment", "domain": "Activities and Participation"},
            {"code": "d470", "title": "Using transportation", "domain": "Activities and Participation"},
            {"code": "d475", "title": "Driving", "domain": "Activities and Participation"},
            {"code": "d5", "title": "Self-care", "domain": "Activities and Participation"},
            {"code": "d510", "title": "Washing oneself", "domain": "Activities and Participation"},
            {"code": "d520", "title": "Caring for body parts", "domain": "Activities and Participation"},
            {"code": "d530", "title": "Toileting", "domain": "Activities and Participation"},
            {"code": "d540", "title": "Dressing", "domain": "Activities and Participation"},
            {"code": "d550", "title": "Eating", "domain": "Activities and Participation"},
            {"code": "d560", "title": "Drinking", "domain": "Activities and Participation"},
            {"code": "d570", "title": "Looking after one's health", "domain": "Activities and Participation"},
            {"code": "d6", "title": "Domestic life", "domain": "Activities and Participation"},
            {"code": "d610", "title": "Acquiring a place to live", "domain": "Activities and Participation"},
            {"code": "d620", "title": "Acquisition of goods and services", "domain": "Activities and Participation"},
            {"code": "d630", "title": "Preparing meals", "domain": "Activities and Participation"},
            {"code": "d640", "title": "Doing housework", "domain": "Activities and Participation"},
            {"code": "d650", "title": "Caring for household objects", "domain": "Activities and Participation"},
            {"code": "d660", "title": "Assisting others", "domain": "Activities and Participation"},
            {"code": "d7", "title": "Interpersonal interactions and relationships", "domain": "Activities and Participation"},
            {"code": "d710", "title": "Basic interpersonal interactions", "domain": "Activities and Participation"},
            {"code": "d720", "title": "Complex interpersonal interactions", "domain": "Activities and Participation"},
            {"code": "d730", "title": "Relating with strangers", "domain": "Activities and Participation"},
            {"code": "d740", "title": "Formal relationships", "domain": "Activities and Participation"},
            {"code": "d750", "title": "Informal social relationships", "domain": "Activities and Participation"},
            {"code": "d760", "title": "Family relationships", "domain": "Activities and Participation"},
            {"code": "d770", "title": "Intimate relationships", "domain": "Activities and Participation"},
            {"code": "d8", "title": "Major life areas", "domain": "Activities and Participation"},
            {"code": "d810", "title": "Informal education", "domain": "Activities and Participation"},
            {"code": "d815", "title": "Preschool education", "domain": "Activities and Participation"},
            {"code": "d820", "title": "School education", "domain": "Activities and Participation"},
            {"code": "d825", "title": "Vocational training", "domain": "Activities and Participation"},
            {"code": "d830", "title": "Higher education", "domain": "Activities and Participation"},
            {"code": "d835", "title": "Remunerative employment", "domain": "Activities and Participation"},
            {"code": "d840", "title": "Apprenticeship", "domain": "Activities and Participation"},
            {"code": "d845", "title": "Acquiring, keeping and terminating a job", "domain": "Activities and Participation"},
            {"code": "d850", "title": "Remunerative work", "domain": "Activities and Participation"},
            {"code": "d855", "title": "Non-remunerative employment", "domain": "Activities and Participation"},
            {"code": "d860", "title": "Basic economic transactions", "domain": "Activities and Participation"},
            {"code": "d865", "title": "Complex economic transactions", "domain": "Activities and Participation"},
            {"code": "d870", "title": "Economic self-sufficiency", "domain": "Activities and Participation"},
            {"code": "d9", "title": "Community, social and civic life", "domain": "Activities and Participation"},
            {"code": "d910", "title": "Community life", "domain": "Activities and Participation"},
            {"code": "d920", "title": "Recreation and leisure", "domain": "Activities and Participation"},
            {"code": "d930", "title": "Religion and spirituality", "domain": "Activities and Participation"},
            {"code": "d940", "title": "Human rights", "domain": "Activities and Participation"},
            {"code": "d950", "title": "Political life and citizenship", "domain": "Activities and Participation"},
            # Environmental Factors (e)
            {"code": "e1", "title": "Products and technology", "domain": "Environmental Factors"},
            {"code": "e110", "title": "Products for personal consumption", "domain": "Environmental Factors"},
            {"code": "e115", "title": "Products for personal use in daily living", "domain": "Environmental Factors"},
            {"code": "e120", "title": "Products for personal indoor and outdoor mobility and transportation", "domain": "Environmental Factors"},
            {"code": "e125", "title": "Products for communication", "domain": "Environmental Factors"},
            {"code": "e130", "title": "Products for education", "domain": "Environmental Factors"},
            {"code": "e135", "title": "Products for employment", "domain": "Environmental Factors"},
            {"code": "e140", "title": "Products for culture, recreation and sport", "domain": "Environmental Factors"},
            {"code": "e150", "title": "Design, construction and building products and technology of buildings for public use", "domain": "Environmental Factors"},
            {"code": "e155", "title": "Design, construction and building products and technology of buildings for private use", "domain": "Environmental Factors"},
            {"code": "e160", "title": "Products and technology of land development", "domain": "Environmental Factors"},
            {"code": "e2", "title": "Natural environment and human-made changes to environment", "domain": "Environmental Factors"},
            {"code": "e210", "title": "Physical geography", "domain": "Environmental Factors"},
            {"code": "e215", "title": "Population", "domain": "Environmental Factors"},
            {"code": "e220", "title": "Flora and fauna", "domain": "Environmental Factors"},
            {"code": "e225", "title": "Climate", "domain": "Environmental Factors"},
            {"code": "e230", "title": "Natural events", "domain": "Environmental Factors"},
            {"code": "e235", "title": "Human-caused events", "domain": "Environmental Factors"},
            {"code": "e240", "title": "Light", "domain": "Environmental Factors"},
            {"code": "e245", "title": "Time-related changes", "domain": "Environmental Factors"},
            {"code": "e250", "title": "Sound", "domain": "Environmental Factors"},
            {"code": "e255", "title": "Vibration", "domain": "Environmental Factors"},
            {"code": "e260", "title": "Air quality", "domain": "Environmental Factors"},
            {"code": "e3", "title": "Support and relationships", "domain": "Environmental Factors"},
            {"code": "e310", "title": "Immediate family", "domain": "Environmental Factors"},
            {"code": "e315", "title": "Extended family", "domain": "Environmental Factors"},
            {"code": "e320", "title": "Friends", "domain": "Environmental Factors"},
            {"code": "e325", "title": "Acquaintances, peers, colleagues, neighbours and community members", "domain": "Environmental Factors"},
            {"code": "e330", "title": "People in positions of authority", "domain": "Environmental Factors"},
            {"code": "e335", "title": "People in subordinate positions", "domain": "Environmental Factors"},
            {"code": "e340", "title": "Personal care providers and personal assistants", "domain": "Environmental Factors"},
            {"code": "e345", "title": "Strangers", "domain": "Environmental Factors"},
            {"code": "e350", "title": "Domesticated animals", "domain": "Environmental Factors"},
            {"code": "e355", "title": "Health professionals", "domain": "Environmental Factors"},
            {"code": "e360", "title": "Other professionals", "domain": "Environmental Factors"},
            {"code": "e4", "title": "Attitudes", "domain": "Environmental Factors"},
            {"code": "e410", "title": "Individual attitudes of immediate family members", "domain": "Environmental Factors"},
            {"code": "e415", "title": "Individual attitudes of extended family members", "domain": "Environmental Factors"},
            {"code": "e420", "title": "Individual attitudes of friends", "domain": "Environmental Factors"},
            {"code": "e425", "title": "Individual attitudes of acquaintances, peers, colleagues, neighbours and community members", "domain": "Environmental Factors"},
            {"code": "e430", "title": "Individual attitudes of people in positions of authority", "domain": "Environmental Factors"},
            {"code": "e435", "title": "Individual attitudes of people in subordinate positions", "domain": "Environmental Factors"},
            {"code": "e440", "title": "Individual attitudes of personal care providers and personal assistants", "domain": "Environmental Factors"},
            {"code": "e445", "title": "Individual attitudes of strangers", "domain": "Environmental Factors"},
            {"code": "e450", "title": "Individual attitudes of health professionals", "domain": "Environmental Factors"},
            {"code": "e455", "title": "Individual attitudes of other professionals", "domain": "Environmental Factors"},
            {"code": "e460", "title": "Societal attitudes", "domain": "Environmental Factors"},
            {"code": "e465", "title": "Social norms, practices and ideologies", "domain": "Environmental Factors"},
            {"code": "e5", "title": "Services, systems and policies", "domain": "Environmental Factors"},
            {"code": "e510", "title": "Services, systems and policies for the production of consumer goods", "domain": "Environmental Factors"},
            {"code": "e515", "title": "Architecture and construction services, systems and policies", "domain": "Environmental Factors"},
            {"code": "e520", "title": "Open space planning services, systems and policies", "domain": "Environmental Factors"},
            {"code": "e525", "title": "Housing services, systems and policies", "domain": "Environmental Factors"},
            {"code": "e530", "title": "Utilities services, systems and policies", "domain": "Environmental Factors"},
            {"code": "e535", "title": "Communication services, systems and policies", "domain": "Environmental Factors"},
            {"code": "e540", "title": "Transportation services, systems and policies", "domain": "Environmental Factors"},
            {"code": "e545", "title": "Civil protection services, systems and policies", "domain": "Environmental Factors"},
            {"code": "e550", "title": "Legal services, systems and policies", "domain": "Environmental Factors"},
            {"code": "e555", "title": "Associations and organizational services, systems and policies", "domain": "Environmental Factors"},
            {"code": "e560", "title": "Media services, systems and policies", "domain": "Environmental Factors"},
            {"code": "e565", "title": "Economic services, systems and policies", "domain": "Environmental Factors"},
            {"code": "e570", "title": "Social security services, systems and policies", "domain": "Environmental Factors"},
            {"code": "e575", "title": "General social support services, systems and policies", "domain": "Environmental Factors"},
            {"code": "e580", "title": "Health services, systems and policies", "domain": "Environmental Factors"},
            {"code": "e585", "title": "Education and training services, systems and policies", "domain": "Environmental Factors"},
            {"code": "e590", "title": "Labour and employment services, systems and policies", "domain": "Environmental Factors"},
            {"code": "e595", "title": "Political services, systems and policies", "domain": "Environmental Factors"},
        ]

        with open(self.local_json, 'w', encoding='utf-8') as f:
            json.dump(sample_data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"✅ تم إنشاء {len(sample_data)} مصطلح نموذجي")
        return len(sample_data)
