"""
MedDRA (Medical Dictionary for Regulatory Activities) Collector

⚠️ ⚠️ ⚠️ تحذير هام جداً:
MedDRA تديرها ICH (International Council for Harmonisation) ومتاحة فقط عبر MSSO.

- الاشتراكات **مدفوعة** للشركات (sliding scale)
- مجاني فقط للمنظمين الحكوميين (FDA, EMA, إلخ)
- يتطلب ترخيص MedDRA Subscription Agreement

لا يوجد API مجاني للوصول العام.

للحصول على MedDRA:
https://www.meddra.org/how-to-use/support-documentation/downloads

هذا الملف placeholder فقط.
"""

from collectors.base import BaseCollector


class MedDRACollector(BaseCollector):
    """
    مجمع placeholder لـ MedDRA
    يتطلب اشتراك MSSO مدفوع
    """

    def __init__(self, config: dict = None):
        super().__init__(
            "MedDRA",
            "https://www.meddra.org/",
            config
        )

    def collect(self) -> int:
        self.logger.error(
            "❌ MedDRA تتطلب اشتراك MSSO مدفوع.\n"
            "مجاني فقط للمنظمين الحكوميين.\n"
            "للحصول عليها: https://www.meddra.org/how-to-use/support-documentation/downloads"
        )
        return 0
