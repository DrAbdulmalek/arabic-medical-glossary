"""
لوحة تحكم محسّنة للمسارد الطبية.
رسوم بيانية تفاعلية (Plotly) + تصفية متقدمة + تصدير.
"""

import json
import os
import csv
import io
from datetime import datetime

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Medical Glossary Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="📚",
)

# ─── CSS مخصص ────────────────────────────────────────────────────

st.markdown("""
<style>
    .stMetric { background: #f8f9fa; border-radius: 8px; padding: 12px; }
    .block-container { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)


# ─── تحميل البيانات ──────────────────────────────────────────────

@st.cache_data(ttl=120)
def load_data():
    """تحميل بيانات المسرد والتقدم مع caching."""
    progress = {}
    merged = {}

    for fp, key in [
        ("data/progress/state.json", "progress"),
        ("data/merged/glossary_master.json", "merged"),
    ]:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                if key == "progress":
                    progress = json.load(f)
                else:
                    merged = json.load(f)
        except FileNotFoundError:
            pass

    return progress, merged


# ─── الرأس ────────────────────────────────────────────────────────

st.title("📚 لوحة تحكم المسارد الطبية")
st.markdown("---")

progress, merged = load_data()

if not merged:
    st.warning("⚠️ لا توجد بيانات. شغّل المجمعات أولاً.")
    st.stop()

# ─── الشريط الجانبي: الفلاتر ───────────────────────────────────

st.sidebar.header("🔍 الفلاتر")

languages = list(merged.get("by_language", {}).keys())
selected_lang = st.sidebar.selectbox("اللغة", ["الكل"] + languages, index=0)

sources = list(merged.get("by_source", {}).keys())
selected_sources = st.sidebar.multiselect("المصادر", sources, default=sources)

min_conf = st.sidebar.slider("الحد الأدنى للثقة", 0.0, 1.0, 0.0, 0.05)

# ─── مقاييس عامة ───────────────────────────────────────────────

terms = merged.get("terms", {})
total = len(terms)

col1, col2, col3, col4 = st.columns(4)
col1.metric("📖 المصطلحات", f"{total:,}")

last_update = progress.get("last_update", "غير معروف")
col2.metric("🕐 آخر تحديث", last_update[:16] if len(str(last_update)) > 16 else last_update)

src_count = len(progress.get("sources", {}))
col3.metric("📡 المصادر", src_count)

err_count = len(progress.get("errors_log", []))
col4.metric("⚠️ الأخطاء", err_count)

st.markdown("---")

# ─── صف الرسوم البيانية ─────────────────────────────────────────

col1, col2 = st.columns(2)

with col1:
    st.subheader("🌐 توزيع اللغات")
    lang_data = merged.get("by_language", {})
    if lang_data:
        lang_df = {
            "اللغة": [l.upper() for l in lang_data.keys()],
            "العدد": [len(v) for v in lang_data.values()],
        }
        fig = px.pie(
            lang_df, values="العدد", names="اللغة",
            color_discrete_sequence=px.colors.qualitative.Set2,
            hole=0.4,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("📊 توزيع المصادر")
    source_data = merged.get("by_source", {})
    if source_data:
        source_df = [
            {"المصدر": s, "العدد": len(v)}
            for s, v in sorted(source_data.items(), key=lambda x: -len(x[1]))
        ]
        fig = px.bar(
            source_df, x="العدد", y="المصدر",
            orientation="h", color="العدد",
            color_continuous_scale="Blues",
        )
        fig.update_layout(showlegend=False, height=max(200, len(source_df) * 30))
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ─── حالة المصادر ───────────────────────────────────────────────

st.subheader("📡 حالة المصادر")
sources_info = progress.get("sources", {})
if sources_info:
    for src, info in sources_info.items():
        status = info.get("status", "unknown")
        emoji = {"completed": "🟢", "running": "🟡", "failed": "🔴", "idle": "⚪"}.get(status, "⚪")
        with st.expander(f"{emoji} {src}"):
            c1, c2, c3 = st.columns(3)
            c1.metric("المصطلحات", f"{info.get('terms_collected', 0):,}")
            c2.metric("الحالة", status)
            last_run = info.get("last_run", "أبداً")
            c3.metric("آخر تشغيل", str(last_run)[:16] if last_run and last_run != "أبداً" else "أبداً")

st.markdown("---")

# ─── البحث ───────────────────────────────────────────────────────

st.subheader("🔍 البحث في المسارد")
query = st.text_input("ابحث:", placeholder="مثال: diabetes, سكري, heart, قلب...")

if query and merged:
    q = query.lower()
    results = []

    for td in terms.values():
        # تطبيق الفلاتر
        if selected_lang != "الكل" and td.get("language") != selected_lang:
            continue
        if selected_sources and td.get("source") not in selected_sources:
            continue
        if td.get("confidence", 0) < min_conf:
            continue
        # البحث
        if q in td.get("term", "").lower() or q in td.get("definition", "").lower():
            results.append(td)

    st.write(f"**{len(results)} نتيجة**")

    for i, r in enumerate(results[:100]):
        st.markdown(f"### {r['term']}")
        st.write(r.get("definition", ""))
        c1, c2, c3 = st.columns(3)
        c1.caption(f"📡 {r.get('source', '')}")
        c2.caption(f"🌐 {r.get('language', '').upper()}")
        c3.caption(f"⭐ {r.get('confidence', 0):.2f}")
        if i < len(results) - 1:
            st.divider()

st.markdown("---")

# ─── التصدير ─────────────────────────────────────────────────────

st.subheader("📥 التصدير")

ec1, ec2 = st.columns(2)

with ec1:
    if st.button("JSON"):
        export = {
            "metadata": {"exported_at": datetime.now().isoformat(), "total": total},
            "terms": list(terms.values()),
        }
        st.download_button(
            "⬇️ تحميل JSON", json.dumps(export, ensure_ascii=False, indent=2),
            file_name="glossary_export.json", mime="application/json",
        )

with ec2:
    if st.button("CSV"):
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["term", "definition", "source", "language", "confidence"])
        writer.writeheader()
        for td in terms.values():
            writer.writerow({k: td.get(k, "") for k in writer.fieldnames})
        st.download_button(
            "⬇️ تحميل CSV", output.getvalue(),
            file_name="glossary_export.csv", mime="text/csv",
        )