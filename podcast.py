"""HS2 SAQ Podcast: two episodes, Test 3 and the final, that cover every written question each one can ask.
Kokoro (local, CPU) reads them; every chapter is its own MP3, so any phone plays, skips and loops them.

    python podcast.py                  # voice whatever is not cached yet, then build everything
    python podcast.py t3               # one episode (t3 | final); add chapter numbers to voice just those: t3 4 5
    python podcast.py --no-build       # voice only (run two or three at once; a .lock per chapter shares the work)
    python podcast.py --build          # MP3s, the player page, the feeds and the zips, from the cache only
    python podcast.py --dry            # words, minutes and every gate; voices nothing
    python podcast.py --audit          # every long or technical word with the phonemes Kokoro will say
    python podcast.py --say "text"     # voice one line to D:/hs2-audio/podcast/say.wav (check a pronunciation)

Script: script/<episode>/*.txt, read in file order. "# Title" starts a chapter. In a chapter:
    @ saq: id            Test 3: an SAQ Trainer id (hs2-test3/content/saq-*.json); the player shows its question and short answer
    @ q: id id           final: question ids from hs2-final's built DATA (cases, the formative test, the RG quiz)
    @ case: c3           final: the case whose scenario the player shows
    @ held: question || line | line     a starred question she has not answered: shown with the podcast's own lines
    % ...                a note, never spoken
    Q: ...               a paragraph read by the second voice (the examiner): the question, the "once more" prompt
    {recap} ...          a paragraph in the chapter AND in the episode's last chapter, Rapid-fire, built from every recap
    [pause] / [pause N]  silence (2 s / N s)
Everything else is spoken by the main voice. Audio is cached per paragraph (sha1 of voice + speed + the PHONEMES spoken), so an
edit, or a pronunciation fix, re-voices only the paragraphs it changes.

Pronunciation: IPA below replaces espeak's guess for a word with phonemes written by hand (Kokoro's own symbol set), because
respelling ("hoh-moh-zy-gus") is fragile. Each was checked against tokenizer.phonemize on 2026-10-16. The text clean-up
between the PORT markers is scripts/hs2-podcast/podcast.py's (estate branch claude/hs2-test3-podcast-509210), so this says
letters, symbols and acronyms the way the Test 2, Module 1 and first Test 3 courses did; the one change is the plural of a
spelled acronym ("STIs" was read "S T is").
"""
import glob, hashlib, json, os, re, shutil, subprocess, sys, time, zipfile
from email.utils import formatdate
from xml.sax.saxutils import escape
import numpy as np
import soundfile as sf

sys.stdout.reconfigure(encoding='utf-8', errors='replace')   # the Windows console is cp1252

HERE = os.path.dirname(os.path.abspath(__file__))
ESTATE = os.path.dirname(HERE)
WORK = "D:/hs2-audio/podcast"                 # cache, zips and the named copies: never in the repo
CACHE = os.path.join(WORK, 'cache')
MODEL_DIR = "D:/hs2-audio/model"
FFMPEG = "C:/Users/USER/AppData/Roaming/GameSentenceMiner/ffmpeg/ffmpeg.exe"
BASE_URL = "https://jeremyspm.github.io/hs2-podcast/"
SR = 24000
SPEED = 1.0
VOICES = {'main': 'af_heart',                 # the voice of every HS2 audio course so far
          'q': 'am_michael'}                  # the examiner: a different voice, so you can HEAR where a question starts
GAP = 0.45                                    # after every spoken paragraph
LEAD, TAIL = 0.4, 1.4
BITRATE = '64k'                               # mono speech at 24 kHz: about 29 MB an hour
os.makedirs(CACHE, exist_ok=True)

EPISODES = {
    't3': dict(
        title='HS2 Test 3 — Every SAQ', short='Test 3', zip='HS2-Test3-Every-SAQ',
        kicker='Module 3 · genetics, the senses, reproduction',
        blurb='Every short-answer question Test 3 can plausibly ask: her two named cases, the pedigree charts she says will be '
              'tested, her help-board topics, her student-marked SAQ quiz and her taste and smell outcomes. One track per question.',
        when='Test 3 closes Mon 26 Oct · 37 questions · 65 min · about 30% of the marks written',
        rapid='Rapid-fire: all 25 answers, back to back',
        rapid_intro='This is the rapid-fire track: every answer in this episode, back to back, one breath each. No teaching, '
                    'no traps, just the answers in the shape you would write them. It is made for the night before, and for '
                    'the bus on the way in. If one of these sounds unfamiliar, go back to its own track.'),
    'final': dict(
        title='HS2 Final — Every case SAQ', short='Final', zip='HS2-Final-Every-Case-SAQ',
        kicker='Modules 1–3 · the ten yellow, starred cases',
        blurb='Her exam is built on the ten starred cases in Case Study Booklet A, and its closed questions are those same case '
              'questions converted. This episode works through every written question in every one of them, in booklet order.',
        when='The final: Wed 4 Nov, on campus · 32 questions · 90 marks · 2 h 10 min · 37% written',
        rapid='Rapid-fire: every case answer, back to back',
        rapid_intro='This is the rapid-fire track: every case answer in this episode, back to back, one breath each, in booklet '
                    'order. It is made for the morning of the exam. If one of these sounds unfamiliar, go back to its own track.'),
}

# ── pronunciation: whole words → phonemes (Kokoro's symbols; checked 2026-10-16 against what espeak said instead) ─────
IPA = {
    # genetics — espeak: "HAH-muh-ZIG-us", "het-er-uh-ZIG-us"
    'homozygous': 'hˌoʊmoʊzˈaɪɡəs', 'heterozygous': 'hˌɛɾəɹoʊzˈaɪɡəs',
    'homozygote': 'hˌoʊmoʊzˈaɪɡoʊt', 'heterozygote': 'hˌɛɾəɹoʊzˈaɪɡoʊt',
    'homozygotes': 'hˌoʊmoʊzˈaɪɡoʊts', 'heterozygotes': 'hˌɛɾəɹoʊzˈaɪɡoʊts',
    'aneuploidy': 'ˈænjuːplˌɔɪdi', 'karyotype': 'kˈæɹioʊtˌaɪp', 'karyotypes': 'kˈæɹioʊtˌaɪps',
    'codominance': 'kˌoʊdˈɑːmɪnəns', 'codominant': 'kˌoʊdˈɑːmɪnənt',
    # reproduction
    'oocyte': 'ˈoʊəsˌaɪt', 'oocytes': 'ˈoʊəsˌaɪts', 'oogenesis': 'ˌoʊədʒˈɛnəsɪs', 'oogonia': 'ˌoʊəɡˈoʊniə',
    'leydig': 'lˈaɪdɪɡ', 'sertoli': 'sɚtˈoʊli', 'prolactin': 'pɹoʊlˈæktɪn',
    'myoepithelial': 'mˌaɪoʊˌɛpɪθˈiːliəl', 'alveoli': 'ælvˈiːəlˌaɪ', 'luteum': 'lˈuːɾiəm',
    'functionalis': 'fˌʌŋkʃənˈælɪs', 'basalis': 'bəsˈælɪs', 'menarche': 'mɛnˈɑːɹki',
    # the ear
    'stapes': 'stˈeɪpiːz', 'incus': 'ˈɪŋkəs', 'cochlear': 'kˈɑːkliɚ', 'vestibulocochlear': 'vɛstˌɪbjʊloʊkˈɑːkliɚ',
    'sensorineural': 'sˌɛnsəɹiːnˈʊɹəl', 'otosclerosis': 'ˌoʊɾoʊskləɹˈoʊsɪs', 'otoliths': 'ˈoʊɾəlˌɪθs',
    'pharyngotympanic': 'fəɹˌɪŋɡoʊtɪmpˈænɪk', 'ototoxic': 'ˌoʊɾoʊtˈɑːksɪk',
    # the eye
    'sclera': 'sklˈɛɹə',
    # taste and smell
    'fungiform': 'fˈʌndʒɪfˌɔːɹm', 'umami': 'uːmˈɑːmi', 'glossopharyngeal': 'ɡlˌɑːsoʊfəɹˈɪndʒiəl',
    'hyposmia': 'haɪpˈɑːzmiə', 'amygdala': 'ɐmˈɪɡdələ', 'orbitofrontal': 'ˌɔːɹbɪɾoʊfɹˈʌntəl',
    # names in the cases (te reo Māori and the rest), said the way they are said here
    'pania': 'pˈɑːniə', 'whānau': 'fˈɑːnoʊ', 'whanau': 'fˈɑːnoʊ', 'mirimiri': 'mˈiːɹimˌiːɹi',
    'manaia': 'mɑːnˈaɪɑː', 'ane': 'ˈɑːnɛ', 'paraone': 'pˌɑːɹɑːˈoʊnɛ', 'aleki': 'ɑːlˈɛki',
    # other words espeak gets wrong
    'tear': 'tˈɛɹ',                            # only ever "wear and tear" here
    'glut': 'ɡlˈuːt',                          # GLUT 4 is "gloot", not "glut"
    'lives': 'lˈɪvz',                          # "Manaia lives with": espeak said "lyves"
    'contract': 'kəntɹˈækt', 'contracts': 'kəntɹˈækts',      # muscles contract: the verb, not the noun
    'insert': 'ɪnsˈɜːt', 'impacted': 'ɪmpˈæktᵻd',
    # ── the 16 Oct audit (python podcast.py --audit): every word below was misstressed or missaid ─────────────────
    # breathing, the lungs, the heart
    'atelectasis': 'ˌæɾəlˈɛktəsɪs', 'baroreceptor': 'bˌæɹoʊɹɪsˈɛptɚ', 'baroreceptors': 'bˌæɹoʊɹɪsˈɛptɚz',
    'bronchodilator': 'bɹˌɑːŋkoʊdaɪlˈeɪɾɚ', 'bronchodilators': 'bɹˌɑːŋkoʊdaɪlˈeɪɾɚz', 'columnar': 'kəlˈʌmnɚ',
    'cuboidal': 'kjuːbˈɔɪdəl', 'epiglottis': 'ˌɛpɪɡlˈɑːɾɪs', 'intrapleural': 'ˌɪntɹəplˈʊɹəl',
    'intrapulmonary': 'ˌɪntɹəpˈʊlmənˌɛɹi', 'pleural': 'plˈʊɹəl', 'pneumothorax': 'nˌuːmoʊθˈɔːɹæks',
    'surfactant': 'sɚfˈæktənt', 'trachea': 'tɹˈeɪkiə', 'salbutamol': 'sælbjˈuːtəmɑːl', 'ketoacidosis': 'kˌiːɾoʊˌæsɪdˈoʊsɪs',
    'sternocleidomastoid': 'stˌɜːnoʊklˌaɪdoʊmˈæstɔɪd', 'nasopharynx': 'nˌeɪzoʊfˈæɹɪŋks',
    'vasodilation': 'vˌeɪzoʊdaɪlˈeɪʃən', 'vasomotor': 'vˌeɪzoʊmˈoʊɾɚ', 'medulla': 'mɪdˈʌlə',
    # lymph, cancer, hormones, diabetes, joints
    'lymphoedema': 'lˌɪmfᵻdˈiːmə', 'metastasis': 'mətˈæstəsɪs', 'macrophages': 'mˈækɹəfˌeɪdʒᵻz',
    'langerhans': 'lˈɑːŋɚhɑːnz', 'mellitus': 'mɛlˈaɪɾəs', 'glycogenolysis': 'ɡlˌaɪkoʊdʒənˈɑːlᵻsɪs',
    'lipolysis': 'lɪpˈɑːlᵻsɪs', 'glucocorticoid': 'ɡlˌuːkoʊkˈɔːɹɾɪkˌɔɪd', 'corticosteroid': 'kˌɔːɹɾɪkoʊstˈɛɹɔɪd',
    'prednisone': 'pɹˈɛdnɪsˌoʊn', 'enthesis': 'ˈɛnθəsɪs', 'denature': 'diːnˈeɪtʃɚ', 'fascia': 'fˈæʃə',
    # the brain and the senses
    'callosum': 'kəlˈoʊsəm', 'occipital': 'ɑːksˈɪpɪɾəl', 'prefrontal': 'pɹiːfɹˈʌntəl', 'precentral': 'pɹiːsˈɛntɹəl',
    'postcentral': 'poʊstsˈɛntɹəl', 'somatosensory': 'soʊmˌæɾoʊsˈɛnsɚɹi', 'wernicke': 'wˈɜːnɪki',
    'presynaptic': 'pɹˌiːsɪnˈæptɪk', 'exocytosis': 'ˌɛksoʊsaɪtˈoʊsɪs', 'excitatory': 'ɪksˈaɪɾətˌɔːɹi',
    'reuptake': 'ɹiːˈʌpteɪk', 'nigra': 'nˈaɪɡɹə', 'chemoreceptors': 'kˌiːmoʊɹɪsˈɛptɚz',
    'mechanoreceptors': 'mˌɛkənoʊɹɪsˈɛptɚz', 'cerumen': 'səɹˈuːmən', 'stapedius': 'stəpˈiːdiəs', 'tympani': 'tˈɪmpəni',
    'otolith': 'ˈoʊɾəlˌɪθ', 'papillae': 'pəpˈɪliː', 'rarefactions': 'ɹˌɛɹᵻfˈækʃənz',
    'photopic': 'foʊtˈɑːpɪk', 'scotopic': 'skoʊtˈɑːpɪk',
    # genetics and reproduction
    'autosomes': 'ˈɔːɾoʊsˌoʊmz', 'chromosomal': 'kɹˌoʊməsˈoʊməl', 'metaphase': 'mˈɛɾəfˌeɪz',
    'secretory': 'sᵻkɹˈiːɾɚɹi', 'uterine': 'jˈuːɾɚɹaɪn', 'luteinising': 'lˈuːtiənˌaɪzɪŋ', 'gonadotropin': 'ɡoʊnˌædəɾˈoʊpɪn',
    'depo': 'dˈɛpoʊ', 'provera': 'pɹoʊvˈɛɹə', 'jadelle': 'dʒədˈɛl',
    'kahoot': 'kəhˈuːt',
}

# ── PORT: scripts/hs2-podcast/podcast.py (estate branch claude/hs2-test3-podcast-509210) ─────────────────────
# The LETTER A is read as the article "uh" anywhere but the start of a chain ("A O" -> "uh oh"), so every 2-6 letter all-caps
# word is spelled with A said "eigh"; "big A", "type A", "little a" and "an A" say "eigh"; and a capital A that does not start a
# sentence is a letter, so it says "eigh" too (the scripts only use the article "A" at the start of a sentence).
SAY_AS_WORD = {'GABA', 'RAAS', 'FAST', 'NAD', 'AIDS', 'HIV', 'COVID', 'MRI', 'GLUT'}
LETTER_A = [(r'\bGnRH\b', 'G N R H'), (r'\b(big|little|type|an) [Aa]\b', r'\1 eigh'),
            (r"(?<![.!?]\s)(?<!^)\bA\b(?![-'])", 'eigh')]


def spell(m):
    w, s = m.group(1), m.group(2)
    if w in SAY_AS_WORD:
        return m.group(0)
    return ' '.join('eigh' if c == 'A' else c for c in w) + ("'s" if s else '')    # "S T I's", not "S T is"


SUBS = [
    (r'\[\[IMG:[^\]]*\]\]', ' '),
    (r'Ca(?:²⁺|2\+|\+\+)', 'calcium ions'), (r'Na(?:⁺|\+)', 'sodium ions'), (r'K(?:⁺|\+)', 'potassium ions'),
    (r'H(?:⁺|\+)', 'hydrogen ions'), (r'HCO(?:₃|3)(?:⁻|-)', 'bicarbonate'), (r'H₂CO₃|H2CO3', 'carbonic acid'),
    (r'CO(?:₂|2)\b', 'carbon dioxide'), (r'\bO(?:₂|2)\b', 'oxygen'), (r'H(?:₂|2)O\b', 'water'),
    (r'\bpH\b', 'P H'),
    (r'mmol/L', 'millimoles per litre'), (r'\bmV\b', 'millivolts'), (r'\bmL\b', 'millilitres'),
    (r'°C', ' degrees Celsius'), (r'%', ' per cent'), (r'&', ' and '),
    (r'→|⇒|->', ' leads to '), (r'↑', 'increased '), (r'↓', 'decreased '),
    (r'\bvs\.?\b', 'versus'), (r'\be\.g\.', 'for example'), (r'\bi\.e\.', 'that is'),
    (r'(?<=\d)\s*[–—-]\s*(?=\d)', ' to '), (r'\s\+\s', ' plus '),
    (r'(?<=\s)−(?=\d)', 'minus '), (r'(?<=\s)-(?=\d)', 'minus '), (r'−', '-'), (r'[–—]', ', '),
    (r'\bC(\d)\b', r'C \1'), (r'\bT(\d{1,2})\b', r'T \1'), (r'\bL(\d)\b', r'L \1'), (r'\bS(\d)\b', r'S \1'),
    (r'[*_#`>]+', ''), (r'^\s*[-•]\s+', '', ),
    (r'(\w)/(\w)', r'\1 or \2'),
    (r'[ \t]+', ' '),
]


def respell(text):
    text = re.sub(r'\b([A-Z]{2,6})(s?)\b', spell, text)
    for pat, rep in LETTER_A:
        text = re.sub(pat, rep, text)
    return text


def normalise(text):
    out = []
    for line in text.split('\n'):
        for pat, rep in SUBS:
            line = re.sub(pat, rep, line, flags=re.M)
        out.append(line.strip())
    return '\n'.join(out)
# ── END PORT ──────────────────────────────────────────────────────────────────────────────────────────────


def pieces(text):
    """('pause', seconds) or ('say', text) for one paragraph, after the clean-up."""
    for piece in re.split(r'(\[pause(?: \d+(?:\.\d+)?)?\])', normalise(respell(text))):
        piece = piece.strip()
        if not piece:
            continue
        m = re.fullmatch(r'\[pause(?: (\d+(?:\.\d+)?))?\]', piece)
        if m:
            yield 'pause', float(m.group(1)) if m.group(1) else 2.0
        else:
            yield 'say', re.sub(r'\s*\n\s*', ' ', piece)


# ── the script ────────────────────────────────────────────────────────────────────────────────────────────
def chapters(ep):
    """[{n, title, meta, paras: [{who, text, recap}]}], the Rapid-fire chapter last."""
    out = []
    files = sorted(glob.glob(os.path.join(HERE, 'script', ep, '*.txt')))
    if not files:
        raise SystemExit(f"no script for {ep}: script/{ep}/*.txt")
    for path in files:
        text = open(path, encoding='utf-8').read().replace('\r\n', '\n')
        for block in re.split(r'(?m)^(?=# )', text):
            if not block.strip():
                continue
            if not block.startswith('# '):
                if any(l.strip() and not l.startswith('%') for l in block.split('\n')):
                    raise SystemExit(f"{os.path.basename(path)}: words before its first '# Title'")
                continue
            head, _, body = block.partition('\n')
            meta, kept = {}, []
            for line in body.split('\n'):
                if line.startswith('%'):
                    continue
                m = re.match(r'@\s*(\w+)\s*:\s*(.*)$', line)
                if m:
                    meta.setdefault(m.group(1), []).append(m.group(2).strip())
                else:
                    kept.append(line)
            paras = []
            for para in re.split(r'\n\s*\n', '\n'.join(kept)):
                para = para.strip()
                if not para:
                    continue
                recap = para.startswith('{recap}')
                if recap:
                    para = para[len('{recap}'):].strip()
                who = 'main'
                if para.startswith('Q:'):
                    who, para = 'q', para[2:].strip()
                paras.append({'who': who, 'text': para, 'recap': recap})
            out.append({'title': head[2:].strip(), 'meta': meta, 'paras': paras, 'file': os.path.basename(path)})
    rapid = [{'who': 'main', 'text': EPISODES[ep]['rapid_intro'], 'recap': False}, {'who': 'main', 'text': '[pause 1]', 'recap': False}]
    for ch in out:
        rec = [p for p in ch['paras'] if p['recap']]
        if rec:
            rapid.append({'who': 'q', 'text': re.sub(r'[.:]?$', '.', ch['meta'].get('say', [ch['title']])[0]), 'recap': False})
            rapid += [{'who': 'main', 'text': p['text'], 'recap': False} for p in rec]
            rapid.append({'who': 'main', 'text': '[pause 0.8]', 'recap': False})
    rapid.append({'who': 'main', 'text': "That's every answer. Go and get them.", 'recap': False})
    out.append({'title': EPISODES[ep]['rapid'], 'meta': {'rapid': ['1']}, 'paras': rapid, 'file': '(built)'})
    for i, ch in enumerate(out, 1):
        ch['n'] = i
    return out


def segs(ch):
    for p in ch['paras']:
        for kind, val in pieces(p['text']):
            yield (kind, p['who'], val)


# ── phonemes, with the hand-written ones spliced in ─────────────────────────────────────────────────────────
_kokoro = None
def kokoro():
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro
        _kokoro = Kokoro(os.path.join(MODEL_DIR, 'kokoro-v1.0.onnx'), os.path.join(MODEL_DIR, 'voices-v1.0.bin'))
        bad = {w: ''.join(c for c in v if c not in _kokoro.tokenizer.vocab) for w, v in IPA.items()}
        bad = {w: v for w, v in bad.items() if v}
        if bad:
            raise SystemExit(f"IPA entries with symbols Kokoro does not have: {bad}")
    return _kokoro


_backend = None
def espeak(texts):
    """Exactly what kokoro's tokenizer.phonemize() returns, for a list of texts, from ONE espeak backend (tokenizer.phonemize
    builds a new backend on every call: about a second each, which made a render's phonemes take longer than its audio)."""
    global _backend
    vocab = kokoro().tokenizer.vocab                 # loading Kokoro also points phonemizer at its espeak library
    if _backend is None:
        from phonemizer.backend import EspeakBackend
        _backend = EspeakBackend('en-us', preserve_punctuation=True, with_stress=True)
    from phonemizer.separator import default_separator
    out = _backend.phonemize([t.strip() for t in texts], separator=default_separator, strip=False)
    return [''.join(c for c in p if c in vocab).strip() for p in out]


_IPA_RE = re.compile(r"\b(" + '|'.join(sorted(map(re.escape, IPA), key=len, reverse=True)) + r")(['’]s)?\b", re.I)
_PH = {}
def phonemes(text):
    if text in _PH:
        return _PH[text]
    out, pos = [], 0
    def plain(chunk):
        if re.search(r'\w', chunk):
            out.append(espeak([chunk])[0])
        else:                                        # a bare comma or full stop between two hand-written words
            out.append(''.join(c for c in chunk if c in '.,!?;:'))
    for m in _IPA_RE.finditer(text):
        if m.start() > pos:
            plain(text[pos:m.start()])
        out.append(IPA[m.group(1).lower()] + ('z' if m.group(2) else ''))
        pos = m.end()
    if pos < len(text):
        plain(text[pos:])
    s = re.sub(r'\s+([.,!?;:])', r'\1', ' '.join(p for p in out if p))
    _PH[text] = s = re.sub(r'\s+', ' ', s).strip()
    return s


def key(ph, who):
    return hashlib.sha1(f"{VOICES[who]}|{SPEED}|{ph}".encode('utf-8')).hexdigest()[:16]


def cached(text, who):
    return os.path.exists(os.path.join(CACHE, key(phonemes(text), who) + '.wav'))


def say(text, who):
    ph = phonemes(text)
    path = os.path.join(CACHE, key(ph, who) + '.wav')
    if os.path.exists(path):
        return sf.read(path, dtype='float32')[0]
    try:
        samples, _ = kokoro().create(ph, voice=VOICES[who], speed=SPEED, is_phonemes=True)
    except Exception as e:
        print(f"      paragraph failed ({e}); retrying sentence by sentence", flush=True)
        samples = np.concatenate([kokoro().create(phonemes(s), voice=VOICES[who], speed=SPEED, is_phonemes=True)[0]
                                  for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()] or [silence(0.1)])
    samples = samples.astype(np.float32)
    sf.write(path + '.part.wav', samples, SR, subtype='PCM_16')
    os.replace(path + '.part.wav', path)
    return samples


def silence(sec):
    return np.zeros(int(SR * sec), dtype=np.float32)


def level(a, target_db=-20.0):
    """Every paragraph to the same speech loudness, so the two voices sit at one level."""
    loud = a[np.abs(a) > 0.02]
    if len(loud) < SR // 10:
        return a
    g = 10 ** (target_db / 20) / float(np.sqrt(np.mean(loud ** 2)))
    peak = float(np.max(np.abs(a))) * g
    if peak > 0.97:
        g *= 0.97 / peak
    return (a * g).astype(np.float32)


def chime():
    """Two soft notes at the top of every chapter: you hear where a new question starts."""
    out = []
    for f in (659.25, 880.0):
        t = np.arange(int(SR * 0.42)) / SR
        out.append(0.11 * np.sin(2 * np.pi * f * t) * np.exp(-t * 7.5) * np.minimum(1, t / 0.006))
    a = np.concatenate([out[0][:int(SR * 0.14)], out[1]])
    return a.astype(np.float32)


def check(chs, ep):
    bad = []
    for ch in chs:
        for p in ch['paras']:      # a LETTER A that starts a sentence is read as the article "uh": write "Letter A" or "Area A"
            for m in re.finditer(r"(?:^|[.!?:]\s+)(A)(?=[,:]|\s+(?:is|shows|marks|and|to)\b)", p['text']):
                bad.append(f"{ep} ch {ch['n']}: a sentence starts with the letter A: …{p['text'][max(0, m.start()-30):m.end()+30]}…")
        for kind, _, val in segs(ch):
            if kind == 'say':
                for m in re.finditer(r'(?<![.!?]\s)(?<!^)\bA\b(?![-\'])', val):
                    bad.append(f"{ep} ch {ch['n']}: …{val[max(0, m.start()-40):m.end()+30]}…")
                for m in re.finditer(r'[^\w\s.,!?;:\'’"()\-]', val):
                    bad.append(f"{ep} ch {ch['n']}: symbol {m.group()!r} would be dropped: …{val[max(0, m.start()-30):m.end()+20]}…")
    if bad:
        raise SystemExit("text the voice would say wrong:\n  " + '\n  '.join(bad))


def voice_chapter(ep, ch):
    todo = [(w, v) for k, w, v in segs(ch) if k == 'say' and not cached(v, w)]
    if not todo:
        return
    lock = os.path.join(CACHE, f"{ep}-{ch['n']:02d}.lock")
    if os.path.exists(lock) and time.time() - os.path.getmtime(lock) < 2 * 3600:
        return                                            # another renderer has this chapter
    open(lock, 'w').write(str(os.getpid()))
    t0 = time.time()
    print(f"[{ep} {ch['n']:02d}] {ch['title']}  ({len(todo)} paragraphs)", flush=True)
    for i, (who, text) in enumerate(todo, 1):
        say(text, who)
        if i % 10 == 0:
            print(f"      {i}/{len(todo)}, {time.time()-t0:.0f}s", flush=True)
    os.remove(lock)
    print(f"[{ep} {ch['n']:02d}] voiced in {(time.time()-t0)/60:.1f} min", flush=True)


def chapter_audio(ch):
    parts = [silence(LEAD), chime(), silence(0.45)]
    for kind, who, val in segs(ch):
        parts += [silence(val)] if kind == 'pause' else [level(say(val, who)), silence(GAP)]
    parts.append(silence(TAIL))
    return np.concatenate(parts)


# ── what the player shows under each chapter: her question and the short answer, from the Paper Sims ──────────
def plain(s):
    return re.sub(r'\s+', ' ', s.replace('**', '')).strip()


def t3_bank():
    bank = {}
    for f in sorted(glob.glob(os.path.join(ESTATE, 'hs2-test3', 'content', 'saq-*.json'))):
        for x in json.load(open(f, encoding='utf-8')):
            bank[x['id']] = x
    if len(bank) < 25:
        raise SystemExit(f"hs2-test3's SAQ Trainer has {len(bank)} questions; expected 25 (is ../hs2-test3 checked out?)")
    return bank


def final_bank():
    lines = open(os.path.join(ESTATE, 'hs2-final', 'index.html'), encoding='utf-8').read().split('\n')
    data = json.loads(next(l for l in lines if l.startswith('const DATA = '))[len('const DATA = '):].rstrip().rstrip(';'))
    shorts = json.loads(next(l for l in lines if l.startswith('const SHORTS = '))[len('const SHORTS = '):].rstrip().rstrip(';'))
    return {q['id']: {**q, 'short': shorts.get(q['id'])} for q in data['questions'] if q.get('mod') == 'cases'}


def show_item(ask, marks, short=None, lines=None):
    groups = []
    if short:
        for g in short['groups']:
            groups.append({'h': plain(g.get('q') or ''), 't': [plain(f['t']) for f in g['facts']]})
    elif lines:
        groups.append({'h': '', 't': lines})
    return {'ask': plain(ask), 'marks': marks, 'hook': plain(short.get('hook', '')) if short else '', 'groups': groups}


def show_for(ep, ch, banks):
    items, scen = [], ''
    if ep == 't3':
        for i in ch['meta'].get('saq', []):
            x = banks['t3'][i]
            items.append(show_item(re.sub(r'\s*\(\d+(\.\d+)? marks?\)\s*$', '', x['ask']), x['marks'], x['short']))
    else:
        for i in ' '.join(ch['meta'].get('q', [])).split():
            q = banks['final'][i]
            if q.get('short'):
                items.append(show_item(q.get('qt') or q['q'], q['pts'], q['short']))
            elif q.get('blanks'):
                items.append(show_item(q.get('qt') or q['q'], q['pts'], lines=[f"{n}. {b['correct']}" for n, b in enumerate(q['blanks'], 1)]))
            elif q.get('opts'):
                ans = q.get('ans')
                items.append(show_item(q['q'], q['pts'], lines=[q['opts'][ans] if isinstance(ans, int) else str(ans)]))
        for h in ch['meta'].get('held', []):
            ask, _, rest = h.partition('||')
            items.append({**show_item(ask.strip() + ' (her answer is not posted yet)', None, lines=[l.strip() for l in rest.split('|') if l.strip()]), 'held': True})
        for c in ch['meta'].get('case', []):
            q = next((q for q in banks['final'].values() if q['quiz'] == f'case-{c}'), None)
            scen = q['scenario'] if q else ''
    return items, scen


def coverage(ep, chs, banks):
    """Every SAQ in the bank is in some chapter, and every id a chapter names exists."""
    named = [i for ch in chs for i in (ch['meta'].get('saq', []) if ep == 't3' else ' '.join(ch['meta'].get('q', [])).split())]
    bank = banks[ep]
    unknown = [i for i in named if i not in bank]
    missing = [i for i in bank if i not in named]
    if unknown or missing:
        raise SystemExit(f"{ep}: coverage gate failed\n  named but not in the bank: {unknown}\n  in the bank, in no chapter: "
                         + ', '.join(f"{i} ({bank[i].get('title') or (bank[i].get('short') or {}).get('title') or bank[i].get('qt', '')[:50]})" for i in missing))
    return len(set(named))


# ── build: MP3s, the page, the feeds, the zips ───────────────────────────────────────────────────────────────
def slug(s):
    return re.sub(r'[^\w]+', ' ', s.replace('’', "'").replace("'", '')).strip()[:70]


def cover(ep):
    path = os.path.join(HERE, 'audio', f'cover-{ep}.png')
    from PIL import Image, ImageDraw, ImageFont
    S = 1400
    img = Image.new('RGB', (S, S))
    d = ImageDraw.Draw(img)
    a, b = (37, 99, 235), (12, 30, 80)
    for y in range(S):
        t = y / S
        d.line([(0, y), (S, y)], fill=tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3)))
    bold = lambda n: ImageFont.truetype('C:/Windows/Fonts/seguibl.ttf', n)
    reg = lambda n: ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', n)
    d.text((110, 120), 'HEALTH SCIENCE 2', font=reg(64), fill=(220, 230, 255))
    d.text((100, 330), 'TEST 3' if ep == 't3' else 'FINAL', font=bold(300), fill=(255, 255, 255))
    d.text((110, 700), 'EVERY SAQ' if ep == 't3' else 'EVERY CASE SAQ', font=bold(120), fill=(255, 255, 255))
    d.text((110, 1150), 'the SAQ podcast', font=reg(70), fill=(200, 215, 250))
    d.ellipse((1060, 1040, 1300, 1280), outline=(255, 255, 255), width=14)
    d.polygon([(1150, 1100), (1150, 1220), (1250, 1160)], fill=(255, 255, 255))
    img.save(path)
    return path


def encode(wav, mp3, tags, art):
    cmd = [FFMPEG, '-y', '-loglevel', 'error', '-i', wav, '-i', art, '-map', '0:a', '-map', '1:v', '-c:v', 'copy',
           '-disposition:v', 'attached_pic', '-metadata:s:v', 'title=Cover', '-metadata:s:v', 'comment=Cover (front)',
           '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11', '-ar', str(SR), '-ac', '1', '-c:a', 'libmp3lame', '-b:a', BITRATE,
           '-id3v2_version', '3']
    for k, v in tags.items():
        cmd += ['-metadata', f'{k}={v}']
    subprocess.run(cmd + [mp3 + '.part.mp3'], check=True)
    os.replace(mp3 + '.part.mp3', mp3)


def build(ep, chs, banks):
    E = EPISODES[ep]
    outdir = os.path.join(HERE, 'audio', ep)
    os.makedirs(outdir, exist_ok=True)
    art = cover(ep)
    named = os.path.join(WORK, E['zip'])
    shutil.rmtree(named, ignore_errors=True)
    os.makedirs(named)
    rows, total = [], 0.0
    for ch in chs:
        a = chapter_audio(ch)
        dur = len(a) / SR
        wav = os.path.join(WORK, f'{ep}-{ch["n"]:02d}.wav')
        sf.write(wav, a, SR, subtype='PCM_16')
        mp3 = os.path.join(outdir, f'{ch["n"]:02d}.mp3')
        title = f'{ch["n"]:02d} · {ch["title"]}'
        encode(wav, mp3, {'title': title, 'album': E['title'], 'artist': 'HS2 SAQ Podcast', 'album_artist': 'HS2 SAQ Podcast',
                          'track': f'{ch["n"]}/{len(chs)}', 'genre': 'Podcast', 'date': '2026',
                          'comment': 'Health Science 2, 722.541. Read by Kokoro.'}, art)
        os.remove(wav)
        shutil.copyfile(mp3, os.path.join(named, f'{ch["n"]:02d} {slug(ch["title"])}.mp3'))
        items, scen = show_for(ep, ch, banks)
        rows.append({'n': ch['n'], 'title': ch['title'], 'file': f'audio/{ep}/{ch["n"]:02d}.mp3', 'dur': round(dur, 1),
                     'bytes': os.path.getsize(mp3), 'rapid': bool(ch['meta'].get('rapid')), 'scen': scen, 'show': items,
                     'marks': sum(i['marks'] or 0 for i in items) or None, 'ver': hashlib.sha1(open(mp3, 'rb').read()).hexdigest()[:10]})
        total += dur
        print(f"  {ep} {ch['n']:02d}  {int(dur//60):2d}:{int(dur%60):02d}  {ch['title']}", flush=True)
    # the whole episode as ONE MP3 too (asked 16 Oct: "give them the option to download the mp3"), for anyone who wants a single
    # file. The chapter MP3s are joined frame for frame (no second encode), with the chapters embedded for apps that read them.
    whole = os.path.join(HERE, 'audio', E['zip'] + '.mp3')
    lst, ffm, t = os.path.join(WORK, f'{ep}-concat.txt'), [';FFMETADATA1', f'title={E["title"]}', f'album={E["title"]}',
                                                          'artist=HS2 SAQ Podcast', 'genre=Podcast'], 0.0
    open(lst, 'w', encoding='utf-8').write(''.join(f"file '{os.path.join(outdir, os.path.basename(r['file']))}'\n" for r in rows))
    for r in rows:
        ffm += ['[CHAPTER]', 'TIMEBASE=1/1000', f'START={int(t * 1000)}', f'END={int((t + r["dur"]) * 1000)}', f'title={r["n"]:02d} · {r["title"]}']
        t += r['dur']
    meta = os.path.join(WORK, f'{ep}-whole.ffmeta')
    open(meta, 'w', encoding='utf-8').write('\n'.join(ffm) + '\n')
    # 'fatal': the frame-for-frame joins log harmless dts warnings at each track boundary (it is silence there)
    subprocess.run([FFMPEG, '-y', '-loglevel', 'fatal', '-f', 'concat', '-safe', '0', '-i', lst, '-i', meta, '-i', art,
                    '-map', '0:a', '-map', '2:v', '-map_metadata', '1', '-map_chapters', '1', '-c', 'copy',
                    '-disposition:v', 'attached_pic', '-id3v2_version', '3', whole + '.part.mp3'], check=True)
    os.replace(whole + '.part.mp3', whole)
    shutil.copyfile(whole, os.path.join(WORK, os.path.basename(whole)))
    full = {'file': f'audio/{E["zip"]}.mp3', 'bytes': os.path.getsize(whole), 'ver': hashlib.sha1(open(whole, 'rb').read()).hexdigest()[:10]}
    zpath = os.path.join(WORK, E['zip'] + '.zip')
    with zipfile.ZipFile(zpath + '.part', 'w', zipfile.ZIP_STORED) as z:
        for f in sorted(os.listdir(named)):
            z.write(os.path.join(named, f), f'{E["zip"]}/{f}')
    os.replace(zpath + '.part', zpath)
    print(f"{ep}: {len(chs)} chapters, {total/60:.0f} min, {sum(r['bytes'] for r in rows)/1e6:.0f} MB · {zpath}", flush=True)
    return {'id': ep, **{k: E[k] for k in ('title', 'short', 'kicker', 'blurb', 'when', 'zip')}, 'dur': round(total),
            'cover': f'audio/cover-{ep}.png', 'feed': f'feed-{ep}.xml', 'full': full, 'chapters': rows}


def feed(e):
    """A podcast feed per episode: each chapter is one episode of a 'serial' show, so apps list them in order."""
    t0 = 1792108800                         # 2026-10-16 00:00 UTC (a past date: some apps hide future ones): chapter n is dated n minutes later, so the order holds
    items = []
    for r in e['chapters']:
        d = int(r['dur'])
        desc = ' '.join(i['ask'] for i in r['show'])[:3900] or e['blurb']
        items.append(f"""  <item>
    <title>{escape(f"{r['n']:02d} · {r['title']}")}</title>
    <itunes:episode>{r['n']}</itunes:episode>
    <itunes:episodeType>full</itunes:episodeType>
    <description>{escape(desc)}</description>
    <enclosure url="{BASE_URL}{r['file']}?v={r['ver']}" length="{r['bytes']}" type="audio/mpeg"/>
    <guid isPermaLink="false">hs2-podcast-{e['id']}-{r['n']:02d}-{r['ver']}</guid>
    <pubDate>{formatdate(t0 + 60 * r['n'], usegmt=True)}</pubDate>
    <itunes:duration>{d // 3600:d}:{d % 3600 // 60:02d}:{d % 60:02d}</itunes:duration>
  </item>""")
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>{escape(e['title'])}</title>
  <link>{BASE_URL}</link>
  <atom:link href="{BASE_URL}{e['feed']}" rel="self" type="application/rss+xml"/>
  <language>en-nz</language>
  <description>{escape(e['blurb'] + ' ' + e['when'] + '.')}</description>
  <itunes:author>HS2 SAQ Podcast</itunes:author>
  <itunes:type>serial</itunes:type>
  <itunes:explicit>false</itunes:explicit>
  <itunes:block>Yes</itunes:block>
  <itunes:image href="{BASE_URL}{e['cover']}"/>
  <itunes:category text="Education"/>
{chr(10).join(items)}
</channel>
</rss>
"""
    open(os.path.join(HERE, e['feed']), 'w', encoding='utf-8', newline='\n').write(xml)


def page(eps):
    tpl = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read()
    if tpl.count('/*@DATA@*/') != 1:
        raise SystemExit("template.html needs exactly one /*@DATA@*/")
    data = {'built': time.strftime('%Y-%m-%d'), 'episodes': eps}
    out = tpl.replace('/*@DATA@*/', json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/'))
    open(os.path.join(HERE, 'index.html'), 'w', encoding='utf-8', newline='\n').write(out)
    json.dump(data, open(os.path.join(HERE, 'episodes.json'), 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=1)
    print(f"index.html + episodes.json: {sum(len(e['chapters']) for e in eps)} chapters", flush=True)


# ── checks ────────────────────────────────────────────────────────────────────────────────────────────────
def dry(ep, chs, banks):
    words = pause = 0
    for ch in chs:
        w = sum(len(v.split()) for k, _, v in segs(ch) if k == 'say')
        p = sum(v for k, _, v in segs(ch) if k == 'pause')
        q = sum(len(v.split()) for k, who, v in segs(ch) if k == 'say' and who == 'q')
        words += w; pause += p
        print(f"  {ep} {ch['n']:02d}  {w:5,} words ({q:3} examiner)  ~{(w / 155 + p / 60):4.1f} min  {ch['title']}")
    print(f"{ep}: {len(chs)} chapters, {words:,} words, ~{words / 155 + pause / 60:.0f} min · coverage {coverage(ep, chs, banks)} questions")


WORDS_OK = set("""about above across after again against along also although always among another answer answers around
because become becomes before begin behind being below between both bring brings called cannot change changes come comes
could different does doing done down during each either every first follow following from gives going happen happens
having here inside into itself just keeps know large later least less little long made make makes many marks might more
most much must near need needs never next none nothing number often once only other others over part parts people place
question questions really right same says second should show shows side since small some something start starts still
such take takes tell than that their them then there these they thing things think third this those three through time
times together too toward towards under until very want what when where which while whole will with without words would
write your yourself because""".split())


def audit(eps):
    seen = {}
    for ep in eps:
        for ch in chapters(ep):
            for k, _, v in segs(ch):
                if k == 'say':
                    for w in re.findall(r"[A-Za-zāēīōū][A-Za-zāēīōū'’-]*", v):
                        w = w.strip("'’-")
                        if len(w) >= 6 and w.lower() not in WORDS_OK:
                            seen.setdefault(w.lower(), w)
    words = sorted(seen)
    said = dict(zip(words, espeak([seen[w] for w in words])))
    for lw in words:
        tag = '*' if lw in IPA else ' '
        print(f"{tag} {seen[lw]:24s} {IPA.get(lw) or said[lw]}")
    print(f"{len(seen)} words (* = hand-written phonemes)")


if __name__ == '__main__':
    argv = sys.argv[1:]
    if '--say' in argv:
        text = argv[argv.index('--say') + 1]
        who = 'q' if '--q' in argv else 'main'
        ph = ' '.join(phonemes(v) for k, v in pieces(text) if k == 'say')
        print(ph)
        a = np.concatenate([level(say(v, who)) for k, v in pieces(text) if k == 'say'])
        sf.write(os.path.join(WORK, 'say.wav'), a, SR, subtype='PCM_16')
        print(f"{WORK}/say.wav  {len(a)/SR:.1f} s")
        sys.exit()
    eps = [a for a in argv if a in EPISODES] or list(EPISODES)
    if '--audit' in argv:
        audit(eps); sys.exit()
    banks = {'t3': t3_bank(), 'final': final_bank()}
    chs = {ep: chapters(ep) for ep in eps}
    for ep in eps:
        check(chs[ep], ep)
        coverage(ep, chs[ep], banks)
    if '--dry' in argv:
        for ep in eps:
            dry(ep, chs[ep], banks)
        sys.exit()
    if '--build' not in argv:
        wanted = [int(a) for a in argv if a.isdigit()]
        for ep in eps:
            for ch in chs[ep]:
                if not wanted or ch['n'] in wanted:
                    voice_chapter(ep, ch)
    if '--no-build' in argv:
        sys.exit()
    every = {ep: chapters(ep) for ep in EPISODES}
    missing = [(ep, c['n']) for ep in EPISODES for c in every[ep] if any(k == 'say' and not cached(v, w) for k, w, v in segs(c))]
    if missing:
        print('still to voice:', missing)
        sys.exit(1)
    built = [build(ep, every[ep], banks) for ep in EPISODES]
    for e in built:
        feed(e)
    page(built)
