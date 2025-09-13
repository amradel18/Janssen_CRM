# خطة هيكلة مشروع البيانات والتحليلات

هذه الوثيقة تضع خطة تنفيذ مفصلة لبناء بايبلاين تحميل ومعالجة وعرض بيانات Janssen CRM، مع فصل واضح للمسؤوليات على مستوى المجلدات والملفات. تعتمد الخطة على الجداول المتوفرة في Google Drive وعلى مخطط قاعدة البيانات الموضح في ملف janssencrm_database_schema.md.

## الأهداف
- إنشاء مسار بيانات واضح من المصدر (قاعدة البيانات/Drive) حتى التحليلات والرسوم.
- تسهيل إعادة الاستخدام والصيانة عبر فصل الأكواد حسب المرحلة (Load → Process → Visualize → Filter).
- دعم التحميل التزايدي للبيانات والقراءة المباشرة من Drive دون تنزيل.
- تمكين صفحات التحليل والفلترة في التطبيق (Streamlit) من الاستفادة من وحدات جاهزة.

## بنية المجلدات والملفات المقترحة

```
dashboard/
├─ app.py                                 # نقطة الدخول الرئيسية للتطبيق (Streamlit)
├─ pages/                                  # صفحات العرض الحالية والمتوقعة
│  ├─ 1_Customer_Page.py
│  ├─ 2_Calls_Page.py
│  ├─ 3_Tickets_Page.py
│  ├─ 4_Requests_Page.py
│  └─ Filter_Page.py (اختياري لاحقاً)     # في حال جعل الفلاتر صفحة مستقلة
├─ auth/
│  └─ login.py                             # منطق تسجيل الدخول والتحقق من المستخدم (admin/admin)
├─ load_data/
│  ├─ load_database_and_upload_drive.py   # سحب البيانات من DB ورفعها إلى Drive (CSV/Excel) تزايدياً
│  └─ load_data_in_drive.py               # قراءة ملفات من Drive بالاسم مباشرة إلى DataFrame
├─ process/
│  ├─ kpis.py                             # دوال حساب المؤشرات الأساسية (KPIs)
│  └─ table_query.py                      # دوال بناء الاستعلامات والدمج وعمليات groupby
├─ visualize/
│  ├─ charts.py                           # دوال تُرجع رسوم/مخططات (Plotly/Altair)
│  └─ style.py                            # الثيم، الألوان، الأنماط البصرية الموحدة
└─ filter/
   ├─ filter_page.py                      # منطق الفلاتر لصفحة Filter في التطبيق
   └─ mappings.py                         # خرائط المعرفات إلى الأسماء (Companies، Cities، ...)
```

ملاحظة: يمكن لاحقاً إضافة ملفات/مجلدات مساندة مثل `utils/` إذا ظهرت وظائف مشتركة بين أكثر من طبقة.

## الجداول المتوفرة على Google Drive (كمصدر للقراءة)
- call_categories
- call_types
- cities
- companies
- customer_phones
- customercall
- customers (الجدول الأساسي لتغذية الفلاتر)
- governorates
- product_info
- request_reasons
- ticket_categories
- ticket_item_change_another
- ticket_item_change_same
- ticket_item_maintenance
- ticket_items
- ticketcall
- tickets
- users

## مواصفات كل ملف ووظيفته

### 1) load_data/load_database_and_upload_drive.py
- الوظيفة: 
  - الاتصال بقاعدة البيانات (إن وُجدت)، سحب الجداول المطلوبة (list of table_names).
  - دعم التحميل التزايدي (by id أو by created_at/updated_at حسب المتاح).
  - حفظ البيانات مؤقتاً إلى DataFrame ثم رفعها إلى Google Drive بصيغة CSV/Excel.
  - سياسات الرفع:
    - إذا الملف غير موجود في Drive → إنشاء ملف جديد.
    - إذا موجود ونفس الأعمدة → إضافة الصفوف الجديدة فقط (append) أو استبدال ذكي إن لزم.
    - إذا اختلفت الأعمدة → استبدال كامل مع تحذير واضح.
- مخرجات: ملفات محدثة على Drive لكل جدول.
- اعتبارات:
  - إدارة التوكن (token.pkl) و client_secret.json.
  - التسجيل (logging) ورسائل حالة واضحة.
  - التوافق مع الدوال العامة في `utils.py` و `database.py` الحالية قدر الإمكان.

### 2) load_data/load_data_in_drive.py
- الوظيفة:
  - إنشاء خدمة Google Drive (get_drive_service()) وإرجاعها.
  - دوال قراءة مباشرة من Drive بالاسم إلى الذاكرة دون تنزيل:
    - read_csv_from_drive_by_name(filename, folder_id=None) → DataFrame
    - لاحقاً: read_excel_from_drive_by_name(...)
  - دعم البحث داخل مجلد محدد Folder ID عند الحاجة.
- مخرجات: DataFrame جاهزة للاستخدام في المعالجة/العرض.
- اعتبارات: إدارة الأخطاء (ملف غير موجود، أكثر من ملف بنفس الاسم، ترميز الحروف، تواريخ...).

### 3) process/kpis.py
- الوظيفة: تعريف دوال للمؤشرات الأساسية. أمثلة مبدئية:
  - إجمالي العملاء، العملاء النشطون (بناءً على وجود تذاكر/مكالمات خلال فترة).
  - عدد التذاكر حسب الحالة (مفتوحة/مغلقة/قيد المعالجة) ومتوسط زمن الحل.
  - توزيع المكالمات حسب الفئة/النوع، ومتوسط المكالمات اليومي/الأسبوعي.
  - التذاكر لكل عميل/شركة، ومعدل التصعيد.
- المخرجات: دوال ترجع أرقام/جداول موجزة قابلة للعرض.
- اعتبارات: توحيد أسماء الأعمدة، التعامل مع القيم المفقودة، ضبط المناطق الزمنية.

### 4) process/table_query.py
- الوظيفة: بناء استعلامات ودمج الجداول:
  - ضم customers مع companies, governorates, cities, users عبر مفاتيح ID.
  - دوال groupby جاهزة (by company, by governorate, by city, by created_at period).
  - دوال مساعدة: تحويل الأنواع، parsing للتواريخ، إعادة تسمية أعمدة موحدة.
- المخرجات: DataFrames معالجة جاهزة للعرض أو لحساب KPIs.

### 5) visualize/charts.py
- الوظيفة: إنشاء الرسوم البيانية القياسية:
  - Bar/Line لزمنياً (trend) على أساس created_at.
  - Pie/Donut لتوزيعات الفئات (tickets by category, calls by type).
  - Heatmap أو Treemap إن لزم.
- المخرجات: كائنات رسومية (مثل Plotly Figure) للاستخدام في صفحات Streamlit.

### 6) visualize/style.py
- الوظيفة: الثيم والألوان والخطوط:
  - لوحة ألوان موحدة (Primary/Secondary/Accent، ودرجات محايدة).
  - إعدادات حجم الخط، سماكات الحدود، خلفيات البطاقات.
  - تهيئة عامة لـ Streamlit (إن لزم) لضمان اتساق الشكل.

### 7) filter/filter_page.py
- الوظيفة: بناء عناصر الفلترة لصفحة Filter في التطبيق:
  - الحقول: [company_id, name, governorate_id, city_id, created_by, created_at].
  - استبدال IDs بالأسماء من الجداول المساعدة (companies, governorates, cities, users).
  - مصدر البيانات الأساسي customers، مع القدرة على تغذية بقية الجداول إذا لزم.
  - واجهة تفاعلية (Streamlit) تُعيد DataFrame مُفلتر لاستخدامه في الصفحات الأخرى.

### 8) filter/mappings.py
- الوظيفة: دوال ترجمة المعرفات لأسماء نصية، مع caching بسيط:
  - get_company_name(id), get_city_name(id), get_governorate_name(id), get_user_name(id)
  - دوال تحميل جداول المرجع من Drive مرة واحدة وإعادة استخدامها.

## تدفق البيانات (Pipeline Flow)
1) Load (load_data):
   - من قاعدة البيانات (إن وُجدت) → إلى Drive (CSV/Excel) بتسمية موحدة.
   - أو القراءة المباشرة من Drive إلى DataFrame عند الحاجة.
2) Process (process):
   - تنظيف، دمج، تحضير جداول التحليل.
   - حساب KPIs.
3) Visualize (visualize):
   - تحويل النتائة إلى رسوم متسقة الشكل.
4) Filter (filter):
   - طبقة الفلترة لصفحة Filter تغذي بقية الصفحات التحليلية.

## معايير تسمية الملفات على Drive (اقتراح)
- استخدام اسم ثابت لكل جدول لتسهيل القراءة بالاسم: `customers.csv`, `tickets.csv`, ...
- بديل: الاحتفاظ بإصدار/تاريخ في اسم الملف مع رابط ثابت لآخر نسخة.

## خريطة المفاتيح والخرائط النصية (مبدئية)
- customers.company_id → companies.name
- customers.governorate_id → governorates.name
- customers.city_id → cities.name
- customers.created_by → users.name

## خطوات التنفيذ (Roadmap)
1) إنشاء المجلدات والملفات الفارغة حسب الهيكل أعلاه.
2) نقل/استخراج وظائف Google Drive العامة إلى `load_data/load_data_in_drive.py` (get_drive_service, read_csv_by_name).
3) بناء التحميل التزايدي في `load_database_and_upload_drive.py` بالاعتماد على المنطق الحالي في `database.py` وتحسين الرسائل.
4) إعداد `process/table_query.py` بعمليات الدمج الأساسية و parsing للتواريخ.
5) تعريف مجموعة أولى من KPIs في `process/kpis.py` (5–8 مؤشرات).
6) إنشاء ثيم أولي في `visualize/style.py` وبناء رسمين/ثلاثة في `visualize/charts.py`.
7) إعداد `filter/mappings.py` و`filter/filter_page.py` لواجهة الفلاتر الأساسية.
8) دمج الصفحة الجديدة ضمن التطبيق (إضافة صفحة Filter في مجلد pages/ وربطها بالوحدات أعلاه).
9) اختبارات سريعة + معالجة الحواف (جداول مفقودة على Drive، اختلاف أعمدة، ترميزات).

## اختبار القيم والأنواع
- التأكد من أن الأعمدة المرجعية (IDs) أعداد صحيحة بدون فراغات.
- توحيد ترميز النصوص UTF-8 عند القراءة/الكتابة.
- تحويل الأعمدة الزمنية إلى datetime مع timezone-aware إن لزم.

## مخرجات متوقعة للتكامل
- القدرة على تحميل وتحديث الجداول على Drive تزايدياً بضغطة زر.
- قراءة فورية للبيانات داخل الصفحات دون تنزيل محلي.
- طبقة معالجة موحدة تُسهل بناء مؤشرات ولوحات جديدة بسرعة.
- واجهة فلاتر مرنة تغذي جميع الصفحات وتوحّد تجربة المستخدم.
## ملخص وتنظيم مُحسّن
- هذه الخلاصة تُرتب الخطة وتبرز أهم ما سيتم تنفيذه عملياً مع روابط الأقسام أدناه.
- الهدف: هيكلة واضحة لمسار البيانات (Load → Process → Visualize → Filter) مع قابلية التشغيل الآن ثم التوسعة لاحقاً.

## خطة التنفيذ التفصيلية (Milestones)
1) نقل وظائف Drive العامة من <mcfile name="database.py" path="f:/C_S/dashboard/database.py"></mcfile> إلى load_data/load_data_in_drive.py مع الحفاظ على التوافق.
2) إضافة load_tables_from_drive لتجميع قراءة جميع الجداول في خطوة واحدة.
3) إنشاء process/table_query.py وبناء دوال الدمج المذكورة، مع parse_dates للأعمدة الزمنية (created_at, updated_at, closed_at).
4) إنشاء process/kpis.py وتنفيذ مؤشرات المرحلة الأولى (6–8 مؤشرات).
5) إنشاء visualize/style.py و visualize/charts.py مع ثيم أولي ورسوم أساسية (trend, bar, pie).
6) بناء filter/mappings.py و filter/filter_page.py، ثم إضافة صفحة Filter ضمن pages/.
7) تعديل الصفحات الحالية pages/1..4 لاستخدام الدوال الجديدة، وإضافة كاش مناسب.
8) إعداد سكريبت إدارة لتشغيل الرفع التزايدي يدوياً من داخل التطبيق (زر تحديث).
9) اختبارات وظيفية سريعة + معالجة الحواف (جداول مفقودة على Drive، اختلاف أعمدة، ترميزات).

## اختبار القيم والأنواع
- التأكد من أن الأعمدة المرجعية (IDs) أعداد صحيحة بدون فراغات.
- توحيد ترميز النصوص UTF-8 عند القراءة/الكتابة.
- تحويل الأعمدة الزمنية إلى datetime مع timezone-aware إن لزم.

## مخرجات متوقعة للتكامل
- القدرة على تحميل وتحديث الجداول على Drive تزايدياً بضغطة زر.
- قراءة فورية للبيانات داخل الصفحات دون تنزيل محلي.
- طبقة معالجة موحدة تُسهل بناء مؤشرات ولوحات جديدة بسرعة.
- واجهة فلاتر مرنة تغذي جميع الصفحات وتوحّد تجربة المستخدم.
## ملخص وتنظيم مُحسّن
- هذه الخلاصة تُرتب الخطة وتبرز أهم ما سيتم تنفيذه عملياً مع روابط الأقسام أدناه.
- الهدف: هيكلة واضحة لمسار البيانات (Load → Process → Visualize → Filter) مع قابلية التشغيل الآن ثم التوسعة لاحقاً.