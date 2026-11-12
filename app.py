"""Local-first, free TikTok content planning MVP. No TikTok integration or auto-publishing."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import json, os, sqlite3, threading, urllib.request, urllib.error

ROOT = Path(__file__).parent
DB = ROOT / "data.db"
PORT = int(os.getenv("PORT", "8000"))
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "").strip()
LOCK = threading.Lock()


def connect():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    with connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, topic TEXT NOT NULL, track TEXT NOT NULL,
            script TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'idea',
            review TEXT NOT NULL DEFAULT '', views INTEGER, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")


def rows(query, params=()):
    with connect() as db:
        return [dict(r) for r in db.execute(query, params).fetchall()]


def one(query, params=()):
    result = rows(query, params)
    return result[0] if result else None


def rank(topic):
    # Heuristic only: not a prediction of virality.
    score = 50
    if len(topic) < 8: score -= 5
    if any(w in topic.lower() for w in ("لغز", "كيف", "معلومة", "قصة", "تحدي")): score += 12
    if "؟" in topic or "?" in topic: score += 5
    return max(0, min(100, score))


def draft(topic, track):
    if OLLAMA_MODEL:
        prompt = ("اكتب مسودة فيديو تيك ��وك عربية أصلية وقصيرة من 20 إلى 35 ثانية. "
                  "ابدأ بجملة جاذبة، ثم شرح واضح، ثم خاتمة تفاعلية غير مضللة. "
                  "لا تظهر نساء أو تقترح تصويرهن؛ استخدم رسوم/أدوات/طبيعة فقط. "
                  "تجنب الموسيقى، الألفاظ البذيئة، الادعاءات غير المثبتة، والمحتوى المخالف للقيم الإسلامية. "
                  "لا تنسخ عملاً معروفاً. إذا كان الموضوع حملة، لا تخترع ادعاءات أو روابط. "
                  f"المسار: {track}. الموضوع: {topic}")
        try:
            request = urllib.request.Request("http://127.0.0.1:11434/api/generate",
                data=json.dumps({"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}).encode(),
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(request, timeout=90) as response:
                text = json.loads(response.read()).get("response", "").strip()
                if text: return text
        except (OSError, ValueError, urllib.error.URLError):
            pass
    return (f"[افتتاحية] هل تعرف هذه المعلومة عن {topic}؟\n\n"
            f"[المحتوى] اشرح الفكرة في نقاط قصيرة، وتحقق من المعلومة ومصدرها قبل التسجيل. "
            "استخدم رسومًا أو أدوات أو لقطات طبيعة فقط، دون ظهور أشخاص.\n\n"
            "[الخاتمة] ما رأيك؟ اكتب إجابتك أو اقترح موضوعاً للفيديو القادم.\n\n"
            "هذه مسودة قالبية؛ أكملها بمعلومات موثوقة ومحتوى أصلي قبل الإنتاج.")


def review_text(script, track):
    # Lightweight keyword checks; cannot inspect rendered video or make religious rulings.
    checks = {
        "لغة/محتوى حساس": ["إباحية", "قمار", "مخدرات", "عري", "كحول"],
        "نساء/ظهور أشخاص (راجع يدوياً)": ["امرأة", "نساء", "بنت", "فتاة", "ممثلة"],
        "ادعاء دخل/نتيجة مضمونة": ["مضمون الربح", "مليون مشاهدة مضمونة", "ثراء مضمون", "اربح حتماً"],
    }
    hits = [label + ": " + ", ".join(w for w in words if w in script.lower())
            for label, words in checks.items() if any(w in script.lower() for w in words)]
    if track == "campaign":
        hits.append("تحقق يدوياً من شروط الحملة والإفصاح الإعلاني قبل النشر.")
    hits.append("الفحص نصّي محدود؛ لا يفحص الصوت أو الصورة، ولا يضمن الامتثال أو الحكم الشرعي.")
    return "\n".join(hits) if hits else "لم تظهر كلمات من قائمة الفحص. هذا ليس ضماناً؛ راجع النص والصوت والصورة يدوياً."


HTML = r'''<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>مدير محتوى محلي</title>
<style>body{font-family:system-ui;max-width:1000px;margin:2rem auto;padding:0 1rem;background:#f6f7fb;color:#18202a}h1{color:#174ea6}.card{background:white;padding:1rem;margin:1rem 0;border-radius:12px;box-shadow:0 2px 10px #0001}input,select,button,textarea{font:inherit;padding:.65rem;margin:.25rem;border:1px solid #ccd2dc;border-radius:7px}input{min-width:45%}button{background:#174ea6;color:white;cursor:pointer;border:0}.warn{color:#8b3b00}.item{border-top:1px solid #ddd;padding:.7rem 0;white-space:pre-wrap}.muted{color:#596575;font-size:.92em}</style>
<h1>مدير محتوى تيك توك — نسخة محلية</h1><p class="warn">لا يوجد اتصال بتيك توك أو نشر تلقائي. النشر التلقائي يتطلب تكاملاً رسمياً وموافقة. لا توجد ضمانات للانتشار.</p>
<div class="card"><h2>إضافة فكرة</h2><form id="idea"><input name="topic" required placeholder="اكتب فكرة أو ترنداً رصدته بنفسك"><select name="track"><option value="organic">بدون حملة</option><option value="campaign">حملة</option></select><button>إضافة</button></form></div>
<div class="card"><h2>الأداء</h2><div id="stats">جارٍ التحميل…</div><p class="muted">المشاهدات لا تحدد وحدها جودة الفيديو. قارن مدة المشاهدة والتفاعل من تحليلات المنصة يدوياً.</p></div>
<div class="card"><h2>الأفكار والفيديوهات</h2><div id="videos"></div></div>
<script>
async function load(){let d=await (await fetch('/api/dashboard')).json();document.getElementById('stats').textContent=`عدد الفيديوهات: ${d.count} | مجموع المشاهدات المسجلة: ${d.views} | آخر فيديو: ${d.latest_views??'لا يوجد'}`;let v=await (await fetch('/api/videos')).json();document.getElementById('videos').innerHTML=v.map(x=>`<div class="item"><b>#${x.id} — ${esc(x.topic)}</b> [${x.track==='campaign'?'حملة':'عضوي'}] — ${x.status} — التقييم الإرشادي ${x.score}/100<br>${esc(x.script||'لم تُكتب المسودة بعد')}<br><button onclick="action(${x.id},'generate')">كتابة/تحديث المسودة</button> <button onclick="action(${x.id},'review')">مراجعة آلية</button> <button onclick="views(${x.id})">تسجيل المشاهدات</button><p class="muted">${esc(x.review||'')}</p></div>`).join('')||'لا توجد أفكار بعد.'}
function esc(s){return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
document.getElementById('idea').onsubmit=async e=>{e.preventDefault();let f=new FormData(e.target);await fetch('/api/ideas',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.fromEntries(f))});e.target.reset();load()};
async function action(id,a){await fetch(`/api/videos/${id}/${a}`,{method:'POST'});load()}
async function views(id){let n=prompt('أدخل المشاهدات الحالية من تحليلاتك:');if(n===null||!/^\\d+$/.test(n))return;await fetch(`/api/videos/${id}/views`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({views:Number(n)})});load()}
load();</script></html>'''


class Handler(BaseHTTPRequestHandler):
    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(body)

    def body_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > 100_000: raise ValueError("request too large")
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            body = HTML.encode(); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        elif path == "/api/videos":
            videos = rows("SELECT * FROM videos ORDER BY id DESC")
            for v in videos: v["score"] = rank(v["topic"])
            self.send_json(videos)
        elif path == "/api/dashboard":
            stat = one("SELECT COUNT(*) AS count, COALESCE(SUM(views),0) AS views FROM videos")
            latest = one("SELECT views FROM videos WHERE views IS NOT NULL ORDER BY id DESC LIMIT 1")
            stat["latest_views"] = latest["views"] if latest else None
            self.send_json(stat)
        else: self.send_json({"error":"not found"},404)

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            data = self.body_json()
            if path == "/api/ideas":
                topic = str(data.get("topic", "")).strip()[:500]
                track = data.get("track", "organic")
                if not topic or track not in ("organic", "campaign"): return self.send_json({"error":"invalid topic or track"},400)
                with connect() as db: cur = db.execute("INSERT INTO videos(topic,track) VALUES(?,?)",(topic,track)); vid = cur.lastrowid
                return self.send_json({"id":vid,"score":rank(topic)},201)
            parts = path.strip("/").split("/")
            if len(parts) == 4 and parts[0] == "api" and parts[1] == "videos" and parts[2].isdigit():
                vid, action = int(parts[2]), parts[3]
                item = one("SELECT * FROM videos WHERE id=?",(vid,))
                if not item: return self.send_json({"error":"video not found"},404)
                if action == "generate":
                    text = draft(item["topic"],item["track"])
                    with connect() as db: db.execute("UPDATE videos SET script=?,status='draft',updated_at=CURRENT_TIMESTAMP WHERE id=?",(text,vid))
                    return self.send_json({"script":text})
                if action == "review":
                    report = review_text(item["script"],item["track"])
                    with connect() as db: db.execute("UPDATE videos SET review=?,status='reviewed',updated_at=CURRENT_TIMESTAMP WHERE id=?",(report,vid))
                    return self.send_json({"review":report})
                if action == "views":
                    views = data.get("views")
                    if not isinstance(views,int) or views < 0: return self.send_json({"error":"views must be a non-negative integer"},400)
                    with connect() as db: db.execute("UPDATE videos SET views=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(views,vid))
                    return self.send_json({"views":views})
            self.send_json({"error":"not found"},404)
        except (ValueError, json.JSONDecodeError): self.send_json({"error":"invalid request"},400)
        except Exception as e: self.send_json({"error":str(e)},500)

    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))


if __name__ == "__main__":
    init_db()
    print(f"Local content manager: http://127.0.0.1:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
