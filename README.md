# skill-ask-s3df

S3DF (SLAC Shared Data Facility) documentation assistant skill — a knowledge wrapper that answers questions about the SDF environment using a locally indexed copy of [slaclab/sdf-docs](https://github.com/slaclab/sdf-docs).

This repo is **externalized** — it is centrally deployed to S3DF by [deploy-opencode](https://github.com/carbonscott/deploy-opencode) via `./deploy.sh ask-s3df`. Do not edit the deployed copy directly; push here and re-deploy.

## Layout

```
.
├── README.md
├── claude/
│   └── skills/ask-s3df/      # Claude Code skill copy
│       ├── SKILL.md
│       ├── bin/              # docs-index helpers (search frontend)
│       ├── env.sh            # APP_DIR resolver + helpers
│       ├── env.local         # facility config (S3DF paths)
│       └── setup.sh
├── opencode/
│   └── skills/ask-s3df/      # opencode skill copy (byte-identical to claude/)
│       └── ...
└── tools/
    └── sdf-docs/             # cron-driven data refresh tool
        ├── env.sh
        └── scripts/
            └── sdf-docs-cron.sh
```

Both `claude/skills/ask-s3df/` and `opencode/skills/ask-s3df/` hold identical content; deploy-opencode rsyncs them into the corresponding agent-runtime locations on S3DF.

## Deploy targets

| Source in this repo | S3DF destination |
|---|---|
| `opencode/skills/ask-s3df/` | `/sdf/group/lcls/ds/dm/apps/dev/opencode/skills/ask-s3df/` |
| `tools/sdf-docs/` | `/sdf/group/lcls/ds/dm/apps/dev/tools/sdf-docs/` |

The `claude/` tree is for local Claude Code users (mirror of the opencode copy).

## Data dependency

The skill queries an FTS5-indexed SQLite catalog of the sdf-docs repo at:

```
/sdf/group/lcls/ds/dm/apps/dev/data/sdf-docs/
```

This data directory is git-cloned and re-indexed by the cron job below — the skill itself is read-only against the index.

## Cron schedule

**HOURLY refresh** — every hour at minute 0:

```
0 * * * * /sdf/group/lcls/ds/dm/apps/dev/tools/sdf-docs/scripts/sdf-docs-cron.sh run >> /sdf/group/lcls/ds/dm/apps/dev/data/sdf-docs/cron.log 2>&1
```

This is a **more aggressive refresh than the other cron-bearing skills** in the deploy-opencode fleet (which run weekly Sun 3am) — sdf-docs is a high-traffic upstream and we want the index fresh.

The cron script pulls `slaclab/sdf-docs` (branch `prod`), re-runs `docs-index` to rebuild the FTS5 SQLite, and fixes `ps-data` group permissions. Helpers (run on `sdfcron001`):

```
/sdf/group/lcls/ds/dm/apps/dev/tools/sdf-docs/scripts/sdf-docs-cron.sh enable    # install crontab entry
/sdf/group/lcls/ds/dm/apps/dev/tools/sdf-docs/scripts/sdf-docs-cron.sh disable   # remove
/sdf/group/lcls/ds/dm/apps/dev/tools/sdf-docs/scripts/sdf-docs-cron.sh status    # check
```

## License

Inherited from upstream skill content authored at SLAC.
