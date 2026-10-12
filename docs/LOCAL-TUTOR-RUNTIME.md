# Optional local tutor runtime

The default app configuration is unchanged. This experimental launcher creates a
separate loopback Ollama server using your installed models. It does not download
models, generate answers, edit `.env`, or stop your existing server.

Validate first:

```sh
python3 scripts/local_tutor_runtime.py --full-cache --check
```

Run in a terminal:

```sh
python3 scripts/local_tutor_runtime.py --full-cache
```

The server listens on `127.0.0.1:11435`; choose another unused port with `--port`.
Ctrl-C or SIGTERM stops the launcher and its owned server. Nothing starts on login.
Port 11434 is deliberately rejected. `--ollama PATH` selects an installed executable;
full-cache mode requires its sibling llama-server to advertise `--swa-full`.

To deliberately test this server with the app, start your development stack from a
shell with `OLLAMA_HOST=http://127.0.0.1:11435 make dev` **after stopping any existing
stack using the same app ports**. An already running backend will not switch hosts.
Keep the runtime terminal open. For rollback, stop that development stack and the
optional runtime, then launch normally without the environment override. No permanent
configuration is changed by these commands. Starting without `--full-cache` provides
a standard-cache comparison on the separate port.

## Cost and limits

On the tested Gemma3 12B model with 32768 context, full SWA allocated 12 GiB of KV cache,
roughly 11 GiB more than the normal configuration. This is cache alone, excluding model
weights and other apps. Watch macOS Activity Monitor's memory pressure. Running both
servers with the same large model can add pressure; do not assume 48 GB makes every
combination safe. Two resident models are allowed so a small embedding model can
coexist with the tutor; this is not an invitation to preload two large chat models.
Cloud use is disabled and requests are serial per model. The default app's model
choices, learning context and answer budgets remain unchanged.

A single changed-question comparison reduced first text from 9.78 s to 4.28 s and total
from 16.71 s to 11.24 s. This is promising evidence, not a general guarantee. Both answers
still hit the existing 190-token cap. Cold model loading remains. Broader real-Session,
source-heavy, concurrent retrieval and teaching-quality validation are outstanding.
The option is **not promoted to the default runtime**.

See [measurement details](slices/session-latency-observability.md). The installed
runner's help and runtime log were checked; other Ollama versions may behave differently.
