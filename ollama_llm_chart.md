# AMBER — Ollama Model Inventory
> Generated: 2026-07-10 · 46 models pulled (42 inference · 4 embedding)

## Legend
- **CTX** — native context window (tokens)
- **Params** — total parameter count
- **Embed Dim** — hidden embedding dimension
- **Disk** — size on disk from `ollama list`
- **Capabilities** — `completion` · `tools` · `thinking` · `vision` · `embedding` · `insert`
- **Arch** — GGUF architecture tag

---

## Inference Models

| Model                                                          | Arch          | Params | CTX (tokens)   | Embed Dim | Disk   | Capabilities                                    | Pulled       |
| -------------------------------------------------------------- | ------------- | -----: | -------------: | --------: | -----: | ----------------------------------------------- | ------------ |
| `osint-tuned-v3:latest`                                        | llama         |   7.2B |   32 768 (32K) |     4 096 | 4.4 GB | completion                                      | 10 days ago  |
| `osint-tuned:latest`                                           | llama         |   7.2B |   32 768 (32K) |     4 096 | 5.1 GB | completion                                      | 12 days ago  |
| `mistral:7b-instruct-v0.3-q5_K_M`                              | llama         |   7.2B |   32 768 (32K) |     4 096 | 5.1 GB | completion · tools                              | 13 days ago  |
| `finetuneforge-netsec-analysis:latest`                         | qwen2         |   3.1B |   32 768 (32K) |     2 048 | 6.2 GB | completion · tools                              | 13 days ago  |
| `finetuneforge-psychological-analysis:latest`                  | qwen2         |   3.1B |   32 768 (32K) |     2 048 | 6.2 GB | completion · tools                              | 13 days ago  |
| `finetuneforge-breach-analysis:latest`                         | qwen2         |   3.1B |   32 768 (32K) |     2 048 | 6.2 GB | completion · tools                              | 13 days ago  |
| `finetuneforge-osint-investigation:latest`                     | qwen2         |   3.1B |   32 768 (32K) |     2 048 | 6.2 GB | completion · tools                              | 13 days ago  |
| `finetuneforge-criminal-behavior-analysis:latest`              | qwen2         |   3.1B |   32 768 (32K) |     2 048 | 6.2 GB | completion · tools                              | 2 weeks ago  |
| `huihui_ai/dolphin3-abliterated:8b`                            | llama         |   8.0B | 131 072 (128K) |     4 096 | 4.9 GB | completion · tools                              | 3 weeks ago  |
| `qwen3:8b`                                                     | qwen3         |   8.2B |   40 960 (40K) |     4 096 | 5.2 GB | completion · tools · thinking                   | 3 weeks ago  |
| `fredrezones55/Gemma-4-Uncensored-HauhauCS-Aggressive:e2b-SCN` | gemma4        |   4.8B | 131 072 (128K) |     1 536 | 3.8 GB | completion · tools · thinking · vision          | 8 weeks ago  |
| `hermes3:3b`                                                   | llama         |   3.2B | 131 072 (128K) |     3 072 | 2.0 GB | completion · tools                              | 2 months ago |
| `qwen2.5:3b`                                                   | qwen2         |   3.1B |   32 768 (32K) |     2 048 | 1.9 GB | completion · tools                              | 2 months ago |
| `qwen-coder-optimized:latest`                                  | qwen35        |   9.7B | 262 144 (256K) |     4 096 | 6.6 GB | completion · tools · thinking · vision · insert | 2 months ago |
| `llama3.1:latest`                                              | llama         |   8.0B | 131 072 (128K) |     4 096 | 4.9 GB | completion · tools                              | 2 months ago |
| `qwen2.5-coder:7b`                                             | qwen2         |   7.6B |   32 768 (32K) |     3 584 | 4.7 GB | completion · tools · insert                     | 2 months ago |
| `huihui_ai/qwen3.5-abliterated:9b`                             | qwen35        |   9.7B | 262 144 (256K) |     4 096 | 6.6 GB | completion · tools · thinking · vision          | 3 months ago |
| `mistral-16k-tuned:latest`                                     | llama         |   7.2B |   32 768 (32K) |     4 096 | 4.4 GB | completion · tools                              | 3 months ago |
| `qwen-investigator2-tuned:latest`                              | qwen35        |   9.7B | 262 144 (256K) |     4 096 | 6.6 GB | completion · tools · thinking · vision          | 3 months ago |
| `qwen35-9b-hauhau:latest`                                      | qwen35        |   9.0B | 262 144 (256K) |     4 096 | 5.6 GB | completion · tools · thinking                   | 3 months ago |
| `deephermes3-joe:latest`                                       | llama         |   8.0B | 131 072 (128K) |     4 096 | 4.9 GB | completion                                      | 3 months ago |
| `huihui_ai/deephermes3-abliterated:latest`                     | llama         |   8.0B | 131 072 (128K) |     4 096 | 4.9 GB | completion                                      | 3 months ago |
| `josie-tuned:latest`                                           | qwen2         |   7.6B |   32 768 (32K) |     3 584 | 4.7 GB | completion · tools                              | 3 months ago |
| `goekdenizguelmez/JOSIEFIED-Qwen2.5:latest`                    | qwen2         |   7.6B |   32 768 (32K) |     3 584 | 4.7 GB | completion · tools                              | 3 months ago |
| `qwen2.5-coder-16k:latest`                                     | qwen2         |   7.6B |   32 768 (32K) |     3 584 | 4.7 GB | completion · tools · insert                     | 3 months ago |
| `qwen3-14b-16k:latest`                                         | qwen3         |  14.8B |   40 960 (40K) |     5 120 | 9.0 GB | completion · tools · thinking                   | 3 months ago |
| `qwen2.5-7b-16k:latest`                                        | qwen2         |   7.6B |   32 768 (32K) |     3 584 | 4.7 GB | completion · tools                              | 3 months ago |
| `richardyoung/qwen3-14b-abliterated-mlm:latest`                | qwen3         |  14.8B |   40 960 (40K) |     5 120 | 9.0 GB | completion · tools · thinking                   | 4 months ago |
| `svjack/Qwen3-8B-heretic:latest`                               | qwen3         |   8.2B |   40 960 (40K) |     4 096 | 5.0 GB | completion · tools · thinking                   | 4 months ago |
| `richardyoung/qwen3-14b-abliterated:latest`                    | qwen3         |  14.8B |   40 960 (40K) |     5 120 | 9.0 GB | completion · tools · thinking                   | 4 months ago |
| `huihui_ai/orchestrator-abliterated:8b-Q4_K_M`                 | qwen3         |   8.2B |   40 960 (40K) |     4 096 | 5.0 GB | completion · tools · thinking                   | 4 months ago |
| `huihui_ai/lfm2.5-abliterated:1.2b-instruct-q8_0`              | lfm2          |   1.2B | 128 000 (128K) |     2 048 | 1.2 GB | completion · tools                              | 4 months ago |
| `huihui_ai/qwen3-abliterated:8b`                               | qwen3         |   8.2B |   40 960 (40K) |     4 096 | 5.0 GB | completion · tools · thinking                   | 4 months ago |
| `dagbs/qwen2.5-coder-1.5b-instruct-abliterated:f`              | qwen2         |   1.8B |   32 768 (32K) |     1 536 | 3.6 GB | completion · tools · insert                     | 4 months ago |
| `dagbs/qwen2.5-coder-1.5b-instruct-abliterated:latest`         | qwen2         |   1.8B |   32 768 (32K) |     1 536 | 1.1 GB | completion · tools · insert                     | 5 months ago |
| `deepseek-r1:7b`                                               | qwen2         |   7.6B | 131 072 (128K) |     3 584 | 4.7 GB | completion · tools · thinking                   | 5 months ago |
| `phi3.5:latest`                                                | phi3          |   3.8B | 131 072 (128K) |     3 072 | 2.2 GB | completion                                      | 5 months ago |
| `qwen2.5:7b-instruct`                                          | qwen2         |   7.6B |   32 768 (32K) |     3 584 | 4.7 GB | completion · tools                              | 5 months ago |
| `huihui_ai/qwen3-vl-abliterated:8b`                            | qwen3vl       |   8.8B | 262 144 (256K) |     4 096 | 6.1 GB | completion · tools · thinking · vision          | 5 months ago |
| `huihui_ai/qwen3-vl-abliterated:4b`                            | qwen3vl       |   4.4B | 262 144 (256K) |     2 560 | 3.3 GB | completion · tools · thinking · vision          | 5 months ago |
| `huihui_ai/hy-mt1.5-abliterated:7b`                            | hunyuan-dense |   7.5B | 262 144 (256K) |     4 096 | 4.6 GB | completion                                      | 5 months ago |

---

## Embedding Models

| Model                      | Arch       | Params | CTX (tokens) | Embed Dim | Disk   | Capabilities | Pulled       |
| -------------------------- | ---------- | -----: | -----------: | --------: | -----: | ------------ | ------------ |
| `bge-m3:latest`            | bert       |   567M |   8 192 (8K) |     1 024 | 1.2 GB | embedding    | 3 weeks ago  |
| `embeddinggemma:latest`    | gemma3     |   308M |   2 048 (2K) |       768 | 621 MB | embedding    | 4 months ago |
| `mxbai-embed-large:latest` | bert       |   334M |   512 (0.5K) |     1 024 | 669 MB | embedding    | 4 months ago |
| `nomic-embed-text:latest`  | nomic-bert |   137M |   2 048 (2K) |       768 | 274 MB | embedding    | 5 months ago |

---

## Notes

- **AMBER ICI uses `embeddinggemma:latest`** for all vector/fractal indexing — hardcoded in the launcher.
- `bge-m3` has an 8K context window and 1024-dim output — the strongest embedder on disk by capacity, but not yet wired into AMBER. Worth evaluating as a swap-in for `embeddinggemma` on long-document indexing.
- `mxbai-embed-large` has a hard 512-token BERT limit; inputs are silently truncated. Not used by AMBER.
- The five `finetuneforge-*` models (netsec, psychological, breach, osint-investigation, criminal-behavior) are all F16 3.1B qwen2 fine-tunes of the same base — same CTX/embed dim, differ only in domain-tuning data.
- `osint-tuned-v3`, `osint-tuned`, and `mistral:7b-instruct-v0.3-q5_K_M` share the same llama 7.2B base architecture.
- `josie-tuned` and `goekdenizguelmez/JOSIEFIED-Qwen2.5` are both fine-tunes of the same Qwen2.5-7B base.
- The `richardyoung/qwen3-14b-abliterated*` and `qwen3-14b-16k` models share the same 14.8B qwen3 base.
- Models with **thinking** capability support extended chain-of-thought (`/think` toggle in AMBER ICI).
- Models with **vision** capability can accept image inputs.
- The ICI CTX selector (2K / 4K / 8K / 16K / 32K) caps what is *sent* to Ollama — independent of native model CTX.
