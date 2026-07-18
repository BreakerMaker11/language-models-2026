# Gold Labeling Codebook — v1.1 (matches gold_test.csv @ v0.3-gold-frozen)

v1.0 was used for initial labeling; v1.1 incorporates the pre-freeze
substance-use amendment and reflects the descoped stakeholder task.
This file is the verbatim source for config.yaml category descriptions and
all classification prompts. Never paraphrase or extend these definitions.

Unit: label the CARD (title + opening text) — the question is "what is this
card about?", because the card is exactly what every model sees.

## Topic definitions (single label — the document's PRIMARY subject)

- **public_health** — population-level health protection and preparedness:
  pandemics, COVID measures, vaccination programs, infectious disease,
  antimicrobial resistance, disease surveillance, health emergencies; and
  substance use as a population crisis — opioids, overdose, toxic drug
  supply, addiction, harm reduction, drug policy (amended v1.1).
- **pharmacare** — drugs and medical devices as products and programs:
  coverage, pricing, shortages, approval and safety, patented medicines,
  pharmaceutical supply, medical devices.
- **womens_health** — health of women and reproductive health: maternal
  care, breast and cervical cancer, menopause, endometriosis, contraception,
  midwifery.
- **mental_health** — mental illness and psychiatric care: mood and anxiety
  disorders, depression, psychiatric and psychological services, suicide
  prevention. Does NOT include substance use or addiction — those are
  public_health (amended v1.1).
- **workforce** — the people who deliver care: shortages, training,
  credential recognition, internationally trained professionals, retention,
  burnout, scope of practice, licensure.
- **indigenous_health** — health of First Nations, Inuit and Métis Peoples:
  access, self-determination, culturally safe care, Jordan's Principle, NIHB.
- **cancer** — cancer prevention, screening, treatment and care NOT specific
  to women's cancers: pediatric oncology, carcinogens, oncology services,
  general cancer care.
- **childrens_health** — health of children and youth: pediatric care,
  neonatal health, child development, child-specific services.
- **other_none** — real health-policy content that fits no topic above, or
  content that is not primarily about a health topic (e.g. civil-liberties
  arguments about mandates). Do NOT force-fit; this label is information.
  (Note: multi-topic cards are NOT other_none — they get the best-fit topic
  under Rule 5.)

## Tie-break rules (labeling protocol; Rule 2's precedence may be quoted in
## prompts, the rest are annotator protocol)

1. **Primary over mentioned** — label the thesis, not the vocabulary; harm
   and evidence sections do not outvote the ask.
2. **Specific over broad** — womens_health beats cancer for breast/cervical
   cancer; indigenous_health beats mental_health; childrens_health beats
   cancer for pediatric oncology.
3. **Occasion is not topic** — the study, bill, or event that prompted the
   brief does not determine its label; what the author argues about does.
4. **Ask over setting** — label what the author wants changed.
5. Torn after 1–4 → best fit, runner-up in notes. No blanks; no defaulting
   to other_none for compound cards.

## Stakeholder (metadata only — classification task descoped)

stakeholder_type in the manifest/corpus (physician_org, patient_advocacy,
industry, academic, government, individual, unknown) is retained for
filtering and analysis. It is not a modeled task and gold_stakeholder is
not evaluated.

## Second-pass protocol (day-13 kappa)

Relabel second_pass_sheet.csv against THIS version (v1.1), same rules, no
peeking at first-pass answers. Expect and report that first-pass labels for
substance-use cards predate the amendment where applicable. Kappa is
reported only; gold_test.csv is never modified from the second pass.
