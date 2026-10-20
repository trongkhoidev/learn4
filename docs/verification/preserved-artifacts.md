# Preserved local artifact manifest

Metadata only, captured on 2026-10-18. No database rows, media payloads, curl output, model cache
contents, `.env` values or credentials are included here. The Playwright app used a separate
temporary SQLite database and storage directory; backend tests use isolated fixtures.

| Local path | Baseline | Final check |
|---|---|---|
| `backend/lexilearn.db` | 323,584 bytes; SHA-256 `eef05fa65934788d911040032aa54b0b36c2deb4b6f01b6686b2c65b6f19a647` | Same size and SHA-256 |
| `backend/test.m4a` | 254,808 bytes; SHA-256 `114a8c3319e38c9777c01e4c586979d654975c32182d96ba6eac870e1b381170` | Same size and SHA-256 |
| `backend/test.webm` | 55,306 bytes; SHA-256 `200959cd9e7837a251443f83d18649c2208a0404fb804f6b2848dadec9708f8a` | Same size and SHA-256 |
| `backend/curl_out.txt` | 1,615 bytes; SHA-256 `0473849b69e805fb0db0504e4787d9724b9897e161bac4798d08415ed14e8a56` | Same size and SHA-256; contents were not opened |
| `backend/storage/speaking/` | 34 files; 2,060,453 total bytes; baseline catalog SHA-256 `7ca11d68de924edaf312e26757a2977f474a70301ce2ffde5c080470ad240577` | 34 files and 2,060,453 total bytes |

The baseline storage summary retained only a catalog digest, not its per-file entries or the
catalog-generation method. The final file count and total bytes match; exact per-object equality
for that directory cannot be established from the retained baseline metadata. No refactor or test
command was configured to write to the real storage directory.
