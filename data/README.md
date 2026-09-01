# Data

Only a small synthetic SQLite database is included for smoke testing and the
quick start. Benchmark datasets and generated vector indexes are excluded from
this repository.

## DAComp

Download the English DAComp tasks from Hugging Face:

```bash
python -m pip install -U "huggingface_hub>=0.25"
hf download DAComp/dacomp-da \
  --repo-type dataset \
  --local-dir data/benchmark/DAComp/dacomp-da
```

The expected layout is:

```text
data/benchmark/DAComp/dacomp-da/
  dacomp-da.jsonl
  dacomp-001/dacomp-001.sqlite
  ...
```

Review the dataset's current license and terms at its source before use or
redistribution.
