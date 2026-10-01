# Ingest Progress

Implementation details are documented by the source code and regression tests. Private execution history is retained locally.

## Local audio decoder readiness
On macOS, install `ffmpeg` with `brew install ffmpeg` when the native decoder cannot read an audio format. Decoder availability is checked when a media file is processed; subsequent files can use FFmpeg once installed. Previously failed files still need a retry. An archive video may contain no audio track: inspect it with `ffprobe -v error -show_entries stream=codec_type,codec_name -of json <file>` before treating it as missing lecture speech. Installing a decoder cannot create a transcript for silent footage. Resuming an interrupted run retains completed items; parser errors need a separate reviewed retry.
