# Native one-tap intro

The README uses one GitHub-hosted video attachment as its header. Its first
frame is a 16-bit wall; Play breaks the wall and leaves the stable name/role
card in the same video rectangle. The rest of the README uses the original
responsive SVG panels and normal clickable project links. There are no
cover accordions or separate unlock banners.

GitHub adds its own filename header and video controls. The video contains
pixels, not live links. Native playback behavior in GitHub's mobile app is
controlled by that app; desktop inline playback is verified.

The video deliberately excludes changing stats and the “now building” field.
The regular refresh workflow continues updating activity and project panels
without re-uploading a video every six hours.

## Regenerate after an identity change

From this repository, install the Node dependencies and Pillow from
`scripts/requirements-render.txt`, and have Chrome plus ffmpeg available:

```sh
python3 scripts/build.py --cached --base-only
node scripts/render-video-header.mjs /tmp/jai-native-intro
python3 scripts/make-video-intro.py /tmp/jai-native-intro
```

The scripts preserve the visible dot-font end state and generate
`assets/jai.mp4` and `assets/intro-poster.png`.

Upload the MP4 to GitHub attachment storage (the same endpoint used by gh's
native `--attach` feature), scoped to this repository. Using gh's existing
authentication:

```sh
gh api --method POST \
  -H 'Content-Type: application/octet-stream' \
  -H 'Accept: application/vnd.github+json' \
  'https://uploads.github.com/user-attachments/assets?name=jai.mp4&content_type=video%2Fmp4&repository_id=626264001' \
  --input assets/jai.mp4
```

Put the returned permanent `url` in `assets/intro.json`, update its SHA-256,
then run `python3 scripts/build.py --cached`. GitHub embeds that bare URL as
its supported native video player. Ordinary external/raw MP4 URLs do not
produce the same README player.
