"""HybrIK 全流程(在 3ds Max 内运行)

流程: 选图片 -> 推理(子进程调用 hybrik conda 环境) -> 生成虚拟体+骨骼+圆环总控
      -> 映射到选中 Biped。

为什么用子进程: Max 内嵌 Python 跑不了 HybrIK 的 CUDA 依赖, 故推理交给
hybrik 环境的 python(infer_headless.py)完成, 本脚本用 pymxs 负责建场景与映射。

运行方式: 3ds Max 菜单 Scripting > Run Python Script... 选择本文件;
或 MAXScript: python.ExecuteFile @"...\hybrik_in_max.py"

若路径与默认不同, 修改下方 CONDA_PY / REPO 两个常量即可。
"""
import os
import sys
import json
import tempfile
import subprocess

import pymxs
from pymxs import runtime as rt

# ===================== 路径配置(按需修改) =====================
CONDA_PY = r"C:\Users\fengtengji\miniconda3\envs\hybrik\python.exe"
REPO = r"D:\3dsmaxScript\GitHub\HybrIK"
INFER = os.path.join(REPO, "scripts", "infer_headless.py")

# 骨架生成参数(固定)
SCALE = 220.0      # 米 -> 单位
PT_SIZE = 3.0      # 虚拟体尺寸

# ===================== SMPL / Biped 映射表 =====================
SMPL_NAMES = [
    "pelvis", "left_hip", "right_hip", "spine1", "left_knee", "right_knee",
    "spine2", "left_ankle", "right_ankle", "spine3", "left_foot", "right_foot",
    "neck", "left_collar", "right_collar", "head", "left_shoulder",
    "right_shoulder", "left_elbow", "right_elbow", "left_wrist", "right_wrist",
    "left_hand", "right_hand",
]
SMPL_PARENTS = [-1, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 9, 9, 12, 13, 14,
                16, 17, 18, 19, 20, 21]
# SMPL 关节 -> 标准 Biped 骨骼名后缀; None = 跳过
SUFFIX = [
    "", " L Thigh", " R Thigh", " Spine", " L Calf", " R Calf", " Spine1",
    " L Foot", " R Foot", " Spine2", " L Toe0", " R Toe0", " Neck",
    " L Clavicle", " R Clavicle", " Head", " L UpperArm", " R UpperArm",
    " L Forearm", " R Forearm", " L Hand", " R Hand", None, None,
]
# 每关节"指向"的子关节(0-based 索引, -1 = 无)
AIM_CHILD = [-1, 4, 5, 6, 7, 8, 9, 10, 11, 12, -1, -1, 15, 16, 17, -1,
             18, 19, 20, 21, 22, 23, -1, -1]


# ===================== 向量工具(纯 python) =====================
def vsub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vdot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def vlen(a):
    return (a[0] * a[0] + a[1] * a[1] + a[2] * a[2]) ** 0.5


def vnorm(a):
    n = vlen(a)
    if n < 1e-9:
        return (0.0, 0.0, 0.0)
    return (a[0] / n, a[1] / n, a[2] / n)


def vcross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def p3(v):
    return rt.Point3(float(v[0]), float(v[1]), float(v[2]))


# ===================== 推理(子进程) =====================
def run_inference(img_path, model_key, log):
    out_path = os.path.join(tempfile.gettempdir(), "hybrik_pose.json")
    overlay_path = os.path.splitext(out_path)[0] + "_overlay.jpg"
    cmd = [CONDA_PY, INFER, img_path, out_path, model_key]
    log("推理中(首次会加载模型, 请稍候)...")
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, encoding="utf-8", errors="ignore")
    if proc.stderr:
        log(proc.stderr.strip())
    if proc.returncode != 0:
        raise RuntimeError("推理失败, 见上方日志。")
    with open(out_path, "r", encoding="utf-8") as fid:
        jd = json.load(fid)
    return jd, overlay_path


# ===================== 建骨架(pymxs) =====================
def compute_positions(jd):
    joints = jd["joints_3d"]            # 24+(29) 个 [x,y,z]
    pos = []
    for j in range(24):
        x, y, z = joints[j][0], joints[j][1], joints[j][2]
        # SMPL(x右,y下,z前) -> Max(x右, y=z前, z=-y上)
        pos.append([x * SCALE, z * SCALE, -y * SCALE])
    # 修正: pelvis 取两胯中点; spine3 取 spine2-neck 中点
    pos[0] = [(pos[1][i] + pos[2][i]) / 2.0 for i in range(3)]
    pos[9] = [(pos[6][i] + pos[12][i]) / 2.0 for i in range(3)]
    # 脚部落地(最低 Z = 0)
    minz = min(p[2] for p in pos)
    for p in pos:
        p[2] -= minz
    return pos


def make_bone(ps, pe, name, root, lyr):
    d = vsub(pe, ps)
    if vlen(d) < 1e-4:
        return
    up = (0.0, 0.0, 1.0)
    if abs(vdot(vnorm(d), up)) > 0.95:
        up = (0.0, 1.0, 0.0)
    zax = vnorm(vcross(d, up))
    bn = rt.BoneSys.createBone(p3(ps), p3(pe), p3(zax))
    bn.name = name
    bn.width = bn.height = PT_SIZE * 1.2
    bn.wirecolor = rt.color(255, 200, 80)
    bn.taper = 90.0
    bn.parent = root
    lyr.addNode(bn)


def build_skeleton(jd, log):
    pos = compute_positions(jd)

    lyr = rt.LayerManager.getLayerFromName("HybrIK_SMPL")
    if lyr is None:
        lyr = rt.LayerManager.newLayerFromName("HybrIK_SMPL")

    # 圆环总控
    ringR = max(max(p[2] for p in pos) * 0.22, PT_SIZE * 4)
    root = rt.circle(radius=float(ringR), pos=rt.Point3(float(pos[0][0]), float(pos[0][1]), 0.0),
                     name="HybrIK_Root", wirecolor=rt.color(60, 220, 120))
    lyr.addNode(root)

    # 虚拟体
    pts = []
    for j in range(24):
        pt = rt.Point(pos=p3(pos[j]), size=float(PT_SIZE), box=True, cross=False,
                      centermarker=False, axistripod=False,
                      wirecolor=rt.color(80, 180, 255), name="SMPL_" + SMPL_NAMES[j])
        lyr.addNode(pt)
        pts.append(pt)
    for j in range(24):
        par = SMPL_PARENTS[j]
        if par >= 0:
            pts[j].parent = pts[par]
    pts[0].parent = root

    # 骨骼
    for j in range(24):
        par = SMPL_PARENTS[j]
        if par >= 0:
            make_bone(pos[par], pos[j], "Bone_" + SMPL_NAMES[j], root, lyr)

    rt.select(root)
    log("已生成: 圆环总控 + 24 虚拟体 + 骨骼。可移动/旋转/缩放 HybrIK_Root 整体调整。")


# ===================== 映射到 Biped(pymxs) =====================
def find_biped_root():
    sel = list(rt.selection)
    if not sel:
        return None
    n = sel[0]
    while n.parent is not None and rt.classof(n.parent) == rt.Biped_Object:
        n = n.parent
    if rt.classof(n) != rt.Biped_Object:
        return None
    return n


def node_pos(node):
    r4 = node.transform.row4
    return (r4.x, r4.y, r4.z)


def to_biped(log):
    root = find_biped_root()
    if root is None:
        raise RuntimeError("请先选中目标 Biped 的任意骨骼。")

    P = [None] * 24
    found = 0
    for j in range(24):
        nd = rt.getNodeByName("SMPL_" + SMPL_NAMES[j], exact=True)
        if nd is not None:
            P[j] = node_pos(nd)
            found += 1
    if found < 10:
        raise RuntimeError("未找到 SMPL_ 虚拟体, 请先生成骨架。")

    if P[0] is not None:
        rt.biped.setTransform(root, rt.Name("pos"), p3(P[0]), True)

    applied = 0
    for j in range(24):
        suf = SUFFIX[j]
        if suf is None or suf == "":
            continue
        nd = rt.getNodeByName(root.name + suf, exact=True)
        if nd is None:
            continue
        c = AIM_CHILD[j]
        if c < 0 or P[j] is None or P[c] is None:
            continue
        d = vsub(P[c], P[j])
        if vlen(d) < 1e-4:
            continue
        d = vnorm(d)
        cur = nd.transform
        upv = vnorm((cur.row2.x, cur.row2.y, cur.row2.z))
        if abs(vdot(d, upv)) > 0.95:
            upv = vnorm((cur.row3.x, cur.row3.y, cur.row3.z))
        zax = vnorm(vcross(d, upv))
        yax = vnorm(vcross(zax, d))
        m = rt.matrix3(p3(d), p3(yax), p3(zax), cur.row4)
        rt.biped.setTransform(nd, rt.Name("rotation"), m.rotation, True)
        applied += 1

    log("已映射 %d 根骨骼到 %s" % (applied, root.name))


def delete_all(log):
    names = []
    for o in list(rt.objects):
        nm = o.name
        if nm.startswith("SMPL_") or nm.startswith("Bone_") or nm == "HybrIK_Root":
            names.append(o)
    cnt = len(names)
    for o in names:
        rt.delete(o)
    log("已删除 %d 个生成对象。" % cnt)


# ===================== PySide UI =====================
try:
    from PySide2 import QtWidgets, QtCore, QtGui
    _QT = "PySide2"
except ImportError:
    from PySide6 import QtWidgets, QtCore, QtGui
    _QT = "PySide6"

try:
    import qtmax
    _MAXWIN = qtmax.GetQMaxMainWindow()
except Exception:
    _MAXWIN = None


class HybrIKDialog(QtWidgets.QDialog):
    def __init__(self, parent=_MAXWIN):
        super(HybrIKDialog, self).__init__(parent)
        self.setWindowTitle("HybrIK -> Biped (全流程)")
        self.setMinimumWidth(440)
        self._jd = None
        self._cur_img = None
        self._build_ui()

    def _build_ui(self):
        lay = QtWidgets.QVBoxLayout(self)

        row = QtWidgets.QHBoxLayout()
        self.ed_img = QtWidgets.QLineEdit()
        btn_br = QtWidgets.QPushButton("浏览图片...")
        btn_br.clicked.connect(self._browse)
        row.addWidget(self.ed_img)
        row.addWidget(btn_br)
        lay.addLayout(row)

        row2 = QtWidgets.QHBoxLayout()
        row2.addWidget(QtWidgets.QLabel("模型:"))
        self.cb_model = QtWidgets.QComboBox()
        self.cb_model.addItems(["res34 (快)", "hrnet (准)"])
        row2.addWidget(self.cb_model, 1)
        lay.addLayout(row2)

        # 图片预览(点击放大)
        self.img_view = QtWidgets.QLabel("无图片")
        self.img_view.setAlignment(QtCore.Qt.AlignCenter)
        self.img_view.setMinimumHeight(300)
        self.img_view.setStyleSheet("background:#222; color:#888;")
        self.img_view.setToolTip("点击放大查看")
        self.img_view.setCursor(QtCore.Qt.PointingHandCursor)
        self.img_view.mousePressEvent = self._open_full
        lay.addWidget(self.img_view)

        self.btn_run = QtWidgets.QPushButton("① 推理")
        self.btn_run.clicked.connect(self._on_infer)
        lay.addWidget(self.btn_run)

        self.btn_build = QtWidgets.QPushButton("② 生成骨骼")
        self.btn_build.clicked.connect(self._on_build)
        lay.addWidget(self.btn_build)

        self.btn_map = QtWidgets.QPushButton("③ 映射到选中 Biped")
        self.btn_map.clicked.connect(self._on_map)
        lay.addWidget(self.btn_map)

        self.btn_del = QtWidgets.QPushButton("删除生成物")
        self.btn_del.clicked.connect(self._on_del)
        lay.addWidget(self.btn_del)

        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(120)
        lay.addWidget(self.log)

    def _log(self, msg):
        self.log.appendPlainText(str(msg))
        QtWidgets.QApplication.processEvents()

    def _show_image(self, path):
        pm = QtGui.QPixmap(path)
        if pm.isNull():
            self.img_view.setText("无法加载预览图")
            self._cur_img = None
            return
        self._cur_img = path
        self.img_view.setPixmap(pm.scaled(
            self.img_view.width(), self.img_view.height(),
            QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))

    def _open_full(self, event=None):
        if not self._cur_img or not os.path.isfile(self._cur_img):
            return
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("预览 (原始分辨率, 可滚动查看细节)")
        dlg.resize(960, 760)
        v = QtWidgets.QVBoxLayout(dlg)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(False)
        lbl = QtWidgets.QLabel()
        lbl.setPixmap(QtGui.QPixmap(self._cur_img))
        lbl.adjustSize()
        scroll.setWidget(lbl)
        v.addWidget(scroll)
        dlg.show()

    def _browse(self):
        f, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "选择图片", "", "图片 (*.jpg *.jpeg *.png *.bmp);;所有文件 (*.*)")
        if f:
            self.ed_img.setText(f)
            self._show_image(f)

    def _on_infer(self):
        img = self.ed_img.text().strip()
        if not img or not os.path.isfile(img):
            self._log("请先选择有效图片。")
            return
        key = "res34" if self.cb_model.currentIndex() == 0 else "hrnet"
        self.btn_run.setEnabled(False)
        try:
            self._jd, overlay = run_inference(img, key, self._log)
            if os.path.isfile(overlay):
                self._show_image(overlay)
            self._log("推理完成, 可点'② 生成骨骼'。")
        except Exception as e:
            self._log("错误: %s" % e)
        finally:
            self.btn_run.setEnabled(True)

    def _on_build(self):
        if self._jd is None:
            self._log("请先点'① 推理'。")
            return
        try:
            with pymxs.undo(True, "HybrIK Build"):
                build_skeleton(self._jd, self._log)
            rt.redrawViews()
        except Exception as e:
            self._log("错误: %s" % e)

    def _on_map(self):
        try:
            with pymxs.undo(True, "HybrIK To Biped"):
                to_biped(self._log)
            rt.redrawViews()
        except Exception as e:
            self._log("错误: %s" % e)

    def _on_del(self):
        try:
            with pymxs.undo(True, "HybrIK Delete"):
                delete_all(self._log)
        except Exception as e:
            self._log("错误: %s" % e)


def show():
    global _hybrik_dialog
    try:
        _hybrik_dialog.close()
    except Exception:
        pass
    _hybrik_dialog = HybrIKDialog()
    _hybrik_dialog.show()


show()
