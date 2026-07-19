#!/usr/bin/env python3
"""Custom contribution snake GIF:
- snake GROWS each time it eats a contribution cell (capped)
- eaten green cells turn GREY at the SAME intensity (pattern stays visible)
- thicker / more visible snake
Reads contrib.json (GitHub GraphQL contributionCalendar). Light theme."""
import json, sys
from PIL import Image, ImageDraw

CONTRIB = sys.argv[1] if len(sys.argv) > 1 else "contrib.json"
OUT = sys.argv[2] if len(sys.argv) > 2 else "snake.gif"

GREEN = {0:"#ebedf0",1:"#9be9a8",2:"#40c463",3:"#30a14e",4:"#216e39"}
GREY  = {0:"#ebedf0",1:"#c9ced4",2:"#aab0b8",3:"#848c96",4:"#5b636d"}
COL2LVL = {"#ebedf0":0,"#9be9a8":1,"#40c463":2,"#30a14e":3,"#216e39":4}
SNAKE_HEAD = (139, 92, 246)     # purple #8B5CF6
SNAKE_TAIL = (47, 129, 247)     # blue   #2F81F7

CELL, GAP = 13, 3
PITCH = CELL + GAP
PAD = 12
ROWS = 7
LMIN, LMAX = 5, 24              # snake length: start -> cap
FPS_MS = 55                     # ms per frame

def hx(h): return tuple(int(h[i:i+2],16) for i in (1,3,5))

def load_grid():
    d = json.load(open(CONTRIB))
    weeks = d["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    cols = len(weeks)
    grid = [[0]*ROWS for _ in range(cols)]
    have = [[False]*ROWS for _ in range(cols)]
    counts = [day["contributionCount"] for w in weeks for day in w["contributionDays"]]
    mx = max(counts) or 1
    for ci, w in enumerate(weeks):
        for day in w["contributionDays"]:
            r = day["weekday"]
            lvl = COL2LVL.get(day["color"].lower())
            if lvl is None:                     # themed color fallback by count
                c = day["contributionCount"]
                lvl = 0 if c == 0 else min(4, 1 + int(3 * c / mx))
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

def lerp(a, b, t): return tuple(round(a[i]+(b[i]-a[i])*t) for i in range(3))

def cell_xy(c, r):
    return PAD + c*PITCH, PAD + r*PITCH

def rrect(draw, x, y, size, color, rad=3):
    draw.rounded_rectangle([x, y, x+size, y+size], radius=rad, fill=color)

def main():
    grid, have, cols = load_grid()
    path = serpentine(cols)
    W = PAD*2 + cols*PITCH - GAP
    H = PAD*2 + ROWS*PITCH - GAP
    green = {k: hx(v) for k, v in GREEN.items()}
    grey = {k: hx(v) for k, v in GREY.items()}

    # precompute snake length at each step (grows on eat, capped)
    length = []
    L = LMIN
    for i, (c, r) in enumerate(path):
        if grid[c][r] > 0:
            L = min(LMAX, L + 1)
        length.append(L)

    frames = []
    eaten = [[False]*ROWS for _ in range(cols)]
    STRIDE = 1
    for i in range(0, len(path), STRIDE):
        c, r = path[i]
        if grid[c][r] > 0:
            eaten[c][r] = True
        img = Image.new("RGB", (W, H), (255, 255, 255))
        d = ImageDraw.Draw(img)
        # grid cells
        for cc in range(cols):
            for rr in range(ROWS):
                if not have[cc][rr]:
                    continue
                lvl = grid[cc][rr]
                col = (grey[lvl] if eaten[cc][rr] else green[lvl]) if lvl > 0 else green[0]
                x, y = cell_xy(cc, rr)
                rrect(d, x, y, CELL, col)
        # snake body (tail -> head), thicker & inflated
        L = length[i]
        body = path[max(0, i-L+1): i+1]
        n = len(body)
        for k, (bc, br) in enumerate(body):
            t = k/(n-1) if n > 1 else 1.0
            col = lerp(SNAKE_TAIL, SNAKE_HEAD, t)
            x, y = cell_xy(bc, br)
            infl = 3 if k == n-1 else 2      # head a bit bigger
            rrect(d, x-infl, y-infl, CELL+2*infl, col, rad=5)
        frames.append(img.convert("P", palette=Image.ADAPTIVE, colors=64))

    # small end pause
    frames += [frames[-1]] * 12
    frames[0].save(OUT, save_all=True, append_images=frames[1:],
                   duration=FPS_MS, loop=0, disposal=2, optimize=True)
    import os
    print(f"wrote {OUT}  {W}x{H}  {len(frames)} frames  {os.path.getsize(OUT)//1024} KB")

if __name__ == "__main__":
    main()
