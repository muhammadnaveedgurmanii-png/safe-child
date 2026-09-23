"""Safe Child — production app. 100% Python (Reflex), koi handwritten JS nahi."""

import os
import random
import reflex as rx
from datetime import datetime
from urllib.parse import quote


from safe_child.data import (
    AGE_GROUPS,
    CATEGORIES,
    band_meta,
    get_broad_questions,
    get_deep_questions,
    get_question,
    score_answers,
)
from safe_child import auth as auth_mod
from safe_child import db as db_mod

TEAL = "#2AA89B"

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-only-secret-change-me")

_db_available: bool | None = None


def db_ok() -> bool:
    """Supabase reachable? Cached. App fully works without it (offline/demo mode)."""
    global _db_available
    if _db_available is None:
        try:
            db_mod.get_client()
            _db_available = True
        except Exception:
            _db_available = False
    return _db_available


ANS = ["yes", "sometimes", "no", "unknown"]

OPTIONS = [
    ("ہاں، اکثر", "Yes, often", 1.0),
    ("کبھی کبھی", "Sometimes", 0.5),
    ("نہیں", "No", 0.0),
    ("مجھے معلوم نہیں", "Don't know", 0.0),
]


WIZARD = [
    ("ملزم کی تفصیل", "Accused details"),
    ("واقعہ", "Incident"),
    ("بچے کی تفصیل", "Child details"),
    ("رپورٹر", "Reporter"),
    ("اقرار نامہ", "Declaration"),
    ("کیس فائل کا جائزہ", "Case file review"),
    ("آفیشل راستے", "Official channels"),
]


ABUSE_TYPES = [
    ("جسمانی", "Physical"), ("جذباتی", "Emotional"), ("جنسی", "Sexual"),
    ("نظر انداز", "Neglect"), ("ڈیجیٹل", "Digital"),
]


RELATIONS = [
    ("والد", "Father"), ("والدہ", "Mother"), ("بھائی", "Brother"), ("بہن", "Sister"),
    ("چچا", "Uncle"), ("ماموں", "Maternal uncle"), ("دیگر رشتہ دار", "Other relative"),
]


TOUR = [
    ("پہلے علامات کو سمجھیں", "Understand signals first",
     "چھ مختصر کیٹیگریز سے شروع کریں۔ صرف وہاں مزید سوالات آئیں گے جہاں توجہ کی ضرورت ہو۔",
     "Start with six short categories. Follow-up questions appear only where closer attention may help."),
    ("رپورٹ مرحلہ وار بنائیں", "Build a report step by step",
     "سات واضح مراحل میں مصنوعی معلومات درج کریں، جائزہ لیں اور ایک ڈیمو کیس فائل تیار کریں۔",
     "Add synthetic details across seven clear steps, review them and prepare a demo case file."),
    ("مدد ہمیشہ ایک قدم دور", "Help is always one step away",
     "ہر اسکرین پر 1121 نظر آتا ہے۔ فوری خطرے میں پولیس 15 یا ریسکیو 1122 سے رابطہ کریں۔",
     "1121 stays visible on every screen. In immediate danger, call Police 15 or Rescue 1122."),
]


NEXT_STEPS = [
    ("بچے سے پرسکون وقت میں کھلے سوال پوچھیں، لیکن جواب کے لیے دباؤ نہ ڈالیں۔",
     "Ask open questions in a calm moment — never pressure for answers."),
    ("اگلے 7–14 دن اہم تبدیلیاں نوٹ کریں اور دوبارہ اسکریننگ کریں۔",
     "Note important changes over the next 7–14 days and re-screen."),
    ("اگر علامات برقرار رہیں تو بچوں کے ماہرِ نفسیات یا تربیت یافتہ کونسلر سے رابطہ کریں۔",
     "If signs persist, contact a child psychologist or trained counselor."),
]

# ---------------------------------------------------------------- state ---
class State(rx.State):
    lang: str = "ur"
    view: str = "home"
    tour_step: int = 0
    tour_done: bool = False
    dark: bool = False
    toast_msg: str = ""

    # account (Supabase; offline demo fallback)
    user_name: str = ""
    user_id: str = ""
    token: str = ""
    auth_mode: str = "login"
    in_name: str = ""
    in_contact: str = ""
    in_pass: str = ""

    # screening (adaptive, rule-based)
    age: str = "3-6"
    answers: dict[str, str] = {}
    done_cats: list[str] = []
    cur_cat: str = ""
    cur_qids: list[str] = []
    cur_qi: int = 0
    cur_q_total: int = 1
    cur_q_ur: str = ""
    cur_q_en: str = ""
    cur_q_kind: str = "broad"
    picked: int = -1
    res_score: float = 0.0
    res_band: str = ""
    res_band_ur: str = ""
    res_band_en: str = ""
    res_action_ur: str = ""
    res_action_en: str = ""
    res_critical: bool = False
    res_bars: list[str] = []
    res_triggers: list[str] = []
    my_reports: list[dict] = []

    # filing wizard
    step: int = 1
    draft_saved: bool = False
    a_name: str = ""; a_fname: str = ""; a_age: str = ""; a_photo: str = ""
    i_type: str = ""; i_date: str = ""; i_place: str = ""
    i_addr: str = ""; i_desc: str = ""
    c_name: str = ""; c_age: str = ""; c_photo: str = ""
    r_name: str = ""; r_fname: str = ""; r_cnic: str = ""
    r_phone: str = ""; r_rel: str = ""
    declaration: bool = False
    case_id: str = ""

    # ---------------- generic ----------------
    def t(self, ur: str, en: str):
        return rx.cond(self.lang == "ur", ur, en)

    def ts(self, ur: str, en: str) -> str:
        """Plain-string version for use inside event handlers."""
        return ur if self.lang == "ur" else en

    def set_field(self, field: str, value):
        setattr(self, field, value if isinstance(value, str) else str(value))

    def go(self, view: str):
        self.view = view
        self.toast_msg = ""
        if view == "history":
            self._load_history()

    def _load_history(self):
        self.my_reports = []
        if self.user_id and db_ok():
            try:
                rows = db_mod.list_reports(self.user_id)
                self.my_reports = [
                    {"case_id": r.get("case_id", ""),
                     "date": str(r.get("created_at", ""))[:10],
                     "status": r.get("status", "")}
                    for r in rows
                ]
            except Exception:
                pass

    def toggle_lang(self):
        self.lang = "en" if self.lang == "ur" else "ur"

    def toggle_dark(self):
        self.dark = not self.dark

    def toast(self, msg: str):
        self.toast_msg = msg

    def clear_toast(self):
        self.toast_msg = ""

    # ---------------- tour ----------------
    def tour_next(self):
        if self.tour_step < 2:
            self.tour_step += 1
        else:
            self.tour_done = True

    def tour_skip(self):
        self.tour_done = True

    # ---------------- account ----------------
    def set_auth_mode(self, mode: str):
        self.auth_mode = mode

    def do_auth(self):
        contact = self.in_contact.strip()
        pw = self.in_pass.strip()
        if not contact or not pw:
            self.toast_msg = self.ts("فون/ای میل اور پاس ورڈ لکھیں", "Enter phone/email and password")
            return
        if db_ok():
            try:
                if self.auth_mode == "signup":
                    if len(pw) < 6:
                        self.toast_msg = self.ts("پاس ورڈ کم از کم 6 حروف کا ہو",
                                                 "Password must be at least 6 characters")
                        return
                    row = db_mod.create_user(self.in_name.strip() or contact, contact,
                                             auth_mod.hash_password(pw))
                else:
                    row = db_mod.find_user(contact)
                    if not row or not auth_mod.verify_password(pw, row.get("pw_hash", "")):
                        self.toast_msg = self.ts("غلط فون/ای میل یا پاس ورڈ",
                                                 "Wrong phone/email or password")
                        return
                self.user_id = str(row["id"])
                self.user_name = row.get("name") or contact
                self.token = auth_mod.create_token(self.user_id, JWT_SECRET)
                self.in_name = ""; self.in_contact = ""; self.in_pass = ""
                self.toast_msg = self.ts("خوش آمدید!", "Welcome!")
                self.view = "home"
                return
            except ValueError:
                self.toast_msg = self.ts("یہ فون/ای میل پہلے سے رجسٹرڈ ہے",
                                         "This phone/email is already registered")
                return
            except Exception:
                pass  # neeche demo fallback
        self.user_id = ""
        self.user_name = self.in_name.strip() or "Demo User"
        self.token = ""
        self.in_name = ""; self.in_contact = ""; self.in_pass = ""
        self.toast_msg = self.ts("خوش آمدید! ڈیمو سیشن شروع (آف لائن)",
                                 "Welcome! Demo session started (offline)")
        self.view = "home"

    def logout(self):
        self.user_id = ""
        self.user_name = ""
        self.token = ""
        self.toast_msg = self.ts("لاگ آؤٹ ہو گیا", "Logged out")

    # ---------------- screening (adaptive) ----------------
    def set_age(self, a: str):
        if a != self.age:
            self.age = a
            self.answers = {}
            self.done_cats = []

    def start_category(self, cat: str):
        qs = [q for q in get_broad_questions(self.age) if q["category"] == cat]
        if not qs:
            return
        if cat in self.done_cats:
            self.done_cats = [c for c in self.done_cats if c != cat]
        self.cur_cat = cat
        self.cur_qids = [qs[0]["qid"]]
        self.cur_qi = 0
        self.picked = -1
        self.toast_msg = ""
        self._load_current()
        self.view = "question"

    def _load_current(self):
        q = get_question(self.cur_qids[self.cur_qi]) or {}
        self.cur_q_ur = q.get("text_ur", "")
        self.cur_q_en = q.get("text_en", "")
        self.cur_q_kind = q.get("kind", "broad")
        self.cur_q_total = len(self.cur_qids)

    def pick(self, i: int):
        self.picked = i

    def q_next(self):
        if self.picked < 0:
            self.toast_msg = self.ts("براہ کرم ایک جواب منتخب کریں", "Please choose an answer")
            return
        self.toast_msg = ""
        ans = ANS[self.picked]
        qid = self.cur_qids[self.cur_qi]
        self.answers[qid] = ans
        if self.cur_q_kind == "broad" and ans in ("yes", "sometimes"):
            for q in get_deep_questions(self.age, self.cur_cat):
                if q["qid"] not in self.cur_qids:
                    self.cur_qids.append(q["qid"])
        self.picked = -1
        if self.cur_qi + 1 < len(self.cur_qids):
            self.cur_qi += 1
            self._load_current()
        else:
            if self.cur_cat not in self.done_cats:
                self.done_cats.append(self.cur_cat)
            if len(self.done_cats) >= len(CATEGORIES):
                self._finish_screening()
            else:
                self.view = "categories"

    def q_prev(self):
        if self.cur_qi > 0:
            self.cur_qi -= 1
            self.picked = -1
            self._load_current()
        else:
            self.view = "categories"

    def restart_screening(self):
        self.answers = {}
        self.done_cats = []
        self.cur_cat = ""
        self.cur_qids = []
        self.cur_qi = 0
        self.picked = -1
        self.res_band = ""
        self.view = "categories"

    def finish_early(self):
        if len(self.done_cats) > 0:
            self._finish_screening()
        else:
            self.toast_msg = self.ts("پہلے کم از کم ایک کیٹیگری مکمل کریں",
                                     "Complete at least one category first")

    def _finish_screening(self):
        res = score_answers(dict(self.answers))
        meta = band_meta(res["band"])
        self.res_score = res["score"]
        self.res_band = res["band"]
        self.res_band_ur = meta["ur"]
        self.res_band_en = meta["en"]
        self.res_action_ur = res["action"]["ur"]
        self.res_action_en = res["action"]["en"]
        self.res_critical = res["critical_triggered"]
        self.res_triggers = res["critical_triggers"]
        self.res_bars = [f'{res["per_category"][c["key"]]["score"]}%'
                         for c in CATEGORIES]
        self.view = "report"
        if db_ok():
            try:
                db_mod.save_screening(self.user_id or None, {
                    "age_group": self.age,
                    "answers": dict(self.answers),
                    "score": res["score"],
                    "band": res["band"],
                    "critical": res["critical_triggered"],
                })
            except Exception:
                pass

    @rx.var
    def score_str(self) -> str:
        return f"{self.res_score}%"

    @rx.var
    def done_count(self) -> int:
        return len(self.done_cats)

    @rx.var
    def wa_share(self) -> str:
        txt = (f"Safe Child screening: {self.res_band_en or self.res_band} "
               f"({self.res_score}%). Child helpline 1121.")
        return "https://wa.me/?text=" + quote(txt)

    # ---------------- filing ----------------
    def start_filing(self):
        self.step = 1
        self.view = "filing"

    def next_step(self):
        if self.step == 5 and not self.declaration:
            self.toast_msg = self.ts("آگے بڑھنے کے لیے اقرار نامہ قبول کریں",
                                    "Accept the declaration to continue")
            return
        self.toast_msg = ""
        if self.step < 7:
            self.step += 1
            if self.step == 6 and not self.case_id:
                self.case_id = f"SC-2026-{random.randint(1000, 9999)}"
                self._save_report_db("ready")

    def _save_report_db(self, status: str):
        if not self.case_id or not db_ok():
            return
        try:
            db_mod.save_report(self.user_id or None, self.case_id, {
                "accused": {"name": self.a_name, "father": self.a_fname,
                            "age": self.a_age, "photo": self.a_photo},
                "incident": {"type": self.i_type, "date": self.i_date,
                             "place": self.i_place, "address": self.i_addr,
                             "desc": self.i_desc},
                "child": {"name": self.c_name, "age": self.c_age,
                          "photo": self.c_photo},
                "reporter": {"name": self.r_name, "father": self.r_fname,
                             "cnic": self.r_cnic, "phone": self.r_phone,
                             "relation": self.r_rel},
                "declaration": self.declaration,
                "filed_at": datetime.now().isoformat(),
            })
            db_mod.update_report_status(self.case_id, status)
        except Exception:
            pass

    def prev_step(self):
        if self.step > 1:
            self.step -= 1

    def save_draft(self):
        self.draft_saved = True
        if self.case_id:
            self._save_report_db("draft")
        self.toast_msg = self.ts("مسودہ اس سیشن میں محفوظ", "Draft saved in this session")

    def set_abuse_type(self, v: str):
        self.i_type = v

    def set_relation(self, v: str):
        self.r_rel = v

    def toggle_declaration(self):
        self.declaration = not self.declaration

    def set_declaration(self, v: bool):
        self.declaration = bool(v)

    async def on_accused_photo(self, files: list[rx.UploadFile]):
        for f in files:
            data = await f.read()
            (rx.get_upload_dir() / f.filename).write_bytes(data)
            self.a_photo = f.filename

    async def on_child_photo(self, files: list[rx.UploadFile]):
        for f in files:
            data = await f.read()
            (rx.get_upload_dir() / f.filename).write_bytes(data)
            self.c_photo = f.filename

    @rx.var
    def case_ts(self) -> str:
        return datetime.now().strftime("%d %b %Y • %I:%M %p")

    @rx.var
    def case_download(self) -> str:
        html = f"""<html><head><meta charset='utf-8'><title>Case File {self.case_id}</title></head>
<body style='font-family:sans-serif;max-width:600px;margin:20px auto'>
<h2>Safe Child — Case File</h2>
<p><b>Case ID:</b> {self.case_id}<br><b>Date:</b> {self.case_ts}</p>
<h3>Accused (MULZIM)</h3><p>Name: {self.a_name}<br>Father: {self.a_fname}<br>Age: {self.a_age}</p>
<h3>Incident</h3><p>Type: {self.i_type}<br>Date: {self.i_date}<br>Place: {self.i_place}<br>{self.i_desc}</p>
<h3>Child (MUTASIRA)</h3><p>Name: {self.c_name}<br>Age: {self.c_age}</p>
<h3>Reporter</h3><p>Name: {self.r_name}<br>CNIC: {self.r_cnic}<br>Phone: {self.r_phone}</p>
<p><i>Demo file — synthetic data only. Not submitted to any authority.</i></p>
</body></html>"""
        return "data:text/html;charset=utf-8," + quote(html)


def T(ur: str, en: str):
    return rx.cond(State.lang == "ur", ur, en)

# ---------------------------------------------------------- components ----
def shield_svg(size=22):
    return rx.html(
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round"><path d="M12 3 20 6v5c0 5-3 8-8 11-5-3-8-6-8-11V6Z"/>'
        '<path d="M8.5 12 11 14.5 15.8 9"/></svg>'
    )


def topbar():
    return rx.box(
        rx.button(
            rx.el.span(shield_svg(), class_name="sc-shield"),
            rx.el.span(
                rx.el.b("Safe Child"),
                rx.el.small("Child Safety • Pakistan"),
            ),
            class_name="sc-brand",
            on_click=State.go("home"),
        ),
        rx.box(
            rx.button(
                rx.cond(State.user_name != "",
                        rx.text(State.user_name[:1]),
                        rx.icon("user", size=16)),
                rx.text(rx.cond(State.user_name != "",
                                State.user_name,
                                T("لاگ اِن", "Log in"))),
                class_name="sc-pill",
                on_click=State.go("account"),
            ),
            rx.button(
                rx.cond(State.dark, rx.icon("sun", size=17), rx.icon("moon", size=17)),
                class_name="sc-iconbtn",
                on_click=State.toggle_dark,
                title="Dark mode",
            ),
            rx.button(
                T("English", "اردو"),
                class_name="sc-pill",
                on_click=State.toggle_lang,
            ),
            class_name="sc-top-actions",
        ),
        class_name="sc-topbar",
    )


def helpline():
    return rx.link(
        rx.icon("phone-call", size=18),
        rx.text(T("چائلڈ ہیلپ لائن 1121 — مفت، 24/7",
                  "Child helpline 1121 — free, 24/7")),
        href="tel:1121",
        class_name="sc-helpline",
    )


def navrow():
    tabs = [
        ("home", "گھر", "Home"),
        ("categories", "اسکریننگ", "Screening"),
        ("filing", "رپورٹ درج کریں", "File report"),
        ("report", "اسکریننگ نتیجہ", "Screening result"),
        ("resources", "مدد", "Help"),
        ("history", "My Reports", "My Reports"),
    ]
    return rx.box(
        *[
            rx.button(
                T(ur, en),
                class_name=rx.cond(State.view == v, "sc-navbtn active", "sc-navbtn"),
                on_click=State.go(v),
            )
            for v, ur, en in tabs
        ],
        class_name="sc-navrow",
    )


def _tour_title():
    return rx.cond(
        State.tour_step == 0, T(TOUR[0][0], TOUR[0][1]),
        rx.cond(State.tour_step == 1, T(TOUR[1][0], TOUR[1][1]),
                T(TOUR[2][0], TOUR[2][1])))


def _tour_copy():
    return rx.cond(
        State.tour_step == 0, T(TOUR[0][2], TOUR[0][3]),
        rx.cond(State.tour_step == 1, T(TOUR[1][2], TOUR[1][3]),
                T(TOUR[2][2], TOUR[2][3])))


def tour_overlay():
    return rx.cond(
        ~State.tour_done,
        rx.box(
            rx.box(
                rx.box(class_name="sc-mascot"),
                rx.el.div(
                    rx.cond(State.tour_step == 0, "1 / 3",
                    rx.cond(State.tour_step == 1, "2 / 3", "3 / 3")),
                    class_name="sc-tour-count"),
                rx.el.h2(_tour_title()),
                rx.el.p(_tour_copy()),
                rx.box(
                    rx.el.i(class_name=rx.cond(State.tour_step == 0, "active", "")),
                    rx.el.i(class_name=rx.cond(State.tour_step == 1, "active", "")),
                    rx.el.i(class_name=rx.cond(State.tour_step == 2, "active", "")),
                    class_name="sc-dots",
                ),
                rx.box(
                    rx.button(T("ابھی چھوڑ دیں", "Skip for now"),
                              class_name="sc-btn ghost", on_click=State.tour_skip),
                    rx.button(
                        rx.cond(State.tour_step == 2,
                                T("شروع کریں", "Get started"), T("اگلا", "Next")),
                        class_name="sc-btn", on_click=State.tour_next),
                    class_name="sc-tour-actions",
                ),
                class_name="sc-tour-card",
            ),
            class_name="sc-tour",
        ),
        rx.fragment(),
    )


def bottomnav():
    tabs = [
        ("home", "house", "گھر", "Home"),
        ("categories", "clipboard-list", "اسکریننگ", "Screening"),
        ("filing", "file-text", "رپورٹ", "Report"),
        ("resources", "life-buoy", "مدد", "Help"),
        ("history", "folder", "میری رپورٹس", "My Reports"),
    ]
    return rx.box(
        *[
            rx.button(
                rx.icon(ic, size=20),
                rx.el.span(T(ur, en)),
                class_name=rx.cond(State.view == v, "sc-tab active", "sc-tab"),
                on_click=State.go(v),
            )
            for v, ic, ur, en in tabs
        ],
        class_name="sc-bottomnav",
    )


def toast():
    return rx.cond(
        State.toast_msg != "",
        rx.box(
            rx.text(State.toast_msg),
            class_name="sc-toast",
            on_click=State.clear_toast,
        ),
        rx.fragment(),
    )


def demo_note():
    return rx.box(
        T("یہ ڈیمو صرف مصنوعی معلومات دکھاتا ہے — کہیں بھیجا نہیں جاتا۔",
          "This demo shows synthetic data only — nothing is sent anywhere."),
        class_name="sc-demo-note",
    )

# ---------------------------------------------------------------- views ---
def home_view():
    return rx.box(
        rx.box(
            rx.el.h1(T("آج ہم آپ کے بچے کی حفاظت میں کیسے مدد کر سکتے ہیں؟",
                       "How can we help keep your child safe today?")),
            rx.el.p(T("چند احتیاط سے منتخب سوالات کے ذریعے رویّے، جذبات اور جسمانی علامات "
                      "کو بہتر انداز میں سمجھیں — بغیر کسی فیصلے یا تشخیص کے۔",
                      "Understand behavior, feelings and physical signs through a few careful "
                      "questions — with no judgement or diagnosis.")),
            class_name="sc-hero",
        ),
        rx.box(
            rx.button(
                rx.el.span(rx.icon("clipboard-list", size=26), class_name="ic"),
                rx.el.span(
                    rx.el.b(T("رویّوں کی اسکریننگ", "Behavioral Screening")),
                    rx.el.small(T("علامات سمجھیں، نرم اگلے قدم پائیں",
                                   "Know the signs, get gentle next steps")),
                ),
                rx.icon("chevron-right", size=20, class_name="chev"),
                class_name="sc-card",
                on_click=State.go("categories"),
            ),
            rx.button(
                rx.el.span(rx.icon("file-text", size=26), class_name="ic"),
                rx.el.span(
                    rx.el.b(T("رپورٹ درج کریں", "File a Report")),
                    rx.el.small(T("سات مراحل میں کیس فائل تیار کریں",
                                   "Prepare a case file in seven steps")),
                ),
                rx.icon("chevron-right", size=20, class_name="chev"),
                class_name="sc-card",
                on_click=State.start_filing,
            ),
            rx.cond(
                State.draft_saved,
                rx.button(
                    rx.el.span(rx.icon("history", size=26), class_name="ic"),
                    rx.el.span(
                        rx.el.b(T("ادھوری رپورٹ جاری رکھیں", "Resume draft report")),
                        rx.el.small(T("یہ مسودہ صرف اس کھلے سیشن میں موجود ہے",
                                       "This draft exists only in this open session")),
                    ),
                    rx.icon("chevron-right", size=20, class_name="chev"),
                    class_name="sc-card",
                    on_click=State.go("filing"),
                ),
                rx.fragment(),
            ),
            rx.button(
                rx.el.span(rx.icon("life-buoy", size=26), class_name="ic"),
                rx.el.span(
                    rx.el.b(T("مدد کے ذرائع دیکھیں", "See help resources")),
                    rx.el.small(T("ہیلپ لائنز اور رہنمائی",
                                   "Helplines and guidance")),
                ),
                rx.icon("chevron-right", size=20, class_name="chev"),
                class_name="sc-card",
                on_click=State.go("resources"),
            ),
            rx.button(
                rx.el.span(rx.icon("user", size=26), class_name="ic"),
                rx.el.span(
                    rx.el.b(T("لاگ اِن / اکاؤنٹ بنائیں", "Log in / Create account")),
                    rx.el.small(T("اکاؤنٹ اختیاری ہے", "Account is optional")),
                ),
                rx.icon("chevron-right", size=20, class_name="chev"),
                class_name="sc-card",
                on_click=State.go("account"),
            ),
            class_name="sc-cards",
        ),
        rx.box(
            rx.el.span(T("کوئی نام درکار نہیں", "No name needed"), class_name="sc-chip"),
            rx.el.span(T("تقریباً 5–7 منٹ", "About 5–7 min"), class_name="sc-chip"),
            rx.el.span(T("اردو اور English", "Urdu and English"), class_name="sc-chip"),
            class_name="sc-chips",
        ),
        rx.box(
            rx.icon("lock", size=14),
            rx.text(T("آپ کی معلومات آپ کے فون میں رہتی ہیں",
                      "Your data stays on your phone")),
            class_name="sc-note",
        ),
    )


def categories_view():
    return rx.box(
        rx.box(
            rx.el.h2(T("آج آپ نے کیا محسوس کیا؟", "What have you noticed today?")),
            rx.el.p(T("ہر کیٹیگری ایک مختصر ابتدائی سوال سے شروع ہوگی۔ "
                      "صرف ضروری جگہ پر مزید سوالات آئیں گے۔",
                      "Each category starts with one short opening question. "
                      "More questions appear only where needed."),
                    class_name="sub"),
            class_name="sc-sec",
        ),
        rx.box(
            rx.el.h2(T("بچے کی عمر", "Child's age"), style={"font_size": "15px"}),
            rx.box(
                *[
                    rx.button(
                        a,
                        class_name=rx.cond(State.age == a, "sc-type sel", "sc-type"),
                        on_click=State.set_age(a),
                    )
                    for a in AGE_GROUPS
                ],
                class_name="sc-agepills",
            ),
            rx.el.p(
                State.done_count.to_string() + " / 6 "
                + T("کیٹیگریز مکمل", "categories done"),
                style={"font_size": "12.5px", "color": "var(--muted)",
                       "margin_top": "8px"}),
            class_name="sc-sec",
            style={"padding_top": "0"},
        ),
        rx.box(
            *[
                rx.button(
                    rx.el.span(rx.icon(c["icon"], size=22), class_name="ic"),
                    rx.el.b(T(c["ur"], c["en"])),
                    rx.el.small(rx.cond(
                        State.done_cats.contains(c["key"]),
                        T("✓ مکمل", "✓ Done"),
                        T("شروع کریں", "Start"))),
                    class_name="sc-cat",
                    on_click=State.start_category(c["key"]),
                )
                for c in CATEGORIES
            ],
            class_name="sc-grid",
            style={"padding": "0 14px 14px"},
        ),
        rx.cond(
            State.done_count > 0,
            rx.box(
                rx.button(T("نتیجہ دیکھیں", "See result"),
                          class_name="sc-btn block",
                          on_click=State.finish_early),
                style={"padding": "0 14px 14px"},
            ),
            rx.fragment(),
        ),
    )

def question_view():
    return rx.box(
        rx.box(
            rx.button(T("→ واپس", "→ Back"), class_name="sc-back",
                      on_click=State.q_prev),
            rx.box(
                T("آپ اچھا کر رہے ہیں — جلدی کی ضرورت نہیں۔",
                  "You're doing well — no rush."),
                class_name="sc-reassure",
            ),
            rx.el.div(
                rx.el.span(State.cur_qi + 1),
                " / ",
                rx.el.span(State.cur_q_total),
                rx.el.span(
                    rx.cond(State.cur_q_kind == "broad",
                            T(" — ابتدائی سوال", " — opening question"),
                            T(" — مزید تفصیل", " — follow-up")),
                    style={"color": "var(--muted)"}),
                style={"font_size": "12.5px", "color": "var(--muted)",
                       "margin_bottom": "8px"},
            ),
            rx.box(
                rx.el.p(T(State.cur_q_ur, State.cur_q_en)),
                class_name="sc-qbox",
            ),
            rx.box(
                *[
                    rx.button(
                        T(ur, en),
                        class_name=rx.cond(State.picked == i, "sc-opt sel", "sc-opt"),
                        on_click=State.pick(i),
                    )
                    for i, (ur, en, _m) in enumerate(OPTIONS)
                ],
                class_name="sc-opts",
            ),
            rx.box(
                rx.button(T("اگلا", "Next"), class_name="sc-btn",
                          on_click=State.q_next),
                class_name="sc-qnav",
            ),
            class_name="sc-sec",
        ),
    )

def _field(label_ur, label_en, comp):
    return rx.box(
        rx.el.label(T(label_ur, label_en)),
        comp,
        class_name="sc-field",
    )


def _photo_box(photo_var, label_ur, label_en, tag_ur, tag_en, on_drop):
    return rx.box(
        rx.cond(
            photo_var != "",
            rx.image(src=rx.get_upload_url(photo_var),
                     style={"width": "100%", "height": "100%", "object_fit": "cover"}),
            rx.box(
                rx.icon("camera", size=22),
                rx.el.b(T(tag_ur, tag_en)),
                rx.el.span(T("تصویر شامل کریں", "Add photo"),
                           style={"font_size": "11px"}),
                style={"display": "flex", "flex_direction": "column",
                       "align_items": "center", "gap": "6px"},
            ),
        ),
        rx.upload(
            rx.button(T("تصویر منتخب کریں", "Choose photo"),
                      class_name="sc-pill", size="1"),
            on_drop=on_drop,
            max_files=1,
            style={"margin_top": "8px"},
        ),
        rx.el.div(T(label_ur, label_en),
                  style={"font_size": "12px", "color": "var(--muted)",
                         "margin_top": "6px", "text_align": "center"}),
    )


def filing_step_content():
    return rx.match(
        State.step,
        (1, rx.box(
            rx.el.h2(T("ملزم کی بنیادی تفصیل", "Accused: basic details")),
            rx.el.p(T("صرف وہ معلومات شامل کریں جو آپ کے علم میں درست ہوں۔ تمام نظر آنے والا ڈیٹا مصنوعی ہے۔",
                      "Only include what you know to be correct. All visible data is synthetic."),
                    class_name="sub"),
            _field("نام", "Name", rx.input(value=State.a_name,
                   on_change=lambda v: State.set_field("a_name", v),
                   placeholder=T("مصنوعی نام", "Synthetic name"))),
            _field("والد کا نام", "Father's name", rx.input(value=State.a_fname,
                   on_change=lambda v: State.set_field("a_fname", v))),
            _field("عمر (1–100)", "Age (1–100)", rx.input(value=State.a_age,
                   on_change=lambda v: State.set_field("a_age", v), type="number")),
            _photo_box(State.a_photo, "تصویر (اگر دستیاب ہو) — صرف اسی سیشن میں پیش نظارہ",
                       "Photo (if available) — preview in this session only",
                       "ملزم", "MULZIM", State.on_accused_photo),
        )),
        (2, rx.box(
            rx.el.h2(T("واقعہ کی تفصیل", "Incident details")),
            rx.el.p(T("قسم، تاریخ اور جگہ درج کریں۔ اندازہ لگانے کے بجائے غیر معلوم بات خالی چھوڑیں۔",
                      "Enter type, date and place. Leave unknown things blank instead of guessing."),
                    class_name="sub"),
            rx.el.label(T("بدسلوکی کی قسم", "Type of abuse"),
                        style={"font_size": "13.5px", "font_weight": "700",
                               "display": "block", "margin_bottom": "6px"}),
            rx.box(
                *[rx.button(T(ur, en),
                            class_name=rx.cond(State.i_type == ur, "sc-type sel", "sc-type"),
                            on_click=State.set_abuse_type(ur))
                  for ur, en in ABUSE_TYPES],
                class_name="sc-typerow", style={"margin_bottom": "14px"}),
            _field("تاریخ", "Date", rx.input(value=State.i_date,
                   on_change=lambda v: State.set_field("i_date", v), type="date")),
            _field("جگہ", "Place", rx.input(value=State.i_place,
                   on_change=lambda v: State.set_field("i_place", v),
                   placeholder=T("مثلاً گھر، اسکول، محلہ", "e.g. home, school, street"))),
            _field("پتہ", "Address", rx.input(value=State.i_addr,
                   on_change=lambda v: State.set_field("i_addr", v))),
            _field("مختصر تفصیل", "Brief description",
                   rx.text_area(value=State.i_desc, on_change=lambda v: State.set_field("i_desc", v),
                                placeholder=T("مصنوعی مثال — صرف انٹرفیس کے لیے",
                                              "Synthetic example for interface preview only"))),
        )),
        (3, rx.box(
            rx.el.h2(T("بچے کی تفصیل", "Child details")),
            rx.el.p(T("تصویر اختیاری ہے اور اس ڈیمو میں کہیں اپ لوڈ نہیں ہوتی۔",
                      "Photo is optional and is not uploaded anywhere in this demo."),
                    class_name="sub"),
            _field("نام", "Name", rx.input(value=State.c_name,
                   on_change=lambda v: State.set_field("c_name", v))),
            _field("عمر", "Age", rx.input(value=State.c_age,
                   on_change=lambda v: State.set_field("c_age", v), type="number")),
            _photo_box(State.c_photo, "بچے کی تصویر (اختیاری)",
                       "Child's photo (optional)",
                       "متاثرہ", "MUTASIRA", State.on_child_photo),
        )),
        (4, rx.box(
            rx.el.h2(T("رپورٹ کرنے والے کی تفصیل", "Reporter details")),
            rx.el.p(T("رشتہ داروں تک محدود — شناخت رپورٹ کو قابلِ سراغ رکھتی ہے۔",
                      "Limited to relatives — identity keeps the report traceable."),
                    class_name="sub"),
            _field("نام", "Name", rx.input(value=State.r_name,
                   on_change=lambda v: State.set_field("r_name", v))),
            _field("والد کا نام", "Father's name", rx.input(value=State.r_fname,
                   on_change=lambda v: State.set_field("r_fname", v))),
            _field("CNIC", "CNIC", rx.input(value=State.r_cnic,
                   on_change=lambda v: State.set_field("r_cnic", v), placeholder="35202-1234567-1")),
            _field("فون", "Phone", rx.input(value=State.r_phone,
                   on_change=lambda v: State.set_field("r_phone", v), placeholder="03xx-xxxxxxx")),
            rx.el.label(T("بچے سے رشتہ", "Relationship to child"),
                        style={"font_size": "13.5px", "font_weight": "700",
                               "display": "block", "margin_bottom": "6px"}),
            rx.box(
                *[rx.button(T(ur, en),
                            class_name=rx.cond(State.r_rel == ur, "sc-type sel", "sc-type"),
                            on_click=State.set_relation(ur))
                  for ur, en in RELATIONS],
                class_name="sc-typerow"),
        )),
        (5, rx.box(
            rx.el.h2(T("اقرار نامہ", "Declaration of truthfulness")),
            rx.el.p(T("جھوٹی رپورٹ قانونی نتائج رکھ سکتی ہے۔",
                      "A false report can have legal consequences."),
                    class_name="sub"),
            rx.box(
                rx.checkbox(checked=State.declaration,
                            on_change=State.set_declaration),
                rx.el.span(T("میں اقرار کرتا/کرتی ہوں کہ درج کردہ معلومات میرے علم کے مطابق درست ہیں۔",
                             "I declare that the information provided is true to my knowledge."),
                           on_click=State.toggle_declaration,
                           style={"cursor": "pointer"}),
                class_name="sc-check",
            ),
        )),
        (6, case_review()),
        (7, filing_actions()),
        rx.box(),
    )


def case_review():
    def kv(k_ur, k_en, v):
        return rx.box(
            rx.el.span(T(k_ur, k_en)),
            rx.el.span(rx.text(v)),
            class_name="sc-kv",
        )
    return rx.box(
        rx.el.h2(T("کیس فائل کا جائزہ", "Case file review")),
        rx.box(
            rx.el.h3("Safe Child — ", T("کیس فائل", "Case File")),
            rx.box(rx.text(State.case_id), class_name="cid"),
            rx.box(rx.text(State.case_ts), class_name="ts"),
            rx.box(
                rx.box(
                    rx.cond(
                        State.a_photo != "",
                        rx.image(src=rx.get_upload_url(State.a_photo)),
                        rx.box(rx.icon("user", size=26)),
                    ),
                    rx.el.div(T("ملزم", "MULZIM"),
                              style={"font_size": "12px", "font_weight": "700",
                                     "color": "var(--teal-dark)", "margin_top": "6px"}),
                    class_name="sc-photo",
                ),
                rx.box(
                    rx.cond(
                        State.c_photo != "",
                        rx.image(src=rx.get_upload_url(State.c_photo)),
                        rx.box(rx.icon("user", size=26)),
                    ),
                    rx.el.div(T("متاثرہ", "MUTASIRA"),
                              style={"font_size": "12px", "font_weight": "700",
                                     "color": "var(--teal-dark)", "margin_top": "6px"}),
                    class_name="sc-photo",
                ),
                class_name="sc-photos",
            ),
            kv("ملزم کا نام", "Accused name", State.a_name),
            kv("واقعے کی قسم", "Incident type", State.i_type),
            kv("تاریخ", "Date", State.i_date),
            kv("جگہ", "Place", State.i_place),
            kv("بچے کا نام", "Child name", State.c_name),
            kv("رپورٹر", "Reporter", State.r_name),
            kv("رشتہ", "Relationship", State.r_rel),
            class_name="sc-case",
        ),
    )


def filing_actions():
    return rx.box(
        rx.el.h2(T("آفیشل راستے", "Official channels")),
        rx.el.p(T("یہ ڈیمو رپورٹ براہِ راست جمع نہیں کرتا۔ کیس فائل ڈاؤن لوڈ کریں اور متعلقہ پورٹل پر خود جمع کروائیں۔",
                  "This demo does not submit the report directly. Download the case file and submit it yourself on the relevant portal."),
                class_name="sub"),
        rx.link(
            rx.icon("download", size=18),
            rx.text(T("کیس فائل ڈاؤن لوڈ کریں", "Download case file")),
            href=State.case_download,
            download="safe-child-case-file.html",
            class_name="sc-call",
            style={"display": "inline-flex", "margin_bottom": "12px"},
        ),
        rx.box(
            rx.link(T("FIA سائبر کرائم پورٹل", "FIA Cybercrime Portal"),
                    href="https://complaint.fia.gov.pk", is_external=True,
                    class_name="sc-call alt"),
            rx.link(T("پنجاب پولیس", "Punjab Police"),
                    href="https://punjabpolice.gov.pk", is_external=True,
                    class_name="sc-call alt"),
            rx.link(rx.icon("phone-call", size=18), rx.text("1121"),
                    href="tel:1121", class_name="sc-call"),
            class_name="sc-callrow",
        ),
    )


def filing_view():
    return rx.box(
        rx.box(
            rx.el.h2(T("رپورٹ درج کریں", "File a report")),
            rx.el.p(T("سات واضح مراحل میں معلومات جمع کریں، جائزہ لیں اور آفیشل پورٹل کے لیے کیس فائل تیار کریں۔",
                      "Collect information in seven clear steps, review it and prepare a case file for the official portal."),
                    class_name="sub"),
            rx.button(T("مسودہ محفوظ کریں", "Save draft"),
                      class_name="sc-btn outline", on_click=State.save_draft,
                      style={"margin_bottom": "10px"}),
            demo_note(),
            rx.box(
                *[rx.box(
                    rx.box(class_name="bar"),
                    rx.el.span(T(ur, en)),
                    class_name=rx.cond(
                        State.step == i + 1, "sc-step now",
                        rx.cond(State.step > i + 1, "sc-step done", "sc-step")),
                  )
                  for i, (ur, en) in enumerate(WIZARD)],
                class_name="sc-steps",
            ),
            rx.el.div(
                T("مرحلہ", "Step"),
                rx.text(f" {State.step} / 7 — "),
                rx.cond(State.step == 1, T(*WIZARD[0]),
                rx.cond(State.step == 2, T(*WIZARD[1]),
                rx.cond(State.step == 3, T(*WIZARD[2]),
                rx.cond(State.step == 4, T(*WIZARD[3]),
                rx.cond(State.step == 5, T(*WIZARD[4]),
                rx.cond(State.step == 6, T(*WIZARD[5]),
                        T(*WIZARD[6]))))))),
                style={"font_weight": "700", "margin_bottom": "12px"}),
            filing_step_content(),
            rx.box(
                rx.button(T("پچھلا", "Previous"), class_name="sc-btn outline",
                          on_click=State.prev_step, disabled=State.step == 1),
                rx.cond(
                    State.step < 7,
                    rx.button(T("اگلا", "Next"), class_name="sc-btn",
                              on_click=State.next_step),
                    rx.fragment(),
                ),
                class_name="sc-qnav",
            ),
            class_name="sc-sec",
        ),
    )

def report_view():
    return rx.cond(
        State.res_band != "",
        rx.box(
            demo_note(),
            rx.cond(
                State.res_critical,
                rx.link(
                    rx.el.b(T("فوری توجہ: بچے کی حفاظت پہلے — 1121 پر کال کریں",
                              "Urgent: child's safety first — call 1121")),
                    href="tel:1121",
                    class_name="sc-critical",
                    style={"display": "block", "text_decoration": "none"},
                ),
                rx.fragment(),
            ),
            rx.box(
                rx.el.div(T("مجموعی اسکور", "Overall score"),
                          style={"font_size": "14px", "opacity": ".9"}),
                rx.el.div(rx.text(State.score_str),
                          class_name="score"),
                rx.el.div(T(State.res_band_ur, State.res_band_en),
                          style={"font_size": "20px", "font_weight": "800"}),
                rx.el.div(T(State.res_action_ur, State.res_action_en),
                          style={"font_size": "13.5px", "opacity": ".92",
                                 "line_height": "2", "margin_top": "6px"}),
                class_name=rx.cond(
                    State.res_band == "low", "sc-band low",
                    rx.cond(State.res_band == "moderate", "sc-band moderate",
                    rx.cond(State.res_band == "high", "sc-band high",
                            "sc-band critical"))),
            ),
            rx.el.p(T("یہ نتیجہ کسی تشخیص یا ثبوت کے طور پر نہیں — صرف توجہ کے قابل علامات کی نشاندہی کرتا ہے۔",
                      "This result is not a diagnosis or proof — it only flags signs worth attention."),
                    class_name="sub", style={"text_align": "center"}),
            rx.el.h2(T("کیٹیگری کے لحاظ سے", "By category"),
                     style={"font_size": "16px"}),
            rx.box(
                *[
                    rx.box(
                        rx.el.span(T(c["ur"], c["en"]),
                                   class_name="lbl"),
                        rx.box(
                            rx.el.i(style={
                                "width": State.res_bars[i]}),
                            class_name="sc-bar",
                        ),
                        rx.el.span(rx.text(State.res_bars[i]),
                                   style={"font_size": "12px",
                                          "color": "var(--muted)",
                                          "min_width": "44px"}),
                        class_name="sc-bar-row",
                    )
                    for i, c in enumerate(CATEGORIES)
                ],
                class_name="sc-bars",
            ),
            rx.el.h2(T("اگلے نرم قدم", "Gentle next steps"),
                     style={"font_size": "16px"}),
            rx.box(
                *[rx.box(rx.el.b(f"{i + 1}"), rx.el.span(T(ur, en)),
                         class_name="stp")
                  for i, (ur, en) in enumerate(NEXT_STEPS)],
                class_name="sc-steps-list",
            ),
            rx.box(
                rx.link(
                    rx.icon("share-2", size=18),
                    rx.text("WhatsApp"),
                    href=State.wa_share, is_external=True,
                    class_name="sc-call alt",
                    style={"display": "inline-flex", "text_decoration": "none"}),
                rx.button(T("مدد کے ذرائع", "Help resources"),
                          class_name="sc-btn outline",
                          on_click=State.go("resources")),
                rx.button(T("نئی اسکریننگ", "New screening"),
                          class_name="sc-btn ghost",
                          on_click=State.restart_screening),
                class_name="sc-callrow",
                style={"margin_top": "6px"},
            ),
            class_name="sc-sec",
        ),
        rx.box(
            rx.el.h2(T("اسکریننگ نتیجہ", "Screening result")),
            rx.el.p(T("پہلے اسکریننگ مکمل کریں — چھ مختصر کیٹیگریز، تقریباً 5 منٹ۔",
                      "Complete the screening first — six short categories, about 5 minutes."),
                    class_name="sub"),
            rx.button(T("اسکریننگ شروع کریں", "Start screening"),
                      class_name="sc-btn block", on_click=State.go("categories")),
            class_name="sc-sec",
        ),
    )

def resources_view():
    return rx.box(
        rx.el.h2(T("مدد آپ کے قریب ہے", "Help is near you")),
        rx.el.p(T("فوری خطرے، آن لائن ہراسانی یا اگلے قدم کی رہنمائی کے لیے درست رابطہ منتخب کریں۔",
                  "Choose the right contact for immediate danger, online harassment, or next-step guidance."),
                class_name="sub"),
        rx.box(
            rx.el.h4(T("فوری ایمرجنسی", "Immediate emergency")),
            rx.el.p(T("فوری خطرے میں پولیس 15 یا ریسکیو 1122 سے رابطہ کریں۔ بچوں کے تحفظ کی رہنمائی کے لیے 1121 جہاں دستیاب ہو۔",
                      "In immediate danger call Police 15 or Rescue 1122. For child-protection guidance call 1121 where available.")),
            rx.box(
                rx.link(rx.icon("phone-call", size=16), rx.text("15"),
                        href="tel:15", class_name="sc-call"),
                rx.link(rx.icon("phone-call", size=16), rx.text("1122"),
                        href="tel:1122", class_name="sc-call"),
                rx.link(rx.icon("phone-call", size=16), rx.text("1121"),
                        href="tel:1121", class_name="sc-call"),
                class_name="sc-callrow",
            ),
            class_name="sc-res",
        ),
        rx.box(
            rx.el.h4(T("FIA سائبر کرائم", "FIA Cybercrime")),
            rx.el.p(T("آن لائن بلیک میلنگ، ہراسانی، استحصال یا مشکوک ڈیجیٹل رابطے کے لیے۔",
                      "For online blackmail, harassment, exploitation or suspicious digital contact.")),
            rx.box(
                rx.link(rx.icon("phone-call", size=16), rx.text("1991"),
                        href="tel:1991", class_name="sc-call alt"),
                rx.link(T("complaint.fia.gov.pk", "complaint.fia.gov.pk"), href="https://complaint.fia.gov.pk",
                        is_external=True, class_name="sc-call alt"),
                class_name="sc-callrow",
            ),
            class_name="sc-res",
        ),
        rx.box(
            rx.el.b(T("پرسکون رہیں", "Stay calm")),
            rx.el.span(T(" — بچے کو یقین دلائیں کہ اس کی بات سننا اور حفاظت کرنا آپ کی ترجیح ہے۔",
                         " — reassure the child that hearing them and keeping them safe is your priority.")),
            class_name="sc-tip",
        ),
        rx.box(
            rx.el.b(T("الفاظ نہ ڈالیں", "Don't put words in")),
            rx.el.span(T(" — کھلے سوال پوچھیں؛ بچے کے منہ میں الفاظ یا کوئی مخصوص جواب نہ ڈالیں۔",
                         " — ask open questions; don't suggest words or a specific answer.")),
            class_name="sc-tip",
        ),
        rx.box(
            rx.el.b(T("فوری حفاظت", "Immediate safety")),
            rx.el.span(T(" — اگر خطرہ فوری ہو تو بچے کو محفوظ جگہ پر لے جائیں اور متعلقہ ہیلپ لائن سے رابطہ کریں۔",
                         " — if danger is immediate, move the child somewhere safe and call the helpline.")),
            class_name="sc-tip",
        ),
        class_name="sc-sec",
    )


def account_view():
    return rx.cond(
        State.user_name != "",
        rx.box(
            rx.el.h2(T("اکاؤنٹ", "Account")),
            rx.box(
                rx.box(State.user_name[:1], class_name="sc-avatar"),
                rx.box(
                    rx.el.b(rx.text(State.user_name)),
                    rx.el.div(
                        rx.cond(State.user_id != "",
                                T("آپ اپنے محفوظ اکاؤنٹ میں لاگ اِن ہیں۔",
                                  "You are logged in to your secure account."),
                                T("آپ ڈیمو سیشن میں ہیں (آف لائن)۔",
                                  "You are in a demo session (offline).")),
                        style={"font_size": "12.5px", "color": "var(--muted)"}),
                ),
                class_name="sc-userchip",
            ),
            rx.button(T("My Reports دیکھیں", "View My Reports"),
                      class_name="sc-btn block", on_click=State.go("history"),
                      style={"margin_bottom": "10px"}),
            rx.button(T("لاگ آؤٹ", "Log out"), class_name="sc-btn outline block",
                      on_click=State.logout),
            class_name="sc-sec",
        ),
        rx.box(
            rx.el.h2("Safe Child ", T("اکاؤنٹ", "account")),
            rx.el.p(T("اکاؤنٹ اختیاری ہے — اسکریننگ بغیر اکاؤنٹ کے چلتی ہے۔ صرف My Reports میں درج شدہ کیس کی ٹریکنگ کے لیے لاگ اِن ضروری ہے۔",
                      "Account is optional — screening works without one. Log in only to track filed cases in My Reports."),
                    class_name="sub"),
            rx.box(
                rx.box(
                    rx.button(T("لاگ اِن", "Log in"),
                              class_name=rx.cond(State.auth_mode == "login", "on", ""),
                              on_click=State.set_auth_mode("login")),
                    rx.button(T("اکاؤنٹ بنائیں", "Sign up"),
                              class_name=rx.cond(State.auth_mode == "signup", "on", ""),
                              on_click=State.set_auth_mode("signup")),
                    class_name="sc-seg",
                ),
                rx.cond(
                    State.auth_mode == "signup",
                    _field("نام", "Name", rx.input(value=State.in_name,
                           on_change=lambda v: State.set_field("in_name", v))),
                    rx.fragment(),
                ),
                _field("فون یا ای میل", "Phone or email",
                       rx.input(value=State.in_contact, on_change=lambda v: State.set_field("in_contact", v))),
                _field("پاس ورڈ", "Password",
                       rx.input(value=State.in_pass, on_change=lambda v: State.set_field("in_pass", v),
                                type="password")),
                rx.button(
                    rx.cond(State.auth_mode == "login",
                            T("لاگ اِن کریں", "Log in"), T("اکاؤنٹ بنائیں", "Sign up")),
                    class_name="sc-btn block", on_click=State.do_auth),
                rx.el.p(T("اکاؤنٹ Supabase میں محفوظ ہوتا ہے۔ انٹرنیٹ نہ ہو تو ڈیمو سیشن چلتا ہے۔",
                          "Accounts are stored in Supabase. Without internet, a demo session runs."),
                        style={"font_size": "12px", "color": "var(--muted)",
                               "line_height": "2", "margin_top": "12px"}),
                class_name="sc-auth",
            ),
            class_name="sc-sec",
        ),
    )

def history_view():
    return rx.cond(
        State.user_name != "",
        rx.box(
            rx.el.h2("My Reports"),
            rx.el.p(T("درج شدہ رپورٹس کی ٹریکنگ اور اسٹیٹس۔",
                      "Tracking and status of filed reports."),
                    class_name="sub"),
            rx.cond(
                State.user_id == "",
                rx.el.p(T("ڈیمو سیشن میں رپورٹس محفوظ نہیں ہوتیں — مستقل ٹریکنگ کے لیے اکاؤنٹ بنائیں۔",
                          "Reports are not saved in a demo session — create an account for permanent tracking."),
                        class_name="sub"),
                rx.fragment(),
            ),
            rx.cond(
                State.my_reports.length() == 0,
                rx.el.p(T("ابھی کوئی رپورٹ درج نہیں۔", "No reports filed yet."),
                        class_name="sub"),
                rx.box(
                    rx.foreach(
                        State.my_reports,
                        lambda r: rx.box(
                            rx.box(
                                rx.el.b(r["case_id"]),
                                rx.el.span(r["status"], class_name="sc-status"),
                                class_name="row",
                            ),
                            rx.el.div(r["date"],
                                      style={"font_size": "13px",
                                             "color": "var(--muted)"}),
                            class_name="sc-caseitem",
                        ),
                    ),
                ),
            ),
            rx.el.div(T("یہ اسٹیٹس حقیقی سرکاری سبمیشن نہیں ہے — رپورٹ متعلقہ پورٹل پر خود جمع کروائیں۔",
                        "This status is not a real government submission — file the report yourself on the relevant portal."),
                      style={"font_size": "12.5px", "color": "var(--muted)",
                             "margin_top": "6px", "line_height": "2"}),
            class_name="sc-sec",
        ),
        rx.box(
            rx.el.h2("My Reports"),
            rx.el.p(T("رپورٹس دیکھنے کے لیے لاگ اِن کریں۔ اکاؤنٹ رپورٹ کو آپ کی شناخت سے جوڑ کر قابلِ سراغ رکھتا ہے۔ اسکریننگ پھر بھی بغیر اکاؤنٹ جاری رہ سکتی ہے۔",
                      "Log in to see reports. An account links the report to your identity, keeping it traceable. Screening still works without an account."),
                    class_name="sub"),
            rx.button(T("لاگ اِن / اکاؤنٹ بنائیں", "Log in / Sign up"),
                      class_name="sc-btn block", on_click=State.go("account")),
            class_name="sc-sec",
        ),
    )

def index():
    return rx.box(
        tour_overlay(),
        topbar(),
        helpline(),
        navrow(),
        rx.box(
            rx.match(
                State.view,
                ("home", home_view()),
                ("categories", categories_view()),
                ("question", question_view()),
                ("filing", filing_view()),
                ("report", report_view()),
                ("resources", resources_view()),
                ("account", account_view()),
                ("history", history_view()),
                home_view(),
            ),
            class_name="sc-shell",
        ),
        bottomnav(),
        toast(),
        class_name=rx.cond(State.dark, "sc-root theme-dark ", "sc-root theme-light ")
                   + rx.cond(State.lang == "ur", "font-ur", "font-en"),
        dir=rx.cond(State.lang == "ur", "rtl", "ltr"),
    )
