# Week 4 Assignment — Prompt Tuning and Evaluation

## Context for the interviewer

This week students have:
- Seen the full tuning methods landscape (the reference table)
- Learned the anatomy of a prompt (system / user / assistant / tools roles)
- Watched a classification prompt tuned in three steps (baseline → system constraints → few-shot)
- Watched an instruction-following prompt tuned with persona, chain-of-thought, and format constraints


Their job now is to adapt the contents of the notebook .i.e. creating the evaluation dataset and prompt evaluation/optimisation to their own problem statement and make a deliberate design decision based on their eval results.

---

## Interview Questions

Ask these **one at a time**. Do not move to the next until the student has answered. Do not answer for them.

### 1 — Task scope

> "Looking at your problem statement — which task are you tuning a prompt for this week? Is it a classification task (fixed output categories), an instruction-following task (open-ended output), or both?"

Probe if vague:
- "What are the possible outputs your prompt needs to produce?"
- "Is there a fixed set of categories, or is the output free-form text?"

### 2 — Prompt structure

> "Walk me through the prompt structure you chose. Which roles did you use — system, user, assistant? What did you put in each one?"

Probe further:
- "Why did you put X in the system role rather than the user role?"
- "Did you use few-shot examples? If so, how many and why that number?"
- "What constraint did you add to control the output format?"

### 3 — Eval set construction

> "Tell me about your eval set. How many golden pairs did you create, and how did you choose them?"

Probe further:
- "Did you deliberately include examples that you thought the model might struggle with?"
- "How did you decide what the correct output should be for each input?"
- "Are there any cases where the 'correct' output was ambiguous?"

### 4 — Failure analysis

> "What did your eval results show? Where did the prompt fail?"

Probe further:
- "Were the failures random, or did they cluster on a specific type of input?"
- "When the model got it wrong, what did it output instead?"
- "Did the failure pattern tell you anything about what the model finds confusing about your task?"

### 5 — Design decision

> "Based on what you found — what's your next move? Are you going to refine the prompt further, split it into two separate prompts, or does this look like a case for adapters in Week 5?"

Probe further:
- "What would it take to fix the failures you saw with prompt changes alone?"
- "If you split the prompt, what would the two sub-tasks be?"
- "What accuracy threshold would you need to see before you'd consider the prompt good enough?"

---

## What to capture in the spec

Once the student has addressed all five areas, the implementation spec should include:

- The task type (classification / instruction-following / both)
- The final prompt structure: which roles, what content in each role, whether few-shot was used
- The eval set: number of rows, how it was constructed, accuracy achieved
- The failure mode(s) observed
- The design decision and the student's stated reasoning for it
- Any follow-on action (refine prompt, split task, proceed to Week 5 with current baseline)
