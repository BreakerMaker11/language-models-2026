# Notebook Image Catalogue

All 35 images are embedded inline as base64 PNGs. Extracted copies are in `notebook_images/` for reference.

## ⚠ Missing Images

Two cells reference a diagram that is not present:

| Notebook | Cell ID | Text referencing the missing image |
|---|---|---|
| `week1_introducton_to_llms.ipynb` | `b1bf5add` | "In the diagram below you can see a visual representation of what happens under the hood when we inference over *gemma2:2b*..." |
| `week7_multimodal_models.ipynb` | `outro-audio` | "The diagram below shows the full path from raw audio to transformer input, the two main approaches to audio encoding..." |

---

## Week 1 — Introduction to LLMs (3 images)

| File | Description |
|---|---|
| `week1_introducton_to_llms__0a5c0a52__md_1.png` | Diagram showing how LLMs generate text one token at a time, with logits and probability distributions for candidate next tokens |
| `week1_introducton_to_llms__20a9ef2d__md_2.png` | Technology stack diagram showing application layers from recipe classifier UI down through Ollama to the Gemma2:2b model weights |
| `week1_introducton_to_llms__emaflzu3vlh__md_3.png` | Flow chart of three training phases: pre-training on raw text, instruction fine-tuning on curated conversations, and RLHF with human preference rankings |

---

## Week 2 — Tokenization and Embeddings (3 images)

| File | Description |
|---|---|
| `week2_tokenization_and_embedding__image-tokenization-pipeline__md_1.png` | Five-phase pipeline: raw text → BPE tokenization → token IDs → embedding layer → transformer layers → token prediction |
| `week2_tokenization_and_embedding__image-cosine-similarity__md_2.png` | 2D embedding space showing cooking-related terms clustered by semantic similarity, with cosine similarity formula |
| `week2_tokenization_and_embedding__image-bpe-merges__md_3.png` | BPE algorithm diagram showing character-level merging steps that build vocabulary from frequent character pairs |

---

## Week 3 — Transformer Architecture (6 images)

| File | Description |
|---|---|
| `week3_transformer_architecture__a653ecf4__md_1.png` | Training (weights updated, causal masking) vs inference (weights frozen, sequential generation) phase comparison |
| `week3_transformer_architecture__8af7b454__md_2.png` | Causal masking: BERT-style bidirectional attention vs Gemma's autoregressive masking where each token only sees its past |
| `week3_transformer_architecture__3ce061c8__md_3.png` | Standard Multi-Head Attention (8 independent KV heads) vs Grouped Query Attention in Gemma 2 (4 KV heads shared across queries) |
| `week3_transformer_architecture__b52c4bb8__md_4.png` | Embedding pipeline: skip duplicates → prepare rows → batch loop → embed with Gemma → store in ChromaDB |
| `week3_transformer_architecture__d6b4e2f8__md_5.png` | Query pipeline with embedding and retrieval stages, showing raw embeddings and intelligent filtering flow |
| `week3_transformer_architecture__39ef3856__md_6.png` | Extended context window strategies: RoPE scaling, sliding window attention, flash attention, and very long context models |

---

## Week 4 — Prompt Engineering and Evaluation (2 images)

| File | Description |
|---|---|
| `week4_prompt_tuning_and_evaluation__507d17bf__md_1.png` | Prompt design framework showing how system message (persona, format, instructions), user query, and assistant response fit in the context window |
| `week4_prompt_tuning_and_evaluation__0fb05ce1__md_2.png` | Decision tree for choosing prompt strategy: fixed system prompt, user prompt, or RAG based on whether context is static or dynamic |

---

## Week 5 — Fine-tuning with Adapters (2 images)

| File | Description |
|---|---|
| `week5_fine_tuning_with_adapters__6b490d60__md_1.png` | LoRA adapter architecture: frozen base layer with trainable low-rank A and B matrices added via residual connection |
| `week5_fine_tuning_with_adapters__700faedd__md_2.png` | Five-step adapter fine-tuning workflow: define problem → generate labels → validate quality → train with SFTTrainer/LoRA → evaluate before/after |

---

## Week 6 — Semantic Search and RAG (9 images)

| File | Description |
|---|---|
| `week6_semantic_search_and_rag__968faf53__md_1.png` | Dual retrieval: dense retrieval vs sparse retrieval results merged with RRF ranking |
| `week6_semantic_search_and_rag__d8bba000__md_2.png` | Two-pass retrieval: bi-encoder for fast top-20 candidate selection, then cross-encoder re-ranker for accurate top-3 final results |
| `week6_semantic_search_and_rag__035697dc__md_3.png` | Simple RAG pipeline: query embedding → vector store cosine similarity search → top-k chunk retrieval with optional re-ranking |
| `week6_semantic_search_and_rag__221f9888__md_4.png` | Hybrid retrieval combining dense and sparse methods through a query router with optional fallback to web search |
| `week6_semantic_search_and_rag__774fb32b__md_5.png` | Multi-layer personalization: user history → inferred skill profile + recipe/technique retrieval → personalized prompt |
| `week6_semantic_search_and_rag__150fe952__md_6.png` | Evaluation comparing static skill labeling directly via LLM vs dynamic approach using user history and inferred profiles |
| `week6_semantic_search_and_rag__1dab1c27__md_7.png` | Evaluation metrics summary across cooking context layers: clean cuts, split test, semantic boundary, adaptive feedback |
| `week6_semantic_search_and_rag__cb231979__md_8.png` | Semantic search demonstration with recipe cards showing split-level semantic chunking |
| `week6_semantic_search_and_rag__aa9d05f5__md_9.png` | Advanced retrieval pipeline: query router → multiple retrievers → relevance evaluator → fallback to web search |

---

## Week 7 — Multimodal Models (6 images)

| File | Description |
|---|---|
| `week7_multimodal_models__5d43307d__md_1.png` | Vision preprocessing pipeline: image split into 14×14 patches → ViT-style encoder → projection to text embedding dimension |
| `week7_multimodal_models__1fd74c21__md_2.png` | Two fusion approaches: early fusion (Gemma 4 prepends image tokens before text) vs cross-attention fusion (image representation injected across layers) |
| `week7_multimodal_models__cell1-extract__output_3.png` | Photograph of a cookbook page showing a Taco Bake recipe (used as example input in the multimodal demo) |
| `week7_multimodal_models__1902064f__md_4.png` | Vision-language pipeline: Gemma 4 vision model → JSON output → Pydantic validation → quality checks → full classification pipeline |
| `week7_multimodal_models__60bd696e__md_5.png` | Audio processing pipeline: waveform → STFT → log-mel spectrogram → CNN embeddings → transformer encoder |
| `week7_multimodal_models__fecef8cb__md_6.png` | Spectrogram-based (Whisper, SpeechT5) vs raw waveform (Wav2Vec2, HuBERT) audio input approach comparison |

---

## Week 8 — Evaluation and Beyond (4 images)

| File | Description |
|---|---|
| `week8_evaluation_and_beyond__d304c814__md_1.png` | Course timeline across 8 weeks: prompt design → embeddings → retrieval → optimization → fine-tuning → dynamic context → multimodal |
| `week8_evaluation_and_beyond__75ea32f4__md_2.png` | Four evaluation dimensions: task completion, trajectory quality (retries, retrieval relevance), output quality, robustness under stress |
| `week8_evaluation_and_beyond__b86de8af__md_3.png` | Deterministic pipeline (fixed-order extraction/classification) vs ReAct agent pattern (reasoning loop with tool use and memory) |
| `week8_evaluation_and_beyond__f3341540__md_4.png` | Visual trace of a recipe classification pipeline showing step execution times, token counts, and failure points |
