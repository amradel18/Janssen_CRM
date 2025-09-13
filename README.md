# Janssen CRM

تطبيق Streamlit لتحليل بيانات CRM.

طريقة التشغيل محليًا:
- تثبيت الاعتمادات: `pip install -r requirements.txt`
- تشغيل التطبيق: `streamlit run pages/7_Actions_items_Analysis.py`

إدارة الأسرار والبيئة:
- يتم تجاهل الملفات الحساسة بواسطة .gitignore: `.env`, `streamlit/secrets.toml`, `token.pkl`, ومجلد `venv/`.
- للتشغيل محليًا، ضع متغيرات البيئة في ملف `.env` أو استخدم `streamlit/secrets.toml` عند الحاجة.

ملاحظة:
- إذا واجهت رسالة تتعلق بالأسرار في Streamlit، فهذا طبيعي عند عدم وجود `secrets.toml`، وسيتم الاعتماد على `.env` كخيار احتياطي.
