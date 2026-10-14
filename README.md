> [!IMPORTANT]
> **📦 أُرشف هذا المستودع بالكامل خارج GitHub** — النسخة الكاملة (الشيفرة + تاريخ git كامل + جميع الفروع) محفوظة في:
>
> | الوجهة | المسار |
> |---|---|
> | 🤗 Hugging Face Bucket | [`DrAbdulmalek/github-repo-backups`](https://huggingface.co/buckets/DrAbdulmalek/github-repo-backups) — الملف: `2026-10-14/arabic-medical-glossary_2026-10-14.tar.gz` (11 MB) *(خاص — يتطلب توكن HF)* |
> | 📁 Google Drive | `github-repo-backups/2026-10-14/arabic-medical-glossary_2026-10-14.tar.gz` |
>
> **SHA256**: `48f19b74d0a7ef762d5ee0ddc6298a26f4fbe41d51390691123c299c969cd04c`
> **آخر كومِت مُؤرشف**: `0b52555e39ed` — 2026-10-06T12:28:58Z — "fix(ci): daily-collect.yml schema violations (actionlint ×5) + missing"
>
> للاستعادة راجع `RESTORE.md` داخل الـ Bucket. *تاريخ الأرشفة: 2026-10-14 — هذا المستودع أُرشف كاملاً.*


# Arabic Medical Glossary & Terminology Base

ثنائي اللغة عربي-إنجليزي — مصطلحات وعبارات طبية مستخلصة من النشرات الدوائية والمراجع السريرية

## البنية

```
glossaries/          ← مسارد الجمل والعبارات المتقابلة (phrase-level)
terms/               ← قواعد المصطلحات المفردية (term-level)
sources/             ← مراجع المستخلصات (ملفات PDF/صور أصلية)
```

## المساهمة

كل إضافة يجب أن تكون:
- **مستخلصة من مصدر حقيقي** (نشرة دوائية، مرجع سريري، توثيق طبي)
- **بدون إضافات خارجية** — المصطلحات كما وردت في المصدر فقط
- **ثنائية اللغة** — كل مصطلح/عبارة بسطر عربي وآخر إنجليزي