# 🎓 منصة تعليمية إلكترونية باستخدام Django

![Django](https://img.shields.io/badge/Django-4.x-green?logo=django)
![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python)
![License](https://img.shields.io/badge/License-MIT-lightgrey)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)



## 📘 نظرة عامة

منصة تعليمية إلكترونية تسمح للطلاب بالتسجيل في الدورات، مشاهدة الفيديوهات التعليمية، إكمال الاختبارات، والحصول على شهادات.  
كما تتيح للمعلمين إنشاء دورات ورفع دروس وإدارة طلابهم وتقييماتهم.



## ✨ أبرز الميزات

- 🧑‍🏫 **حسابات المعلمين**: إدارة الدورات، إضافة دروس وفيديوهات، إنشاء اختبارات.
- 👨‍🎓 **حسابات الطلاب**: عرض الدورات، إكمال الدروس، تتبع التقدم.
- 🎬 **دروس فيديو**: مرفوعة بصيغة آمنة تمنع التحميل.
- 📊 **لوحة تحكم** لكل مستخدم حسب دوره.
- 🧪 **اختبارات تفاعلية** متعددة الخيارات.
- 🏆 **نظام الشهادات** للطلاب عند إتمام الدورة.
- ⭐ **تقييمات وتعليقات** لكل دورة.


## 🧱 بنية المشروع

```markdown
📁 project-root/
│
├── 📁 courses/                  # التطبيق الرئيسي
│   ├── models.py               # النماذج: الدورات، الدروس، التقييم، التقدم
│   ├── views.py                # جميع العروض (Views)
│   ├── forms.py                # نماذج الإدخال
│   ├── urls.py                 # الروابط المخصصة للتطبيق
│   ├── templates/courses/      # ملفات HTML (الواجهات)
│   ├── static/courses/         # ملفات CSS و JS ووسائط
│
├── 📁 media/                   # ملفات الوسائط المرفوعة (صور، فيديوهات)
├── 📁 templates/              # القوالب العامة
├── 📁 static/                 # ملفات التصميم العامة
├── manage.py                  # ملف التشغيل
├── requirements.txt           # ملف التبعيات
└── README.md                  # هذا الملف
```

---

## 🚀 خطوات تشغيل المشروع محليًا

### 1️⃣ استنساخ المشروع:

```bash
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
```

### 2️⃣ إنشاء بيئة افتراضية:

```bash
python -m venv env
source env/bin/activate        # على macOS / Linux
env\Scripts\activate           # على Windows
```

### 3️⃣ تثبيت المتطلبات:

```bash
pip install -r requirements.txt
```

### 4️⃣ تجهيز قاعدة البيانات:

```bash
python manage.py migrate
```

### 5️⃣ إنشاء مستخدم مشرف:

```bash
python manage.py createsuperuser
```

### 6️⃣ تشغيل الخادم:

```bash
python manage.py runserver
```

📍 الآن يمكنك زيارة:  
[http://127.0.0.1:8000/](http://127.0.0.1:8000/)

---

## 📦 ملف التبعيات (`requirements.txt`)

```txt
Django>=4.2
Pillow>=9.5.0
django-crispy-forms>=2.0
crispy-bootstrap5>=0.7
django-widget-tweaks>=1.4.12
gunicorn>=20.1.0
```

---

## 🔒 ملاحظات الأمان

- تم تعطيل زر تحميل الفيديوهات باستخدام:
  - `controlsList="nodownload"`
  - `oncontextmenu="return false"`
- صلاحيات المعلم والطالب مفصولة بشكل دقيق.
- يمكن الوصول للدروس والاختبارات فقط بعد التسجيل في الدورة.


## 👨‍💻 المطور

- 👤 الاسم: يوسف هاني
- 🔗 [حساب LinkedIn](https://www.linkedin.com/in/yousef-hany-279aa5240/)



## 📄 الرخصة

هذا المشروع مرخص بموجب رخصة MIT.  
[عرض الرخصة ›](LICENSE)

---

