# HS2 SAQ Podcast (unlisted, `noindex`: https://jeremyspm.github.io/hs2-podcast/)

Two episodes that cover every written question each sitting can ask, read by Kokoro (local, CPU):

| Episode | Tracks | What is in it |
|---|---|---|
| **Test 3 — Every SAQ** | 41 | Her words (10 Aug): "there is no such list" of test questions; the Module 3 Learning Checklist "limits what I may ask". So every one of its 36 points has a track (`@ crit:`, gated): the 25 SAQ Trainer questions of [hs2-test3](../hs2-test3) (`content/saq-*.json`), plus eight tracks added 16 Oct from her quiz keys, model answers and 2026 decks: genetics terms (her quiz 211104 Q13), DNA and mutations, multiple alleles and X-linked, the retina (Q2), the male and female systems (Q17, 10 marks), semen and the male response, the female response and the four terms; and testosterone in females (Q21). Then track 35, **the closed questions** (`script/t3/5-closed-extras.txt`, ~10 min): Test 3 is ~70% closed by marks, so the one-line facts her quiz keys ask that no written answer covers, each from her key (the quiz ids are in the file's `%` notes): Klinefelter / Turner / Edwards, amniocentesis, the pupil's sympathetic and parasympathetic control, the inverted image and the optic chiasma, her eye-conditions and treatments tables, ototoxic drugs (sensorineural), tonotopy, sound shirts, Doppler, and fertilisation and early pregnancy (not on her checklist, asked in her quizzes). **20 Oct: five fine-print tracks** (~33 min), one at the end of each section: every one of the 429 questions in hs2-test3's `bank-dump.json` was read against the scripts, and each key no track said went into one, in her key's words — genetics (pedigree symbols, Y-linked, Queen Victoria, monohybrid, test cross, gametes outside / zygotes inside, mutagen, haploid / diploid, the flowers, sickle-cell crosses, amniocentesis = most common but CVS = most reliable), the eye part by part (her 20-mark table and worksheets: conjunctiva, both humours, hyaloid canal, macula, optic disc, choroid, strabismus, blue-eye pigment), the ear and sound (meatus, ceruminous glands, round window, perilymph low K⁺ / endolymph high K⁺, glutamate, apex vs base, her orders, photons, lux, red-to-violet), sperm, eggs and ovulation (acrosome, midpiece mitochondria, the cells with their chromosome counts, her six differences, the tertiary follicle, her hormone tables), and erection, the breast and her female words (her five steps in order, her breast tables, abortion, 40 weeks). The pedigree track also says the deceased line and the numbering now. An intro first, Rapid-fire last. |
| **Final — Every case SAQ** | 21 | All 75 written and formative questions of the ten yellow, starred cases in [hs2-final](../hs2-final)'s built DATA, in booklet order, plus the 8 starred questions she has not answered (held in the sim), each answered from her module content and said to be. |

**One MP3 per chapter** — the answer to "my phone has no app that reads embedded chapters": any music app, file app or
podcast app shows numbered tracks and can repeat one. Three ways in, all from the same files:

1. `index.html` — the player: tap a question, loop it (or play each ×2 / ×3), speed, resume, lock-screen and earbud
   controls (skip = next question), and the question with her short answer under the track that is playing (answer hidden
   until tapped). `#t3` / `#final` opens that episode.
2. Download: ⤓ beside each track, or "Download all", which zips the episode **in the browser** (JSZip from cdnjs), so the
   audio is stored once. The same zips are built locally in `D:/hs2-audio/podcast/` for sharing directly.
3. `feed-t3.xml`, `feed-final.xml` — podcast feeds (a serial show; every question an episode, in order;
   `itunes:block` so directories never list it). Apple Podcasts → Library → ⋯ → Follow a Show by URL.

**Subtitles** (20 Oct): every chapter has `audio/<ep>/NN.vtt`, timed by the build itself, not by speech recognition. `chapter_audio`
knows where each spoken paragraph starts and ends to the sample; the lines inside a paragraph (sentences, long ones cut again at
their commas) share its span by length. The text is the script as written (`shown()`), not the respelling the voice reads, and
the examiner's lines carry `<v Examiner>`. The player shows the current line above the title (CC toggles it); the `.vtt` files are not in
any zip (below); the feeds carry `podcast:transcript` for apps that show transcripts. A paragraph
whose written and spoken pieces don't line up fails `--dry`.

**Videos and scripts** (21 Oct): a classmate unzipped the episode, opened a `.vtt` ("a file only playing text but no sound") and
could not find a subtitle button. No phone does anything with a `.vtt`, so every chapter also has `audio/<ep>/NN.mp4`: the same
audio with the words drawn on (portrait 720×1280, the line being said big and bright, the examiner's in amber, the lines around it
dim; `ass()` writes the subtitles, libass draws them), which plays in any gallery or files app. And `audio/<ep>/NN.pdf`, the script
as written, the examiner's paragraphs in bold (`script_pdf()`, byte-identical between builds). Videos stop when a phone locks, so
the MP3 stays the one to listen to. Rendered MP4s are kept in `D:/hs2-audio/podcast/video` by hash of their subtitles and MP3,
so a build renders only the chapters that changed. The player has 🎬 / 📄 under the playing track and a zip of every video and
script; the local zips are `<zip>.zip` (MP3s) and `<zip>-Videos-and-scripts.zip`.

## Build

    python podcast.py --dry        # words, minutes, every gate; voices nothing
    python podcast.py --audit      # every long word with the phonemes Kokoro will say (review after any script edit)
    python podcast.py --say "..."  # one line to D:/hs2-audio/podcast/say.wav
    python podcast.py --no-build   # voice what is not cached (run two or three at once: a .lock per chapter shares the work)
    python podcast.py --build      # MP3s → audio/, index.html + episodes.json, both feeds, the local zips

Then commit `audio/`, `index.html`, `episodes.json` and the feeds. Each chapter's `?v=` is a hash of its MP3, so a re-render
reaches browsers and podcast apps; a track whose audio did not change keeps its hash.

Paths: model `D:/hs2-audio/model`, paragraph cache `D:/hs2-audio/podcast/cache` (sha1 of voice + speed + **phonemes**, so a
pronunciation fix re-voices only the paragraphs that contain the word), ffmpeg from GameSentenceMiner. The on-screen text
needs `../hs2-test3` and `../hs2-final` checked out next to this repo.

**Long paragraphs** (20 Oct, "stutters at the end, less than a syllable"): Kokoro takes at most 510 phonemes, and past that
kokoro_onnx used to cut for us, at any comma. A paragraph of 509 or 510 phonemes left its last full stop as a piece of its own,
voiced as a loud 0.14 s blip after the last word (Test 3 tracks 2, 23, 27, 41), and its other cuts fell mid-sentence with no
pause. Now `batches()` cuts anything over 400 phonemes itself: whole sentences only, as evenly as they allow (no piece under
100 phonemes), joined by a 0.35 s sentence break. Long inputs also came out rushed: the same paragraph is 3.6 s longer in pieces.

## Gates (the render stops on any)

- **Checklist** (Test 3): every point of her Module 3 Learning Checklist (G1–9, SS1–13, R1–14) is named by some track's
  `@ crit:`; provoked 16 Oct by dropping a track (fails, naming R13 and R14).
- **Coverage**: every SAQ Trainer id in hs2-test3 and every `mod: 'cases'` question in hs2-final's DATA is named by some
  chapter's `@ saq:` / `@ q:`, and every id named exists. A new SAQ in either sim fails the build until a chapter covers it.
- A capital **A** used as a letter at the start of a sentence ("A, the trachea") — Kokoro reads it as "uh". Write "Letter A".
- A symbol the voice would drop; every hand-written phoneme must be in Kokoro's symbol set.

## The script (`script/<episode>/*.txt`, read in file order)

`# Title` starts a chapter; `@ saq:` / `@ q:` / `@ case:` / `@ held:` / `@ ask:` feed the player; `@ crit:` names checklist points; `@ say:` is the short name the
Rapid-fire track announces; `Q:` paragraphs are the examiner's voice (am_puck, picked by ear from 14 samples); `{recap}` paragraphs are in the chapter
and in Rapid-fire; `[pause N]`; `%` lines are notes. Everything else is af_heart, the voice of the Test 2 and Module 1
courses. Every answer follows the sim's own answer for that question (her model answers, decks, recorded sessions, quiz keys);
where it is the tool's or the podcast's reading, the track says so out loud.

## Pronunciation

`IPA` in `podcast.py` replaces espeak's guess with phonemes written by hand, spliced into the phoneme string Kokoro reads —
not respellings. 16 Oct 2026: the reported pair (homozygous "HAH-muh-ZIG-us", heterozygous "het-er-uh-ZIG-us") plus every
word the audit flagged across both scripts (≈85: stapes, Sertoli, prolactin, sclera, medulla, metastasis, Wernicke's, the
case names in te reo Māori, "contract" stressed as a noun, "Manaia lives" read as "lyves"…). Possessives follow the word
("Manaia's"). After any script edit, run `--audit` and read the words you added.
