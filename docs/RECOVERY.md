# Recovery guide (P5)

**What a backup is.** One zip made by `make backup out=<file>`: a consistent SQLite snapshot, a manifest with checksums, and (optionally) the transcript cache. It is **not encrypted** — keep it on an encrypted disk. Never in a backup: `.env` and every secret, model binaries, Qdrant vectors, course originals. Default scope `learner` leaves the corpus text of purchased courses out; `scope=full` is for your own private reinstall only.

**Make one.**
```bash
make backup out=~/Backups/audhs-tutor-$(date +%F).zip            # learner scope
make backup out=~/Backups/audhs-tutor-full-$(date +%F).zip scope=full transcripts=1
make backup-inspect f=~/Backups/audhs-tutor-2026-09-20.zip        # verify checksums, print the manifest
```
`make backup` reads the live database read-only (SQLite online backup) and never overwrites an existing file.

**Bring one back (new machine or empty folder).**
1. Clone the repo, `scripts/bootstrap.sh`, do **not** start the app yet.
2. `make backup-restore f=<file> target=<empty folder>` — refuses a non-empty target, a corrupted or unknown archive, and never touches `data/dev.db`. Migrations run inside the restored copy.
3. Read `<target>/RESTORE-NOTES.md`. Either move `<target>/data` to the repo's `data/` (app stopped) or set `DATABASE_URL`/`TRANSCRIPT_CACHE_DIR` in `.env` to the restored paths.
4. Recreate secrets by hand in `.env`. Pull models again (`make models args=list`, then `scripts/models.py pull <id>`); routing assignments are learner preferences and came back with the data.
5. Start Qdrant (`make qdrant`) and rebuild vectors: `uv run --project backend python scripts/reindex.py --embedding-version <N>` (`N` is listed under `index.collections` in `backup-manifest.json`).
6. Learner scope only: re-ingest the courses listed under `sources.documents` (`make ingest src=<folder>`). Ingest is idempotent by content hash; lessons citing old passages show "no longer in the corpus" until re-published.

**Portability vs recovery.** `scripts/export.py --learner <id>` / `scripts/wipe.py` move or delete one learner's rows as JSON (unchanged); they do not restore an installation.
