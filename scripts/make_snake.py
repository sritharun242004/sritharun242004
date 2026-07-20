#!/usr/bin/env python3
"""High-quality PURPLE contribution snake GIF:
- smooth anti-aliased rounded-tube snake (supersampled), with a head + eye
- organic pathfinding movement (wanders to nearest contribution, not a fixed sweep)
- grows as it eats; eaten green cells turn GREY at the same intensity (pattern stays)
Reads contrib.json (GitHub GraphQL). Light theme. Deterministic (seeded)."""
import json, sys, random
from collections import deque
from PIL import Image, ImageDraw

random.seed(42)
CONTRIB = sys.argv[1] if len(sys.argv) > 1 else "contrib.json"
OUT = sys.argv[2] if len(sys.argv) > 2 else "snake.gif"

GREEN = {0:"#ebedf0",1:"#9be9a8",2:"#40c463",3:"#30a14e",4:"#216e39"}
GREY  = {0:"#ebedf0",1:"#c9ced4",2:"#aab0b8",3:"#848c96",4:"#5b636d"}
COL2LVL = {"#ebedf0":0,"#9be9a8":1,"#40c463":2,"#30a14e":3,"#216e39":4}
SNAKE_HEAD = (124, 58, 237)     # deep purple  #7C3AED
SNAKE_TAIL = (167, 139, 250)    # light purple #A78BFA

CELL, GAP, PAD, ROWS = 14, 3, 16, 7
PITCH = CELL + GAP
SS = 2
BODYW = CELL + 3
LMIN, LMAX = 5, 44
FPS_MS = 90
MAX_FRAMES = 135

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

def neighbors(c, r, cols):
    for dc, dr in ((1,0),(-1,0),(0,1),(0,-1)):
        nc, nr = c+dc, r+dr
        if 0 <= nc < cols and 0 <= nr < ROWS:
            yield nc, nr

def bfs(start, goal, cols):
    prev = {start: None}; q = deque([start])
    while q:
        cur = q.popleft()
        if cur == goal:
            break
        for nb in neighbors(*cur, cols):
            if nb not in prev:
                prev[nb] = cur; q.append(nb)
    if goal not in prev:
        return []
    path, cur = [], goal
    while cur != start:
        path.append(cur); cur = prev[cur]
    return path[::-1]

def build_path(grid, cols):
    targets = {(c, r) for c in range(cols) for r in range(ROWS) if grid[c][r] > 0}
    head = (0, 3); path = [head]
    while targets:
        hx0, hy0 = head
        best = min(targets, key=lambda t: abs(t[0]-hx0)+abs(t[1]-hy0) + random.random())
        seg = bfs(head, best, cols)
        if not seg:
            targets.discard(best); continue
        path.extend(seg)
        for cell in seg:
            targets.discard(cell)
        head = best
    return path

def cell_center(c, r):
    return (PAD + c*PITCH + CELL/2, PAD + r*PITCH + CELL/2)

def main():
    grid, have, cols = load_grid()
    path = build_path(grid, cols)
    stride = max(1, len(path)//MAX_FRAMES)
    W = PAD*2 + cols*PITCH - GAP
    H = PAD*2 + ROWS*PITCH - GAP
    green = {k: hx(v) for k, v in GREEN.items()}
    grey = {k: hx(v) for k, v in GREY.items()}

    length, L = [], LMIN
    for (c, r) in path:
        if grid[c][r] > 0:
            L = min(LMAX, L + 1)
        length.append(L)

    eaten = [[False]*ROWS for _ in range(cols)]
    frames = []
    for i in range(0, len(path), stride):
        for k in range(max(0, i-stride), i+1):
            c, r = path[k]
            if grid[c][r] > 0:
                eaten[c][r] = True
        big = Image.new("RGB", (W*SS, H*SS), (255, 255, 255))
        d = ImageDraw.Draw(big)
        for cc in range(cols):
            for rr in range(ROWS):
                if not have[cc][rr]:
                    continue
                lvl = grid[cc][rr]
                col = (grey[lvl] if eaten[cc][rr] else green[lvl]) if lvl > 0 else green[0]
                x = (PAD + cc*PITCH)*SS; y = (PAD + rr*PITCH)*SS
                d.rounded_rectangle([x, y, x+CELL*SS, y+CELL*SS], radius=3*SS, fill=col)
        L = length[i]
        body = path[max(0, i-L+1): i+1]
        pts = [tuple(v*SS for v in cell_center(c, r)) for (c, r) in body]
        n = len(pts); w = BODYW*SS
        for k in range(n):
            col = lerp(SNAKE_TAIL, SNAKE_HEAD, k/(n-1) if n > 1 else 1.0)
            px, py = pts[k]
            if k < n-1:
                d.line([pts[k], pts[k+1]], fill=col, width=w)
            d.ellipse([px-w/2, py-w/2, px+w/2, py+w/2], fill=col)
        if pts:
            hxp, hyp = pts[-1]; hr = w*0.62
            d.ellipse([hxp-hr, hyp-hr, hxp+hr, hyp+hr], fill=SNAKE_HEAD)
            dx, dy = (0, 0)
            if n > 1:
                dx, dy = pts[-1][0]-pts[-2][0], pts[-1][1]-pts[-2][1]
                mag = (dx*dx+dy*dy)**0.5 or 1; dx, dy = dx/mag, dy/mag
            ex, ey = hxp + dx*hr*0.4, hyp + dy*hr*0.4; er = hr*0.42
            d.ellipse([ex-er, ey-er, ex+er, ey+er], fill=(255, 255, 255))
            d.ellipse([ex-er*0.5, ey-er*0.5, ex+er*0.5, ey+er*0.5], fill=(26, 22, 52))
        small = big.resize((W, H), Image.LANCZOS)
        frames.append(small.quantize(colors=64, method=Image.MEDIANCUT))

    frames += [frames[-1]] * 14
    frames[0].save(OUT, save_all=True, append_images=frames[1:],
                   duration=FPS_MS, loop=0, disposal=2, optimize=True)
    import os
    print(f"wrote {OUT}  {W}x{H}  {len(frames)} frames  {os.path.getsize(OUT)//1024} KB")

if __name__ == "__main__":
    main()
