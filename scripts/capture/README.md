The cover uses the material-refined `scripts/vendor/opus-jelly/jelly.js` renderer
derived from the original Claude/Opus browser implementation. See
`../vendor/opus-jelly/SOURCE.md` for the material changes.

To regenerate the transparent recordings:

1. Run `python3 scripts/capture/serve.py /tmp/jai-opus-frames`.
2. Open http://127.0.0.1:5190/scripts/capture/jelly.html in a WebGL2 browser.
3. Call `recordJelly({name, w, h, dpr})` for these geometries:
   header 480×360; d-header 960×268; activity 480×262;
   d-activity 960×188; tile 200×200 (dpr 2); d-tile 400×150 (dpr 2);
   stack 480×64; d-stack 960×64. The default dpr is 1.5.
4. With Pillow 11.3.0 installed, run
   `python scripts/capture/encode.py /tmp/jai-opus-frames`.
5. Build the existing SVG panels with `python3 scripts/build.py --base-only`.
6. Rasterize those panels at 2× using `base.js` in the shared preview browser,
   or `node scripts/capture/base-ci.mjs /tmp/jai-profile-bases` in CI.
7. Run `python scripts/jelly_cover.py /tmp/jai-profile-bases` to composite
   the original jelly over the current panels as native animated WebP files.
8. Run `python3 scripts/build.py --cached` to update the README.

The capture adapter supplies scripted gestures, runs the original simulation
at 60 Hz and records at 12 fps. It changes no material physics or shader code.
The RGBA recording contains only the jelly. Each stats refresh composites it
over newly generated profile content; stale stats are never baked into the source
recording. Native WebP is used because SVG image contexts freeze nested raster
animations. Reduced-motion readers see the original
panels without the added cover animation.
