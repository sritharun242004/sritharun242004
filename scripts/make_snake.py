#!/usr/bin/env python3
"""Contribution snake GIF — clean 3–4 dot snake (classic look), high quality:
- FIXED 4-segment snake, dots drawn at cell size (separated, never merged)
- supersampled for crisp anti-aliased edges
- eaten green cells turn GREY at the same intensity (pattern stays visible)
- purple->blue dots. Reads contrib.json (GitHub GraphQL). Light theme."""
import json, sys
from PIL import Image, ImageDraw

CONTRIB = sys.argv[1] if len(sys.argv) > 1 else "contrib.json"
OUT = sys.argv[2] if len(sys.argv) > 2 else "snake.gif"

GREEN = {0:"#ebedf0",1:"#9be9a8",2:"#40c463",3:"#30a14e",4:"#216e39"}
GREY  = {0:"#ebedf0",1:"#c9ced4",2:"#aab0b8",3:"#848c96",4:"#5b636d"}
COL2LVL = {"#ebedf0":0,"#9be9a8":1,"#40c463":2,"#30a14e":3,"#216e39":4}
HEAD = (139, 92, 246)     # purple #8B5CF6
TAIL = (47, 129, 247)     # blue   #2F81F7

CELL, GAP, PAD, ROWS = 13, 3, 12, 7
PITCH = CELL + GAP
SS = 2                    # supersample for crisp quality
LEN = 4                   # fixed 4-dot snake
STEP = 2                  # advance 2 cells/frame (fewer frames -> smaller file)
FPS_MS = 90

def hx(h): return tuple(int(h[i:i+2], 16) for i in (1, 3, 5))
def lerp(a, b, t): return tuple(round(a[i]+(b[i]-a[i])*t) for i in range(3))

def load_grid():
    d = json.load(open(CONTRIB))
    weeks = d["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    cols = len(weeks)
    grid = [[0]*ROWS for _ in range(cols)]
    have = [[False]*ROWS for _ in range(cols)]
    mx = max((day["contributionCount"] for w in weeks for day in w["contributionDays"]), default=1) or 1
    for ci, w in enumerate(weeks):
        for day in w["contributionDays"]:
            r = day["weekday"]
            lvl = COL2LVL.get(day["color"].lower())
            if lvl is None:
                c = day["contributionCount"]
                lvl = 0 if c == 0 else min(4, 1 + int(3*c/mx))
            grid[ci][r] = lvl
            have[ci][r] = True
    return grid, have, cols

def serpentine(cols):
    path = []
    for c in range(cols):
        rows = range(ROWS) if c % 2 == 0 else range(ROWS-1, -1, -1)
        for r in rows:
            path.append((c, r))
    return path

def rrect(d, cx, ry, size, color, rad):
    d.rounded_rectangle([cx, ry, cx+size, ry+size], radius=rad, fill=color)

def main():
    grid, have, cols = load_grid()
    path = serpentine(cols)
    W = PAD*2 + cols*PITCH - GAP
    H = PAD*2 + ROWS*PITCH - GAP
    green = {k: hx(v) for k, v in GREEN.items()}
    grey = {k: hx(v) for k, v in GREY.items()}

    eaten = [[False]*ROWS for _ in range(cols)]
    frames = []
    for i in range(0, len(path), STEP):
        for k in range(max(0, i-STEP+1), i+1):     # mark eaten for skipped steps too
            cc0, rr0 = path[k]
            if grid[cc0][rr0] > 0:
                eaten[cc0][rr0] = True
        big = Image.new("RGB", (W*SS, H*SS), (255, 255, 255))
        d = ImageDraw.Draw(big)
        # grid cells
        for cc in range(cols):
            for rr in range(ROWS):
                if not have[cc][rr]:
                    continue
                lvl = grid[cc][rr]
                col = (grey[lvl] if eaten[cc][rr] else green[lvl]) if lvl > 0 else green[0]
                x = (PAD + cc*PITCH)*SS; y = (PAD + rr*PITCH)*SS
                rrect(d, x, y, CELL*SS, col, 3*SS)
        # snake: exactly LEN dots, drawn at cell size (separated, never merged)
        body = path[max(0, i-LEN+1): i+1]
        n = len(body)
        for k, (bc, br) in enumerate(body):
            t = k/(n-1) if n > 1 else 1.0
            col = lerp(TAIL, HEAD, t)     # tail blue -> head purple
            x = (PAD + bc*PITCH)*SS; y = (PAD + br*PITCH)*SS
            rrect(d, x, y, CELL*SS, col, 4*SS)
        small = big.resize((W, H), Image.LANCZOS)
        frames.append(small.quantize(colors=64, method=Image.MEDIANCUT))

    frames += [frames[-1]] * 12
    frames[0].save(OUT, save_all=True, append_images=frames[1:],
                   duration=FPS_MS, loop=0, disposal=2, optimize=True)
    import os
    print(f"wrote {OUT}  {W}x{H}  {len(frames)} frames  {os.path.getsize(OUT)//1024} KB")

if __name__ == "__main__":
    main()
