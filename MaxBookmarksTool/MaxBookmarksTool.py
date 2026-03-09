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
# 全局配置
# ─────────────────────────────────────────────────────────────
Y_OFFSET    = 0
RULER_H     = 20
TRACK_H_MIN = 0
TRACK_H_MAX = 300
BM_LEFT     = 80   # ★ 轨道左侧面板宽度（与标题栏按钮区对齐）
BM_RIGHT    = 60   # ★ 轨道右侧出血宽度

# ★ 主题色表
_dark_mode = True
_THEMES = {
    "dark": {
        "bg":          "#1a1a1a",
        "panel_bg":    "#141414",
        "panel_sep":   "#333",
        "panel_txt":   "#444",
        "ruler_bg":    "#111",
        "tick_sm":     "#3a3a3a",
        "tick_lg":     "#555",
        "bm_label":    "#ffffffcc",
        "container":   "background:#1a1a1a;",
    },
    "light": {
        "bg":          "#d4d4d4",
        "panel_bg":    "#c0c0c0",
        "panel_sep":   "#999",
        "panel_txt":   "#777",
        "ruler_bg":    "#bbbbbb",
        "tick_sm":     "#aaaaaa",
        "tick_lg":     "#888888",
        "bm_label":    "#000000cc",
        "container":   "background:#d4d4d4;",
    },
}

def _tc(key):
    """获取当前主题颜色"""
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
    return {"track_h": 60}

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

def get_max_scene_dir():
    """获取当前 Max 场景文件所在目录，若未保存则返回 DOC_DIR"""
    try:
        p = str(rt.maxFilePath).strip()
        if p and os.path.isdir(p):
            return p
    except: pass
    return DOC_DIR

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
        self._bm    = bm
        self._color = bm["color"]
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
            "QCheckBox::indicator{width:14px;height:14px;border:1px solid #888;border-radius:2px;background:#2d2d2d;}"
            "QCheckBox::indicator:checked{background:#FFD700;border-color:#FFD700;}")
        self.chk_lock.setChecked(self._bm.get("locked",False))

        lay.addRow("名称:",   self.e_name)
        lay.addRow("起始帧:", self.s_start)
        lay.addRow("结束帧:", self.s_end)
        lay.addRow("颜色:",   self.btn_color)
        lay.addRow("", self.chk_lock)

        btn_row = QtWidgets.QHBoxLayout()

        btn_ok = QtWidgets.QPushButton("✅ 确认")
        btn_ok.setStyleSheet(
            "QPushButton{background:#2a7a2a;color:#fff;border:none;border-radius:3px;padding:3px 12px;}"
            "QPushButton:hover{background:#4caf50;}")
        btn_ok.clicked.connect(self.accept)

        btn_del = QtWidgets.QPushButton("🗑 删除")
        btn_del.setStyleSheet(
            "QPushButton{background:#7a2a2a;color:#fff;border:none;border-radius:3px;padding:3px 12px;}"
            "QPushButton:hover{background:#c62828;}")
        btn_del.clicked.connect(self._on_delete)

        btn_cancel = QtWidgets.QPushButton("✖ 取消")
        btn_cancel.setStyleSheet(
            "QPushButton{background:#444;color:#ccc;border:none;border-radius:3px;padding:3px 12px;}"
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
                            min(TRACK_H_MAX, cfg.get("track_h", 60)))
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

        # ★ 双击隔离状态：记录隔离前的原始范围
        self._isolated_bm_idx  = -1   # 当前被隔离的书签索引，-1表示无
        self._prev_anim_start  = self._anim_start
        self._prev_anim_end    = self._anim_end

        self._auto_load()

        # ★ 帧光标按钮
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
        total = max(self._anim_end - self._anim_start, 1)
        avail = max(self.width() - BM_LEFT - BM_RIGHT, 1)
        return BM_LEFT + int((frame - self._anim_start) / total * avail)

    def _x2f(self, x):
        total = max(self._anim_end - self._anim_start, 1)
        avail = max(self.width() - BM_LEFT - BM_RIGHT, 1)
        return int(round(
            self._anim_start + ((x - BM_LEFT) / avail) * total))

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
        # 限制按钟不超出左右面板区域
        cx = max(BM_LEFT, min(self.width() - BM_RIGHT, cx))
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

    # ══ ★ 双击书签：隔离/恢复动画范围 ════════════════════════
    def _toggle_isolate(self, idx):
        bm = self.bookmarks[idx]
        if self._isolated_bm_idx == idx:
            # ★ 用 MaxScript execute 字符串方式设置范围
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

        # ★ 左侧面板背景
        p.fillRect(QRect(0, 0, BM_LEFT, self.height()), QColor(_tc("panel_bg")))
        p.setPen(QPen(QColor(_tc("panel_sep")), 1))
        p.drawLine(BM_LEFT, 0, BM_LEFT, self.height())
        # 左侧面板提示文字
        p.setPen(QColor(_tc("panel_txt")))
        p.setFont(QFont("Arial", 7))
        p.drawText(QRect(0, RULER_H, BM_LEFT, self.height()-RULER_H),
                   Qt.AlignCenter, "书签轨道")

        # ★ 右侧出血背景
        rp = self.width() - BM_RIGHT
        p.fillRect(QRect(rp, 0, BM_RIGHT, self.height()), QColor(_tc("panel_bg")))
        p.setPen(QPen(QColor(_tc("panel_sep")), 1))
        p.drawLine(rp, 0, rp, self.height())

        if self._add_mode:
            p.fillRect(QRect(BM_LEFT, RULER_H, self.width()-BM_LEFT-BM_RIGHT,
                             self.height()-RULER_H),
                       QColor(255,200,0,15))

        self._draw_ruler(p)

        fn = QFont("Arial", 10, QFont.Bold)
        fs = QFont("Arial", 10)
        fm = QFontMetrics(fs)

        for i, bm in enumerate(self.bookmarks):
            r   = self._bm_rect(bm)
            col = QColor(bm["color"])
            fill = QColor(col); fill.setAlpha(160)
            p.fillRect(r, fill)

            # ★ 被隔离的书签加亮边框
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
            p.setPen(QColor(_tc("bm_label")))
            s_txt = str(bm["start"])
            e_txt = str(bm["end"])
            sw = fm.horizontalAdvance(s_txt)
            ew = fm.horizontalAdvance(e_txt)
            sx = r.left()-sw-3 if r.left()>=sw+3 else r.left()+2
            p.drawText(QRect(sx,r.top(),sw+2,r.height()),
                       Qt.AlignVCenter|Qt.AlignLeft, s_txt)
            ex = r.right()+3
            if ex+ew > self.width(): ex = r.right()-ew-4
            p.drawText(QRect(ex,r.top(),ew+2,r.height()),
                       Qt.AlignVCenter|Qt.AlignLeft, e_txt)

            if r.width() > 50:
                p.setPen(QColor("#fff"))
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
        cx = max(BM_LEFT, min(self.width() - BM_RIGHT, cx))
        p.setPen(QPen(QColor("#FF5722"),1))
        p.drawLine(cx, 0, cx, self.height())
        p.end()

    def _draw_ruler(self, p):
        a_s   = self._anim_start
        a_e   = self._anim_end
        w     = self.width()
        avail = max(w - BM_LEFT - BM_RIGHT, 1)
        total = max(a_e - a_s, 1)
        p.fillRect(QRect(BM_LEFT, 0, avail, RULER_H), QColor(_tc("ruler_bg")))

        def f2x(f):
            return BM_LEFT + int((f - a_s) / total * avail)

        px_per_frame = avail / total
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

        font_b = QFont("Arial",10,QFont.Bold)
        p.setFont(font_b)
        fm = QFontMetrics(font_b)
        for frame, side in [(a_s,"left"),(a_e,"right")]:
            x   = f2x(frame)
            txt = str(frame)
            tw  = fm.horizontalAdvance(txt)
            pad = 3
            p.setPen(QPen(QColor("#FF5722"),2))
            p.drawLine(x,0,x,RULER_H)
            bx = x+3 if side=="left" else x-tw-pad*2-1
            bx = max(BM_LEFT, min(bx, w-BM_RIGHT-tw-pad*2-1))
            br = QRect(bx,1,tw+pad*2,RULER_H-2)
            p.fillRect(br, QColor("#FF5722"))
            p.setPen(QColor("#fff"))
            p.drawText(br, Qt.AlignCenter, txt)

    # ══ 碰撞检测 ══════════════════════════════════════════════
    def _hit(self, x, y):
        # ★ 左侧面板区域和右侧出血区域均不响应书签操作
        if x < BM_LEFT or x > self.width() - BM_RIGHT: return "panel", -1
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
            if mode in ("ruler","locked","panel"): return
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
            mode, idx = self._hit(e.x(),e.y())
            # panel/ruler 区域右键也弹出全局菜单
            if idx >= 0 and mode not in ("panel", "ruler"): self._open_edit(idx)
            else: self._global_menu(e.globalPos())

    def mouseDoubleClickEvent(self, e):
        """★ 双击书签：隔离/恢复动画范围"""
        if e.button() == Qt.LeftButton:
            mode, idx = self._hit(e.x(), e.y())
            if idx >= 0 and mode not in ("ruler", "locked", "panel"):
                self._toggle_isolate(idx)

    def mouseMoveEvent(self, e):
        if not (e.buttons() & Qt.LeftButton):
            mode, _ = self._hit(e.x(),e.y())
            if mode in ("ruler", "panel"):
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
        # 以 Max 主窗口为父级，避免浮动 dock 丢失焦点导致菜单关闭
        menu = QtWidgets.QMenu(get_max_main_window())
        menu.setStyleSheet(
            "QMenu{background:#2b2b2b;color:#eee;border:1px solid #555;}"
            "QMenu::item:selected{background:#444;}")
        add_icon = "✅" if self._add_mode else "⬜"
        act_add  = menu.addAction(add_icon + "  添加范围模式")
        menu.addSeparator()
        act_save = menu.addAction("\U0001f4be  保存书签")
        act_load = menu.addAction("\U0001f4c2  加载书签")
        act = menu.exec_(gpos)
        if not act: return
        if act == act_add:
            self.toggle_add_mode()
        elif act == act_save:
            self._do_save()
        elif act == act_load:
            self._do_load()

    def _do_save(self):
        """\u76f4接在轨道上执行保存（不依赖 TitleBar）"""
        scene        = self._last_scene
        default_dir  = get_max_scene_dir()
        default_name = scene if scene else "_unsaved"
        default_path = os.path.join(default_dir, f"{default_name}.json")
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "保存书签", default_path, "JSON (*.json)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.bookmarks, f, ensure_ascii=False, indent=2)
            QtWidgets.QMessageBox.information(
                self, "保存成功", f"已保存到:\n{path}")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "保存失败", str(e))

    def _do_load(self):
        """\u76f4接在轨道上执行加载（不依赖 TitleBar）"""
        default_dir = get_max_scene_dir()
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "选择书签文件", default_dir, "JSON (*.json)")
        if path:
            self.bookmarks = load_bms_from(path)
            self.update()

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
    HEIGHT = 28

    def __init__(self, parent_win):
        super().__init__(parent_win)
        self.parent_win = parent_win
        self.setFixedHeight(self.HEIGHT)
        self._drag_pos  = None
        # ★ 延迟 build，等 _track 创建完再初始化 spinner 值
        self._built = False

    def late_build(self):
        """★ 由 TimelineOverlay.__init__ 在 _track 创建后调用"""
        if self._built: return
        self._built = True
        self._build()

    def _build(self):
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(4,0,8,0)
        lay.setSpacing(4)

        # ★ 左侧功能按钮区（与轨道 BM_LEFT 对齐）
        self._btn_add = QtWidgets.QPushButton("➕")
        self._btn_add.setFixedSize(28, 22)
        self._btn_add.setToolTip("添加范围模式")
        self._btn_add.clicked.connect(
            lambda: self.parent_win._track.toggle_add_mode())
        lay.addWidget(self._btn_add)
        self._refresh_add_btn()

        for icon, slot, bg, tip, w in [
            ("💾", self._save, "#2a5298", "保存书签", 28),
            ("📂", self._load, "#2a5298", "加载书签", 28),
        ]:
            btn = QtWidgets.QPushButton(icon)
            btn.setFixedSize(w, 22)
            btn.setToolTip(tip)
            btn.setStyleSheet(
                f"QPushButton{{background:{bg};color:#fff;border:none;"
                f"border-radius:3px;font-size:13px;}}"
                f"QPushButton:hover{{background:{QColor(bg).lighter(130).name()};}}")
            btn.clicked.connect(slot)
            lay.addWidget(btn)

        # ★ 深浅切换按钮
        self._btn_theme = QtWidgets.QPushButton("☀")
        self._btn_theme.setFixedSize(28, 22)
        self._btn_theme.setToolTip("切换深色/浅色主题")
        self._btn_theme.setStyleSheet(
            "QPushButton{background:#555;color:#fff;border:none;"
            "border-radius:3px;font-size:15px;}"
            "QPushButton:hover{background:#888;}")
        self._btn_theme.clicked.connect(self._toggle_theme)
        lay.addWidget(self._btn_theme)

        # ★ 高度 Spinner
        lbl_h = QtWidgets.QLabel("H:")
        lbl_h.setStyleSheet("color:#888;font-size:12px;")
        lay.addWidget(lbl_h)

        self._spin_h = QtWidgets.QSpinBox()
        self._spin_h.setRange(TRACK_H_MIN, TRACK_H_MAX)
        # 读取 track 当前实际高度，在 connect 前 setVaule 不会触发回调
        self._spin_h.setValue(self.parent_win._track._track_h)
        self._spin_h.setFixedSize(64, 22)
        self._spin_h.setToolTip("调整标签行高度，可直接输入数字回车确认")
        self._spin_h.setKeyboardTracking(False)
        self._spin_h.setStyleSheet("""
            QSpinBox{background:#2d2d2d;color:#eee;border:1px solid #555;
                border-radius:3px;font-size:12px;padding:0 2px;}
            QSpinBox::up-button{width:18px;}
            QSpinBox::down-button{width:18px;}
        """)
        self._spin_h.valueChanged.connect(self._on_height_changed)
        lay.addWidget(self._spin_h)

        # ★ 分隔线后放标题标签（右侧剩余区域居中）
        #lay.addStretch()
        #lbl = QtWidgets.QLabel("📌 Bookmarks   by：一方狂三")
        #lbl.setStyleSheet("color:#555;font-size:11px;")
        #lay.addWidget(lbl)

    def _on_height_changed(self, val):
        try:
            self.parent_win._track.setFixedHeight(val)
            cfg = load_settings()
            cfg["track_h"] = val
            save_settings(cfg)
        except: pass

    def _toggle_theme(self):
        global _dark_mode
        _dark_mode = not _dark_mode
        # 更新容器背景色
        try:
            self.parent_win._container.setStyleSheet(_tc("container"))
        except: pass
        # 按钮图标和颜色跟随切换
        icon = "🌙" if _dark_mode else "☀"
        bg   = "#555"   if _dark_mode else "#c8a800"
        self._btn_theme.setText(icon)
        self._btn_theme.setStyleSheet(
            f"QPushButton{{background:{bg};color:#fff;border:none;"
            f"border-radius:3px;font-size:15px;}}"
            f"QPushButton:hover{{background:{QColor(bg).lighter(120).name()};}}")
        self.parent_win._track.update()

    def _refresh_add_btn(self):
        try:
            on = self.parent_win._track._add_mode
        except: on = False
        bg = "#4caf50" if on else "#2a7a2a"
        self._btn_add.setStyleSheet(
            f"QPushButton{{background:{bg};color:#fff;border:none;"
            f"border-radius:3px;font-size:14px;}}"
            f"QPushButton:hover{{background:{QColor(bg).lighter(120).name()};}}")

    def _save(self):
        self.parent_win._track._do_save()

    def _load(self):
        self.parent_win._track._do_load()

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
        self.setWindowTitle("📌 Bookmarks  ")
        self.setObjectName(self.DOCK_NAME)
        self.setAllowedAreas(
            #Qt.LeftDockWidgetArea  |
            #Qt.RightDockWidgetArea |
            #Qt.TopDockWidgetArea   |
            Qt.BottomDockWidgetArea
        )

        self._container = QWidget()
        self._container.setStyleSheet("background:#1a1a1a;")
        self.setWidget(self._container)

        lay = QtWidgets.QVBoxLayout(self._container)
        lay.setContentsMargins(0,0,0,0)
        lay.setSpacing(0)

        # ★ 先创建 TitleBar（空壳），再创建 _track，最后调 late_build
        self._title = TitleBar(self)
        self._track = BookmarkTrack(self)   # ← _track 先于 _build 存在
        self._title.late_build()            # ← 此时 _track 已就绪

        lay.addWidget(self._title)
        lay.addWidget(self._track)

        self._register_callbacks()

        # 200ms 轮询动画范围（无对应回调）
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

    def _poll_anim_range(self):
        try: self._track.on_anim_range_changed()
        except: pass
        # ★ 持续吸附在时间轴正上方
        try: self._snap_to_timeline()
        except: pass

    def _snap_to_timeline(self):
        """★ 将浮动窗口吸附到时间轴正上方，宽度对齐主窗口"""
        if not self.isFloating(): return
        tl = find_timeline_widget()
        if not tl: return
        main = get_max_main_window()
        if not main: return
        gp = tl.mapToGlobal(QPoint(0, 0))
        mg = main.mapToGlobal(QPoint(0, 0))
        target_x = mg.x()
        target_y = gp.y() - self.height()
        target_w = main.width()
        cur = self.geometry()
        if (cur.x() != target_x or cur.y() != target_y
                or cur.width() != target_w):
            self.setGeometry(target_x, target_y, target_w, self.height())

    def _on_float_changed(self, floating: bool):
        if floating:
            try: self._snap_to_timeline()
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
        # ★ 启动后浮动、去掉系统标题栏
        _overlay.setFloating(True)
        _overlay.setTitleBarWidget(QWidget())  # 隐藏系统标题栏
        # ★ 延迟吸附：让事件循环先完成布局，self.height() 才有正确值
        #   通过 exec()/MaxScript 启动时 widget 尚未渲染，立即吸附会位置错误
        QTimer.singleShot(0,   _overlay._snap_to_timeline)
        QTimer.singleShot(100, _overlay._snap_to_timeline)
        print("[Bookmarks] 启动成功 ✅")
    except Exception as e:
        print(f"[Bookmarks] 启动失败: {e}")
    return _overlay

_overlay = run()
