"""Screening question bank for the Safe Child project.

Pure Python — no Reflex, no web dependencies. Safe to import anywhere.

Structure: 3 age groups x 6 categories x (1 broad + 3 deep) = 72 questions.
Deep questions are only asked when the broad answer for that category
signals concern.

Answer values (handled in scoring.py):
    "yes"       -> full weight
    "sometimes" -> half weight
    "no"        -> 0
    "unknown"   -> 0
"""

AGE_GROUPS = ["3-6", "7-12", "13-17"]

CATEGORIES = [
    {"key": "sleep", "ur": "نیند", "en": "Sleep", "icon": "moon"},
    {"key": "health", "ur": "بھوک و صحت", "en": "Appetite & Health", "icon": "apple"},
    {"key": "mood", "ur": "موڈ و جذبات", "en": "Mood & Feelings", "icon": "heart"},
    {"key": "behavior", "ur": "رویہ", "en": "Behavior", "icon": "users"},
    {"key": "school", "ur": "اسکول", "en": "School", "icon": "book"},
    {"key": "physical", "ur": "جسمانی نشانات", "en": "Physical Signs", "icon": "alert"},
]

ANSWER_LABELS = {
    "yes": {"ur": "ہاں", "en": "Yes"},
    "sometimes": {"ur": "کبھی کبھی", "en": "Sometimes"},
    "no": {"ur": "نہیں", "en": "No"},
    "unknown": {"ur": "پتا نہیں", "en": "Don't know"},
}

# Raw data: (kind, text_ur, text_en, weight, critical, double_weight)
# weight: 1 = signal, 2 = medium, 3 = strong
# critical=True: a "yes" answer jumps the whole screening to the critical band.
# double_weight=True: counts double in scoring (used for physical-sign items).
_RAW = {
    "3-6": {
        "sleep": [
            ("broad", "کیا بچے کی نیند میں پچھلے چند ہفتوں میں کوئی نمایاں تبدیلی آئی ہے؟",
             "Has there been a noticeable change in your child's sleep in the past few weeks?", 1, False, False),
            ("deep", "کیا بچہ سوتے ہوئے ڈرتا ہے، چیختا ہے یا بار بار جاگتا ہے؟",
             "Does the child seem frightened, cry out, or wake up repeatedly during sleep?", 2, False, False),
            ("deep", "کیا بچہ سونے سے پہلے بے چین ہوتا ہے یا سونے سے انکار کرتا ہے؟",
             "Is the child restless before bedtime or refuses to go to sleep?", 2, False, False),
            ("deep", "کیا بچہ بستر گیلا کرنے لگا ہے حالانکہ پہلے ایسا نہیں کرتا تھا؟",
             "Has the child started wetting the bed after having stopped?", 2, False, False),
        ],
        "health": [
            ("broad", "کیا بچے کی بھوک یا کھانے کی عادت میں کوئی نمایاں تبدیلی آئی ہے؟",
             "Has there been a noticeable change in your child's appetite or eating habits?", 1, False, False),
            ("deep", "کیا بچہ کھانے سے انکار کرتا ہے یا بہت کم کھاتا ہے؟",
             "Does the child refuse food or eat very little?", 2, False, False),
            ("deep", "کیا بچہ بغیر کسی واضح وجہ کے پیٹ یا سر درد کی شکایت کرتا ہے؟",
             "Does the child complain of stomach or head pain without a clear reason?", 2, False, False),
            ("deep", "کیا بچے کا وزن غیر معمولی طور پر کم ہوا ہے؟",
             "Has the child lost weight unusually?", 2, False, False),
        ],
        "mood": [
            ("broad", "کیا بچے کے موڈ میں پچھلے چند ہفتوں میں کوئی نمایاں تبدیلی آئی ہے؟",
             "Has there been a noticeable change in your child's mood in the past few weeks?", 1, False, False),
            ("deep", "کیا بچہ اکثر اداس، خاموش یا روتا ہوا نظر آتا ہے؟",
             "Does the child often seem sad, withdrawn, or tearful?", 2, False, False),
            ("deep", "کیا بچہ چھوٹی چھوٹی باتوں پر بہت زیادہ غصہ یا خوف ظاہر کرتا ہے؟",
             "Does the child show intense anger or fear over small things?", 2, False, False),
            ("deep", "کیا بچہ پہلے کی طرح ہنستا کھیلتا نہیں ہے؟",
             "Does the child no longer laugh and play like before?", 2, False, False),
        ],
        "behavior": [
            ("broad", "کیا بچے کے رویے میں پچھلے چند ہفتوں میں کوئی نمایاں تبدیلی آئی ہے؟",
             "Has there been a noticeable change in your child's behavior in the past few weeks?", 1, False, False),
            ("deep", "کیا بچہ کسی خاص شخص کے پاس جانے سے ڈرتا ہے یا انکار کرتا ہے؟",
             "Is the child afraid of going near a particular person, or refuses to?", 2, False, False),
            ("deep", "کیا بچہ جارحانہ ہو گیا ہے — مارتا ہے، کاٹتا ہے یا چیزیں توڑتا ہے؟",
             "Has the child become aggressive — hitting, biting, or breaking things?", 2, False, False),
            ("deep", "کیا بچہ اپنی عمر سے بڑی باتیں یا حرکتیں کرنے لگا ہے؟",
             "Has the child started talking or behaving in ways beyond their age?", 2, False, False),
        ],
        "school": [
            ("broad", "کیا بچہ اسکول، پلے گروپ یا مدرسہ جانے سے انکار کرتا ہے یا روتا ہے؟",
             "Does the child refuse to go to school, playgroup, or madrasa, or cry about going?", 1, False, False),
            ("deep", "کیا بچہ اسکول سے واپس آ کر خاموش یا پریشان رہتا ہے؟",
             "Does the child come home from school quiet or upset?", 2, False, False),
            ("deep", "کیا بچے کی پڑھائی میں دلچسپی یا توجہ کم ہوئی ہے؟",
             "Has the child's interest or attention in learning declined?", 2, False, False),
            ("deep", "کیا بچہ اسکول کے کسی خاص شخص یا جگہ سے ڈرتا ہے؟",
             "Is the child afraid of a particular person or place at school?", 2, False, False),
        ],
        "physical": [
            ("broad", "کیا بچے کے جسم پر کوئی ایسے نشان، چوٹ یا خراش نظر آئی ہے جس کی وجہ معلوم نہ ہو؟",
             "Have you noticed any marks, bruises, or scratches on the child's body with no known cause?", 2, False, True),
            ("deep", "کیا بچے کے جسم پر بار بار بغیر وضاحت کے چوٹ کے نشان نظر آتے ہیں؟",
             "Do unexplained injury marks appear on the child's body repeatedly?", 3, True, True),
            ("deep", "کیا بچہ جسم کے کسی حصے میں ایسے درد کی شکایت کرتا ہے جس کی وجہ سمجھ نہ آئے؟",
             "Does the child complain of pain in a part of the body with no clear cause?", 3, False, True),
            ("deep", "کیا بچہ نہاتے وقت یا کپڑے بدلتے وقت غیر معمولی شرماتا ہے یا چھپانے کی کوشش کرتا ہے؟",
             "Does the child seem unusually shy or try to hide while bathing or changing clothes?", 2, False, True),
        ],
    },
    "7-12": {
        "sleep": [
            ("broad", "کیا بچے کی نیند میں پچھلے چند ہفتوں میں کوئی نمایاں تبدیلی آئی ہے؟",
             "Has there been a noticeable change in your child's sleep in the past few weeks?", 1, False, False),
            ("deep", "کیا بچے کو سونے میں دشواری ہوتی ہے یا وہ رات کو بار بار جاگتا ہے؟",
             "Does the child have difficulty falling asleep or wake up repeatedly at night?", 2, False, False),
            ("deep", "کیا بچہ ڈراؤنے خوابوں کی شکایت کرتا ہے؟",
             "Does the child complain of frightening dreams?", 2, False, False),
            ("deep", "کیا بچہ دن میں غیر معمولی طور پر تھکا ہوا یا سست رہتا ہے؟",
             "Is the child unusually tired or sluggish during the day?", 2, False, False),
        ],
        "health": [
            ("broad", "کیا بچے کی بھوک یا کھانے کی عادت میں کوئی نمایاں تبدیلی آئی ہے؟",
             "Has there been a noticeable change in your child's appetite or eating habits?", 1, False, False),
            ("deep", "کیا بچہ کھانا چھوڑ دیتا ہے یا چھپ کر کھاتا ہے؟",
             "Does the child skip meals or eat in secret?", 2, False, False),
            ("deep", "کیا بچہ بغیر کسی طبی وجہ کے بار بار پیٹ یا سر درد کی شکایت کرتا ہے؟",
             "Does the child frequently complain of stomach or head pain without a medical reason?", 2, False, False),
            ("deep", "کیا بچے کی صحت یا توانائی میں واضح کمی آئی ہے؟",
             "Has there been a clear decline in the child's health or energy?", 2, False, False),
        ],
        "mood": [
            ("broad", "کیا بچے کے موڈ میں پچھلے چند ہفتوں میں کوئی نمایاں تبدیلی آئی ہے؟",
             "Has there been a noticeable change in your child's mood in the past few weeks?", 1, False, False),
            ("deep", "کیا بچہ اکثر اداس رہتا ہے یا پہلے کی طرح خوش نظر نہیں آتا؟",
             "Is the child often sad or not as cheerful as before?", 2, False, False),
            ("deep", "کیا بچہ اپنے جذبات چھپاتا ہے یا ان کے بارے میں بات کرنے سے گریز کرتا ہے؟",
             "Does the child hide their feelings or avoid talking about them?", 2, False, False),
            ("deep", "کیا بچہ کہتا ہے کہ کوئی اسے پسند نہیں کرتا یا وہ خود برا ہے؟",
             "Does the child say that nobody likes them or that they are bad?", 2, False, False),
        ],
        "behavior": [
            ("broad", "کیا بچے کے رویے میں پچھلے چند ہفتوں میں کوئی نمایاں تبدیلی آئی ہے؟",
             "Has there been a noticeable change in your child's behavior in the past few weeks?", 1, False, False),
            ("deep", "کیا بچہ کسی خاص شخص سے ملنے سے گھبراتا ہے یا اس سے بچنے کی کوشش کرتا ہے؟",
             "Does the child seem nervous about meeting a particular person, or try to avoid them?", 2, False, False),
            ("deep", "کیا بچہ چوری، جھوٹ یا اصول توڑنے جیسے رویے دکھانے لگا ہے؟",
             "Has the child started behaviors like stealing, lying, or breaking rules?", 2, False, False),
            ("deep", "کیا بچہ نامناسب یا جنسی نوعیت کی باتیں یا حرکتیں کرنے لگا ہے؟",
             "Has the child started using inappropriate or sexualized language or behavior?", 3, False, False),
        ],
        "school": [
            ("broad", "کیا بچہ اسکول یا مدرسہ جانے سے کتراتا ہے یا بہانے بناتا ہے؟",
             "Does the child avoid going to school or madrasa, or make excuses?", 1, False, False),
            ("deep", "کیا بچے کے نمبروں یا پڑھائی میں دلچسپی میں کمی آئی ہے؟",
             "Have the child's grades or interest in studies declined?", 2, False, False),
            ("deep", "کیا بچہ اسکول میں دوستوں سے الگ تھلگ رہنے لگا ہے؟",
             "Has the child started staying isolated from friends at school?", 2, False, False),
            ("deep", "کیا بچہ اساتذہ یا اسکول کے عملے کے بارے میں خوف یا شکایت ظاہر کرتا ہے؟",
             "Does the child show fear of, or complain about, teachers or school staff?", 2, False, False),
        ],
        "physical": [
            ("broad", "کیا بچے کے جسم پر کوئی ایسے نشان یا چوٹ نظر آئی ہے جس کی تسلی بخش وضاحت نہ ہو؟",
             "Have you noticed any marks or injuries on the child's body without a satisfactory explanation?", 2, False, True),
            ("deep", "کیا بچہ چوٹ کی وجہ بتاتے ہوئے متضاد یا الجھی ہوئی باتیں کرتا ہے؟",
             "Does the child give contradictory or confused explanations for injuries?", 3, False, True),
            ("deep", "کیا بچے نے بتایا ہے کہ کسی نے اسے مارا ہے یا برے طریقے سے چھوا ہے؟",
             "Has the child said that someone hurt them or touched them in a bad way?", 3, True, True),
            ("deep", "کیا بچہ گرم موسم میں بھی جسم ڈھانپنے والے کپڑے پہننے پر اصرار کرتا ہے؟",
             "Does the child insist on wearing body-covering clothes even in hot weather?", 2, False, True),
        ],
    },
    "13-17": {
        "sleep": [
            ("broad", "کیا نوجوان کی نیند میں پچھلے چند ہفتوں میں کوئی نمایاں تبدیلی آئی ہے؟",
             "Has there been a noticeable change in the teenager's sleep in the past few weeks?", 1, False, False),
            ("deep", "کیا وہ رات دیر تک جاگتا ہے اور صبح اٹھنے میں اسے دشواری ہوتی ہے؟",
             "Do they stay up very late at night and struggle to get up in the morning?", 2, False, False),
            ("deep", "کیا وہ نیند نہ آنے یا بے خوابی کی شکایت کرتا ہے؟",
             "Do they complain of not being able to sleep, or of insomnia?", 2, False, False),
            ("deep", "کیا وہ دن میں غیر معمولی طور پر زیادہ سوتا رہتا ہے؟",
             "Do they sleep unusually much during the day?", 2, False, False),
        ],
        "health": [
            ("broad", "کیا نوجوان کی بھوک یا کھانے کی عادت میں کوئی نمایاں تبدیلی آئی ہے؟",
             "Has there been a noticeable change in the teenager's appetite or eating habits?", 1, False, False),
            ("deep", "کیا وہ کھانا چھوڑ دیتا ہے یا اپنے وزن کے بارے میں غیر معمولی فکر کرتا ہے؟",
             "Do they skip meals or worry excessively about their weight?", 2, False, False),
            ("deep", "کیا وہ بار بار جسمانی تکالیف (سر یا پیٹ درد) کی شکایت کرتا ہے جن کی طبی وجہ نہ ملے؟",
             "Do they frequently complain of physical pains (head or stomach) with no medical cause found?", 2, False, False),
            ("deep", "کیا اس کی صحت یا جسمانی توانائی میں واضح کمی آئی ہے؟",
             "Has there been a clear decline in their health or physical energy?", 2, False, False),
        ],
        "mood": [
            ("broad", "کیا نوجوان کے موڈ میں پچھلے چند ہفتوں میں کوئی نمایاں تبدیلی آئی ہے؟",
             "Has there been a noticeable change in the teenager's mood in the past few weeks?", 1, False, False),
            ("deep", "کیا وہ اکثر اداس، مایوس یا بے حس نظر آتا ہے؟",
             "Do they often seem sad, hopeless, or emotionally numb?", 2, False, False),
            ("deep", "کیا وہ دوستوں اور گھر والوں سے الگ تھلگ ہو گیا ہے؟",
             "Have they withdrawn from friends and family?", 2, False, False),
            ("deep", "کیا اس نے خود کو نقصان پہنچانے یا اپنی زندگی ختم کرنے کی بات کی ہے؟",
             "Have they talked about harming themselves or ending their life?", 3, True, False),
        ],
        "behavior": [
            ("broad", "کیا نوجوان کے رویے میں پچھلے چند ہفتوں میں کوئی نمایاں تبدیلی آئی ہے؟",
             "Has there been a noticeable change in the teenager's behavior in the past few weeks?", 1, False, False),
            ("deep", "کیا وہ کسی خاص شخص سے شدید خوف ظاہر کرتا ہے یا اس سے ملنے سے سختی سے انکار کرتا ہے؟",
             "Do they show intense fear of a specific person, or strongly refuse to meet them?", 3, True, False),
            ("deep", "کیا وہ خطرناک یا اصول توڑنے والے رویوں میں ملوث ہوا ہے؟",
             "Have they become involved in risky or rule-breaking behavior?", 2, False, False),
            ("deep", "کیا وہ موبائل یا انٹرنیٹ پر کسی نامعلوم شخص سے خفیہ رابطہ رکھتا ہے؟",
             "Do they secretly stay in contact with an unknown person on mobile or the internet?", 2, False, False),
        ],
        "school": [
            ("broad", "کیا نوجوان اسکول یا کالج جانے سے کتراتا ہے یا غیر حاضر رہنے لگا ہے؟",
             "Does the teenager avoid going to school or college, or stay absent?", 1, False, False),
            ("deep", "کیا اس کے نمبروں میں اچانک نمایاں کمی آئی ہے؟",
             "Have their grades dropped suddenly and noticeably?", 2, False, False),
            ("deep", "کیا وہ پڑھائی اور اپنے مستقبل کے بارے میں مکمل بے پروا ہو گیا ہے؟",
             "Have they become completely indifferent about their studies and future?", 2, False, False),
            ("deep", "کیا وہ اسکول یا کالج کے کسی استاد یا فرد کے بارے میں خوف یا شکایت ظاہر کرتا ہے؟",
             "Do they show fear of, or complain about, a teacher or person at school or college?", 2, False, False),
        ],
        "physical": [
            ("broad", "کیا نوجوان کے جسم پر کوئی ایسے نشان یا چوٹ نظر آئی ہے جس کی تسلی بخش وضاحت نہ ہو؟",
             "Have you noticed any marks or injuries on the teenager's body without a satisfactory explanation?", 2, False, True),
            ("deep", "کیا اس کے بازوؤں یا جسم پر کٹ کے نشان نظر آئے ہیں؟",
             "Have you noticed cut marks on their arms or body?", 3, False, True),
            ("deep", "کیا وہ چوٹوں کو چھپانے کی کوشش کرتا ہے یا ان کی وضاحت سے گریز کرتا ہے؟",
             "Do they try to hide injuries or avoid explaining them?", 3, False, True),
            ("deep", "کیا اس نے بتایا ہے کہ کسی نے اسے جسمانی یا جنسی طور پر نقصان پہنچایا ہے؟",
             "Have they said that someone harmed them physically or sexually?", 3, True, True),
        ],
    },
}


def _build_questions():
    questions = []
    for age_group, cats in _RAW.items():
        for cat_key, items in cats.items():
            deep_n = 0
            for kind, ur, en, weight, critical, double_weight in items:
                if kind == "broad":
                    qid = f"{cat_key}_broad_{age_group}"
                else:
                    deep_n += 1
                    qid = f"{cat_key}_deep{deep_n}_{age_group}"
                questions.append({
                    "qid": qid,
                    "category": cat_key,
                    "age_group": age_group,
                    "kind": kind,  # "broad" | "deep"
                    "text_ur": ur,
                    "text_en": en,
                    "weight": weight,  # 1 = signal, 2 = medium, 3 = strong
                    "critical": critical,
                    "double_weight": double_weight,
                })
    return questions


QUESTIONS = _build_questions()

# Structural validation at import time.
assert len(QUESTIONS) == 72, f"expected 72 questions, got {len(QUESTIONS)}"
for _ag in AGE_GROUPS:
    _qs = [q for q in QUESTIONS if q["age_group"] == _ag]
    assert len(_qs) == 24, f"age {_ag}: expected 24, got {len(_qs)}"
    for _cat in CATEGORIES:
        _cq = [q for q in _qs if q["category"] == _cat["key"]]
        assert len(_cq) == 4, f"{_ag}/{_cat['key']}: expected 4, got {len(_cq)}"
        assert sum(1 for q in _cq if q["kind"] == "broad") == 1
        assert sum(1 for q in _cq if q["kind"] == "deep") == 3
assert len({q["qid"] for q in QUESTIONS}) == 72, "duplicate qids found"

_BY_QID = {q["qid"]: q for q in QUESTIONS}


def get_question(qid):
    """Return the question dict for qid, or None."""
    return _BY_QID.get(qid)


def get_broad_questions(age_group):
    """The 6 broad screening questions for an age group."""
    return [q for q in QUESTIONS
            if q["age_group"] == age_group and q["kind"] == "broad"]


def get_deep_questions(age_group, category):
    """The 3 deeper follow-up questions for an age group + category."""
    return [q for q in QUESTIONS
            if q["age_group"] == age_group
            and q["category"] == category
            and q["kind"] == "deep"]
