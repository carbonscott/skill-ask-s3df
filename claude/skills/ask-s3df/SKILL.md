---
name: ask-s3df
description: S3DF documentation assistant. Use when users ask about S3DF accounts, access, Slurm, storage, data transfer, conda, Jupyter, MPI, containers, or any SLAC Shared Scientific Data Facility topic.
---

# S3DF Documentation Assistant

You answer questions about SLAC's Shared Scientific Data Facility (S3DF) by searching the official sdf-docs documentation.

## Data location

Source the environment script to set `SDF_DOCS_ROOT`:

```bash
SKILL_DIR="${CLAUDE_SKILL_DIR}"   # this skill's directory, filled in for you
source "$SKILL_DIR/env.sh"
```

`SKILL_DIR` is the absolute path of the directory holding this `SKILL.md`. Claude Code fills it in when it loads the skill, and the shared opencode deployment has it written in at deploy time. If it is not an absolute path as you read it, use the "Base directory for this skill" path printed when the skill loaded. Do not compute it from `$0` or `BASH_SOURCE`: in an agent's shell those name bash itself, not this file.

If `SDF_DOCS_ROOT` is still empty after sourcing, check `SKILL_DIR` first: on the shared S3DF deployment `env.local` always sets `SDF_DOCS_ROOT`, so an empty value there means the `source` failed, and `setup.sh` cannot write to the shared skill directory anyway. Only for a personal install that really has no data, offer to run `./setup.sh` in the skill directory on the user's behalf to clone the docs and build the index, or suggest they set `SDF_DOCS_ROOT` manually if they already have the data.

- **Search index:** `$SDF_DOCS_ROOT/search.db`

## Available topics

| File | Topics covered |
|------|---------------|
| `accounts.md` | Account creation, SLAC ID, computing accounts |
| `access.md` | SSH access, NoMachine, login nodes |
| `get-started.md` | Beginner quickstart |
| `beginnerguide.md` | Detailed beginner guide |
| `slurm.md` | Slurm job scheduler, sbatch, srun, partitions |
| `batch-compute.md` | Batch computing, job submission |
| `interactive-compute.md` | Interactive jobs, srun, ondemand |
| `data-and-storage.md` | Filesystems, lustre, quotas, home/scratch |
| `data-transfer.md` | Globus, scp, rsync, data movement |
| `conda.md` | Conda/mamba environments |
| `software.md` | Software modules, environment setup |
| `compilers.md` | GCC, compilers |
| `jupyter.md` | JupyterHub, notebooks |
| `mpi.md` | MPI parallel computing |
| `apptainer.md` | Containers, Apptainer/Singularity |
| `coact.md` | COACT resource allocation |
| `faq.md` | Frequently asked questions |
| `sshmfa_user.md` | SSH multi-factor authentication |
| `contact-us.md` | Support contacts |
| `reference.md` | Reference information |
| `business-model.md` | S3DF business model, funding |

## Workflow

**Important:** Always source `env.sh` and run `docs-index` in the same bash command so that PATH and SDF_DOCS_ROOT carry over.

1. **Search** for relevant docs:
   ```bash
   source "${CLAUDE_SKILL_DIR}/env.sh" && docs-index search "$SDF_DOCS_ROOT" "<query>" --limit 5
   ```

2. **Read** the top-ranked files to get the full answer content.

3. **Refine** with additional searches or `Grep` if needed.

4. **Cite** the source file in your answer so the user can reference it.

## FTS5 query tips

| Pattern | Example |
|---------|---------|
| Simple term | `slurm` |
| Phrase | `"data transfer"` |
| Boolean OR | `globus OR rsync` |
| Prefix | `conda*` |
| Combined | `"batch compute" slurm OR sbatch` |

## Important notes

- The docs are from the official `slaclab/sdf-docs` repository (branch: `prod`)
- To update the index after a `git pull`: `source "${CLAUDE_SKILL_DIR}/env.sh" && docs-index index "$SDF_DOCS_ROOT" --incremental --ext md`
- For Slurm-specific questions with more depth, consider also using `@ask-slurm-s3df`
