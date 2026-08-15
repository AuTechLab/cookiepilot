"""coin_reader.py — OCR digit reader สำหรับอ่านยอดเหรียญจากหน้า Result

Algorithm (reverse-engineered from CookieGame_Multi_4.5.23):
    1. Crop COIN_ROI จาก screenshot
    2. Grayscale → adaptive threshold (max−12) → binary
    3. Column-projection segmentation หาแต่ละหลัก
    4. Resize แต่ละหลักเป็น DIGIT_GW × DIGIT_GH
    5. matchTemplate TM_CCOEFF_NORMED กับ digit 0-9
    6. รวมตัวอักษร → int
"""

import os

import cv2
import numpy as np

from config import (
    COIN_ROI,
    DIGIT_GH,
    DIGIT_GW,
    DIGIT_MIN_SCORE,
    DIGIT_TEMPLATE_SUBDIR,
    TEMPLATE_DIR,
)

# ── Lazy-loaded digit template cache ──────────────────────────────────────────
_digit_templates: dict | None = None   # {'0': np.ndarray, ..., '9': np.ndarray}


def _load_digit_templates() -> dict:
    """Load digit templates 0-9 from the digits/ sub-folder (lazy, cached)."""
    global _digit_templates
    if _digit_templates is not None:
        return _digit_templates

    digits_dir = os.path.join(TEMPLATE_DIR, DIGIT_TEMPLATE_SUBDIR)
    tpls: dict = {}
    for d in range(10):
        path = os.path.join(digits_dir, f"{d}.png")
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if img is not None:
            # Resize to canonical size and cast to float32
            tpls[str(d)] = cv2.resize(img, (DIGIT_GW, DIGIT_GH)).astype(np.float32)
    _digit_templates = tpls
    return _digit_templates


# ── Column-projection digit segmentation ──────────────────────────────────────
def _segment_digits(gray_roi: np.ndarray) -> tuple[np.ndarray, list]:
    """Return (binary_roi, list_of_[x1,y1,x2,y2] bounding boxes) for each digit.

    Faithful implementation of CookieGame_Multi digit segmentation:
        1. Fixed threshold at 110 with THRESH_BINARY_INV.
        2. Column projection with noise floor threshold (> 1500) to ignore faint lines.
        3. Row bounds extraction (> 510) to trim top/bottom margins.
        4. Height filter (>= 0.45 * maxh) to filter out commas and small dots.
        5. Width filter (3..45) to ignore massive blobs like coin icons.
    """
    g = cv2.cvtColor(gray_roi, cv2.COLOR_BGR2GRAY) if len(gray_roi.shape) == 3 else gray_roi
    _, th = cv2.threshold(g, 110, 255, cv2.THRESH_BINARY_INV)

    # Clean horizontal line noise by requiring > 1500 col sum
    cols = th.sum(axis=0)
    cols_clean = np.where(cols > 1500, cols, 0)

    groups = []
    inrun = False
    start = 0
    for x, v in enumerate(cols_clean):
        if v > 0 and not inrun:
            inrun = True
            start = x
        elif v == 0 and inrun:
            inrun = False
            groups.append((start, x))
    if inrun:
        groups.append((start, len(cols_clean)))

    boxes = []
    for x0, x1 in groups:
        row_sums = th[:, x0:x1].sum(axis=1)
        rows = np.where(row_sums > 510)[0]
        if len(rows) > 0:
            y0, y1 = int(rows[0]), int(rows[-1]) + 1
            boxes.append([x0, y0, x1, y1])

    if not boxes:
        return th, []

    # Original bot height filter (filters out commas & small dots)
    maxh = max(b[3] - b[1] for b in boxes)
    boxes = [b for b in boxes if (b[3] - b[1]) >= 0.45 * maxh]

    # Filter out coin icon or merged wide blobs (> 45px) and tiny noise (< 3px)
    boxes = [b for b in boxes if 3 <= (b[2] - b[0]) <= 45]

    return th, boxes


# ── Main public API ────────────────────────────────────────────────────────────
def read_coins(screen: np.ndarray | None) -> int | None:
    """Read the coin number from a full-resolution screenshot."""
    if screen is None:
        return None

    tpls = _load_digit_templates()
    if len(tpls) < 10:
        return None

    x1, y1, x2, y2 = COIN_ROI
    roi_color = screen[y1:y2, x1:x2]
    if roi_color.size == 0:
        return None

    gray = cv2.cvtColor(roi_color, cv2.COLOR_BGR2GRAY)
    th, boxes = _segment_digits(gray)
    if not boxes:
        return None

    out = ""
    for (bx1, by1, bx2, by2) in boxes:
        g = cv2.resize(
            th[by1:by2, bx1:bx2],
            (DIGIT_GW, DIGIT_GH),
        ).astype(np.float32)

        best_char = None
        best_score = -1.0
        for ch, tpl in tpls.items():
            try:
                res = cv2.matchTemplate(g, tpl, cv2.TM_CCOEFF_NORMED)
                score = float(res[0][0])
            except cv2.error:
                continue
            if score > best_score:
                best_score = score
                best_char = ch

        if best_score < DIGIT_MIN_SCORE or best_char is None:
            # Skip unrecognised box artifact instead of invalidating the whole string
            continue
        out += best_char

    if not out:
        return None
    try:
        return int(out)
    except ValueError:
        return None

def read_result_boxes(screen: np.ndarray | None) -> int | None:
    """Read the number of mystery boxes obtained from the Result screen."""
    if screen is None:
        return None

    tpls = _load_digit_templates()
    if len(tpls) < 10:
        return None

    # Load BOX_RESULT template
    box_tpl_path = os.path.join(TEMPLATE_DIR, "BOX_RESULT_1.png")
    tpl = cv2.imread(box_tpl_path, cv2.IMREAD_COLOR)
    if tpl is None:
        return None

    from config import BOX_RESULT_ROI
    x1, y1, x2, y2 = BOX_RESULT_ROI
    roi = screen[y1:y2, x1:x2]
    th, tw = tpl.shape[:2]
    
    if roi.shape[0] < th or roi.shape[1] < tw:
        return None
        
    res = cv2.matchTemplate(roi, tpl, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    
    if max_val < 0.8:
        return 0  # No box result found
        
    bx = x1 + max_loc[0]
    by = y1 + max_loc[1]
    
    # Text is to the right of the box
    cx0 = bx + tw
    cx1 = min(cx0 + 115, screen.shape[1])
    cy0 = by
    cy1 = min(by + th, screen.shape[0])
    
    text_roi = screen[cy0:cy1, cx0:cx1]
    if text_roi.size == 0:
        return 0
        
    gray = cv2.cvtColor(text_roi, cv2.COLOR_BGR2GRAY)
    th_img, boxes = _segment_digits(gray)
    if not boxes:
        return 0
        
    out = ""
    for (bx1, by1, bx2, by2) in boxes:
        g = cv2.resize(th_img[by1:by2, bx1:bx2], (DIGIT_GW, DIGIT_GH)).astype(np.float32)
        best_char = None
        best_score = -1.0
        for ch, digit_tpl in tpls.items():
            try:
                r = cv2.matchTemplate(g, digit_tpl, cv2.TM_CCOEFF_NORMED)
                score = float(r[0][0])
            except cv2.error:
                continue
            if score > best_score:
                best_score = score
                best_char = ch
        
        if best_score >= DIGIT_MIN_SCORE and best_char is not None:
            out += best_char
            
    if not out:
        return 1  # Box icon was found, default to 1 box if digit read fails (e.g. 'x1')
    try:
        return int(out)
    except ValueError:
        return 1
