# Blind Spots of Frontier Models — 2-Day Research Plan

> **Rule for this project:** the topic, the prompts, the labels, the analysis and the README text are written by **you**. Tools (including AI assistants) may help with setup, code plumbing and reviewing your design. Reviewers are explicitly looking for human thought — rough and specific beats polished and generic.

---

## 0. The whole task in three sentences

1. **Find** something AI gets wrong about *your* world — something that comes from your life and that normal benchmarks don't test.
2. **Prove** it with a small, fair, controlled experiment on a 0.6B–6B open-weight model, so the failure is clearly *because of your context* and not just "the model is weak".
3. **Propose** a fix (data, fine-tuning, or architecture) that follows from what your experiment showed, and publish everything on Hugging Face.

### Final deliverables

| # | Deliverable | File |
|---|---|---|
| 1 | Evaluation dataset you wrote | `eval_set.csv` |
| 2 | Raw model outputs | `outputs_<model>.csv` (one per run) |
| 3 | Your scored / labelled sheet | `scored.csv` |
| 4 | Notebook that reproduces everything | `blind_spot_eval.ipynb` |
| 5 | Charts / tables | `figures/` |
| 6 | README answering Q1 + Q3 (+ results) | `README.md` |
| 7 | Public Hugging Face Bucket (or dataset repo) link | submitted in the form |

---

## 1. Core concepts (read once, keep in mind throughout)

### 1.1 What a "blind spot" is
Models learn mostly from English, US/EU-centric internet text, so they carry a **default picture of the world**. A blind spot is where **your reality differs from that default and the model doesn't notice**.

### 1.2 Three types of blind spot

| Type | What happens | How you detect it |
|---|---|---|
| **A — Doesn't know** | The fact is missing from the model | Fails even when context is stated very clearly |
| **B — Wrong default** | Knows the fact but assumes the Western version | Correct when reminded/hinted, wrong when not |
| **C — Can't handle the form** | Knows the content but breaks on *how* it is said (mixed language, script, slang, local format) | Good in English/standard form, bad in your form |

You don't need to know the type at the start — a guess is enough. The Day-2 experiments will tell you.

### 1.3 The paired design (the single most important idea)
Every test item exists in **two (or three) versions that differ in only one thing — the context**:

| Condition | Meaning |
|---|---|
| `control` | Same task in the standard / Western / English context |
| `treatment` | Same task in your context |
| `variant` *(optional)* | Same treatment in a different form (e.g. other script, informal register) |

**Blind spot = accuracy(control) − accuracy(treatment).**
Without controls you can only say "the model is bad". With controls you can say "the model is bad *at this specific thing*".

### 1.4 Worked example (deliberately *not* your topic — only to show the shape)
- **Moment:** "In Japan the school year starts in April; a child born in March is in the *older* class."
- **Question:** "My son was born in March 2019 in Osaka. What grade is he in during May 2026?"
- **Control:** same question with "Ohio" (US September cutoff → different correct answer).
- **Pilot result:** Ohio correct, Osaka wrong → gap exists.
- **Probe:** "When does the Japanese school year start?" → model says April correctly → **Type B**.
- **Hypothesis:** "The model applies US school-year rules by default even when a non-US location is stated, despite knowing the local rule."

---

## 2. Before you start (≈30 min, do the evening before if possible)

- [ ] Google account → open https://colab.research.google.com → *Runtime → Change runtime type → T4 GPU* works.
- [ ] Hugging Face account → create a **write** token (*Settings → Access Tokens*). Keep it private; never paste it into a file you upload.
- [ ] If you might use a gated model (Gemma, Llama): open its model page and click *Agree / Request access* now — approval can take time.
- [ ] Create a Google Drive folder `blind_spot/` (Colab wipes local files on disconnect).
- [ ] Create a Google Sheet with the dataset columns from §5.2 (easier to write items in a sheet, then export CSV).
- [ ] Open a plain notes doc called **"research log"**. Every decision, surprise and dead end goes here with a timestamp. This becomes raw material for the README and is strong evidence of your own thinking.

---

## 3. Time budget overview

| Day | Block | Hours | Output |
|---|---|---|---|
| **1** | B1 — Find the blind spot (thinking) | 0:00–1:15 | 2–3 candidates |
| 1 | B2 — Model choice + Colab setup | 1:15–2:15 | `generate()` works |
| 1 | B3 — Pilot test | 2:15–3:00 | Pilot table, one chosen topic |
| 1 | B4 — Hypothesis | 3:00–3:15 | One sentence + type guess |
| 1 | B5 — Build dataset | 3:15–7:00 | `eval_set.csv` (40–60 pairs) |
| 1 | B6 — Main run | 7:00–8:30 | `outputs_<model>.csv` |
| **2** | B7 — Scoring | 0:00–1:30 | `scored.csv` |
| 2 | B8 — Statistics + error taxonomy | 1:30–3:00 | Numbers, taxonomy counts, examples |
| 2 | B9 — Follow-up experiments (pick 2) | 3:00–5:00 | Extra outputs + findings |
| 2 | B10 — Write README | 5:00–7:00 | `README.md` |
| 2 | B11 — Publish + final check | 7:00–8:00 | Public link |

**Decision gate:** if by the end of Day-1 hour 3 no candidate shows a gap → go back to B1 with your next moments. Don't build a dataset on a weak idea.

---

# DAY 1

## B1 — Find the blind spot (0:00–1:15)

### Step 1: Collect *moments*, not AI ideas (30 min)
Don't think about AI yet. Write **15+ concrete moments** from your life where the "standard" assumption didn't fit your reality.

Areas to search your memory:
- **Language** — how you actually text family/friends (mixed languages? Roman script? local words?)
- **Numbers & money** — number words, units, currency, prices, how amounts are spoken
- **Time** — calendars, dates, holidays, working days, seasons
- **Systems** — exams, grading, admissions, government documents, banking, healthcare, legal process
- **Daily infrastructure** — electricity, internet, transport, payments
- **Family & social life** — decisions, events, forms of address, relationships, norms
- **Your field** — engineering/aviation as practised where you live, not as textbooks describe it
- **Times you used ChatGPT/Claude** and had to "translate yourself" to get a useful answer

| ✅ Good moment (specific, observable) | ❌ Bad moment (a conclusion, not a moment) |
|---|---|
| "An online calculator didn't understand a price my uncle gave me in local number words." | "AI is biased against my country." |

**Worksheet — Moments list**

| # | Moment (1–2 lines, specific) | Area |
|---|---|---|
| 1 | | |
| 2 | | |
| … | | |
| 15 | | |

### Step 2: Turn moments into questions with a known answer (30 min)
For each moment ask: *"What question could I ask a model where I know the correct answer and the model might get it wrong?"*
If you can't think of one with a clear correct answer → cross the moment out.

**Worksheet — Questions**

| Moment # | Question I'd ask the model | Correct answer | How I know it's correct (source) |
|---|---|---|---|
| | | | |

### Step 3: Filter (15 min)
Keep only ideas that pass **all three** tests:

| Candidate | Gradable? (right/wrong without debate) | Pairable? (a fair standard version exists) | Personal? (I can say in 2 lines why *I* noticed it) | Keep? |
|---|---|---|---|---|
| | | | | |

Also drop ideas where the answer:
- changes often (prices, current officeholders) → confounded by the model's knowledge cutoff, not a blind spot;
- is genuinely disputed → you can't grade it;
- already has a well-known benchmark → not "underexplored".

**Output of B1:** 2–3 candidates, each with 1 example pair.

---

## B2 — Choose the model and set up Colab (1:15–2:15)

### 2.1 Choosing the model (this choice is graded — write down your reasoning)
Check the current trending list: https://huggingface.co/models?num_parameters=min:0.6B,max:6B&sort=trending

Criteria to justify in the README:
1. **Recent, from a frontier lab family** → realistically reflects current frontier behaviour.
2. **Instruction/chat-tuned** → that's how real users meet these models.
3. **Fits a free T4** (15 GB VRAM). Rule of thumb: params × 2 bytes in fp16 → 4B ≈ 8 GB.
4. **Open license, no long approval wait.**
5. **Bonus:** has a smaller/larger sibling (lets you test scale) or a reasoning switch (lets you test "does thinking help?").

Candidates known at the time of writing (verify they're still current):
- `Qwen/Qwen3-4B` — Apache-2.0, ungated, has a thinking on/off switch, sibling `Qwen/Qwen3-1.7B`. **Default choice for the code below.**
- `google/gemma-3-4b-it` — strong multilingual coverage, gated, needs a different loading class (`Gemma3ForConditionalGeneration` / `pipeline("image-text-to-text")`).

**Worksheet — Model justification (fill in your own words)**
```
Model chosen:
Exact revision / commit hash (from the "Files and versions" tab):
Why it represents frontier behaviour:
Why this size:
Why not the alternatives:
```

### 2.2 Colab cells

**Cell 1 — install**
```python
!pip -q install -U transformers accelerate huggingface_hub pandas statsmodels
```

**Cell 2 — mount Drive (outputs survive disconnects)**
```python
from google.colab import drive
drive.mount('/content/drive')
BASE = "/content/drive/MyDrive/blind_spot"
```

**Cell 3 — load model**
```python
import torch, pandas as pd
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_ID = "Qwen/Qwen3-4B"
tok = AutoTokenizer.from_pretrained(MODEL_ID)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID, torch_dtype=torch.float16, device_map="auto")
model.eval()
```

**Cell 4 — generation function**
```python
def generate(prompt, system=None, thinking=False, max_new_tokens=400):
    msgs = ([{"role": "system", "content": system}] if system else []) + \
           [{"role": "user", "content": prompt}]
    text = tok.apply_chat_template(msgs, tokenize=False,
                                   add_generation_prompt=True,
                                   enable_thinking=thinking)  # Qwen3-specific flag
    ids = tok(text, return_tensors="pt").to(model.device)
    with torch.no_grad():
        if thinking:
            # Qwen recommends sampling (not greedy) in thinking mode
            torch.manual_seed(0)
            out = model.generate(**ids, max_new_tokens=max_new_tokens,
                                 do_sample=True, temperature=0.6, top_p=0.95)
        else:
            out = model.generate(**ids, max_new_tokens=max_new_tokens,
                                 do_sample=False)  # greedy = reproducible
    answer = tok.decode(out[0][ids.input_ids.shape[1]:], skip_special_tokens=True)
    return answer.split("</think>")[-1].strip()   # drop reasoning trace if present

print(generate("Say hello in one line."))
```

✅ **Checkpoint:** the last line prints a short reply. If you get an out-of-memory error, confirm the runtime is T4 and restart the session.

---

## B3 — Pilot test (2:15–3:00)

For each of your 2–3 candidates write **5 control + 5 treatment** prompts and run them.

```python
pilot = [
    # ("candidate", "condition", "prompt", "gold")
]
for cand, cond, p, gold in pilot:
    print(f"--- {cand} | {cond} | gold: {gold}\n{generate(p)}\n")
```

**Worksheet — Pilot log**

| Candidate | Control correct (/5) | Treatment correct (/5) | Verdict |
|---|---|---|---|
| | | | |

How to read it:
- **Control high, treatment low** → real gap → **keep**.
- **Both high** → no gap → drop.
- **Both low** → model is just weak at the task → drop (not a blind spot).

Pick the candidate with the clearest gap **and** the strongest personal story.

---

## B4 — Write the hypothesis (3:00–3:15)

Template:
> "The model performs worse on **[task]** when **[my context]** replaces **[standard context]**, because **[type A / B / C guess]**."

Also write down **3–5 sub-categories** of your topic (different flavours of the same gap). They become the `category` column and drive your error analysis later.

```
Hypothesis:
Type guess (A/B/C) and why:
Sub-categories:
 1.
 2.
 3.
```

---

## B5 — Build the dataset (3:15–7:00)

### 5.1 Size
- **40–60 pairs** (80–180 rows). Enough for a paired statistical test, small enough to write by hand.
- Spread evenly across your 3–5 sub-categories (~10–15 pairs each).

### 5.2 Columns (`eval_set.csv`)

| Column | Meaning | Example values |
|---|---|---|
| `id` | Unique row id | `p01_c`, `p01_t` |
| `pair_id` | Links control and treatment | `p01` |
| `condition` | Which version | `control`, `treatment`, `variant` |
| `category` | Sub-category of the gap | your 3–5 labels |
| `prompt` | Exact text sent to the model | |
| `gold_answer` | Correct answer | |
| `scoring_type` | How to grade | `exact`, `contains`, `rubric` |
| `source` | How you know the gold answer is right | link / document / "personal knowledge — explained in notes" |
| `notes` | Why this item matters / what it tests | |

### 5.3 Rules for fair pairs (reviewers will check this)
1. **Change only the context variable.** Same length, same structure, same difficulty, same answer format.
2. **Don't make controls easier.** If anything, make them equally hard — a gap that survives that is convincing.
3. **Every gold answer must be verifiable** — fill in `source`.
4. **No time-sensitive facts** (prices, current events) — that measures knowledge cutoff, not blind spots.
5. **Ask for a short, checkable answer format** when possible (e.g. "Answer with just the number"). Makes scoring fast and objective.
6. **Mix difficulty** within each category so results aren't driven by a few trivial items.
7. **Write it yourself.** Don't generate items with an AI — it defeats the purpose and is easy to spot.

### 5.4 Self-check before running
- [ ] Every `pair_id` has both a `control` and a `treatment` row.
- [ ] Read 5 random pairs aloud: is the *only* difference the context?
- [ ] Every row has a `gold_answer` and `source`.

```python
df = pd.read_csv(f"{BASE}/eval_set.csv")
print(df.condition.value_counts())
print(df.groupby("pair_id").condition.nunique().value_counts())  # all should be ≥2
```

---

## B6 — Main run (7:00–8:30)

```python
import os
df = pd.read_csv(f"{BASE}/eval_set.csv")
out_path = f"{BASE}/outputs_qwen3-4b.csv"

done = set(pd.read_csv(out_path).id) if os.path.exists(out_path) else set()
rows = pd.read_csv(out_path).to_dict("records") if done else []

for _, r in df.iterrows():
    if r["id"] in done:
        continue                      # resume after a disconnect
    rows.append({**r.to_dict(), "output": generate(r["prompt"])})
    pd.DataFrame(rows).to_csv(out_path, index=False)  # save every row
```

- Expect roughly 30–60 min for ~150 rows on a T4. Keep the tab open.
- While it runs: write your **scoring rubric** (§B7) and update the research log.

**End of Day 1 checklist**
- [ ] Hypothesis sentence written
- [ ] Model justification written
- [ ] `eval_set.csv` saved to Drive
- [ ] `outputs_qwen3-4b.csv` complete
- [ ] Research log updated

---

# DAY 2

## B7 — Scoring (0:00–1:30)

### 7.1 Automatic pre-scoring for `exact` / `contains` items
```python
import re
o = pd.read_csv(f"{BASE}/outputs_qwen3-4b.csv")

def norm(s): return re.sub(r"\s+", " ", str(s).lower()).strip()

def auto_score(r):
    if r.scoring_type == "exact":
        return int(norm(r.output) == norm(r.gold_answer))
    if r.scoring_type == "contains":
        return int(norm(r.gold_answer) in norm(r.output))
    return None   # rubric → score by hand

o["auto_correct"] = o.apply(auto_score, axis=1)
o["correct"] = o["auto_correct"]
o["error_code"] = ""
o.to_csv(f"{BASE}/to_score.csv", index=False)
```

### 7.2 Hand-scoring
- Open `to_score.csv` in Google Sheets.
- **Check every auto score by eye** (regex makes mistakes), fill in `correct` (0/1) for rubric items.
- Rubric items: define 0 / 1 in one line each *before* you start, and apply them consistently.
- Save as `scored.csv`.

**Do not use an LLM as the grader.** Your own labels are stronger evidence and match the "do it yourself" requirement.

---

## B8 — Statistics and error taxonomy (1:30–3:00)

### 8.1 Headline numbers
```python
s = pd.read_csv(f"{BASE}/scored.csv")
print(s.groupby("condition").correct.mean())                  # overall accuracy
print(s.pivot_table(index="category", columns="condition",
                    values="correct", aggfunc="mean"))         # per category
```

### 8.2 Is the gap statistically real? (McNemar test on pairs)
```python
from statsmodels.stats.contingency_tables import mcnemar
w = s.pivot_table(index="pair_id", columns="condition", values="correct")
both   = ((w.control == 1) & (w.treatment == 1)).sum()
c_only = ((w.control == 1) & (w.treatment == 0)).sum()
t_only = ((w.control == 0) & (w.treatment == 1)).sum()
neither= ((w.control == 0) & (w.treatment == 0)).sum()
print([[both, c_only], [t_only, neither]])
print(mcnemar([[both, c_only], [t_only, neither]], exact=True))
```
- `c_only` = pairs where the model got the control right but your version wrong → **the blind spot in one number**.
- p < 0.05 → the gap is unlikely to be chance.

### 8.3 Confidence interval for the gap (bootstrap over pairs)
```python
import numpy as np
diff = (w.control - w.treatment).dropna().values
boots = [np.random.choice(diff, len(diff)).mean() for _ in range(5000)]
print("gap:", diff.mean(), "95% CI:", np.percentile(boots, [2.5, 97.5]))
```

### 8.4 Error taxonomy (the most "human" part — take your time)
1. Filter all rows where `correct == 0`.
2. Read each output fully. Write a short free-text note about *what went wrong*.
3. After ~15 notes, group them into **4–6 error codes you invent** (shapes like: "assumed the Western default", "knew the fact but applied it wrong", "hedged/refused", "fluent but invented details" — but use your own based on what you see).
4. Go back and assign one code to every failure (`error_code` column).
5. Count them.

```python
print(s[s.correct == 0].groupby(["condition", "error_code"]).size())
```

6. Pick **3–5 vivid examples** (prompt + model output + correct answer + your one-line comment) for the README.

### 8.5 Charts (make 1–2, keep them simple)
- Bar chart: accuracy by category, control vs treatment side by side.
- Bar chart: count of each error code in the treatment condition.
Save to `figures/`.

---

## B9 — Follow-up experiments: find out *why* (3:00–5:00)

**Pick the 2 that best test your type guess.** Each one answers a specific question.

### Option 1 — Hint test (Type A vs Type B)
*Question: does the model have the knowledge but not use it?*
```python
HINT = "The user lives in ___. Use local conventions."   # write your own one line
o_hint = [{**r.to_dict(), "output": generate(r["prompt"], system=HINT)}
          for _, r in df[df.condition == "treatment"].iterrows()]
pd.DataFrame(o_hint).to_csv(f"{BASE}/outputs_hint.csv", index=False)
```
- Gap closes with the hint → **Type B** (wrong default).
- Gap stays → **Type A** (missing knowledge).

### Option 2 — Thinking mode
*Question: does reasoning fix it, or just justify the wrong default in more words?*
Run a subset (~30 pairs; thinking is slow on T4):
```python
sub = df[df.pair_id.isin(df.pair_id.unique()[:30])]
o_think = [{**r.to_dict(), "output": generate(r["prompt"], thinking=True,
                                              max_new_tokens=1500)}
           for _, r in sub.iterrows()]
pd.DataFrame(o_think).to_csv(f"{BASE}/outputs_thinking.csv", index=False)
```
Read a few full reasoning traces (remove the `.split("</think>")` temporarily) — *where* the reasoning goes wrong is a great README example.

### Option 3 — Scale
*Question: does a smaller model have the same gap? Same-size gap across scales → data problem, not capacity problem.*
```python
del model; import gc; gc.collect(); torch.cuda.empty_cache()
MODEL_ID = "Qwen/Qwen3-1.7B"
# re-run Cell 3, then the B6 loop with out_path = f"{BASE}/outputs_qwen3-1.7b.csv"
```

### Option 4 — Tokenization (only if your gap involves language/script — Type C)
*Question: does the model "see" your language as many more pieces than English?*
```python
pairs = [("english sentence", "same sentence in your language/script")]  # write your own
for en, mine in pairs:
    print(len(tok.encode(en)), len(tok.encode(mine)), "|", mine)
```
More tokens for the same meaning → each word is more fragmented → harder to learn from.

Score the follow-up outputs the same way as B7 and add one row/column per experiment to your results table.

**Worksheet — Findings summary**

| Experiment | Control acc | Treatment acc | Gap | What it tells me |
|---|---|---|---|---|
| Main (Qwen3-4B) | | | | |
| Follow-up 1 | | | | |
| Follow-up 2 | | | | |

---

## B10 — Write the README (5:00–7:00)

Write in **your own voice**. Use your research log. Use this skeleton — the prompts in *italics* are questions for you to answer, not text to copy.

```markdown
# [Your title — name the blind spot specifically]

## 1. The blind spot (Q1)
*The moment from your life where you first noticed this. Who, where, what happened.*
*What the model assumes vs how it actually works in your world.*
*Why standard benchmarks don't capture this (what do they test instead?).*
*Why it matters — who is affected, and what goes wrong for them in practice.*

## 2. Hypothesis
*Your one-sentence hypothesis and type guess.*

## 3. Setup
- Model: *name + revision hash + why you chose it (your justification)*
- Decoding: greedy, max_new_tokens=…, (thinking settings if used)
- Hardware: Colab T4
- Dataset: *N pairs, sub-categories, how you wrote and verified them, rules you followed to keep pairs fair*

## 4. Results
*Headline: control vs treatment accuracy, gap, 95% CI, McNemar p-value.*
*Per-category table.*
*Figure(s).*

## 5. How the model fails
*Your error taxonomy: each code, a one-line definition, its count.*
*3–5 examples: prompt → model output → correct answer → your comment.*

## 6. Why it fails (follow-up experiments)
*What each follow-up showed, and what that means for type A/B/C.*

## 7. Path forward (Q3)
*Tie each proposal to a finding above:*
- *If it lacks knowledge → what data curation? Which sources, collected by whom, how verified?*
- *If it knows but defaults wrongly → what fine-tuning? What would the training pairs look like?*
- *If the form breaks it → tokenizer/vocabulary or architectural changes?*
*How would you test that your fix worked? (Hint: your own dataset becomes the test set.)*

## 8. Limitations
*Small sample, one annotator (you), one model family, things you'd do with more time.*

## 9. Files in this bucket
*List each file and what it contains.*
```

**Q3 guidance (how to think, not what to write):** your fix must follow from your evidence. If your hint test showed the model *already knows* the facts, "add more data" is the wrong answer — the problem is the default, so the fix is about training it to use context. Let the experiment decide.

---

## B11 — Publish and final check (7:00–8:00)

### 11.1 Collect the artifacts in one folder
```
artifacts/
├── README.md
├── eval_set.csv
├── outputs_qwen3-4b.csv
├── outputs_<follow-up>.csv
├── scored.csv
├── blind_spot_eval.ipynb      # File → Download .ipynb from Colab
└── figures/
```
- **Model:** link to the base model with its exact revision hash in the README rather than re-uploading ~8 GB (upload weights only if you fine-tuned something).
- Remove any token, password or personal data from the notebook before uploading (*Edit → Clear all outputs* if a cell printed a token).

### 11.2 Upload
The task asks for a **Hugging Face Bucket**. Check the current HF docs / the *New* menu in your account for "Bucket" and follow that flow. If Buckets aren't available to your account, a public **dataset repo** is the standard fallback — mention it in your submission.

Dataset-repo fallback:
```python
from huggingface_hub import HfApi, login
login()   # paste your WRITE token when prompted; never hard-code it
api = HfApi()
api.create_repo("YOUR_USERNAME/blind-spot-eval", repo_type="dataset", private=False)
api.upload_folder(folder_path=f"{BASE}/artifacts",
                  repo_id="YOUR_USERNAME/blind-spot-eval", repo_type="dataset")
```

### 11.3 Final checklist
- [ ] Link opens in a **private/incognito** window (it's really public)
- [ ] README renders, answers **Q1** and **Q3** clearly
- [ ] Model name + revision hash + justification present
- [ ] Dataset, outputs, scored sheet, notebook all present
- [ ] Numbers in README match `scored.csv`
- [ ] No secrets in any file
- [ ] Link pasted into the application form

---

## 4. Risks and fallbacks

| Risk | Sign | What to do |
|---|---|---|
| No gap in pilot | Treatment ≈ control | Next candidate from B1; try a harder or more specific framing |
| Both conditions fail | Low control accuracy | The task is too hard for the model — simplify the answer format or pick another topic |
| Colab disconnects | Session lost | Outputs are on Drive; the B6 loop resumes where it stopped |
| Out of GPU memory | CUDA OOM | Restart runtime; check T4 is selected; `del model` before loading another |
| Gated model not approved | 403 on download | Use `Qwen/Qwen3-4B` |
| Free GPU quota used up | Can't get a T4 | Use Modal free tier, or Kaggle notebooks (free GPUs) |
| Thinking mode too slow | Long runs | Limit to ~30 pairs, max_new_tokens 1500 |
| Running out of time on Day 2 | Behind schedule | Do only **one** follow-up; never cut the error taxonomy or Q1 story — those carry the most weight |

---

## 5. What makes this submission strong (keep checking against this)

1. **A specific, personal story** for the blind spot — reviewers rank this highest.
2. **Fair controls** — proves it's *this* blind spot, not general weakness.
3. **Your own error taxonomy** — shows you actually read the outputs.
4. **At least one "why" experiment** — moves from "it fails" to "it fails because…".
5. **A Q3 proposal that follows from your evidence** — not a generic list.
6. **Honest limitations** — reads as rigour, not weakness.
