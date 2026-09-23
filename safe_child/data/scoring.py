"""Rule-based scoring engine for Safe Child behavioral screening.

Pure Python — no Reflex, no web dependencies. Safe to import anywhere.

Scoring model
-------------
- Each question has a weight: 1 (signal), 2 (medium), 3 (strong).
- Questions flagged ``double_weight`` (physical-sign items) count double,
  in both earned and maximum weight.
- Answer values: "yes" earns the full weight, "sometimes" earns half,
  "no" and "unknown" earn 0.
- score = earned_weight / max_possible_weight * 100, rounded to 1 decimal,
  where max_possible_weight covers the questions actually answered in this
  screening (the flow is adaptive: deep questions are only asked when the
  broad answer for that category signals concern).
- Bands: low 0-25, moderate 26-50, high 51-75, critical 76+.
- Any question flagged ``critical`` answered "yes" forces the whole
  screening (and its category) into the critical band, regardless of score.

Results describe indicators and next actions only — never a diagnosis,
never a claim of proof of abuse.
"""

from .questions import QUESTIONS, CATEGORIES, get_question

BANDS = ("low", "moderate", "high", "critical")

BAND_META = {
    "low": {"ur": "کم خطرہ", "en": "Low", "color": "#2AA89B"},
    "moderate": {"ur": "درمیانی توجہ", "en": "Moderate", "color": "#C99A1B"},
    "high": {"ur": "زیادہ توجہ", "en": "High", "color": "#DE7A1F"},
    "critical": {"ur": "فوری توجہ", "en": "Critical", "color": "#D64545"},
}

ACTION_TEXT = {
    "low": {
        "ur": ("اچھی خبر: اس وقت کوئی نمایاں تشویشناک علامت نظر نہیں آئی۔ "
               "بچے سے روز بات چیت جاری رکھیں، اس کی بات غور سے سنیں اور گھر میں "
               "محبت بھرا، پُرسکون ماحول برقرار رکھیں۔ اگر مستقبل میں کوئی تبدیلی "
               "محسوس ہو تو دوبارہ اسکریننگ کریں۔"),
        "en": ("Good news: no significant concerning signs at this time. "
               "Keep talking with your child every day, listen carefully, and "
               "maintain a loving, calm home environment. If you notice any "
               "change in the future, screen again."),
    },
    "moderate": {
        "ur": ("کچھ علامات توجہ چاہتی ہیں۔ بچے سے نرمی اور صبر سے بات کریں اور "
               "اسے یقین دلائیں کہ آپ اس کے ساتھ ہیں۔ روزمرہ کے معمولات — نیند، "
               "کھانا، کھیل اور اسکول — پر نظر رکھیں اور ایک دو ہفتے میں دوبارہ "
               "اسکریننگ کریں۔ یاد رکھیں: یہ نتیجہ کسی تشخیص یا ثبوت کے برابر نہیں۔"),
        "en": ("Some signs deserve attention. Talk with your child gently and "
               "patiently, and reassure them that you are there for them. "
               "Watch daily routines — sleep, meals, play, and school — and "
               "screen again in a week or two. Remember: this result is not a "
               "diagnosis or proof of anything."),
    },
    "high": {
        "ur": ("کئی علامات تشویشناک ہیں — براہِ کرم جلد توجہ دیں۔ بچے سے پُرسکون "
               "ماحول میں بات کریں، اس پر دباؤ نہ ڈالیں اور اس کی بات پر یقین "
               "کریں۔ کسی قابلِ اعتماد بڑے، استاد یا بچوں کے ماہرِ نفسیات سے "
               "مشورہ کریں۔ یہ اسکریننگ صرف رہنمائی ہے، تشخیص نہیں۔"),
        "en": ("Several signs are concerning — please act soon. Talk with your "
               "child in a calm setting, do not pressure them, and believe "
               "what they share. Consult a trusted elder, a teacher, or a "
               "child psychologist. This screening is guidance only, not a "
               "diagnosis."),
    },
    "critical": {
        "ur": ("فوری توجہ درکار ہے۔ بچے کی حفاظت کو سب سے پہلے رکھیں — اسے ہر اس "
               "شخص یا جگہ سے دور رکھیں جہاں خطرہ ہو سکتا ہے۔ چائلڈ ہیلپ لائن "
               "1121 پر فوراً کال کریں (مفت، 24/7 دستیاب)۔ پُرسکون رہیں، بچے کو "
               "قصوروار نہ ٹھہرائیں اور اس کی بات غور سے سنیں۔ یہ اسکریننگ کوئی "
               "ثبوت یا تشخیص نہیں دیتی — اصل صورتحال کا تعین متعلقہ ماہرین کریں گے۔"),
        "en": ("Immediate attention needed. Put the child's safety first — keep "
               "them away from any person or place where there may be risk. "
               "Call the Child Helpline 1121 right away (free, available 24/7). "
               "Stay calm, never blame the child, and listen carefully to what "
               "they share. This screening proves nothing and diagnoses "
               "nothing — qualified professionals will assess the actual situation."),
    },
}


def band_for_score(score):
    """Map a 0-100 score to a band name."""
    if score >= 76:
        return "critical"
    if score >= 51:
        return "high"
    if score >= 26:
        return "moderate"
    return "low"


def band_meta(band):
    """Return {"ur", "en", "color"} label info for a band."""
    return dict(BAND_META[band])


def effective_weight(question):
    """Weight counting double for double_weight questions."""
    w = question["weight"]
    return w * 2 if question.get("double_weight") else w


def earned_weight(question, answer):
    """Weight earned for one answered question."""
    w = effective_weight(question)
    if answer == "yes":
        return float(w)
    if answer == "sometimes":
        return w * 0.5
    return 0.0


def score_answers(answers):
    """Score a screening.

    Args:
        answers: dict mapping qid -> one of "yes", "sometimes", "no", "unknown".
                 Only answered questions count toward the score.

    Returns a dict with:
        score, band, critical_triggered, critical_triggers,
        per_category, answered, total_questions, action
    """
    answers = answers or {}

    total_earned = 0.0
    total_max = 0.0
    triggers = []
    answered = 0

    cat_stats = {c["key"]: {"earned": 0.0, "max": 0.0, "triggered": False}
                 for c in CATEGORIES}

    for qid, answer in answers.items():
        q = get_question(qid)
        if q is None:
            continue  # ignore unknown qids
        answered += 1
        w = effective_weight(q)
        total_max += w
        total_earned += earned_weight(q, answer)
        st = cat_stats[q["category"]]
        st["max"] += w
        st["earned"] += earned_weight(q, answer)
        if q.get("critical") and answer == "yes":
            triggers.append(qid)
            st["triggered"] = True

    score = round(total_earned / total_max * 100, 1) if total_max else 0.0
    band = band_for_score(score)
    if triggers:
        band = "critical"

    per_category = {}
    for c in CATEGORIES:
        key = c["key"]
        st = cat_stats[key]
        cscore = round(st["earned"] / st["max"] * 100, 1) if st["max"] else 0.0
        cband = band_for_score(cscore)
        if st["triggered"]:
            cband = "critical"
        per_category[key] = {"score": cscore, "band": cband}

    return {
        "score": score,
        "band": band,
        "critical_triggered": bool(triggers),
        "critical_triggers": triggers,
        "per_category": per_category,
        "answered": answered,
        "total_questions": len(QUESTIONS),
        "action": dict(ACTION_TEXT[band]),
    }
