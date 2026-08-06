# -*- coding: utf-8 -*-
"""
3ds Max PRS 控制器批处理工具

左侧：物体名称 + 通道
右侧：当前选中轨道下的控制器列表（含激活状态）
"""

from __future__ import print_function
import math

from PySide2 import QtCore, QtGui, QtWidgets

QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

try:
    import qtmax
except ImportError:
    qtmax = None

try:
    import pymxs
    from pymxs import runtime as rt
except ImportError:
    pymxs = None
    rt = None


WINDOW_OBJECT_NAME = "MaxAniControlSetWindow"
_window_instance = None

CHANNEL_LABELS = {
    "position": "Position",
    "rotation": "Rotation",
    "scale": "Scale",
}

_channel_icon_cache = {}


def _make_channel_icon(channel, size=20):
    """用 QPainter 绘制通道图标并缓存。"""
    key = (channel, size)
    if key in _channel_icon_cache:
        return _channel_icon_cache[key]

    pixmap = QtGui.QPixmap(size, size)
    pixmap.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(pixmap)
    p.setRenderHint(QtGui.QPainter.Antialiasing, True)

    cx, cy = size / 2.0, size / 2.0
    m = size * 0.38
    head = size * 0.18

    if channel == "position":
        pen = QtGui.QPen(QtGui.QColor("#5ec4f5"), 1.6)
        p.setPen(pen)
        p.setBrush(QtGui.QColor("#5ec4f5"))
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            ex, ey = cx + dx * m, cy + dy * m
            p.drawLine(QtCore.QPointF(cx, cy), QtCore.QPointF(ex, ey))
            perp_x, perp_y = -dy, dx
            p.drawPolygon([
                QtCore.QPointF(ex, ey),
                QtCore.QPointF(ex - dx * head + perp_x * head * 0.45,
                               ey - dy * head + perp_y * head * 0.45),
                QtCore.QPointF(ex - dx * head - perp_x * head * 0.45,
                               ey - dy * head - perp_y * head * 0.45),
            ])

    elif channel == "rotation":
        pen = QtGui.QPen(QtGui.QColor("#6fd89e"), 1.6)
        p.setPen(pen)
        p.setBrush(QtGui.QColor("#6fd89e"))
        r = size * 0.32
        rect = QtCore.QRectF(cx - r, cy - r, r * 2, r * 2)
        p.drawArc(rect, 50 * 16, 260 * 16)
        angle_rad = math.radians(50)
        ax = cx + r * math.cos(angle_rad)
        ay = cy - r * math.sin(angle_rad)
        p.drawPolygon([
            QtCore.QPointF(ax, ay),
            QtCore.QPointF(ax + head * 0.8, ay + head * 0.3),
            QtCore.QPointF(ax + head * 0.1, ay - head * 0.7),
        ])

    elif channel == "scale":
        pen = QtGui.QPen(QtGui.QColor("#f4b95f"), 1.6)
        p.setPen(pen)
        p.setBrush(QtGui.QColor("#f4b95f"))
        d = size * 0.28
        for dx, dy in ((1, -1), (-1, 1)):
            ex, ey = cx + dx * d, cy + dy * d
            p.drawLine(QtCore.QPointF(cx + dx * 2, cy + dy * 2),
                        QtCore.QPointF(ex, ey))
            p.drawPolygon([
                QtCore.QPointF(ex, ey),
                QtCore.QPointF(ex - dx * head, ey),
                QtCore.QPointF(ex, ey - dy * head),
            ])
        for dx, dy in ((-1, -1), (1, 1)):
            ex, ey = cx + dx * d, cy + dy * d
            p.drawLine(QtCore.QPointF(cx + dx * 2, cy + dy * 2),
                        QtCore.QPointF(ex, ey))
            p.drawPolygon([
                QtCore.QPointF(ex, ey),
                QtCore.QPointF(ex - dx * head, ey),
                QtCore.QPointF(ex, ey - dy * head),
            ])

    p.end()
    icon = QtGui.QIcon(pixmap)
    _channel_icon_cache[key] = icon
    return icon

ROLE_DATA = QtCore.Qt.UserRole + 1

LOCKED_CLASS_HINTS = (
    "biped",
    "bipobject",
    "catparent",
    "catbone",
    "catmuscle",
    "catobject",
)

SPECIAL_CLASS_HINTS = (
    "constraint",
    "wire",
    "script",
    "expression",
    "spring",
    "reactor",
    "link_constraint",
    "lookat",
    "path_constraint",
    "attachment",
    "surface",
)


# ---------------------------------------------------------------------------
#  pymxs 桥接
# ---------------------------------------------------------------------------

def _require_pymxs():
    if rt is None:
        raise RuntimeError("当前环境没有 pymxs，请在 3ds Max 中运行本脚本。")


def _safe_str(value, fallback=""):
    try:
        if value is None:
            return fallback
        return str(value)
    except Exception:
        return fallback


def _class_name(obj):
    try:
        return _safe_str(rt.classOf(obj), "Unknown")
    except Exception:
        return "Unknown"


def _is_valid_node(node):
    try:
        return bool(rt.isValidNode(node))
    except Exception:
        return False


def _node_by_handle(handle):
    try:
        node = rt.maxOps.getNodeByHandle(int(handle))
        if node is None:
            return None
        if _safe_str(node) == "undefined":
            return None
        if _is_valid_node(node):
            return node
    except Exception:
        pass
    return None


def _walk_hierarchy(node, collected, seen):
    if not _is_valid_node(node):
        return
    handle = int(node.handle)
    if handle in seen:
        return
    seen.add(handle)
    collected.append(node)
    try:
        children = node.children
        count = int(children.count)
        for i in range(count):
            _walk_hierarchy(children[i], collected, seen)
    except Exception:
        pass


def collect_selected_nodes(include_children=False):
    _require_pymxs()
    collected = []
    seen = set()
    selection = rt.getCurrentSelection()
    count = int(selection.count)
    for i in range(count):
        node = selection[i]
        if include_children:
            _walk_hierarchy(node, collected, seen)
        else:
            if not _is_valid_node(node):
                continue
            handle = int(node.handle)
            if handle in seen:
                continue
            seen.add(handle)
            collected.append(node)
    return collected


_CHANNEL_PROP = {"position": "pos", "rotation": "rotation", "scale": "scale"}
_CHANNEL_SUBANIM_INDEX = {"position": 1, "rotation": 2, "scale": 3}


def get_channel_controller(node, channel):
    """获取 PRS 通道控制器，多种方式兜底。"""
    prop = _CHANNEL_PROP.get(channel)
    if not prop:
        raise ValueError("未知通道: {0}".format(channel))

    # 方法 1：通过 MAXScript evaluate（最可靠，语义和 MAXScript 完全一致）
    try:
        handle = int(node.handle)
        script = "(maxOps.getNodeByHandle {0}).{1}.controller".format(handle, prop)
        ctrl = rt.execute(script)
        if ctrl is not None and _safe_str(ctrl) != "undefined":
            return ctrl
    except Exception:
        pass

    # 方法 2：SubAnim 索引访问  node[3]=Transform, [1]=Pos [2]=Rot [3]=Scale
    try:
        sa_index = _CHANNEL_SUBANIM_INDEX[channel]
        transform_sa = node[3]
        channel_sa = transform_sa[sa_index]
        ctrl = channel_sa.controller
        if ctrl is not None:
            return ctrl
    except Exception:
        pass

    # 方法 3：直接属性链（部分 pymxs 版本可用）
    try:
        if channel == "position":
            return node.pos.controller
        if channel == "rotation":
            return node.rotation.controller
        if channel == "scale":
            return node.scale.controller
    except Exception:
        pass

    return None


def set_channel_controller(node, channel, controller):
    """设置 PRS 通道控制器。"""
    prop = _CHANNEL_PROP.get(channel)
    if not prop:
        raise ValueError("未知通道: {0}".format(channel))

    # 方法 1：MAXScript evaluate（借助全局变量中转控制器对象）
    try:
        handle = int(node.handle)
        rt.execute("global _prs_ctrl_tmp")
        rt._prs_ctrl_tmp = controller
        rt.execute(
            "(maxOps.getNodeByHandle {0}).{1}.controller = _prs_ctrl_tmp".format(handle, prop)
        )
        return
    except Exception:
        pass

    # 方法 2：SubAnim 索引
    try:
        sa_index = _CHANNEL_SUBANIM_INDEX[channel]
        node[3][sa_index].controller = controller
        return
    except Exception:
        pass

    # 方法 3：直接属性链
    if channel == "position":
        node.pos.controller = controller
    elif channel == "rotation":
        node.rotation.controller = controller
    elif channel == "scale":
        node.scale.controller = controller


def get_channel_value(node, channel):
    if channel == "position":
        return node.pos
    if channel == "rotation":
        return node.rotation
    if channel == "scale":
        return node.scale
    raise ValueError("未知通道: {0}".format(channel))


def set_channel_value(node, channel, value):
    if channel == "position":
        node.pos = value
    elif channel == "rotation":
        node.rotation = value
    elif channel == "scale":
        node.scale = value
    else:
        raise ValueError("未知通道: {0}".format(channel))


def create_default_controller(channel):
    if channel == "position":
        return rt.NewDefaultPositionController()
    if channel == "rotation":
        return rt.NewDefaultRotationController()
    if channel == "scale":
        return rt.NewDefaultScaleController()
    raise ValueError("未知通道: {0}".format(channel))


def create_list_controller(channel):
    if channel == "position":
        return rt.position_list()
    if channel == "rotation":
        return rt.rotation_list()
    if channel == "scale":
        return rt.scale_list()
    raise ValueError("未知通道: {0}".format(channel))


def count_keys(controller):
    try:
        n = int(rt.numKeys(controller))
        return max(n, 0)
    except Exception:
        pass
    try:
        return int(controller.keys.count)
    except Exception:
        return 0


def get_controller_name(controller):
    try:
        name = controller.name
        if name is None:
            return ""
        return _safe_str(name).strip()
    except Exception:
        return ""


def set_controller_name(controller, name):
    controller.name = name


def is_node_locked(node):
    class_name = _class_name(node).lower()
    for hint in LOCKED_CLASS_HINTS:
        if hint in class_name:
            return True, "Biped/CAT 不可直接改 PRS"
    try:
        if bool(node.isFrozen):
            return True, "物体已冻结"
    except Exception:
        pass
    return False, ""


def is_list_controller(controller):
    return "list" in _class_name(controller).lower()


def is_special_controller(controller):
    class_name = _class_name(controller).lower()
    if "list" in class_name:
        return False
    for hint in SPECIAL_CLASS_HINTS:
        if hint in class_name:
            return True
    return False


def is_defaultish_controller(controller, channel):
    class_name = _class_name(controller).lower()
    defaults = {
        "position": ("position_xyz", "bezier_position", "linear_position", "tcb_position"),
        "rotation": ("euler_xyz", "bezier_rotation", "linear_rotation", "tcb_rotation", "quaternion"),
        "scale": ("bezier_scale", "scalexyz", "scale_xyz", "linear_scale", "tcb_scale"),
    }
    for name in defaults.get(channel, ()):
        if name in class_name:
            return True
    return False


def clear_controller_keys(controller):
    try:
        rt.deleteKeys(controller, rt.Name("allKeys"))
        return
    except Exception:
        pass
    try:
        rt.deleteKeys(controller.keys, rt.Name("allKeys"))
    except Exception:
        try:
            num_subs = int(controller.numSubs)
            for i in range(1, num_subs + 1):
                sub = controller[i]
                if hasattr(sub, "controller") and sub.controller is not None:
                    clear_controller_keys(sub.controller)
        except Exception:
            raise


def _list_count(list_ctrl):
    try:
        return int(list_ctrl.count)
    except Exception:
        return 0


def _list_active(list_ctrl):
    try:
        return int(list_ctrl.active)
    except Exception:
        return 0


def _list_get_name(list_ctrl, index):
    try:
        return _safe_str(list_ctrl.getName(index), "")
    except Exception:
        return ""


def _list_get_sub(list_ctrl, index):
    try:
        return list_ctrl[index].object
    except Exception:
        try:
            return list_ctrl[index].controller
        except Exception:
            return None


def scan_track(node, channel):
    locked, locked_reason = is_node_locked(node)
    controller = None
    class_name = "None"
    status = "ok"
    note = ""
    key_count = 0
    is_list = False

    try:
        controller = get_channel_controller(node, channel)
    except Exception as exc:
        status = "error"
        note = _safe_str(exc, "读取失败")
        locked = True
        locked_reason = note

    if controller is not None:
        class_name = _class_name(controller)
        key_count = count_keys(controller)
        is_list = is_list_controller(controller)
        if locked:
            status = "locked"
            note = locked_reason
        elif is_special_controller(controller):
            status = "special"
            note = "特殊控制器"
        elif is_list:
            status = "list"
            note = "List ({0})".format(_list_count(controller))
        else:
            status = "ok"
            note = class_name
    elif not locked:
        status = "missing"
        note = "无控制器"

    return {
        "handle": int(node.handle),
        "node_name": _safe_str(node.name, "Unnamed"),
        "channel": channel,
        "channel_label": CHANNEL_LABELS.get(channel, channel),
        "controller_class": class_name,
        "key_count": key_count,
        "status": status,
        "note": note,
        "is_locked": locked,
        "is_list": is_list,
        "is_special": is_special_controller(controller) if controller else False,
    }


def scan_nodes(nodes, channels, only_animated=False):
    tracks = []
    for node in nodes:
        for channel in channels:
            track = scan_track(node, channel)
            if only_animated and track["key_count"] <= 0 and track["status"] not in ("missing", "list"):
                # list 仍显示；无关键非 list 可按需隐藏
                if track["status"] != "list":
                    continue
            tracks.append(track)
    return tracks


def _make_error_item(track, error_text):
    """生成一个错误提示条目，显示在右侧列表。"""
    return {
        "handle": track.get("handle", 0),
        "node_name": track.get("node_name", "?"),
        "channel": track.get("channel", ""),
        "channel_label": track.get("channel_label", "?"),
        "index": 0,
        "is_list_layer": False,
        "controller_name": error_text,
        "controller_class": "-",
        "is_active": False,
        "status": error_text,
        "parent_is_list": False,
    }


def list_controllers_for_track(track):
    """列出某条轨道下的控制器层（List 多层；普通控制器一层）。"""
    node = _node_by_handle(track.get("handle"))
    if node is None:
        return [_make_error_item(track, "物体句柄无效 (handle={0})".format(track.get("handle")))]

    try:
        controller = get_channel_controller(node, track.get("channel", ""))
    except Exception as exc:
        return [_make_error_item(track, "读取失败: {0}".format(_safe_str(exc)))]

    if controller is None:
        return [_make_error_item(track, "无控制器")]

    items = []
    if is_list_controller(controller):
        count = _list_count(controller)
        active = _list_active(controller)
        for index in range(1, count + 1):
            sub = _list_get_sub(controller, index)
            name = _list_get_name(controller, index)
            if not name and sub is not None:
                name = get_controller_name(sub)
            class_name = _class_name(sub) if sub is not None else "Empty"
            if not name:
                name = class_name
            is_active = index == active
            items.append(
                {
                    "handle": track["handle"],
                    "node_name": track["node_name"],
                    "channel": track["channel"],
                    "channel_label": track["channel_label"],
                    "index": index,
                    "is_list_layer": True,
                    "controller_name": name,
                    "controller_class": class_name,
                    "is_active": is_active,
                    "status": "激活" if is_active else "未激活",
                    "parent_is_list": True,
                }
            )
    else:
        name = get_controller_name(controller) or _class_name(controller)
        items.append(
            {
                "handle": track["handle"],
                "node_name": track["node_name"],
                "channel": track["channel"],
                "channel_label": track["channel_label"],
                "index": 0,
                "is_list_layer": False,
                "controller_name": name,
                "controller_class": _class_name(controller),
                "is_active": True,
                "status": "激活",
                "parent_is_list": False,
            }
        )
    return items


def activate_controller_item(item, force_replace=False, preserve_value=True):
    """激活右侧选中的控制器层；非 List 时赋默认控制器。"""
    node = _node_by_handle(item["handle"])
    if node is None:
        return False, "物体已失效"

    locked, reason = is_node_locked(node)
    if locked:
        return False, reason

    channel = item["channel"]
    try:
        controller = get_channel_controller(node, channel)
    except Exception:
        controller = None

    # List 层：setActive
    if item.get("is_list_layer") and controller is not None and is_list_controller(controller):
        try:
            controller.setActive(int(item["index"]))
            return True, "已激活第 {0} 层".format(item["index"])
        except Exception as exc:
            return False, _safe_str(exc, "激活失败")

    # 非 List：赋默认控制器
    if controller is not None:
        if is_special_controller(controller) and not force_replace:
            return False, "特殊控制器，需勾选强制覆盖"
        if is_defaultish_controller(controller, channel) and not force_replace:
            return False, "已是默认可动画控制器"
        if is_list_controller(controller) and not force_replace:
            return False, "当前是 List，请在右侧选择一层激活"

    value = None
    if preserve_value:
        try:
            value = get_channel_value(node, channel)
        except Exception:
            value = None

    new_ctrl = create_default_controller(channel)
    set_channel_controller(node, channel, new_ctrl)
    if preserve_value and value is not None:
        try:
            set_channel_value(node, channel, value)
        except Exception:
            pass
    return True, "已激活"


def activate_track_as_default(track, force_replace=False, preserve_value=True):
    """对左侧轨道整体赋默认控制器。"""
    item = {
        "handle": track["handle"],
        "channel": track["channel"],
        "is_list_layer": False,
        "index": 0,
    }
    return activate_controller_item(item, force_replace=force_replace, preserve_value=preserve_value)


def delete_controller_item(item, force_replace=False, preserve_value=True):
    """删除 List 层，或重置整条轨道控制器。"""
    node = _node_by_handle(item["handle"])
    if node is None:
        return False, "物体已失效"

    locked, reason = is_node_locked(node)
    if locked:
        return False, reason

    channel = item["channel"]
    try:
        controller = get_channel_controller(node, channel)
    except Exception:
        controller = None

    if item.get("is_list_layer") and controller is not None and is_list_controller(controller):
        try:
            count = _list_count(controller)
            if count <= 1:
                return False, "List 至少保留一层，请用重置整条轨道"
            controller.delete(int(item["index"]))
            return True, "已删除第 {0} 层".format(item["index"])
        except Exception as exc:
            return False, _safe_str(exc, "删除失败")

    if controller is not None and is_special_controller(controller) and not force_replace:
        return False, "特殊控制器，需勾选强制覆盖"

    value = None
    if preserve_value:
        try:
            value = get_channel_value(node, channel)
        except Exception:
            value = None

    new_ctrl = create_default_controller(channel)
    set_channel_controller(node, channel, new_ctrl)
    if preserve_value and value is not None:
        try:
            set_channel_value(node, channel, value)
        except Exception:
            pass
    return True, "已重置"


def clear_controller_item_keys(item):
    node = _node_by_handle(item["handle"])
    if node is None:
        return False, "物体已失效"

    locked, reason = is_node_locked(node)
    if locked:
        return False, reason

    try:
        root = get_channel_controller(node, item["channel"])
    except Exception as exc:
        return False, _safe_str(exc, "读取控制器失败")

    if root is None:
        return False, "无控制器"

    target = root
    if item.get("is_list_layer") and is_list_controller(root):
        target = _list_get_sub(root, int(item["index"]))
        if target is None:
            return False, "层控制器无效"

    try:
        clear_controller_keys(target)
    except Exception as exc:
        return False, _safe_str(exc, "删除关键帧失败")
    return True, "已删除关键帧"


def rename_controller_item(item, new_name):
    node = _node_by_handle(item["handle"])
    if node is None:
        return False, "物体已失效"

    locked, reason = is_node_locked(node)
    if locked:
        return False, reason

    try:
        root = get_channel_controller(node, item["channel"])
    except Exception as exc:
        return False, _safe_str(exc, "读取控制器失败")

    if root is None:
        return False, "无控制器"

    try:
        if item.get("is_list_layer") and is_list_controller(root):
            root.setName(int(item["index"]), new_name)
            sub = _list_get_sub(root, int(item["index"]))
            if sub is not None:
                try:
                    set_controller_name(sub, new_name)
                except Exception:
                    pass
        else:
            set_controller_name(root, new_name)
    except Exception as exc:
        return False, _safe_str(exc, "重命名失败")
    return True, new_name


def build_rename_name(item, mode, text, index, auto_number):
    channel_label = item.get("channel_label", "Channel")
    node_name = item.get("node_name", "Object")
    current = item.get("controller_name") or item.get("controller_class") or "Controller"
    text = (text or "").strip()

    if mode == 0:
        name = text or "Control"
    elif mode == 1:
        name = "{0}_{1}".format(node_name, channel_label)
    elif mode == 2:
        name = "{0}_{1}".format(text, current) if text else current
    else:
        name = "{0}_{1}".format(current, text) if text else current

    if auto_number:
        name = "{0}_{1:02d}".format(name, index)
    return name


# ---------------------------------------------------------------------------
#  UI 表格
# ---------------------------------------------------------------------------

class SimpleTable(QtWidgets.QTableWidget):
    def __init__(self, headers, parent=None):
        super(SimpleTable, self).__init__(parent)
        self._headers = headers
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.setShowGrid(False)
        self.verticalHeader().setVisible(False)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

    def set_empty_message(self, text):
        self.clearSpans()
        self.setRowCount(1)
        message = QtWidgets.QTableWidgetItem(text)
        message.setTextAlignment(QtCore.Qt.AlignCenter)
        message.setForeground(QtGui.QColor("#9aa3ad"))
        self.setItem(0, 0, message)
        self.setSpan(0, 0, 1, self.columnCount())

    def clear_rows(self):
        self.clearSpans()
        self.setRowCount(0)

    def apply_filter(self, text):
        text = (text or "").strip().lower()
        for row in range(self.rowCount()):
            item0 = self.item(row, 0)
            if item0 is None or item0.data(ROLE_DATA) is None:
                continue
            if not text:
                self.setRowHidden(row, False)
                continue
            haystack = []
            for col in range(self.columnCount()):
                item = self.item(row, col)
                if item:
                    haystack.append(item.text().lower())
            self.setRowHidden(row, text not in " ".join(haystack))

    def selected_data(self):
        rows = sorted({index.row() for index in self.selectedIndexes()})
        result = []
        for row in rows:
            if self.isRowHidden(row):
                continue
            item = self.item(row, 0)
            if item is None:
                continue
            data = item.data(ROLE_DATA)
            if data:
                result.append(data)
        return result

    def current_data(self):
        row = self.currentRow()
        if row < 0:
            return None
        item = self.item(row, 0)
        if item is None:
            return None
        return item.data(ROLE_DATA)


class TrackTable(SimpleTable):
    """左侧：物体名称 + 通道图标。"""

    def __init__(self, parent=None):
        super(TrackTable, self).__init__(("物体名称", ""), parent)
        self.setIconSize(QtCore.QSize(20, 20))
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
        header.resizeSection(1, 36)

    def set_tracks(self, tracks):
        self.clear_rows()
        self.setRowCount(len(tracks))
        for row, track in enumerate(tracks):
            name_item = QtWidgets.QTableWidgetItem(track["node_name"])
            name_item.setData(ROLE_DATA, track)
            channel = track.get("channel", "")
            channel_item = QtWidgets.QTableWidgetItem()
            channel_item.setIcon(_make_channel_icon(channel))
            channel_item.setToolTip(track.get("channel_label", channel))
            channel_item.setData(ROLE_DATA, track)
            if track.get("status") == "locked":
                name_item.setForeground(QtGui.QColor("#f07777"))
            elif track.get("status") == "list":
                name_item.setForeground(QtGui.QColor("#75cef5"))
            self.setItem(row, 0, name_item)
            self.setItem(row, 1, channel_item)


class ControllerLayerTable(SimpleTable):
    """右侧：来自左侧选中轨道的控制器列表，双击可切换激活。"""

    activated = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super(ControllerLayerTable, self).__init__(
            ("物体名称", "", "#", "控制器名称", "控制器类型", "状态"),
            parent,
        )
        self.setIconSize(QtCore.QSize(20, 20))
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
        header.resizeSection(1, 36)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeToContents)
        self.cellDoubleClicked.connect(self._on_double_click)

    def _on_double_click(self, row, _col):
        cell = self.item(row, 0)
        if cell is None:
            return
        data = cell.data(ROLE_DATA)
        if data:
            self.activated.emit(data)

    def set_controllers(self, items):
        self.clear_rows()
        self.setRowCount(len(items))
        for row, item in enumerate(items):
            index_text = str(item["index"]) if item.get("is_list_layer") else "-"
            channel = item.get("channel", "")

            name_cell = QtWidgets.QTableWidgetItem(item.get("node_name") or "-")
            name_cell.setData(ROLE_DATA, item)

            channel_cell = QtWidgets.QTableWidgetItem()
            channel_cell.setIcon(_make_channel_icon(channel))
            channel_cell.setToolTip(item.get("channel_label", channel))
            channel_cell.setData(ROLE_DATA, item)

            rest_values = (
                index_text,
                item.get("controller_name") or "-",
                item.get("controller_class") or "-",
                item.get("status") or "-",
            )
            self.setItem(row, 0, name_cell)
            self.setItem(row, 1, channel_cell)
            for col, text in enumerate(rest_values, start=2):
                cell = QtWidgets.QTableWidgetItem(text)
                cell.setData(ROLE_DATA, item)
                if col == 5:
                    if item.get("is_active"):
                        cell.setForeground(QtGui.QColor("#8ee5bc"))
                        font = cell.font()
                        font.setBold(True)
                        cell.setFont(font)
                    else:
                        cell.setForeground(QtGui.QColor("#f4b95f"))
                self.setItem(row, col, cell)


class TitleBar(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super(TitleBar, self).__init__(parent)
        self._drag_position = None
        self.setObjectName("titleBar")
        self.setFixedHeight(42)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 6, 0)
        layout.setSpacing(8)

        accent = QtWidgets.QLabel("PRS")
        accent.setObjectName("titleAccent")
        accent.setAlignment(QtCore.Qt.AlignCenter)
        accent.setFixedSize(38, 24)

        title = QtWidgets.QLabel("动画控制器批处理")
        title.setObjectName("windowTitle")
        subtitle = QtWidgets.QLabel("POSITION  ·  ROTATION  ·  SCALE")
        subtitle.setObjectName("windowSubtitle")

        self.minimize_btn = QtWidgets.QPushButton("—")
        self.minimize_btn.setObjectName("windowButton")
        self.minimize_btn.setToolTip("最小化")
        self.close_btn = QtWidgets.QPushButton("×")
        self.close_btn.setObjectName("closeButton")
        self.close_btn.setToolTip("关闭")

        layout.addWidget(accent)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch()
        layout.addWidget(self.minimize_btn)
        layout.addWidget(self.close_btn)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_position = event.globalPos() - self.window().frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_position is not None and event.buttons() & QtCore.Qt.LeftButton:
            self.window().move(event.globalPos() - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_position = None
        super(TitleBar, self).mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            window = self.window()
            window.showNormal() if window.isMaximized() else window.showMaximized()
            event.accept()


class MaxAniControlSetWindow(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(MaxAniControlSetWindow, self).__init__(parent)
        self.setObjectName(WINDOW_OBJECT_NAME)
        self.setWindowTitle("动画控制器批处理")
        self.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setMinimumSize(980, 680)
        self.resize(1100, 760)

        self._tracks = []
        self._source_handles = []
        self._selected_track_key = None

        self._build_ui()
        self._connect_signals()
        self._apply_style()
        self.track_table.set_empty_message("请在场景中选择物体，然后点击“加载选择”")
        self.controller_table.set_empty_message("加载后，在左侧选择轨道即可汇总控制器到右侧")
        self._update_rename_preview()

    def _build_ui(self):
        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(6, 6, 6, 6)

        self.main_panel = QtWidgets.QFrame()
        self.main_panel.setObjectName("mainPanel")
        outer_layout.addWidget(self.main_panel)

        main_layout = QtWidgets.QVBoxLayout(self.main_panel)
        main_layout.setContentsMargins(14, 0, 14, 12)
        main_layout.setSpacing(10)

        self.title_bar = TitleBar()
        main_layout.addWidget(self.title_bar)

        toolbar_layout = QtWidgets.QHBoxLayout()
        self.load_selection_btn = QtWidgets.QPushButton("加载选择")
        self.refresh_btn = QtWidgets.QPushButton("刷新")
        self.select_all_btn = QtWidgets.QPushButton("全选轨道")
        self.select_none_btn = QtWidgets.QPushButton("取消选择")
        toolbar_layout.addWidget(self.load_selection_btn)
        toolbar_layout.addWidget(self.refresh_btn)
        toolbar_layout.addSpacing(12)
        toolbar_layout.addWidget(self.select_all_btn)
        toolbar_layout.addWidget(self.select_none_btn)
        toolbar_layout.addStretch()
        main_layout.addLayout(toolbar_layout)

        channel_group = QtWidgets.QGroupBox("控制通道")
        channel_layout = QtWidgets.QHBoxLayout(channel_group)
        self.position_cb = QtWidgets.QCheckBox("Position")
        self.rotation_cb = QtWidgets.QCheckBox("Rotation")
        self.scale_cb = QtWidgets.QCheckBox("Scale")
        self.position_cb.setIcon(_make_channel_icon("position", 18))
        self.rotation_cb.setIcon(_make_channel_icon("rotation", 18))
        self.scale_cb.setIcon(_make_channel_icon("scale", 18))
        self.position_cb.setChecked(True)
        self.rotation_cb.setChecked(True)
        channel_layout.addWidget(self.position_cb)
        channel_layout.addWidget(self.rotation_cb)
        channel_layout.addWidget(self.scale_cb)
        channel_layout.addStretch()
        main_layout.addWidget(channel_group)

        option_group = QtWidgets.QGroupBox("选项")
        option_layout = QtWidgets.QGridLayout(option_group)
        self.include_children_cb = QtWidgets.QCheckBox("包含层级子物体")
        self.only_animated_cb = QtWidgets.QCheckBox("仅显示已有动画的轨道")
        self.force_replace_cb = QtWidgets.QCheckBox("允许覆盖 Constraint 等特殊控制器")
        self.preserve_value_cb = QtWidgets.QCheckBox("替换控制器时保留当前姿态")
        self.preserve_value_cb.setChecked(True)
        self.force_replace_cb.setToolTip("危险选项：覆盖特殊控制器可能破坏约束或连线关系")
        option_layout.addWidget(self.include_children_cb, 0, 0)
        option_layout.addWidget(self.only_animated_cb, 0, 1)
        option_layout.addWidget(self.preserve_value_cb, 1, 0)
        option_layout.addWidget(self.force_replace_cb, 1, 1)
        main_layout.addWidget(option_group)

        rename_group = QtWidgets.QGroupBox("控制器重命名")
        rename_layout = QtWidgets.QGridLayout(rename_group)
        rename_layout.setColumnStretch(2, 1)

        self.rename_mode_combo = QtWidgets.QComboBox()
        self.rename_mode_combo.addItems(
            ("指定统一名称", "物体名 + 通道名", "添加名称前缀", "添加名称后缀")
        )
        self.rename_edit = QtWidgets.QLineEdit()
        self.rename_edit.setPlaceholderText("输入新的控制器名称...")
        self.rename_preview_label = QtWidgets.QLabel("预览：Control")
        self.rename_preview_label.setObjectName("renamePreview")
        self.auto_number_cb = QtWidgets.QCheckBox("批量添加序号")
        self.rename_btn = QtWidgets.QPushButton("重命名选中控制器")
        self.rename_btn.setProperty("actionRole", "rename")

        rename_layout.addWidget(QtWidgets.QLabel("命名方式"), 0, 0)
        rename_layout.addWidget(self.rename_mode_combo, 0, 1)
        rename_layout.addWidget(QtWidgets.QLabel("名称"), 0, 2, QtCore.Qt.AlignRight)
        rename_layout.addWidget(self.rename_edit, 0, 3)
        rename_layout.addWidget(self.auto_number_cb, 1, 0, 1, 2)
        rename_layout.addWidget(self.rename_preview_label, 1, 2)
        rename_layout.addWidget(self.rename_btn, 1, 3)
        main_layout.addWidget(rename_group)

        list_group = QtWidgets.QGroupBox("控制器列表")
        list_layout = QtWidgets.QVBoxLayout(list_group)
        self.filter_edit = QtWidgets.QLineEdit()
        self.filter_edit.setPlaceholderText("筛选左侧物体名称 / 通道...")

        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        left_panel = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)
        left_title = QtWidgets.QLabel("轨道（物体 / 通道）")
        left_title.setObjectName("panelTitle")
        self.track_table = TrackTable()
        left_layout.addWidget(left_title)
        left_layout.addWidget(self.track_table)

        right_panel = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)
        right_title = QtWidgets.QLabel("控制器（左侧选中汇总）")
        right_title.setObjectName("panelTitle")
        self.controller_table = ControllerLayerTable()
        right_layout.addWidget(right_title)
        right_layout.addWidget(self.controller_table)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([360, 540])

        list_layout.addWidget(self.filter_edit)
        list_layout.addWidget(splitter)
        main_layout.addWidget(list_group, 1)

        operation_layout = QtWidgets.QHBoxLayout()
        self.activate_btn = QtWidgets.QPushButton("激活控制器")
        self.reset_btn = QtWidgets.QPushButton("删除 / 重置控制器")
        self.clear_keys_btn = QtWidgets.QPushButton("删除关键帧")
        self.activate_btn.setProperty("actionRole", "primary")
        self.reset_btn.setProperty("actionRole", "danger")
        self.clear_keys_btn.setProperty("actionRole", "warning")
        self.activate_btn.setToolTip("优先对右侧选中层执行 setActive；若只选左侧则赋默认控制器")
        self.reset_btn.setToolTip("右侧选中 List 层则删除该层；否则重置整条轨道为默认控制器")
        operation_layout.addWidget(self.activate_btn)
        operation_layout.addWidget(self.reset_btn)
        operation_layout.addWidget(self.clear_keys_btn)
        main_layout.addLayout(operation_layout)

        status_layout = QtWidgets.QHBoxLayout()
        self.status_label = QtWidgets.QLabel("就绪")
        self.count_label = QtWidgets.QLabel("物体：0  |  轨道：0  |  控制器：0")
        status_layout.addWidget(self.status_label, 1)
        status_layout.addWidget(self.count_label)
        status_layout.addWidget(QtWidgets.QSizeGrip(self))
        main_layout.addLayout(status_layout)

    def _connect_signals(self):
        self.title_bar.close_btn.clicked.connect(self.close)
        self.title_bar.minimize_btn.clicked.connect(self.showMinimized)

        self.rename_mode_combo.currentIndexChanged.connect(self._update_rename_preview)
        self.rename_edit.textChanged.connect(self._update_rename_preview)
        self.auto_number_cb.toggled.connect(self._update_rename_preview)
        self.rename_btn.clicked.connect(self._on_rename)

        self.load_selection_btn.clicked.connect(self._on_load_selection)
        self.refresh_btn.clicked.connect(self._on_refresh)
        self.activate_btn.clicked.connect(self._on_activate)
        self.reset_btn.clicked.connect(self._on_reset)
        self.clear_keys_btn.clicked.connect(self._on_clear_keys)

        self.select_all_btn.clicked.connect(self.track_table.selectAll)
        self.select_none_btn.clicked.connect(self.track_table.clearSelection)
        self.filter_edit.textChanged.connect(self.track_table.apply_filter)

        # 左侧选中变化时，自动把对应控制器汇总到右侧
        self.track_table.itemSelectionChanged.connect(self._on_track_selection_changed)
        # 右侧双击切换激活状态
        self.controller_table.activated.connect(self._on_controller_double_click)

        self.position_cb.toggled.connect(self._on_refresh)
        self.rotation_cb.toggled.connect(self._on_refresh)
        self.scale_cb.toggled.connect(self._on_refresh)
        self.only_animated_cb.toggled.connect(self._on_refresh)

    def _set_status(self, text):
        self.status_label.setText(text)

    def _selected_channels(self):
        channels = []
        if self.position_cb.isChecked():
            channels.append("position")
        if self.rotation_cb.isChecked():
            channels.append("rotation")
        if self.scale_cb.isChecked():
            channels.append("scale")
        return channels

    def _track_key(self, track):
        if not track:
            return None
        return (track["handle"], track["channel"])

    def _update_counts(self):
        handles = set()
        track_count = 0
        for row in range(self.track_table.rowCount()):
            item = self.track_table.item(row, 0)
            if item is None:
                continue
            track = item.data(ROLE_DATA)
            if not track:
                continue
            if not self.track_table.isRowHidden(row):
                track_count += 1
                handles.add(track["handle"])

        ctrl_count = 0
        for row in range(self.controller_table.rowCount()):
            item = self.controller_table.item(row, 0)
            if item and item.data(ROLE_DATA):
                ctrl_count += 1

        self.count_label.setText(
            "物体：{0}  |  轨道：{1}  |  控制器：{2}".format(
                len(handles), track_count, ctrl_count
            )
        )

    def _populate_tracks(self, tracks, restore_selection=True):
        previous = self._selected_track_key if restore_selection else None
        self._tracks = tracks
        if not tracks:
            self.track_table.set_empty_message("当前没有可显示的轨道")
            self.controller_table.set_empty_message("在左侧选择一条轨道以查看控制器")
            self._selected_track_key = None
            self._update_counts()
            return

        self.track_table.set_tracks(tracks)
        self.track_table.apply_filter(self.filter_edit.text())

        restore_row = 0
        if previous:
            for row in range(self.track_table.rowCount()):
                item = self.track_table.item(row, 0)
                if not item:
                    continue
                track = item.data(ROLE_DATA)
                if self._track_key(track) == previous:
                    restore_row = row
                    break

        self.track_table.blockSignals(True)
        self.track_table.selectRow(restore_row)
        self.track_table.blockSignals(False)
        self._fetch_controllers_from_left(silent=True)

    def _collect_controllers_from_tracks(self, tracks):
        """把多条左侧轨道的控制器汇总成右侧列表数据。"""
        items = []
        for track in tracks:
            layers = list_controllers_for_track(track)
            items.extend(layers)
        return items

    def _fetch_controllers_from_left(self, silent=False):
        """读取左侧选中栏的控制器，打印到右侧列表。"""
        tracks = self.track_table.selected_data()
        current = self.track_table.current_data()
        self._selected_track_key = self._track_key(current)

        if not tracks:
            self.controller_table.set_empty_message("请先在左侧选择一条或多条轨道")
            self._update_counts()
            if not silent:
                self._set_status("未选中左侧轨道")
            return

        try:
            _require_pymxs()
            items = self._collect_controllers_from_tracks(tracks)
        except Exception as exc:
            message = _safe_str(exc, "读取控制器失败")
            self.controller_table.set_empty_message(message)
            self._update_counts()
            if not silent:
                self._set_status(message)
            return

        if not items:
            self.controller_table.set_empty_message("选中轨道没有可显示的控制器")
            self._update_counts()
            if not silent:
                self._set_status("未获取到控制器")
            return

        self.controller_table.set_controllers(items)
        self._update_counts()
        if not silent:
            self._set_status(
                "已获取 {0} 条轨道，共 {1} 个控制器".format(len(tracks), len(items))
            )

    def _on_track_selection_changed(self):
        self._fetch_controllers_from_left(silent=False)

    def _on_controller_double_click(self, item):
        """双击右侧控制器行，切换其激活状态。"""
        try:
            _require_pymxs()
        except RuntimeError as exc:
            self._set_status(_safe_str(exc))
            return

        if not item.get("is_list_layer"):
            self._set_status("非 List 控制器，已经是激活状态")
            return

        force = self.force_replace_cb.isChecked()
        preserve = self.preserve_value_cb.isChecked()

        try:
            with pymxs.undo(True, "Activate Controller Layer"):
                success, message = activate_controller_item(
                    item, force_replace=force, preserve_value=preserve
                )
        except Exception as exc:
            self._set_status("激活失败：{0}".format(_safe_str(exc)))
            return

        if success:
            self._set_status(message)
            self._fetch_controllers_from_left(silent=True)
        else:
            self._set_status(message)

    def _confirm(self, title, text):
        result = QtWidgets.QMessageBox.question(
            self,
            title,
            text,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        return result == QtWidgets.QMessageBox.Yes

    def _operation_targets(self):
        """优先使用右侧选中控制器；否则退回左侧选中轨道。"""
        controllers = self.controller_table.selected_data()
        if controllers:
            return "controller", controllers

        tracks = self.track_table.selected_data()
        if tracks:
            return "track", tracks
        return None, []

    def _run_batch(self, items, worker, undo_name, refresh=True):
        if not items:
            self._set_status("请先在左侧选择轨道，或在右侧选择控制器")
            return

        ok_count = 0
        skip_count = 0
        fail_count = 0
        messages = []

        try:
            with pymxs.undo(True, undo_name):
                for item in items:
                    try:
                        success, message = worker(item)
                    except Exception as exc:
                        success, message = False, _safe_str(exc, "未知错误")
                    if success:
                        ok_count += 1
                    else:
                        skip_hints = ("需勾选", "已是", "锁定", "Biped", "CAT", "冻结", "至少保留")
                        if message and any(h in message for h in skip_hints):
                            skip_count += 1
                        else:
                            fail_count += 1
                        if message:
                            messages.append(
                                "{0}.{1}: {2}".format(
                                    item.get("node_name", "?"),
                                    item.get("channel_label", "?"),
                                    message,
                                )
                            )
        except Exception as exc:
            self._set_status("操作失败：{0}".format(_safe_str(exc)))
            return

        if refresh:
            self._reload_from_handles()

        self._set_status(
            "成功 {0} / 跳过 {1} / 失败 {2}".format(ok_count, skip_count, fail_count)
        )
        if fail_count and messages:
            QtWidgets.QMessageBox.warning(
                self,
                "部分操作未完成",
                "\n".join(messages[:12]) + ("\n..." if len(messages) > 12 else ""),
            )

    def _on_load_selection(self):
        try:
            _require_pymxs()
        except RuntimeError as exc:
            self._set_status(_safe_str(exc))
            return

        channels = self._selected_channels()
        if not channels:
            self._set_status("请至少勾选一个控制通道")
            return

        nodes = collect_selected_nodes(self.include_children_cb.isChecked())
        if not nodes:
            self._source_handles = []
            self._populate_tracks([])
            self._set_status("当前没有选中物体")
            return

        self._source_handles = [int(n.handle) for n in nodes]
        tracks = scan_nodes(nodes, channels, self.only_animated_cb.isChecked())
        self._populate_tracks(tracks, restore_selection=False)
        self._set_status("已加载 {0} 个物体，{1} 条轨道".format(len(nodes), len(tracks)))

    def _reload_from_handles(self):
        if not self._source_handles:
            self._populate_tracks([])
            return

        channels = self._selected_channels()
        if not channels:
            self._populate_tracks([])
            self._set_status("请至少勾选一个控制通道")
            return

        nodes = []
        valid_handles = []
        for handle in self._source_handles:
            node = _node_by_handle(handle)
            if node is not None:
                nodes.append(node)
                valid_handles.append(handle)
        self._source_handles = valid_handles
        tracks = scan_nodes(nodes, channels, self.only_animated_cb.isChecked())
        self._populate_tracks(tracks, restore_selection=True)

    def _on_refresh(self):
        try:
            _require_pymxs()
        except RuntimeError as exc:
            self._set_status(_safe_str(exc))
            return

        if not self._source_handles:
            self._on_load_selection()
            return

        self._reload_from_handles()
        self._set_status("已刷新控制器列表")

    def _on_activate(self):
        try:
            _require_pymxs()
        except RuntimeError as exc:
            self._set_status(_safe_str(exc))
            return

        kind, items = self._operation_targets()
        force = self.force_replace_cb.isChecked()
        preserve = self.preserve_value_cb.isChecked()

        if kind == "controller":
            def worker(item):
                return activate_controller_item(
                    item, force_replace=force, preserve_value=preserve
                )
            self._run_batch(items, worker, "Activate Controllers")
        elif kind == "track":
            def worker(track):
                return activate_track_as_default(
                    track, force_replace=force, preserve_value=preserve
                )
            self._run_batch(items, worker, "Activate Controllers")
        else:
            self._set_status("请先在左侧选择轨道，或在右侧选择控制器")

    def _on_reset(self):
        try:
            _require_pymxs()
        except RuntimeError as exc:
            self._set_status(_safe_str(exc))
            return

        kind, items = self._operation_targets()
        if not items:
            self._set_status("请先在左侧选择轨道，或在右侧选择控制器")
            return

        if kind == "controller":
            tip = "将删除选中的 List 控制器层；若不是 List 层则重置整条轨道。\n是否继续？"
        else:
            tip = "将把选中轨道替换为默认控制器。\n是否继续？"

        if not self._confirm("确认删除 / 重置", tip):
            return

        force = self.force_replace_cb.isChecked()
        preserve = self.preserve_value_cb.isChecked()

        def worker(item):
            if kind == "track":
                item = {
                    "handle": item["handle"],
                    "node_name": item["node_name"],
                    "channel": item["channel"],
                    "channel_label": item["channel_label"],
                    "is_list_layer": False,
                    "index": 0,
                }
            return delete_controller_item(
                item, force_replace=force, preserve_value=preserve
            )

        self._run_batch(items, worker, "Reset Controllers")

    def _on_clear_keys(self):
        try:
            _require_pymxs()
        except RuntimeError as exc:
            self._set_status(_safe_str(exc))
            return

        kind, items = self._operation_targets()
        if not items:
            self._set_status("请先在左侧选择轨道，或在右侧选择控制器")
            return

        if not self._confirm(
            "确认删除关键帧",
            "将删除选中控制器上的全部关键帧。\n是否继续？",
        ):
            return

        def worker(item):
            if kind == "track":
                item = {
                    "handle": item["handle"],
                    "node_name": item["node_name"],
                    "channel": item["channel"],
                    "channel_label": item["channel_label"],
                    "is_list_layer": False,
                    "index": 0,
                }
            return clear_controller_item_keys(item)

        self._run_batch(items, worker, "Clear Controller Keys")

    def _on_rename(self):
        try:
            _require_pymxs()
        except RuntimeError as exc:
            self._set_status(_safe_str(exc))
            return

        kind, items = self._operation_targets()
        if kind != "controller":
            # 无右侧选择时，把左侧轨道映射为当前根控制器
            tracks = self.track_table.selected_data()
            items = []
            for track in tracks:
                layers = list_controllers_for_track(track)
                if layers:
                    # 优先重命名激活层
                    active = [x for x in layers if x.get("is_active")]
                    items.append(active[0] if active else layers[0])
            if not items:
                self._set_status("请先在右侧选择要重命名的控制器")
                return

        mode = self.rename_mode_combo.currentIndex()
        text = self.rename_edit.text().strip()
        auto_number = self.auto_number_cb.isChecked()
        if mode == 0 and not text:
            self._set_status("请输入统一控制器名称")
            return

        counter = [0]

        def worker(item):
            counter[0] += 1
            new_name = build_rename_name(item, mode, text, counter[0], auto_number)
            return rename_controller_item(item, new_name)

        self._run_batch(items, worker, "Rename Controllers")

    def _update_rename_preview(self):
        text = self.rename_edit.text().strip() or "Control"
        mode = self.rename_mode_combo.currentIndex()
        number = "_01" if self.auto_number_cb.isChecked() else ""

        if mode == 0:
            preview = text + number
            self.rename_edit.setPlaceholderText("输入统一控制器名称...")
        elif mode == 1:
            preview = "Box001_Position" + number
            self.rename_edit.setPlaceholderText("此模式不需要输入名称")
        elif mode == 2:
            preview = text + "_Position_Controller" + number
            self.rename_edit.setPlaceholderText("输入名称前缀...")
        else:
            preview = "Position_Controller_" + text + number
            self.rename_edit.setPlaceholderText("输入名称后缀...")

        self.rename_preview_label.setText("预览：" + preview)

    def _apply_style(self):
        self.setStyleSheet(
            """
            QDialog {
                background: transparent;
                color: #f4f7fb;
                font-family: "Microsoft YaHei UI";
                font-size: 14px;
            }
            QFrame#mainPanel {
                background-color: #3b424c;
                border: 1px solid #697584;
                border-radius: 9px;
            }
            QFrame#titleBar {
                background-color: #49525e;
                border: 0;
                border-bottom: 1px solid #606b79;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
            QLabel#titleAccent {
                color: #ffffff;
                background-color: #36a9e1;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 800;
            }
            QLabel#windowTitle {
                color: #ffffff;
                font-size: 17px;
                font-weight: 700;
            }
            QLabel#windowSubtitle {
                color: #aeb9c6;
                font-size: 10px;
                font-weight: 600;
            }
            QLabel#panelTitle {
                color: #75cef5;
                font-weight: 700;
                padding: 2px 0;
            }
            QPushButton#windowButton, QPushButton#closeButton {
                min-width: 32px;
                max-width: 32px;
                min-height: 30px;
                padding: 0;
                border: 0;
                border-radius: 4px;
                background: transparent;
                color: #e9edf2;
                font-size: 18px;
                font-weight: 600;
            }
            QPushButton#windowButton:hover { background-color: #657180; }
            QPushButton#closeButton:hover { background-color: #e05252; color: white; }
            QGroupBox {
                background-color: #444c57;
                border: 1px solid #5d6876;
                border-radius: 6px;
                margin-top: 11px;
                padding-top: 10px;
                color: #f7f9fc;
                font-weight: 700;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
                color: #75cef5;
            }
            QPushButton {
                min-height: 32px;
                padding: 0 15px;
                border: 1px solid #718092;
                border-radius: 5px;
                background-color: #566271;
                color: #ffffff;
                font-weight: 650;
            }
            QPushButton:hover { border-color: #8fdcff; background-color: #657384; }
            QPushButton:pressed { background-color: #424c58; }
            QPushButton[actionRole="primary"] {
                border-color: #49bdf2; background-color: #268fbe; font-size: 15px;
            }
            QPushButton[actionRole="warning"] {
                border-color: #f4b95f; background-color: #b27b2d; font-size: 15px;
            }
            QPushButton[actionRole="danger"] {
                border-color: #f07777; background-color: #b34f54; font-size: 15px;
            }
            QPushButton[actionRole="rename"] {
                border-color: #80d9b0; background-color: #308b68; font-size: 14px;
            }
            QPushButton[actionRole="primary"]:hover { background-color: #31a5d8; }
            QPushButton[actionRole="warning"]:hover { background-color: #c98d35; }
            QPushButton[actionRole="danger"]:hover { background-color: #ca5d63; }
            QPushButton[actionRole="rename"]:hover { background-color: #39a17a; }
            QLineEdit, QComboBox, QTableWidget {
                border: 1px solid #606c7a;
                border-radius: 5px;
                background-color: #343b44;
                color: #f3f6fa;
                selection-background-color: #278fbe;
                selection-color: #ffffff;
            }
            QLineEdit, QComboBox { min-height: 32px; padding: 0 9px; }
            QComboBox::drop-down { width: 24px; border: 0; }
            QComboBox QAbstractItemView {
                border: 1px solid #718092;
                background-color: #414954;
                color: #ffffff;
                selection-background-color: #278fbe;
                outline: 0;
            }
            QHeaderView::section {
                padding: 7px;
                border: 0;
                border-right: 1px solid #5e6976;
                background-color: #505a67;
                color: #ffffff;
                font-weight: 700;
            }
            QTableWidget { alternate-background-color: #3a424c; }
            QSplitter::handle { background: #5a6572; width: 3px; }
            QCheckBox { spacing: 7px; color: #f0f3f7; font-weight: 550; }
            QLabel { color: #edf1f5; }
            QLabel#renamePreview { color: #8ee5bc; font-weight: 650; }
            """
        )


def get_max_main_window():
    if qtmax is None:
        return None
    try:
        return qtmax.GetQMaxMainWindow()
    except Exception:
        return None


def show_window():
    global _window_instance
    if _window_instance is not None:
        try:
            _window_instance.close()
            _window_instance.deleteLater()
        except RuntimeError:
            pass
    _window_instance = MaxAniControlSetWindow(get_max_main_window())
    _window_instance.show()
    _window_instance.raise_()
    _window_instance.activateWindow()
    return _window_instance


if __name__ == "__main__":
    show_window()
