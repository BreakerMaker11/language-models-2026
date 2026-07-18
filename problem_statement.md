# Problem Statement

This project builds an LLM pipeline over 562 public submissions to Parliament's
Standing Committee on Health (HESA):

1. **Topic classification** of stakeholder briefs against a hand-labelled gold
   set, comparing keyword weak supervision, embedding classifiers, and
   prompted/fine-tuned LLMs.
2. **Retrieval-augmented question answering** over the corpus with source citations.
3. **Policy gap analysis** linking stakeholder asks to committee recommendations
   and government responses, demonstrated on the Canadian Medical Association's
   2025 priorities letter.

Tasks (1) and (2) are fully evaluated; (3) is demonstrated on a scoped example.