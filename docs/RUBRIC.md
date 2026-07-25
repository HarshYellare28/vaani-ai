# Judging rubric — verbatim extract

Extracted from the organiser's Builder Handbook bundle for use during the build.
**GrowthX IP** — this is reference material for this build only. Keep this repo
private, or delete this file before publishing it.

Contains: the five Product parameters (scored for every team) and Branch A,
Voice Experience — the single Sarvam parameter this project has locked. The
Document Intelligence and Dubbing branches are omitted because judges score only
the one capability most central to the job, and extra capabilities add no points.

How to use it: read the full level description, not the headline. `SCOPE.md`
holds the target vector — which level we are aiming at on each parameter, and
which demo moment is the proof. The same proof cannot raise two parameters.

---

# Product parameters

## 1. Job-to-be-done completion

**The question:** Did the product produce the correct, usable outcome?

This ladder is locked and reproduced verbatim.

### L1
0 completed tasks. Demo only.

The agent gives canned responses or talks through the workflow, but does not complete the declared job.

Example: the agent talks about modifying an order but does not check the order, does not write to a support queue, does not update a sheet, and does not create any usable output. In hiring, it says it screened a candidate, but no scorecard, ATS update, rejection, shortlist, or next-step decision is created.

### L2
Less than 30% task success.

The agent runs, but the output is broken, fake, incomplete, or unusable.

Example: in payments, it pulls the wrong transaction, gives a made-up refund status, or tells the user that money has been reversed without checking the payment record. In quick commerce, it says the delivery slot has changed, but nothing changes in the support queue, sheet, dispatch mock, or order system.

### L3
50 to 70% task success on mocked, sandbox, or staged surfaces.

The agent completes a useful part of the declared job and creates at least one usable artifact.

Example: the agent verifies an order against a mocked order DB, writes to a mocked dispatch system, updates a sandbox support queue, creates a scorecard, drafts a support note, or classifies a payment dispute. Staged WordPress, sandbox Gmail, dummy ATS, mocked CRM, Airtable, Notion, or Google Sheets also sit here.

### L4
70 to 85% task success on a production-like demo workflow.

The agent completes most of the declared job across a realistic workflow. Human review may still be needed for final approval.

Example: the agent drafts the refund ticket inside a support queue, but a support lead must approve the refund. In hiring, it runs the first-round screen and drafts the scorecard in the ATS, but a recruiter must manually review and move the candidate. In payments, it classifies the dispute and prepares the escalation, but ops must confirm before the case moves.

### L5
85%+ task success across a minimum of three repeated test cases.

The agent completes the declared job end to end using mocked, sandbox, staged, or live demo surfaces, and produces a final usable output without judge intervention.

Example: in quick commerce, the agent verifies the order, identifies missing items, checks refund eligibility, writes back to the support queue, updates the order or ticket, and escalates only exceptions. In payments, it verifies identity, pulls the UTR, classifies failed-but-debited, refund-pending, fraud, or unrecognised transaction, gives the correct next step, and creates the right dispute record. In hiring, it detects the role, runs the right screen, scores the candidate using the right rubric, updates the ATS, and advances or rejects without HR involvement.

---

## 2. Memory and Context

**The question:** Does the product carry forward the right identity, history, task state, permissions, and business rules?

Memory is business continuity, not merely remembering chat messages. It includes what is happening now, what has happened before with this user or case, and what the business allows. It must preserve relevant context without leaking one user's or organisation's information to another.

Score only persisted, governed continuity here. Natural conversational flow inside one exchange belongs to Voice Experience, and describing an authentication scheme without demonstrating carried context does not establish Memory and Context.

### L1
Every interaction starts from zero.

The product does not retain the current task, user identity, prior answers, document state, or business context. The user repeatedly supplies the same details, and any handoff or restart loses everything.

Example: a customer gives the order ID, explains that the milk and bread are missing, and confirms that the bag arrived sealed. When the flow moves from the voice agent to the refund screen, it asks for the order ID again, forgets which items were missing, and makes the customer repeat the entire complaint from the beginning.

### L2
It remembers identifiers, but not the working context.

The product can hold one or two fields such as a name, phone number, case ID, document ID, or preferred language during the current interaction. It does not reliably retain the user's actual goal, prior decisions, permission scope, or the state of the job. Handoffs pass identity at best and re-ask everything that matters.

Example: a payment assistant remembers the caller's phone number and UTR, but loses the ₹4,200 amount, the transaction date, the fact that the account was debited, and the caller's request for a dispute. When the case moves to classification, the assistant knows who the user is but still asks, “What happened with your payment?”

### L3
It maintains the complete current task for an authenticated user.

The product knows who the user is, what they are allowed to access, what has already been supplied, and what remains to be done inside one session or workflow. It uses earlier answers instead of repeating questions. Relevant current-task context survives ordinary steps, but older history, a new session, a new channel, or a handoff is incomplete or lost.

Example: during one GST notice session, the product retains the trader's identity, the uploaded notice, the preferred Kannada explanation, the extracted deadline, and a corrected business name. The user can move from explanation to reply drafting without repeating anything. When the user returns the next day to ask whether the reply was sent, however, the product has no record of the case and starts a fresh upload flow.

### L4
It uses relevant history and carries context across sessions, channels, or handoffs.

The product combines the current task with useful prior history: previous tickets, documents, transactions, corrections, preferences, decisions, or unresolved actions. A handoff receives a concise, accurate state rather than the entire raw transcript, and the next component continues without making the user restart. Authentication and permissions remain intact.

Example: a customer begins a missing-order complaint on a voice call and continues on WhatsApp after the call drops. WhatsApp opens the same case, knows which order and items are disputed, carries forward the photograph already collected, replies in the customer's preferred language, and asks only for the one confirmation still needed before the refund can be reviewed.

### L5
It delivers governed business continuity across the whole product.

The product reliably combines three layers: the current task, the relevant history of this user or case, and the business rules that govern the next step. Context survives every demonstrated session, channel, tool, and handoff. Corrections propagate, stale information is distinguishable from current information, and access stays within the authenticated user's permissions and organisation boundaries.

Example: a lending assistant recognises a returning applicant, resumes the incomplete application at the correct step, and uses the latest income document instead of an older superseded upload. When the eligibility policy changes, it applies the current rule, records why the decision changed, and hands the reviewer a concise case summary rather than a raw transcript. A second applicant using the same device cannot see or retrieve any part of the first applicant's case.

---

## 3. Creativity

**The question:** How uniquely and non-obviously was the problem solved?

Creativity can come from the idea, the problem framing, the interaction mechanic, or the way the solution uses Sarvam. It is not visual polish, implementation difficulty, or the number of APIs connected. A team that chooses an idea from the library can still reach L5 by taking it somewhere nobody could predict from the card.

### L1
The build is the obvious first implementation.

It closely reproduces a reference agent, idea-card flow, tutorial, or generic wrapper. The problem statement is enough to predict the entire demo. Changing the logo, persona, language, or UI theme is not a creative contribution.

Example: a government-scheme bot asks for age, income, state, and occupation, then reads back a list of matching schemes. The team has changed the colours, added a friendly avatar, and translated the responses, but the product is still the exact form-and-results flow anyone would predict from the problem statement.

### L2
There is a twist, but it is cosmetic or loosely attached.

The team adds one variation beyond the obvious build, but it does not materially change how the problem is understood or solved. The novelty may create a demo moment without making the product more coherent or useful.

Example: a GST notice interpreter adds an animated avatar, celebratory transitions, and a choice of dramatic voice styles. Once those effects are removed, the product is still only “upload a notice and receive a summary”; the twist does not change what the trader understands, decides, or does next.

### L3
The solution contains one meaningful, non-obvious choice.

The team has taken a recognisable point of view. At least one mechanic, workflow choice, or use of the Sarvam stack changes how the user solves the problem, rather than decorating the expected solution. The rest of the product may still be conventional.

Example: the obvious contract product translates every clause into simpler language. This product instead lets a shop owner ask, “What can hurt me in this deal?” in their own language, connects each risky clause to the owner's payment terms and inventory exposure, and produces a short negotiation checklist they can use on the next supplier call. The core product changes from translation to decision support.

### L4
The solution is distinctive from end to end.

Several original choices reinforce one another across the problem framing, interaction, and product workflow. The use of Sarvam is purposeful rather than ornamental. Another competent team given the same problem would be unlikely to arrive at the same product.

Example: a factory operator does not stop work to search an English manual or type a clean fault description. The product listens to the machine noise and the operator's code-mixed explanation, identifies the likely fault, retrieves the exact manual section, and talks the operator through the repair one safe step at a time while their hands remain occupied. The input, diagnosis, and teaching interaction all reinforce the same point of view.

### L5
The solution reframes what people thought the product could be.

The idea produces a genuine “I did not know you could solve it that way” reaction, yet feels coherent and inevitable once demonstrated. Its originality is not a gimmick: the non-obvious approach unlocks a materially better possibility for the user. The team has created a memorable product category or interaction that cannot be inferred from the idea card alone.

Example: the expected compliance product translates a new RBI circular and summarises it. This product turns every changed rule into short, role-specific simulated customer conversations, lets frontline staff respond in their everyday language, identifies where their decisions violate the new rule, and gives the compliance head an evidence trail of exactly which teams and scenarios need retraining. The circular becomes an operating system for behaviour change rather than another document to read.

---

## 4. Impact

**The question:** If this product did not exist—or was taken away—whose outcome gets worse, by how much, and how often?

Impact scores the value of solving the problem, not whether this build currently works. A high-impact problem can have a weak prototype, and a flawless prototype can solve a low-impact problem. The team must name the beneficiary or payer, the current baseline, the frequency of the problem, and one metric that moves.

### L1
No credible impact case is articulated.

The team describes the technology or a broad social good but cannot name who experiences the problem, how often it occurs, what it costs today, or which outcome changes.

Example: the team says the product will “empower Bharat with AI” and shows a large number of regional-language users. It cannot say which user faces the problem, how many times that user faces it in a month, what they currently lose or spend, or whether success should change completion, cost, revenue, risk, access, or turnaround time.

### L2
The problem is real, but the value case is weak or unproven.

The team names a user and a metric, but the frequency, current cost, or path from the product to the outcome is mostly assumed. The likely movement is small, below 5%, or limited to a convenience metric that is not important to the beneficiary.

Example: a multilingual FAQ assistant answers a handful of internal questions for a ten-person team. The builders claim that it will save time, but they have not measured current question volume, the time spent per answer, or whether faster answers change support cost, resolution time, conversion, access, or risk. Even if the assistant works perfectly, the business outcome is likely to remain almost unchanged.

### L3
There is a clear case for meaningful value.

The team can defend who benefits, how often the problem occurs, what the current process costs, and a plausible 5% to below 10% movement on one meaningful metric. For public-service or everyday-life products, an equivalent movement in access, completion, turnaround time, error rate, or avoidable loss counts.

Example: a regional compliance team receives eight relevant circulars in an average month and currently spends about two working days interpreting each one for branch teams. The product could reduce that work to one day per circular. The team shows the current staff hours, the monthly volume, and the number of delayed branch updates, then connects the proposed reduction to a plausible 5–10% improvement in compliance turnaround time.

### L4
The product targets a major, measurable bottleneck.

The team shows a defensible path to 10 to 30% movement on an important operating, revenue, cost, risk, access, or service metric. The affected user or payer is explicit, the baseline is credible, and the value survives reasonable challenge to the assumptions.

Example: an MSME has ₹1.8 crore sitting in invoices that are more than 60 days overdue, and its finance team spends 90 hours a month chasing the same buyers. The product prioritises the accounts most likely to pay, conducts regional-language follow-ups, and escalates disputed invoices with the correct evidence. The team can show how a defensible reduction in days-sales-outstanding would release enough working capital to change inventory purchasing and payroll decisions even if adoption is lower than planned.

### L5
The product addresses a top-priority problem with transformational value.

The problem is tied to a critical metric or previously inaccessible outcome, with a credible path to more than 30% movement or an equivalent step-change in cost, revenue, risk, access, or service delivery. The team can show why this is a priority now, why the affected organisation or user would act, and what adoption at meaningful scale looks like.

Example: a lender processes hundreds of thousands of routine collection calls each month, while trained agents spend the same time on simple reminders, genuine hardship, and disputed debt. The product resolves routine cases in the borrower's language, detects hardship or disagreement, and routes only those cases to specialists with the complete context. The team shows the portfolio size, present call cost, resolution baseline, expected recovered value, and adoption path, making the case for a step-change rather than a generic “AI will reduce costs” claim.

---

## 5. Delight

**The question:** At the user's real point of friction, does the product create confidence, clarity, and forward movement?

### L1
The product mishandles the moment of friction.

The user becomes more confused, anxious, or stuck. The product may hide uncertainty, offer false reassurance before it knows the answer, expose raw system output, or end without a usable next step. The builder must explain what to do.

Example: while reading a photographed GST notice, the product repeatedly says “nothing to worry about” before it has classified the document. It later reveals a serious filing issue as a block of extracted fields and confidence scores, with no explanation, deadline, or next action. The reassurance was unearned and the user is now less certain than before.

### L2
The result is usable, but the care is generic.

The product completes the happy path and may add polite language, a friendly voice, animation, or “don't worry” copy. It does not respond to the user's actual concern, explain why the situation is or is not serious, or adapt the next step to the case.

Example: a GST notice assistant produces an accurate English summary and a generic “consult a professional” message. It does not identify the response deadline, distinguish a system mismatch from a genuine filing failure, or explain what the shop owner can verify now. The answer is functional, but the reassurance could have been attached to any notice.

### L3
The product removes the obvious friction.

A first-time user can complete the main flow without builder intervention. The product communicates status honestly, presents the result in the right form and language, and gives a concrete next action. It is context-aware on the common path, but its care stops at the immediate result or becomes generic when the case is uncertain.

Example: a notice interpreter highlights the disputed amount, response deadline, and one recommended next action in Kannada, then creates a reply the shop owner can send to their CA. The owner understands what happened without the builder speaking. When one photographed page is unreadable, however, the product says “processing failed” instead of identifying the page to retake or preserving the completed work.

### L4
The product handles the user's hardest moment with judgment.

The experience identifies the real point of anxiety or friction and responds with the correct emotional weight. It tells the truth without being alarming, reassures only where the evidence supports reassurance, explains what happens next, and recovers without discarding progress. The user feels that the product understands both the job and the situation.

Example: a shop owner uploads a genuine GST notice. The product does not pretend it is harmless. It calmly explains why the notice matters, shows the source lines and response window, distinguishes what is verified from what is uncertain, and gives three ordered options: verify the mismatch, prepare the missing records, or escalate to the CA. If one page is unreadable, it preserves the analysis, names that page, and explains exactly what to retake.

### L5
The product anticipates the pain point and stays with the user through resolution.

The product does everything L4 requires, then goes beyond the immediate interaction. It predicts the next concern, preserves continuity, makes follow-up effortless, and keeps the user informed until the difficult job has a controlled path forward. The support is specific to the user's situation—not a pile of extra features—and every demonstrated edge feels intentional.

Example: a bakery owner photographs a dense four-page GST notice received on WhatsApp. The product gives a concise Kannada explanation, shows why the amount may be valid, and turns the next steps into a case with the response deadline, required records, and a draft message to the CA. The owner can ask follow-up questions without repeating the notice, see whether each action is complete, and receives a reminder before the deadline. When she corrects one business detail, the explanation, case, and draft all update. She is not falsely cheered up or left in the cold; she knows what happened, what will happen next, and how to return if she is still unsure.

---

# Sarvam parameters

Voice, Document Intelligence, and Dubbing are alternatives—not three extra boxes every team needs to tick.

Build deeply on the capability most central to completing the user's job. Every team must demonstrate at least one Sarvam capability. Judges score the single capability most central to completing the user's job.

Additional capabilities do not add points. Get the central capability working deeply first. If the job genuinely requires a second capability, explain why to your mentor before spending time on it; judges may record it as a qualitative differentiator when comparing the top teams. If it is ornamental or force-fitted, ignore it. Depth on one capability beats breadth across several.

## Branch A. Voice Experience

**The question:** Does the voice feel human-grade and appropriate for the declared job?

### L1
The voice works, but the agent feels like a generic phone tree.

Speech-to-text breaks on anything outside neutral speech. Accents, hindi-english code-switching, and background noise produce garbled transcripts that the agent answers anyway. Intent detection is literal. It latches onto the first phrase it hears and misses the real ask. There is no emotional read. A calm caller and a panicked caller get the same flat reply. Turn-taking is broken. The agent talks over the user or freezes when interrupted, and a correction forces the conversation to restart from the top. Pacing stays at one speed regardless of the moment.

The agent works through a fixed question list with no logic between them. There are no real follow-ups, only the next item on the script. The voice itself sounds robotic, with no natural pauses or prosody. Word choice is thin: fillers, repetition, and stock phrases like "I understand your concern" used everywhere.

Example: a candidate joins a hiring call and says "haan, I worked at a B2B SaaS for two years, mostly retention work." The agent replies "could you tell me about your most recent role?" and reads the next three questions from a fixed list. It misses the hindi switch, misses the retention signal, and never follows up. In payments, the agent says "I understand your concern" without sounding urgent or specific to the stuck transaction.

### L2
The voice is usable, but still feels scripted and shallow.

The agent handles neutral speech on a happy path. Heavy accents, code-switching, or noisy lines trip the transcript. Intent detection works for direct asks but misses hedged or layered ones. There is no real emotional read. The agent says the right words for a complaint but does not sound like it senses one. Turn-taking is basic. The agent finishes its turn, the user finishes theirs, but interruptions throw it off and only clean corrections get recovered. Pacing barely shifts.

The agent asks obvious follow-ups instead of smart ones, repeats confirmation lines, and does not know when to be brief or when to slow down. The voice is understandable but flat. Word choice is generic, with stock phrases recycled across very different moments.

Example: in quick commerce, the agent answers "where is my order," but sounds the same whether the user is calm, angry, confused, or asking for a refund. In hiring, it captures candidate answers but asks the same three follow-ups regardless of seniority or role.

### L3
The voice feels functional and domain-aware, but not yet polished.

The agent handles most clean speech and some accent variation. Layered complaints, mixed-language sentences, or unclear speech still break it. Intent detection works for direct asks and obvious follow-ups. The agent picks up obvious emotion or urgency and changes its reply slightly based on the situation. Turn-taking is decent. It handles simple interruptions and recovers from clean corrections, but loses context if the user redirects mid-stream. Pacing modulates slightly between sections of the call.

The agent asks useful, role-specific or domain-specific follow-ups and clarifies missing information. The script seams show in pushback or emotional moments. Prosody is decent. Domain wording is in place. There are fewer fillers, but stock phrases still leak through under pressure.

Example: in hiring, the agent asks role-specific questions and follows up on one answer. In payments, it explains the next step clearly but still sounds slightly scripted when the user pushes back. In quick commerce, it handles a refund ask but stumbles when the user asks two questions at once.

### L4
The voice feels like a competent operator for the declared job.

The agent handles accents, most code-switching, and noisy phone lines without breaking the transcript. Intent detection catches the real ask under hedging or rambling. The emotional read is strong. The agent picks up frustration, urgency, hesitation, and mild anger, and adjusts its tone in the same call. Turn-taking is clean. It handles barge-in without losing context and recovers from corrections without restarting. Pacing varies for the moment: brisk for simple tasks, calm for complaints, careful for payments, sharper for interviews, direct during escalation.

Each follow-up builds on the last answer rather than running down a list. The agent knows when to be brief and when to slow down. The voice has natural pauses and controlled modulation. Word choice is tight. The agent does not over-talk.

Example: in payments, the agent slows down when explaining refund timelines and confirms the next step clearly. In hiring, it probes the candidate's answer like a real interviewer. In quick commerce, it gives fast answers without sounding cold and handles a user changing their mind mid-call without restarting the flow.

### L5
The voice feels human-grade for the declared job.

The agent holds up on real-world indian speech: accents, hindi-english code-switching, noisy phone lines, partial words, and self-corrections do not break the transcript. Intent detection catches the actual ask under hedging, rambling, or incomplete phrasing. The emotional read is sharp. The agent picks up frustration, urgency, hesitation, and confusion, and adapts mid-call without sounding theatrical. Turn-taking is clean and natural. It handles barge-in without losing context, knows when to stop talking, and recovers fluidly from corrections, mid-stream redirects, and "no wait, actually" moments. Pacing shifts deliberately: brisk for confirmations, slower for sensitive moments, real pauses where needed.

Each follow-up builds on the last answer instead of running down a list. The agent knows when to comfort, when to be firm, when to ask one more question, when to wrap, and when to escalate. The voice sounds present, with natural prosody and real modulation. Word choice is tight. No filler, no jargon dump, no repeated stock phrases. It does not sound like it is reading a script. It sounds like it knows the user, the job, and the business rule behind the answer.

Example: a candidate completes a first-round screen and feels like they spoke to a thoughtful interviewer. A payments caller asks about a failed ₹4,200 UPI payment from two days ago, fumbles for the UTR, and the agent offers to find it by amount and timestamp. The agent picks up rising frustration, softens, slows down, confirms the dispute reference in one clean line, and offers to send the case ID on whatsapp. The caller hangs up clear on what happened, what is being done, and when to expect resolution.

---

# Builder pro tips

| Parameter | Evidence that earns the level |
|---|---|
| Job-to-be-done completion | The correct, usable outcome is produced across repeated cases. |
| Memory and Context | Identity, task state, relevant history, permissions, and business rules survive where they should—and do not leak where they should not. |
| Creativity | The running solution contains a surprising, coherent, non-obvious angle. |
| Impact | A defensible baseline, beneficiary or payer, frequency, and material movement on one meaningful metric. |
| Delight | A first-time user completes a difficult flow with unusual ease and recovers without builder help. |
| Voice Experience | Real Indian speech, interruptions, emotion, pacing, and follow-ups hold up in a live conversation. |
| Document Intelligence | An unseen difficult document is represented with structure, source traceability, and controlled uncertainty. |
| Dubbing | Fluent reviewers accept unseen dubbed media as natural, performance-faithful, technically coherent, and publication-ready. |

