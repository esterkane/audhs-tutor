# Optional low-frequency view

Use the installed WaveSurfer spectrogram plugin on demand, reusing its existing 4 kHz decoded overview. Explicitly show only 0–2,000 Hz with time/frequency axes and fixed grayscale strength explanation. No full-spectrum, instrument identification or calibrated loudness claims. Optional pattern comparison, no assessment/mastery.
Restrict to overview-supported files <=20 MiB and <=120 seconds; lazy plugin/worker processing, no automatic start or autoplay, and failure preserves playback/waveform. Unmount destroys plugin; late import cannot mount after closure. Text explains axes/patterns, static canvas respects reduced motion.
No new dependency/API/model/data persistence. Verify ready/failure/cleanup and browser rendering, plus labeled limitations.

Verification: 90 frontend tests pass; final 4 focused lifecycle/label tests pass; Chromium renders a synthetic two-tone signal with visually verified frequency-band shift, then completes prior transport/loop checks. make lint and production build pass. Fixed scientific wording and grayscale direction (igray), plus file replacement identity. Code review no blocker/major; pedagogy re-review ship. Dedicated browser-test Vite cache and explicit lazy dependency prebundling address recurrent React identity conflicts. Library emits benign worker_threads capability-probe warning; browser rendering succeeds.
