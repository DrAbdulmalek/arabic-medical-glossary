import streamlit as st
import json
import os
from datetime import datetime

st.set_page_config(
    page_title="Medical Glossary Collector",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📚 متتبع جمع المسارد الطبية")

# تحميل البيانات
progress_file = "data/progress/state.json"
merged_file = "data/merged/glossary_master.json"

progress = {}
merged = {}

try:
    with open(progress_file, "r", encoding="utf-8") as f:
        progress = json.load(f)
except FileNotFoundError:
    st.warning("⚠️ لم يتم العثور على ملف التقدم. شغّل المجمع أولاً.")

try:
    with open(merged_file, "r", encoding="utf-8") as f:
        merged = json.load(f)
except FileNotFoundError:
    pass

# إحصائيات عامة
col1, col2, col3, col4 = st.columns(4)

total_terms = merged.get("metadata", {}).get("total_terms", 0) if merged else 0
col1.metric("📖 إجمالي المصطلحات", total_terms)

last_update = progress.get("last_update", "غير معروف")
if last_update != "غير معروف":
    last_update = last_update[:16]
col2.metric("🕐 آخر تحديث", last_update)

sources_count = len(progress.get("sources", {}))
col3.metric("📡 عدد المصادر", sources_count)

errors_count = len(progress.get("errors_log", []))
col4.metric("⚠️ الأخطاء", errors_count)

st.divider()

# حالة المصادر
st.subheader("📡 حالة المصادر")

for source, info in progress.get("sources", {}).items():
    status_color = {
        "completed": "🟢",
        "running": "🟡",
        "failed": "🔴",
        "idle": "⚪"
    }.get(info.get("status", "idle"), "⚪")

    with st.expander(f"{status_color} {source}"):
        c1, c2, c3 = st.columns(3)
        c1.metric("المصطلحات", info.get("terms_collected", 0))
        c2.metric("الحالة", info.get("status", "غير معروف"))

        last_run = info.get("last_run", "لم يتم")
        if last_run and last_run != "لم يتم":
            last_run = last_run[:16]
        c3.metric("آخر تشغيل", last_run)

        failures = info.get("consecutive_failures", 0)
        if failures > 0:
            st.error(f"❌ فشل متتالي: {failures} مرات")

        last_error = info.get("last_error")
        if last_error:
            st.error(f"آخر خطأ: {last_error}")

st.divider()

# البحث
st.subheader("🔍 البحث في المسارد")
search_term = st.text_input("أدخل المصطلح للبحث:", placeholder="مثال: diabetes, سكري, heart...")

if search_term and merged:
    results = []
    search_lower = search_term.lower()

    for key, data in merged.get("terms", {}).items():
        term = data.get("term", "").lower()
        definition = data.get("definition", "").lower()

        if search_lower in term or search_lower in definition:
            results.append(data)

    st.write(f"تم العثور على **{len(results)}** نتيجة")

    for r in results[:50]:  # عرض أول 50 نتيجة
        with st.container():
            term = r.get("term", "غير معروف")
            definition = r.get("definition", "لا يوجد تعريف")
            source = r.get("source", "غير معروف")
            lang = r.get("language", "غير معروف")
            confidence = r.get("confidence", 0)

            st.markdown(f"### {term}")
            st.markdown(f"**التعريف:** {definition}")

            meta_col1, meta_col2, meta_col3 = st.columns(3)
            meta_col1.caption(f"📡 المصدر: {source}")
            meta_col2.caption(f"🌐 اللغة: {lang}")
            meta_col3.caption(f"⭐ الثقة: {confidence}")
            st.divider()

# إحصائيات حسب اللغة
if merged and "by_language" in merged:
    st.divider()
    st.subheader("🌐 توزيع اللغات")

    lang_data = merged["by_language"]
    lang_cols = st.columns(len(lang_data))

    for i, (lang, terms) in enumerate(lang_data.items()):
        lang_cols[i].metric(
            f"{'🇦🇪 العربية' if lang == 'ar' else '🇬🇧 الإنجليزية' if lang == 'en' else lang}",
            len(terms)
        )

# إحصائيات حسب المصدر
if merged and "by_source" in merged:
    st.divider()
    st.subheader("📊 توزيع المصادر")

    source_data = merged["by_source"]
    for source, terms in source_data.items():
        st.write(f"**{source}**: {len(terms)} مصطلح")
