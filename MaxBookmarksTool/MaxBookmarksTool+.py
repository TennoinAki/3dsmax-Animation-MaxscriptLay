# ============================================================
# Timeline Bookmarks v8 - 3ds Max
# by：一方狂三
# ============================================================

import sys, json, os
from pymxs import runtime as rt

try:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtCore  import Qt, QTimer, QPoint, QRect
    from PySide2.QtGui   import QPainter, QColor, QPen, QFont, QFontMetrics
    from PySide2.QtWidgets import QWidget, QApplication, QSizePolicy
    import qtmax
except ImportError:
    from PySide6 import QtWidgets, QtCore, QtGui
    from PySide6.QtCore  import Qt, QTimer, QPoint, QRect
    from PySide6.QtGui   import QPainter, QColor, QPen, QFont, QFontMetrics
    from PySide6.QtWidgets import QWidget, QApplication, QSizePolicy
    import qtmax

# ─────────────────────────────────────────────────────────────
# QFontMetrics 兼容（Max2021 PySide2 用 width()）
# ─────────────────────────────────────────────────────────────
def _fm_width(fm, txt):
    try:
        return fm.horizontalAdvance(txt)
    except AttributeError:
        return fm.width(txt)

# ─────────────────────────────────────────────────────────────
# 全局配置
# ─────────────────────────────────────────────────────────────
Y_OFFSET    = 0
RULER_H     = 20
TRACK_H_MIN = 30
TRACK_H_MAX = 300

_dark_mode = True
_THEMES = {
    "dark": {
        "bg":        "#1a1a1a",
        "panel_bg":  "#141414",
        "ruler_bg":  "#111",
        "tick_sm":   "#3a3a3a",
        "tick_lg":   "#555",
        "bm_label":  "#ffffffcc",
        "container": "background:#1a1a1a;",
        "title_bg":  "#1a1a1a",
        "title_fg":  "#888",
    },
    "light": {
        "bg":        "#d4d4d4",
        "panel_bg":  "#c0c0c0",
        "ruler_bg":  "#bbbbbb",
        "tick_sm":   "#aaaaaa",
        "tick_lg":   "#888888",
        "bm_label":  "#000000cc",
        "container": "background:#d4d4d4;",
        "title_bg":  "#d4d4d4",
        "title_fg":  "#444",
    },
}

def _tc(key):
    return _THEMES["dark" if _dark_mode else "light"][key]

PRESET_COLORS = [
    "#E53935","#FB8C00","#FDD835",
    "#43A047","#1E88E5","#8E24AA","#00ACC1"
]

# ─────────────────────────────────────────────────────────────
# 路径工具
# ─────────────────────────────────────────────────────────────
SETTINGS_FILE = os.path.join(
    os.environ.get("LOCALAPPDATA",""), "max_bookmarks_v8_settings.json")
DOC_DIR = os.path.join(
    os.environ.get("USERPROFILE",""), "Documents", "MaxBookmarks")
os.makedirs(DOC_DIR, exist_ok=True)

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE,"r",encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {"track_h": 40, "margin_l": 65, "margin_r": 55, "font_size": 7}

def save_settings(d):
    try:
        with open(SETTINGS_FILE,"w",encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except: pass

def get_max_scene_name():
    try:
        p = str(rt.maxFilePath) + str(rt.maxFileName)
        if p.strip():
            return os.path.splitext(os.path.basename(p))[0]
    except: pass
    return ""

def bookmark_file_for(scene_name):
    name = scene_name if scene_name else "_unsaved"
    return os.path.join(DOC_DIR, f"{name}.json")

def save_bms(bms, scene_name=""):
    path = bookmark_file_for(scene_name)
    try:
        with open(path,"w",encoding="utf-8") as f:
            json.dump(bms, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Bookmarks] 保存失败: {e}")

def load_bms_from(path):
    try:
        with open(path,"r",encoding="utf-8") as f:
            return json.load(f)
    except: return []

# ─────────────────────────────────────────────────────────────
# Max 主窗口 / 时间轴控件
# ─────────────────────────────────────────────────────────────
def get_max_main_window():
    return qtmax.GetQMaxMainWindow()

def find_timeline_widget():
    main = get_max_main_window()
    if not main: return None
    best, best_score = None, 0
    for child in main.findChildren(QWidget):
        try:
            if not child.isVisible(): continue
            geo = child.geometry()
            w, h = geo.width(), geo.height()
            if w < 500 or not (16 <= h <= 50): continue
            gy    = child.mapToGlobal(QPoint(0,0)).y()
            score = gy * 10 + w
            if score > best_score:
                best_score = score
                best = child
        except RuntimeError: continue
    return best

# ─────────────────────────────────────────────────────────────
# 书签数据
# ─────────────────────────────────────────────────────────────
def make_bm(name="", start=0, end=10, color="#E53935", locked=False):
    return {"name":name,"start":start,"end":end,
            "color":color,"locked":locked}

# ─────────────────────────────────────────────────────────────
# 书签编辑对话框
# ─────────────────────────────────────────────────────────────
class BookmarkEditDialog(QtWidgets.QDialog):
    def __init__(self, bm, parent=None):
        super().__init__(parent, Qt.Tool|Qt.WindowStaysOnTopHint)
        self.setWindowTitle("书签设置")
        self.setFixedWidth(300)
        self._bm      = bm
        self._color   = bm["color"]
        self._deleted = False
        self._build()

    def _build(self):
        lay = QtWidgets.QFormLayout(self)
        self.e_name  = QtWidgets.QLineEdit(self._bm["name"])
        self.s_start = QtWidgets.QSpinBox()
        self.s_start.setRange(-99999,99999)
        self.s_start.setValue(self._bm["start"])
        self.s_end   = QtWidgets.QSpinBox()
        self.s_end.setRange(-99999,99999)
        self.s_end.setValue(self._bm["end"])

        self.btn_color = QtWidgets.QPushButton(self._color)
        self.btn_color.setStyleSheet(
            f"background:{self._color};color:#000;border-radius:3px;")
        self.btn_color.clicked.connect(self._pick_color)

        self.chk_lock = QtWidgets.QCheckBox("锁定范围（不可拖动修改）")
        self.chk_lock.setStyleSheet(
            "QCheckBox{color:#FFD700;}"
            "QCheckBox::indicator{width:14px;height:14px;border:1px solid #888;"
            "border-radius:2px;background:#2d2d2d;}"
            "QCheckBox::indicator:checked{background:#FFD700;border-color:#FFD700;}")
        self.chk_lock.setChecked(self._bm.get("locked",False))

        lay.addRow("名称:",   self.e_name)
        lay.addRow("起始帧:", self.s_start)
        lay.addRow("结束帧:", self.s_end)
        lay.addRow("颜色:",   self.btn_color)

        btn_row = QtWidgets.QHBoxLayout()

        btn_ok = QtWidgets.QPushButton("✅ 确认")
        btn_ok.setStyleSheet(
            "QPushButton{background:#2a7a2a;color:#fff;border:none;"
            "border-radius:3px;padding:3px 12px;}"
            "QPushButton:hover{background:#4caf50;}")
        btn_ok.clicked.connect(self.accept)

        btn_del = QtWidgets.QPushButton("🗑 删除")
        btn_del.setStyleSheet(
            "QPushButton{background:#7a2a2a;color:#fff;border:none;"
            "border-radius:3px;padding:3px 12px;}"
            "QPushButton:hover{background:#c62828;}")
        btn_del.clicked.connect(self._on_delete)

        btn_cancel = QtWidgets.QPushButton("✖ 取消")
        btn_cancel.setStyleSheet(
            "QPushButton{background:#444;color:#ccc;border:none;"
            "border-radius:3px;padding:3px 12px;}"
            "QPushButton:hover{background:#666;}")
        btn_cancel.clicked.connect(self.reject)

        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_del)
        btn_row.addWidget(btn_cancel)
        lay.addRow(btn_row)

        self.setStyleSheet("""
            QDialog{background:#1e1e1e;color:#ddd;}
            QLineEdit,QSpinBox{background:#2d2d2d;border:1px solid #555;
                color:#eee;border-radius:3px;padding:2px;}
            QPushButton{background:#3a3a3a;color:#eee;
                border:1px solid #555;border-radius:3px;padding:2px 8px;}
            QPushButton:hover{background:#505050;}
            QCheckBox{color:#ddd;}
        """)

    def was_deleted(self):
        return self._deleted

    def _on_delete(self):
        self._deleted = True
        self.accept()

    def _pick_color(self):
        col = QtWidgets.QColorDialog.getColor(QColor(self._color),self)
        if col.isValid(): self._set_color(col.name())

    def _set_color(self, c):
        self._color = c
        self.btn_color.setText(c)
        self.btn_color.setStyleSheet(
            f"background:{c};color:#000;border-radius:3px;")

    def apply_to(self, bm):
        bm["name"]   = self.e_name.text()
        bm["start"]  = self.s_start.value()
        bm["end"]    = self.s_end.value()
        bm["color"]  = self._color
        bm["locked"] = self.chk_lock.isChecked()

# ─────────────────────────────────────────────────────────────
# 书签轨道
# ─────────────────────────────────────────────────────────────
class BookmarkTrack(QWidget):
    HANDLE_W = 8

    def __init__(self, overlay_ref, parent=None):
        super().__init__(parent)
        self._overlay  = overlay_ref
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        cfg = load_settings()
        self._track_h = max(TRACK_H_MIN,
                            min(TRACK_H_MAX, cfg.get("track_h", 40)))
        self.setFixedHeight(self._track_h)

        self.bookmarks   = []
        self._anim_start = int(rt.animationRange.start)
        self._anim_end   = int(rt.animationRange.end)
        self._add_mode   = False
        self._drag_mode  = None
        self._drag_bm    = -1
        self._drag_ox    = 0
        self._drag_orig  = None
        self._creating   = False
        self._new_s      = 0
        self._new_e      = 0
        self._color_idx  = 0
        self._last_scene = get_max_scene_name()
        self._last_frame = int(rt.sliderTime)
        self._margin_l   = cfg.get("margin_l", 65)
        self._margin_r   = cfg.get("margin_r", 55)
        self._font_size  = cfg.get("font_size", 7)

        self._isolated_bm_idx  = -1
        self._prev_anim_start  = self._anim_start
        self._prev_anim_end    = self._anim_end

        self._auto_load()

        self._cursor_btn = QtWidgets.QPushButton("▼", self)
        self._cursor_btn.setFixedSize(28, 14)
        self._cursor_btn.setCursor(Qt.SizeHorCursor)
        self._cursor_btn.setToolTip("拖动修改当前帧")
        self._cursor_btn.setStyleSheet("""
            QPushButton{background:#FF5722;color:#fff;border:none;
                border-radius:2px;font-size:9px;font-weight:bold;}
            QPushButton:hover{background:#FF7043;}
        """)
        self._cursor_btn.installEventFilter(self)
        self._cursor_btn_dragging    = False
        self._cursor_btn_start_x     = 0
        self._cursor_btn_start_frame = 0
        self._update_cursor_btn_pos()

    # ══ 添加模式 ══════════════════════════════════════════════
    def set_add_mode(self, val: bool):
        self._add_mode = val
        self.update()
        try:
            self._overlay._title._refresh_add_btn()
        except: pass

    def toggle_add_mode(self):
        self.set_add_mode(not self._add_mode)

    def _auto_load(self):
        scene = get_max_scene_name()
        path  = bookmark_file_for(scene)
        self.bookmarks = load_bms_from(path) if os.path.exists(path) else []

    # ══ 坐标转换 ══════════════════════════════════════════════
    def _f2x(self, frame):
        total  = max(self._anim_end - self._anim_start, 1)
        usable = max(self.width() - self._margin_l - self._margin_r, 1)
        return int(self._margin_l + (frame - self._anim_start) / total * usable)

    def _x2f(self, x):
        total  = max(self._anim_end - self._anim_start, 1)
        usable = max(self.width() - self._margin_l - self._margin_r, 1)
        return int(round(
            self._anim_start + ((x - self._margin_l) / usable) * total))

    def _bm_rect(self, bm):
        x1 = self._f2x(bm["start"])
        x2 = self._f2x(bm["end"])
        y  = RULER_H + 1
        h  = self.height() - RULER_H - 2
        return QRect(x1, y, max(x2-x1, 4), h)

    # ══ 帧光标按钮 ════════════════════════════════════════════
    def _update_cursor_btn_pos(self):
        cx = self._f2x(self._last_frame)
        bw = self._cursor_btn.width()
        self._cursor_btn.move(cx - bw // 2, 0)
        self._cursor_btn.raise_()

    def eventFilter(self, obj, event):
        if obj is not self._cursor_btn:
            return super().eventFilter(obj, event)
        t = event.type()
        if t == QtCore.QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                self._cursor_btn_dragging    = True
                self._cursor_btn_start_x     = event.globalX()
                self._cursor_btn_start_frame = self._last_frame
                return True
        elif t == QtCore.QEvent.MouseMove:
            if self._cursor_btn_dragging:
                dx    = event.globalX() - self._cursor_btn_start_x
                total = max(self._anim_end - self._anim_start, 1)
                df    = int(dx * total / max(self.width(), 1))
                new_f = self._cursor_btn_start_frame + df
                new_f = max(self._anim_start, min(self._anim_end, new_f))
                rt.sliderTime = new_f
                self._last_frame = new_f
                self._update_cursor_btn_pos()
                self.update()
                return True
        elif t == QtCore.QEvent.MouseButtonRelease:
            if event.button() == Qt.LeftButton:
                self._cursor_btn_dragging = False
                return True
        return super().eventFilter(obj, event)

    # ══ 回调触发函数 ══════════════════════════════════════════
    def on_time_changed(self):
        if self._cursor_btn_dragging: return
        cur = int(rt.sliderTime)
        if cur != self._last_frame:
            self._last_frame = cur
            self._update_cursor_btn_pos()
            self.update()

    def on_scene_changed(self):
        scene = get_max_scene_name()
        self._last_scene       = scene
        self.bookmarks         = []
        self._isolated_bm_idx  = -1
        self._anim_start       = int(rt.animationRange.start)
        self._anim_end         = int(rt.animationRange.end)
        self._prev_anim_start  = self._anim_start
        self._prev_anim_end    = self._anim_end
        self._auto_load()
        self._update_cursor_btn_pos()
        self.update()

    def on_anim_range_changed(self):
        ns = int(rt.animationRange.start)
        ne = int(rt.animationRange.end)
        if ns == self._anim_start and ne == self._anim_end: return
        self._anim_start = ns
        self._anim_end   = ne
        self._update_cursor_btn_pos()
        self.update()

    # ══ 双击书签：隔离/恢复动画范围 ══════════════════════════
    def _toggle_isolate(self, idx):
        bm = self.bookmarks[idx]
        if self._isolated_bm_idx == idx:
            rt.execute(
                f"animationRange = interval {self._prev_anim_start} {self._prev_anim_end}")
            self._isolated_bm_idx = -1
        else:
            self._prev_anim_start = self._anim_start
            self._prev_anim_end   = self._anim_end
            self._isolated_bm_idx = idx
            rt.execute(
                f"animationRange = interval {bm['start']} {bm['end']}")
        self.update()

    # ══ 绘制 ══════════════════════════════════════════════════
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(_tc("bg")))

        if self._add_mode:
            p.fillRect(QRect(0, RULER_H, self.width(),
                             self.height()-RULER_H),
                       QColor(255,200,0,15))

        if self._margin_l > 0:
            p.fillRect(QRect(0, RULER_H, self._margin_l,
                             self.height()-RULER_H), QColor(_tc("panel_bg")))
        if self._margin_r > 0:
            p.fillRect(QRect(self.width()-self._margin_r, RULER_H,
                             self._margin_r, self.height()-RULER_H),
                       QColor(_tc("panel_bg")))

        self._draw_ruler(p)

        fn = QFont("Arial", self._font_size, QFont.Bold)
        fs = QFont("Arial", self._font_size)
        fm = QFontMetrics(fs)

        for i, bm in enumerate(self.bookmarks):
            r   = self._bm_rect(bm)
            col = QColor(bm["color"])
            fill = QColor(col); fill.setAlpha(160)
            p.fillRect(r, fill)

            if i == self._isolated_bm_idx:
                p.setPen(QPen(QColor("#fff"), 2))
            else:
                pen_style = Qt.DashLine if bm.get("locked") else Qt.SolidLine
                p.setPen(QPen(col.lighter(150), 1, pen_style))
            p.drawRect(r)

            if not bm.get("locked"):
                for hx in [r.left(), r.right()-self.HANDLE_W]:
                    p.fillRect(
                        QRect(hx,r.top(),self.HANDLE_W,r.height()),
                        QColor(255,255,255,55))

            if bm.get("locked") and r.width() > 16:
                p.setPen(QColor("#FFD700"))
                p.setFont(fs)
                p.drawText(r.adjusted(2,0,-2,0),
                           Qt.AlignVCenter|Qt.AlignRight,"🔒")

            p.setFont(fs)
            p.setPen(QColor(0,0,0,200) if not _dark_mode else QColor(255,255,255,200))
            s_txt = str(bm["start"])
            e_txt = str(bm["end"])
            sw = _fm_width(fm, s_txt)
            ew = _fm_width(fm, e_txt)
            sx = r.left()-sw-3 if r.left()>=sw+3 else r.left()+2
            p.drawText(QRect(sx,r.top(),sw+2,r.height()),
                       Qt.AlignVCenter|Qt.AlignLeft, s_txt)
            ex = r.right()+3
            if ex+ew > self.width(): ex = r.right()-ew-4
            p.drawText(QRect(ex,r.top(),ew+2,r.height()),
                       Qt.AlignVCenter|Qt.AlignLeft, e_txt)

            if r.width() > 50:
                p.setPen(QColor(0,0,0,200) if not _dark_mode else QColor(255,255,255,200))   # ← 深色白字/浅色黑字
                p.setFont(fn)
                p.drawText(
                    r.adjusted(self.HANDLE_W+4,0,-self.HANDLE_W-4,0),
                    Qt.AlignVCenter|Qt.AlignHCenter, bm["name"])

        if self._creating:
            x1 = self._f2x(min(self._new_s,self._new_e))
            x2 = self._f2x(max(self._new_s,self._new_e))
            r  = QRect(x1,RULER_H+1,max(x2-x1,2),
                       self.height()-RULER_H-2)
            p.setPen(QPen(QColor("#fff"),1,Qt.DashLine))
            p.setBrush(QColor(255,255,255,30))
            p.drawRect(r)

        cx = self._f2x(self._last_frame)
        p.setPen(QPen(QColor("#FF5722"),1))
        p.drawLine(cx, 0, cx, self.height())
        p.end()

    def _draw_ruler(self, p):
        a_s   = self._anim_start
        a_e   = self._anim_end
        w     = self.width()
        total = max(a_e - a_s, 1)
        ml    = self._margin_l
        mr    = self._margin_r
        p.fillRect(QRect(0,0,w,RULER_H), QColor(_tc("ruler_bg")))

        if ml > 0:
            p.fillRect(QRect(0, 0, ml, RULER_H), QColor(_tc("panel_bg")))
        if mr > 0:
            p.fillRect(QRect(w-mr, 0, mr, RULER_H), QColor(_tc("panel_bg")))

        usable = max(w - ml - mr, 1)

        def f2x(f):
            return int(ml + (f - a_s) / total * usable)

        px_per_frame = usable / total
        tick_step = 1
        for step in [1,2,5,10,20,25,50,100,200,500,1000]:
            if px_per_frame * step >= 50:
                tick_step = step
                break
        small_step = max(1, tick_step // 5)

        p.setPen(QPen(QColor(_tc("tick_sm")),1))
        f = a_s
        while f <= a_e:
            p.drawLine(f2x(f), RULER_H-3, f2x(f), RULER_H)
            f += small_step

        p.setPen(QPen(QColor(_tc("tick_lg")),1))
        f = a_s
        while f <= a_e:
            p.drawLine(f2x(f), RULER_H//2, f2x(f), RULER_H)
            f += tick_step

        font_b = QFont("Arial",7,QFont.Bold)
        p.setFont(font_b)
        fm = QFontMetrics(font_b)
        for frame, side in [(a_s,"left"),(a_e,"right")]:
            x   = f2x(frame)
            txt = str(frame)
            tw  = _fm_width(fm, txt)
            pad = 3
            p.setPen(QPen(QColor("#FF5722"),2))
            p.drawLine(x,0,x,RULER_H)
            bx = x+3 if side=="left" else x-tw-pad*2-1
            bx = max(0, min(bx, w-tw-pad*2-1))
            br = QRect(bx,1,tw+pad*2,RULER_H-2)
            p.fillRect(br, QColor("#FF5722"))
            p.setPen(QColor("#fff"))
            p.drawText(br, Qt.AlignCenter, txt)

    # ══ 碰撞检测 ══════════════════════════════════════════════
    def _hit(self, x, y):
        if y < RULER_H: return "ruler", -1
        for i in range(len(self.bookmarks)-1,-1,-1):
            r = self._bm_rect(self.bookmarks[i])
            if not r.contains(x,y): continue
            if self.bookmarks[i].get("locked"):
                return "locked", i
            if x <= r.left()+self.HANDLE_W: return "left", i
            if x >= r.right()-self.HANDLE_W: return "right", i
            return "move", i
        return "create", -1

    # ══ 鼠标事件 ══════════════════════════════════════════════
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            mode, idx = self._hit(e.x(),e.y())
            if mode in ("ruler","locked"): return
            if mode == "create":
                if not self._add_mode: return
                self._drag_mode = "create"
                self._drag_ox   = e.x()
                self._creating  = True
                self._new_s = self._new_e = self._x2f(e.x())
            else:
                self._drag_mode = mode
                self._drag_bm   = idx
                self._drag_ox   = e.x()
                self._drag_orig = dict(self.bookmarks[idx])
        elif e.button() == Qt.RightButton:
            _, idx = self._hit(e.x(),e.y())
            if idx >= 0: self._open_edit(idx)
            else: self._global_menu(e.globalPos())

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            mode, idx = self._hit(e.x(), e.y())
            if idx >= 0 and mode not in ("ruler","locked"):
                self._toggle_isolate(idx)

    def mouseMoveEvent(self, e):
        if not (e.buttons() & Qt.LeftButton):
            mode, _ = self._hit(e.x(),e.y())
            if mode == "ruler":
                self.setCursor(Qt.ArrowCursor); return
            self.setCursor({
                "left":   Qt.SizeHorCursor,
                "right":  Qt.SizeHorCursor,
                "move":   Qt.SizeAllCursor,
                "locked": Qt.ForbiddenCursor,
            }.get(mode, Qt.CrossCursor if self._add_mode else Qt.ArrowCursor))
            return
        df = self._x2f(e.x()) - self._x2f(self._drag_ox)
        if self._drag_mode == "create":
            self._new_e = self._x2f(e.x())
        elif self._drag_mode == "move" and self._drag_bm >= 0:
            orig = self._drag_orig; ln = orig["end"]-orig["start"]
            self.bookmarks[self._drag_bm]["start"] = orig["start"]+df
            self.bookmarks[self._drag_bm]["end"]   = orig["start"]+df+ln
        elif self._drag_mode == "left" and self._drag_bm >= 0:
            ns = self._drag_orig["start"]+df
            if ns < self.bookmarks[self._drag_bm]["end"]-1:
                self.bookmarks[self._drag_bm]["start"] = ns
        elif self._drag_mode == "right" and self._drag_bm >= 0:
            ne = self._drag_orig["end"]+df
            if ne > self.bookmarks[self._drag_bm]["start"]+1:
                self.bookmarks[self._drag_bm]["end"] = ne
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            if self._drag_mode == "create" and self._creating:
                s,ed = sorted([self._new_s,self._new_e])
                if ed-s >= 1:
                    col = PRESET_COLORS[self._color_idx%len(PRESET_COLORS)]
                    self._color_idx += 1
                    self.bookmarks.append(make_bm("",s,ed,col))
                    save_bms(self.bookmarks,self._last_scene)
                self._creating = False
            elif self._drag_mode in ("move","left","right"):
                save_bms(self.bookmarks,self._last_scene)
            self._drag_mode = None
            self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_cursor_btn_pos()

    def _global_menu(self, gpos):
        menu = QtWidgets.QMenu(self)
        menu.setStyleSheet(
            "QMenu{background:#2b2b2b;color:#eee;border:1px solid #555;}"
            "QMenu::item:selected{background:#444;}")
        act_add  = menu.addAction(
            f"{'✅' if self._add_mode else '⬜'}  添加范围模式")
        menu.addSeparator()
        act_save = menu.addAction("💾  保存书签")
        act_load = menu.addAction("📂  加载书签")
        act = menu.exec_(gpos)
        if not act: return
        if act == act_add:    self.toggle_add_mode()
        elif act == act_save: self._overlay._title._save()
        elif act == act_load: self._overlay._title._load()

    def _open_edit(self, idx):
        bm  = self.bookmarks[idx]
        dlg = BookmarkEditDialog(bm, self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            if dlg.was_deleted():
                del self.bookmarks[idx]
            else:
                dlg.apply_to(bm)
            save_bms(self.bookmarks, self._last_scene)
            self.update()

# ─────────────────────────────────────────────────────────────
# 标题栏
# ─────────────────────────────────────────────────────────────
class TitleBar(QWidget):
    HEIGHT = 22

    def __init__(self, parent_win):
        super().__init__(parent_win)
        self.parent_win = parent_win
        self.setFixedHeight(self.HEIGHT)
        self._drag_pos  = None
        self._built = False

    def late_build(self):
        if self._built: return
        self._built = True
        self._build()

    def _build(self):
        cfg = load_settings()
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(6,0,2,0)
        lay.setSpacing(3)

        lbl = QtWidgets.QLabel("📌 Bookmarks   by：一方狂三")
        lbl.setStyleSheet("color:#aaa;font-size:10px;")
        lay.addWidget(lbl)
        lay.addStretch()

        # 高度 Spinner
        lbl_h = QtWidgets.QLabel("高度:")
        lbl_h.setStyleSheet("color:#888;font-size:10px;")
        lay.addWidget(lbl_h)

        self._spin_h = QtWidgets.QSpinBox()
        self._spin_h.setRange(TRACK_H_MIN, TRACK_H_MAX)
        self._spin_h.setValue(cfg.get("track_h", 40))
        self._spin_h.setFixedSize(58, 18)
        self._spin_h.setToolTip("调整标签行高度")
        self._spin_h.setKeyboardTracking(False)
        self._spin_h.setStyleSheet("""
            QSpinBox{background:#2d2d2d;color:#eee;border:1px solid #555;
                border-radius:2px;font-size:10px;padding:0 2px;}
            QSpinBox::up-button{width:16px;}
            QSpinBox::down-button{width:16px;}
        """)
        self._spin_h.valueChanged.connect(self._on_height_changed)
        lay.addWidget(self._spin_h)

        # 左右边距 Spinner
        lbl_ml = QtWidgets.QLabel("左距:")
        lbl_ml.setStyleSheet("color:#888;font-size:10px;")
        lay.addWidget(lbl_ml)

        self._spin_ml = QtWidgets.QSpinBox()
        self._spin_ml.setRange(0, 300)
        self._spin_ml.setValue(cfg.get("margin_l", 65))
        self._spin_ml.setFixedSize(52, 18)
        self._spin_ml.setToolTip("左边距（像素）")
        self._spin_ml.setKeyboardTracking(False)
        self._spin_ml.setStyleSheet("""
            QSpinBox{background:#2d2d2d;color:#eee;border:1px solid #555;
                border-radius:2px;font-size:10px;padding:0 2px;}
            QSpinBox::up-button{width:16px;}
            QSpinBox::down-button{width:16px;}
        """)
        self._spin_ml.valueChanged.connect(self._on_margin_l_changed)
        lay.addWidget(self._spin_ml)

        lbl_mr = QtWidgets.QLabel("右距:")
        lbl_mr.setStyleSheet("color:#888;font-size:10px;")
        lay.addWidget(lbl_mr)

        self._spin_mr = QtWidgets.QSpinBox()
        self._spin_mr.setRange(0, 300)
        self._spin_mr.setValue(cfg.get("margin_r", 55))
        self._spin_mr.setFixedSize(52, 18)
        self._spin_mr.setToolTip("右边距（像素）")
        self._spin_mr.setKeyboardTracking(False)
        self._spin_mr.setStyleSheet("""
            QSpinBox{background:#2d2d2d;color:#eee;border:1px solid #555;
                border-radius:2px;font-size:10px;padding:0 2px;}
            QSpinBox::up-button{width:16px;}
            QSpinBox::down-button{width:16px;}
        """)
        self._spin_mr.valueChanged.connect(self._on_margin_r_changed)
        lay.addWidget(self._spin_mr)

        # 字号滑块
        lbl_fs = QtWidgets.QLabel("字号:")
        lbl_fs.setStyleSheet("color:#888;font-size:10px;")
        lay.addWidget(lbl_fs)

        self._slider_fs = QtWidgets.QSlider(Qt.Horizontal)
        self._slider_fs.setRange(6, 50)
        self._slider_fs.setValue(cfg.get("font_size", 7))
        self._slider_fs.setFixedSize(60, 18)
        self._slider_fs.setToolTip("调整书签名称字体大小")
        self._slider_fs.setStyleSheet("""
            QSlider::groove:horizontal{height:4px;background:#444;border-radius:2px;}
            QSlider::handle:horizontal{width:10px;height:10px;margin:-3px 0;
                background:#FF5722;border-radius:5px;}
            QSlider::sub-page:horizontal{background:#FF5722;border-radius:2px;}
        """)
        self._slider_fs.valueChanged.connect(self._on_fontsize_changed)
        lay.addWidget(self._slider_fs)

        self._lbl_fs_val = QtWidgets.QLabel(str(cfg.get("font_size", 7)))
        self._lbl_fs_val.setStyleSheet("color:#aaa;font-size:10px;")
        self._lbl_fs_val.setFixedWidth(14)
        lay.addWidget(self._lbl_fs_val)

        # 添加模式按钮
        self._btn_add = QtWidgets.QPushButton("➕")
        self._btn_add.setFixedSize(22,18)
        self._btn_add.setToolTip("添加范围模式")
        self._btn_add.clicked.connect(
            lambda: self.parent_win._track.toggle_add_mode())
        lay.addWidget(self._btn_add)
        self._refresh_add_btn()

        # 固定/停靠按钮
        self._btn_pin = QtWidgets.QPushButton("📌")
        self._btn_pin.setFixedSize(22, 18)
        self._btn_pin.setToolTip("浮动并吸附到时间轴 / 停靠回底部")
        self._btn_pin.setStyleSheet(
            "QPushButton{background:#7a5500;color:#fff;border:none;"
            "border-radius:2px;font-size:10px;}"
            "QPushButton:hover{background:#b87d00;}")
        self._btn_pin.clicked.connect(self._toggle_pin)
        lay.addWidget(self._btn_pin)

        # 主题切换按钮
        self._btn_theme = QtWidgets.QPushButton("☀")
        self._btn_theme.setFixedSize(22, 18)
        self._btn_theme.setToolTip("切换深色/浅色主题")
        self._btn_theme.setStyleSheet(
            "QPushButton{background:#555;color:#fff;border:none;"
            "border-radius:2px;font-size:12px;}"
            "QPushButton:hover{background:#888;}")
        self._btn_theme.clicked.connect(self._toggle_theme)
        lay.addWidget(self._btn_theme)

        for icon, slot, bg, tip, w in [
            ("💾", self._save, "#2a5298", "保存书签", 22),
            ("📂", self._load, "#2a5298", "加载书签", 22),
        ]:
            btn = QtWidgets.QPushButton(icon)
            btn.setFixedSize(w,18)
            btn.setToolTip(tip)
            btn.setStyleSheet(
                f"QPushButton{{background:{bg};color:#fff;border:none;"
                f"border-radius:2px;font-size:10px;}}"
                f"QPushButton:hover{{background:{QColor(bg).lighter(130).name()};}}")
            btn.clicked.connect(slot)
            lay.addWidget(btn)

    # ── 固定/停靠：只做一次初始吸附，之后可自由移动 ──
    def _toggle_pin(self):
        ov = self.parent_win
        if ov.isFloating():
            # 浮动 → 停靠回底部，恢复系统标题栏
            ov.setTitleBarWidget(None)
            ov.setFloating(False)
            self._btn_pin.setText("📌")
            self._btn_pin.setStyleSheet(
                "QPushButton{background:#7a5500;color:#fff;border:none;"
                "border-radius:2px;font-size:10px;}"
                "QPushButton:hover{background:#b87d00;}")
        else:
            # 停靠 → 浮动，一次性吸附到时间轴上方，之后可自由拖动
            ov.setFloating(True)
            ov._empty_title = QWidget()
            ov.setTitleBarWidget(ov._empty_title)  # 隐藏系统标题栏
            QTimer.singleShot(0,   ov._snap_to_timeline)
            QTimer.singleShot(150, ov._snap_to_timeline)
            self._btn_pin.setText("🔓")
            self._btn_pin.setStyleSheet(
                "QPushButton{background:#2a5298;color:#fff;border:none;"
                "border-radius:2px;font-size:10px;}"
                "QPushButton:hover{background:#3d6fcf;}")

    def _toggle_theme(self):
        global _dark_mode
        _dark_mode = not _dark_mode

        try:
            self.parent_win._container.setStyleSheet(_tc("container"))
        except: pass

        bg  = _tc("title_bg")
        fg  = _tc("title_fg")
        inp = "#2d2d2d" if _dark_mode else "#e8e8e8"
        txt = "#eee"    if _dark_mode else "#222"
        brd = "#555"    if _dark_mode else "#aaa"

        self.setStyleSheet(f"QWidget{{background:{bg};}}")

        spin_style = f"""
            QSpinBox{{background:{inp};color:{txt};border:1px solid {brd};
                border-radius:2px;font-size:10px;padding:0 2px;}}
            QSpinBox::up-button{{width:16px;}}
            QSpinBox::down-button{{width:16px;}}
        """
        slider_style = f"""
            QSlider::groove:horizontal{{height:4px;background:{brd};border-radius:2px;}}
            QSlider::handle:horizontal{{width:10px;height:10px;margin:-3px 0;
                background:#FF5722;border-radius:5px;}}
            QSlider::sub-page:horizontal{{background:#FF5722;border-radius:2px;}}
        """
        lbl_style = f"color:{fg};font-size:10px;"

        for w in self.findChildren(QtWidgets.QSpinBox):
            w.setStyleSheet(spin_style)
        for w in self.findChildren(QtWidgets.QSlider):
            w.setStyleSheet(slider_style)
        for w in self.findChildren(QtWidgets.QLabel):
            w.setStyleSheet(lbl_style)

        icon = "🌙" if _dark_mode else "☀"
        bbg  = "#555" if _dark_mode else "#c8a800"
        self._btn_theme.setText(icon)
        self._btn_theme.setStyleSheet(
            f"QPushButton{{background:{bbg};color:#fff;border:none;"
            f"border-radius:2px;font-size:12px;}}"
            f"QPushButton:hover{{background:{QColor(bbg).lighter(120).name()};}}")

        self.parent_win._track.update()

    def _on_height_changed(self, val):
        try:
            self.parent_win._track.setFixedHeight(val)
            cfg = load_settings()
            cfg["track_h"] = val
            save_settings(cfg)
        except: pass

    def _on_margin_l_changed(self, val):
        try:
            self.parent_win._track._margin_l = val
            self.parent_win._track._update_cursor_btn_pos()
            self.parent_win._track.update()
            cfg = load_settings()
            cfg["margin_l"] = val
            save_settings(cfg)
        except: pass

    def _on_margin_r_changed(self, val):
        try:
            self.parent_win._track._margin_r = val
            self.parent_win._track._update_cursor_btn_pos()
            self.parent_win._track.update()
            cfg = load_settings()
            cfg["margin_r"] = val
            save_settings(cfg)
        except: pass

    def _on_fontsize_changed(self, val):
        try:
            self._lbl_fs_val.setText(str(val))
            self.parent_win._track._font_size = val
            self.parent_win._track.update()
            cfg = load_settings()
            cfg["font_size"] = val
            save_settings(cfg)
        except: pass

    def _refresh_add_btn(self):
        try:
            on = self.parent_win._track._add_mode
        except: on = False
        bg = "#4caf50" if on else "#2a7a2a"
        self._btn_add.setStyleSheet(
            f"QPushButton{{background:{bg};color:#fff;border:none;"
            f"border-radius:2px;font-size:10px;}}"
            f"QPushButton:hover{{background:{QColor(bg).lighter(120).name()};}}")

    def _save(self):
        track = self.parent_win._track
        scene = track._last_scene
        save_bms(track.bookmarks, scene)
        QtWidgets.QMessageBox.information(
            self,"保存成功",f"已保存到:\n{bookmark_file_for(scene)}")

    def _load(self):
        track  = self.parent_win._track
        scene  = track._last_scene
        auto_p = bookmark_file_for(scene)
        if os.path.exists(auto_p):
            track.bookmarks = load_bms_from(auto_p)
            track.update()
            QtWidgets.QMessageBox.information(
                self,"自动加载",f"已自动加载:\n{auto_p}")
            return
        path,_ = QtWidgets.QFileDialog.getOpenFileName(
            self,"选择书签文件",DOC_DIR,"JSON (*.json)")
        if path:
            track.bookmarks = load_bms_from(path)
            track.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = (e.globalPos() -
                self.parent_win.frameGeometry().topLeft())

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.LeftButton and self._drag_pos:
            if self.parent_win.isFloating():
                self.parent_win.move(e.globalPos()-self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

# ─────────────────────────────────────────────────────────────
# 主容器：QDockWidget
# ─────────────────────────────────────────────────────────────
class TimelineOverlay(QtWidgets.QDockWidget):

    DOCK_NAME = "BookmarksDockV8"

    def __init__(self):
        parent = qtmax.GetQMaxMainWindow()
        super().__init__(parent)
        self.setWindowTitle("📌 Bookmarks  by：一方狂三")
        self.setObjectName(self.DOCK_NAME)
        self.setAllowedAreas(
            Qt.LeftDockWidgetArea  |
            Qt.RightDockWidgetArea |
            Qt.TopDockWidgetArea   |
            Qt.BottomDockWidgetArea
        )

        self._container = QWidget()
        self._container.setStyleSheet("background:#1a1a1a;")
        self.setWidget(self._container)

        lay = QtWidgets.QVBoxLayout(self._container)
        lay.setContentsMargins(0,0,0,0)
        lay.setSpacing(0)

        self._title = TitleBar(self)
        self._track = BookmarkTrack(self)
        self._title.late_build()

        lay.addWidget(self._title)
        lay.addWidget(self._track)

        self._register_callbacks()

        self._timer_range = QTimer(self)
        self._timer_range.timeout.connect(self._poll_anim_range)
        self._timer_range.start(200)

        self.topLevelChanged.connect(self._on_float_changed)

    # ══ 回调注册 ══════════════════════════════════════════════
    def _register_callbacks(self):
        self._unregister_callbacks()
        rt.registerTimeCallback(_bm_on_time_changed)
        rt.callbacks.addScript(
            rt.Name("systemPostNew"), _bm_on_scene_changed,
            id=rt.Name("bm_scene_new"))
        rt.callbacks.addScript(
            rt.Name("filePostOpen"), _bm_on_scene_changed,
            id=rt.Name("bm_scene_open"))
        rt.callbacks.addScript(
            rt.Name("systemPostReset"), _bm_on_scene_changed,
            id=rt.Name("bm_scene_reset"))

    def _unregister_callbacks(self):
        try: rt.unregisterTimeCallback(_bm_on_time_changed)
        except: pass
        for cb_id in ["bm_scene_new","bm_scene_open","bm_scene_reset"]:
            try: rt.callbacks.removeScripts(id=rt.Name(cb_id))
            except: pass

    # ── _poll_anim_range：只轮询范围，不持续吸附 ──
    def _poll_anim_range(self):
        try: self._track.on_anim_range_changed()
        except: pass

    # ── 一次性吸附：点击📌时触发，之后不再锁死 ──
    def _snap_to_timeline(self):
        if not self.isFloating(): return
        try:
            tl = find_timeline_widget()
            if not tl: return
            main = get_max_main_window()
            if not main: return
            gp       = tl.mapToGlobal(QPoint(0, 0))
            mg       = main.mapToGlobal(QPoint(0, 0))
            target_x = mg.x()
            target_y = gp.y() - self.height()
            target_w = main.width()
            cur = self.geometry()
            if (cur.x() != target_x or cur.y() != target_y
                    or cur.width() != target_w):
                self.setGeometry(target_x, target_y, target_w, self.height())
        except RuntimeError:
            pass

    def _on_float_changed(self, floating: bool):
        if floating:
            try:
                tl = find_timeline_widget()
                if not tl: return
                gp = tl.mapToGlobal(QPoint(0,0))
                self.setGeometry(gp.x(),
                                 gp.y()-self.height()+Y_OFFSET,
                                 tl.width(), self.height())
            except RuntimeError: pass

    def closeEvent(self, event):
        self._unregister_callbacks()
        try:
            self._timer_range.stop()
            self._timer_range.disconnect()
        except: pass
        super().closeEvent(event)

# ─────────────────────────────────────────────────────────────
# 全局回调函数
# ─────────────────────────────────────────────────────────────
def _bm_on_time_changed():
    try:
        if _overlay:
            _overlay._track.on_time_changed()
    except Exception as e:
        print(f"[Bookmarks] timeChanged: {e}")

def _bm_on_scene_changed():
    try:
        if _overlay:
            _overlay._track.on_scene_changed()
    except Exception as e:
        print(f"[Bookmarks] sceneChanged: {e}")

# ─────────────────────────────────────────────────────────────
# 启动
# ─────────────────────────────────────────────────────────────
_overlay = None

def run():
    global _overlay
    try:
        main_win = qtmax.GetQMaxMainWindow()
        for w in main_win.findChildren(QtWidgets.QDockWidget):
            if w.objectName() == TimelineOverlay.DOCK_NAME:
                try: w.close()
                except: pass
                try: w.deleteLater()
                except: pass
        QApplication.processEvents()
        _overlay = TimelineOverlay()
        main_win.addDockWidget(Qt.BottomDockWidgetArea, _overlay)
        _overlay.show()
        print("[Bookmarks] 启动成功 ✅")
    except Exception as e:
        print(f"[Bookmarks] 启动失败: {e}")
    return _overlay

_overlay = run()
