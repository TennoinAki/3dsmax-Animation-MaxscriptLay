# -*- coding: utf-8 -*-
"""
3DsPipeLineTools (PLT工具)
==========================
3ds Max 浮动工具栏：动态光球 + 模式切换 + 可定制脚本按钮 + 配置锁定。

模式：模型 / 绑定 / 动画 / 导出 / 自定义
配置（双层）：
  • 共用：与本脚本同目录的 button_config.json（团队下发的 modes/buttons 模板）
  • 个人：3ds Max 用户脚本目录下的 PLT_user_config.json
         （当前模式 / 锁定状态 / 各按钮 color_level / 拖动顺序）
"""
from PySide2 import QtWidgets, QtCore, QtGui
import json
import os
import math
import sys


def _resolve_script_dir():
    """安全获取本脚本所在目录
    
    3ds Max 的 python.executeFile 只在执行期间设置 __file__，
    回调里访问会 NameError。这里在模块加载期立刻解析出绝对路径并缓存。
    """
    # 优先使用 __file__（标准方式）
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        pass
    # 备选 1: 通过 pymxs 拿到当前正在执行的 MaxScript 源文件
    try:
        import pymxs
        fname = pymxs.runtime.getSourceFileName()
        if fname:
            return os.path.dirname(os.path.abspath(str(fname)))
    except Exception:
        pass
    # 备选 2: sys.argv[0]
    try:
        if sys.argv and sys.argv[0]:
            return os.path.dirname(os.path.abspath(sys.argv[0]))
    except Exception:
        pass
    # 兜底：当前工作目录
    return os.getcwd()


# 模块加载时立即缓存，避免按钮点击等延迟回调拿不到 __file__
SCRIPT_DIR = _resolve_script_dir()


def _resolve_user_scripts_dir():
    """获取 3ds Max 当前用户的脚本目录，用于存放个人配置

    标准位置：C:\\Users\\<用户>\\AppData\\Local\\Autodesk\\3dsMax\\<版本>\\ENU\\scripts\\
    优先调用 pymxs.runtime.getDir(#userScripts)，失败时退到 %APPDATA% 兜底，
    保证脱离 Max 调试时也不会崩溃。
    """
    try:
        import pymxs
        rt = pymxs.runtime
        path = rt.getDir(rt.Name('userScripts'))
        if path:
            return os.path.abspath(str(path))
    except Exception:
        pass
    try:
        import pymxs
        rt = pymxs.runtime
        path = rt.getDir(rt.Name('scripts'))
        if path:
            return os.path.abspath(str(path))
    except Exception:
        pass
    appdata = os.environ.get('APPDATA') or os.environ.get('LOCALAPPDATA') or os.path.expanduser('~')
    fallback = os.path.join(appdata, 'Autodesk', '3dsMax_PLT')
    try:
        os.makedirs(fallback, exist_ok=True)
    except Exception:
        pass
    return fallback


USER_SCRIPTS_DIR = _resolve_user_scripts_dir()


class AnimatedOrbButton(QtWidgets.QPushButton):
    """动态彩色光球按钮 - 模拟流动彩色光球，颜色会随时间流动"""
    def __init__(self, parent=None):
        super(AnimatedOrbButton, self).__init__("", parent)
        self.phase = 0.0  # 动画相位 0~1 循环
        self._hovered = False
        self._pressed = False
        # 关闭默认背景，靠 paintEvent 自绘
        self.setFlat(True)
        self.setStyleSheet("QPushButton { background: transparent; border: none; }")
        self.setAttribute(QtCore.Qt.WA_Hover, True)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        # 动画定时器（约30fps）
        self.anim_timer = QtCore.QTimer(self)
        self.anim_timer.timeout.connect(self._tick)
        self.anim_timer.start(33)
    
    def _tick(self):
        # 推进相位，色彩随时间持续流动
        # 不重置 phase：sin/cos 本身周期化，避免循环时各色斑因速度不同步产生跳变
        self.phase += 0.012
        # 仅在极大值时回绕一次，绕回到所有色斑公共周期点（200 是各速度的整数倍数），保证无跳变
        if self.phase > 200.0:
            self.phase -= 200.0
        self.update()
    
    def enterEvent(self, event):
        self._hovered = True
        self.update()
        # 直接调用基类（避免脚本重载时 super(类名, self) 不匹配）
        try:
            QtWidgets.QPushButton.enterEvent(self, event)
        except Exception:
            pass
    
    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        try:
            QtWidgets.QPushButton.leaveEvent(self, event)
        except Exception:
            pass
    
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._pressed = True
            self.update()
        try:
            QtWidgets.QPushButton.mousePressEvent(self, event)
        except Exception:
            pass
    
    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._pressed = False
            self.update()
        try:
            QtWidgets.QPushButton.mouseReleaseEvent(self, event)
        except Exception:
            pass
    
    def showEvent(self, event):
        try:
            QtWidgets.QPushButton.showEvent(self, event)
        except Exception:
            pass
        if not self.anim_timer.isActive():
            self.anim_timer.start(33)
    
    def hideEvent(self, event):
        # 窗口隐藏时停止动画，节省 CPU
        try:
            self.anim_timer.stop()
        except Exception:
            pass
        try:
            QtWidgets.QPushButton.hideEvent(self, event)
        except Exception:
            pass
    
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        rect = self.rect()
        cx = rect.width() / 2.0
        cy = rect.height() / 2.0
        # 留出一点边距给外发光
        radius = min(rect.width(), rect.height()) / 2.0 - 3.0
        
        # 按下/悬停时缩放
        if self._pressed:
            radius *= 0.94
        elif self._hovered:
            radius *= 1.04
        
        phase_rad = self.phase * 2.0 * math.pi
        
        # 1) 外发光（halo）
        glow_radius = radius * 1.18
        glow_grad = QtGui.QRadialGradient(cx, cy, glow_radius)
        glow_grad.setColorAt(0.55, QtGui.QColor(190, 130, 230, 0))
        glow_grad.setColorAt(0.78, QtGui.QColor(210, 150, 240, 70))
        glow_grad.setColorAt(0.92, QtGui.QColor(180, 130, 230, 25))
        glow_grad.setColorAt(1.00, QtGui.QColor(180, 130, 230, 0))
        painter.setBrush(glow_grad)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawEllipse(QtCore.QPointF(cx, cy), glow_radius, glow_radius)
        
        # 2) 主光球：用圆形剪裁后绘制内部多层渐变
        path = QtGui.QPainterPath()
        path.addEllipse(QtCore.QPointF(cx, cy), radius, radius)
        painter.save()
        painter.setClipPath(path)
        
        # 球体底色（深紫蓝）
        painter.fillRect(rect, QtGui.QColor(60, 50, 110))
        
        # 3) 旋转的彩色光斑：每个光斑以不同速度/角度环绕，形成"色彩流动"
        hotspots = [
            # (R, G, B, 角度起始(0~1圈), 距离系数, 大小系数, 速度倍率)
            (255, 200, 230, 0.00, 0.35, 0.95, 1.00),  # 粉
            (140, 180, 255, 0.30, 0.40, 0.85, 0.70),  # 蓝
            (255, 215, 140, 0.62, 0.42, 0.65, 1.40),  # 黄
            (210, 140, 255, 0.85, 0.32, 0.85, 0.55),  # 紫
        ]
        for r, g, b, offset, dist_f, size_f, speed in hotspots:
            ang = phase_rad * speed + offset * 2.0 * math.pi
            # sin 调制让运动更有机不机械
            dist = dist_f + 0.06 * math.sin(ang * 1.7 + offset * 6.28)
            hx = cx + radius * dist * math.cos(ang)
            hy = cy + radius * dist * math.sin(ang)
            hr = radius * size_f
            grad = QtGui.QRadialGradient(hx, hy, hr)
            grad.setColorAt(0.0, QtGui.QColor(r, g, b, 230))
            grad.setColorAt(0.45, QtGui.QColor(r, g, b, 110))
            grad.setColorAt(1.0, QtGui.QColor(r, g, b, 0))
            painter.setBrush(grad)
            painter.drawEllipse(QtCore.QPointF(hx, hy), hr, hr)
        
        # 4) 中心高光（偏左上，体现球体立体感）
        hl_x = cx - radius * 0.18
        hl_y = cy - radius * 0.22
        hl_grad = QtGui.QRadialGradient(hl_x, hl_y, radius * 0.55)
        hl_grad.setColorAt(0.0, QtGui.QColor(255, 255, 255, 180))
        hl_grad.setColorAt(0.4, QtGui.QColor(255, 255, 255, 60))
        hl_grad.setColorAt(1.0, QtGui.QColor(255, 255, 255, 0))
        painter.setBrush(hl_grad)
        painter.drawEllipse(QtCore.QPointF(cx, cy), radius, radius)
        
        # 5) 边缘暗化（球体阴影感）
        edge_grad = QtGui.QRadialGradient(cx, cy, radius)
        edge_grad.setColorAt(0.70, QtGui.QColor(0, 0, 0, 0))
        edge_grad.setColorAt(0.92, QtGui.QColor(40, 20, 70, 80))
        edge_grad.setColorAt(1.00, QtGui.QColor(20, 5, 40, 140))
        painter.setBrush(edge_grad)
        painter.drawEllipse(QtCore.QPointF(cx, cy), radius, radius)
        
        painter.restore()
        
        # 6) 边缘高光环
        rim_alpha = 180 if self._hovered else 140
        rim_pen = QtGui.QPen(QtGui.QColor(255, 230, 250, rim_alpha), 1.2)
        painter.setPen(rim_pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawEllipse(QtCore.QPointF(cx, cy), radius, radius)
        
        painter.end()


class ModeButton(QtWidgets.QPushButton):
    """模式切换按钮（pill 形/胶囊形），区别于其它按钮"""
    def __init__(self, parent=None):
        super(ModeButton, self).__init__(parent)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setCursor(QtCore.Qt.PointingHandCursor)
    
    def apply_mode_color(self, hex_color):
        """根据模式主色重设按钮样式"""
        c = QtGui.QColor(hex_color)
        r, g, b = c.red(), c.green(), c.blue()
        h_r = min(int(r * 1.18), 255)
        h_g = min(int(g * 1.18), 255)
        h_b = min(int(b * 1.18), 255)
        p_r = int(r * 0.82)
        p_g = int(g * 0.82)
        p_b = int(b * 0.82)
        # pill 形 + 高亮内边光 + 微妙渐变
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb({h_r},{h_g},{h_b}),
                    stop:1 rgb({p_r},{p_g},{p_b})
                );
                border: 2px solid rgba(255,255,255,80);
                border-radius: 19px;
                color: #ffffff;
                font-size: 10pt;
                font-weight: bold;
                padding: 0 14px;
            }}
            QPushButton:hover {{
                border: 2px solid rgba(255,255,255,180);
            }}
            QPushButton:pressed {{
                background-color: rgb({p_r},{p_g},{p_b});
            }}
        """)


class DraggableButton(QtWidgets.QPushButton):
    """可拖动的按钮类（支持悬停3秒显示介绍）"""
    HOVER_TIP_DELAY_MS = 3000  # 悬停多久后弹出介绍
    
    def __init__(self, text, parent=None):
        super(DraggableButton, self).__init__(text, parent)
        self.drag_start_position = None
        self.is_dragging = False
        self.original_index = -1
        self.description = ""  # 按钮介绍（来自 config）
        # 悬停延迟显示介绍的定时器
        self._hover_timer = QtCore.QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.timeout.connect(self._show_description_tip)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
    
    def _show_description_tip(self):
        """显示按钮介绍（仅当鼠标仍在按钮上）"""
        try:
            if self.description and self.underMouse():
                pos = self.mapToGlobal(QtCore.QPoint(0, self.height() + 4))
                QtWidgets.QToolTip.showText(pos, self.description, self)
        except Exception:
            pass
    
    def enterEvent(self, event):
        # 进入按钮：如有介绍则启动延迟定时器
        if self.description:
            self._hover_timer.start(self.HOVER_TIP_DELAY_MS)
        try:
            QtWidgets.QPushButton.enterEvent(self, event)
        except Exception:
            pass
    
    def leaveEvent(self, event):
        # 离开按钮：取消定时器并隐藏介绍
        try:
            self._hover_timer.stop()
        except Exception:
            pass
        try:
            QtWidgets.QToolTip.hideText()
        except Exception:
            pass
        try:
            QtWidgets.QPushButton.leaveEvent(self, event)
        except Exception:
            pass
    
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.drag_start_position = event.pos()
            self.is_dragging = False
            # 用户点击按钮时取消介绍延迟
            try:
                self._hover_timer.stop()
                QtWidgets.QToolTip.hideText()
            except Exception:
                pass
        try:
            QtWidgets.QPushButton.mousePressEvent(self, event)
        except Exception:
            pass
    
    def mouseMoveEvent(self, event):
        if not (event.buttons() & QtCore.Qt.LeftButton):
            return
        if self.drag_start_position is None:
            return
        if (event.pos() - self.drag_start_position).manhattanLength() < QtWidgets.QApplication.startDragDistance():
            return
        
        # 注：拖拽重排只改 button_order（个人状态），不受"锁定共用配置"影响，
        # 即使锁定也允许拖动并即时持久化到 PLT_user_config.json。
        
        if not self.is_dragging:
            self.is_dragging = True
            # 通知父窗口开始拖动
            parent = self.parent()
            while parent:
                if isinstance(parent, PLTWindow):
                    parent.start_button_drag(self)
                    break
                parent = parent.parent()
        
        # 通知父窗口更新拖动位置
        parent = self.parent()
        while parent:
            if isinstance(parent, PLTWindow):
                # 转换为全局坐标再转换为父容器坐标
                global_pos = self.mapToGlobal(event.pos())
                parent_pos = parent.content_widget.mapFromGlobal(global_pos)
                # 同时传 x/y，update_button_drag 内部按 orientation 选择主轴
                parent.update_button_drag(self, parent_pos.x(), parent_pos.y(), global_pos)
                break
            parent = parent.parent()
    
    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            if self.is_dragging:
                # 通知父窗口结束拖动
                parent = self.parent()
                while parent:
                    if isinstance(parent, PLTWindow):
                        parent.end_button_drag(self)
                        break
                    parent = parent.parent()
            self.is_dragging = False
            self.drag_start_position = None
        try:
            QtWidgets.QPushButton.mouseReleaseEvent(self, event)
        except Exception:
            pass

class PLTWindow(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(PLTWindow, self).__init__(parent)
        # 设置无边框和透明背景
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)  # 透明背景用于圆角
        self.setWindowTitle("3DsPipeLineTools (PLT工具)")
        self.drag_position = None  # 初始化拖动位置
        self.is_expanded = False  # 窗口展开状态
        self.dynamic_buttons = []  # 存储动态按钮列表
        self.button_counter = 0  # 按钮计数器
        self.dragging_button = None  # 当前拖动的按钮
        self.drag_ghost = None  # 拖动时跟随鼠标的浮窗按钮
        self.drag_offset = QtCore.QPoint(0, 0)  # 鼠标点击位置相对按钮左上角的偏移
        # 默认模式列表（type=default 不可删除/重命名，type=custom 可自定义）
        # 每个模式拥有独立的 buttons 列表，切换模式时 UI 重新加载该模式按钮
        self.modes = [
            {"name": "模型模式", "type": "default", "color": "#5d8fd4", "buttons": []},
            {"name": "绑定模式", "type": "default", "color": "#5dd48f", "buttons": []},
            {"name": "动画模式", "type": "default", "color": "#d4a85d", "buttons": []},
            {"name": "导出模式", "type": "default", "color": "#a85dd4", "buttons": []},
        ]
        self.current_mode_index = 0  # 当前激活模式索引
        # 启动默认锁定。lock 字段不持久化到个人配置：
        #   - 锁定 = 冻结【共用配置 button_config.json】写入（save_config 中共用分支短路）；
        #           个人配置 PLT_user_config.json 不受影响，仍正常写盘；
        #   - 解锁 = 主动从磁盘 reload，吸纳外部对共用配置的编辑。
        self.is_locked = True
        # 自定义模式默认配色（循环使用）
        self.custom_mode_colors = [
            "#d45d79", "#5dd4d4", "#d4d45d", "#aa55ee", "#ff8855", "#55cc99",
        ]
        # 预定义颜色列表（循环使用）
        self.button_colors = [
            "#d45d79",  # 粉红
            "#5d8fd4",  # 蓝色
            "#5dd48f",  # 绿色
            "#d4a85d",  # 橙色
            "#a85dd4",  # 紫色
            "#d4d45d",  # 黄色
            "#5dd4d4",  # 青色
        ]
        # 配置文件路径（双配置：共用 = 团队下发的 modes/buttons 模板；个人 = 当前用户的状态）
        self.config_file = os.path.join(SCRIPT_DIR, "button_config.json")
        self.user_config_file = os.path.join(USER_SCRIPTS_DIR, "PLT_user_config.json")
        # 个人侧状态：模式索引 / 锁定 / 每模式每按钮的 color_level / 拖动顺序
        # 结构：{mode_name: {"color_levels": {btn_name: int}, "button_order": [btn_name, ...]}}
        self.user_modes_state = {}
        # 布局朝向："horizontal" | "vertical"（仅影响显示，属于个人偏好）
        # 启动时先用默认值搭 UI；随后 load_config 读到个人配置里的真实值会触发重建
        self.layout_orientation = "horizontal"
        print(f"[PLT] 共用配置: {self.config_file}")
        print(f"[PLT] 个人配置: {self.user_config_file}")
        self.setup_ui()
        self.load_config()  # 加载配置
        # 配置读完后，如果磁盘里写的是 vertical 而 setup_ui 用的是默认 horizontal，
        # 需要按读到的方向重建一次 UI（仅在不一致时）
        self._ensure_orientation_applied()
    
    def setup_ui(self):
        """根据 self.layout_orientation 搭建 UI。可重复调用（切换布局时复用）"""
        is_vertical = (self.layout_orientation == "vertical")
        
        # 主布局：水平 / 垂直
        main_layout = QtWidgets.QVBoxLayout() if is_vertical else QtWidgets.QHBoxLayout()
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)
        
        # 光球按钮
        self.btn = AnimatedOrbButton()
        self.btn.setFixedSize(46, 46)
        self.btn.clicked.connect(self.on_button_clicked)
        # 水平时贴左居中；垂直时贴顶居中。伸缩动画过程中保持原位
        if is_vertical:
            main_layout.addWidget(self.btn, 0, QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)
        else:
            main_layout.addWidget(self.btn, 0, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        
        # 内容容器（朝向与主布局保持一致）
        self.content_widget = QtWidgets.QWidget()
        self.content_layout = QtWidgets.QVBoxLayout() if is_vertical else QtWidgets.QHBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(8)
        
        # 模式按钮（"新增按钮"功能已移到模式按钮右键菜单中）
        self.mode_btn = ModeButton()
        self.mode_btn.setFixedHeight(38)
        self.mode_btn.clicked.connect(self.cycle_mode)
        self.mode_btn.customContextMenuRequested.connect(self.show_mode_menu)
        if is_vertical:
            self.content_layout.addWidget(self.mode_btn, 0, QtCore.Qt.AlignHCenter)
        else:
            self.content_layout.addWidget(self.mode_btn)
        
        self.content_widget.setLayout(self.content_layout)
        self.content_widget.setVisible(False)
        if is_vertical:
            main_layout.addWidget(self.content_widget, 0, QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)
        else:
            main_layout.addWidget(self.content_widget, 0, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        # stretch 让多余空间在动画过程中推到另一端，让光球始终贴边
        main_layout.addStretch(1)
        
        self.setLayout(main_layout)
        # 初始固定 70x70（仅光球可见）
        self.resize(70, 70)
        self.setMinimumSize(70, 70)
        self.setMaximumSize(70, 70)
        
        # 初始化模式按钮外观
        self.update_mode_button()
        # 标记本次 setup_ui 实际应用的朝向，供启动期 _ensure_orientation_applied 比对
        self._applied_orientation = self.layout_orientation
    
    # ============== 模式切换相关 ==============
    def update_mode_button(self):
        """根据当前模式刷新模式按钮的文字、颜色、宽度"""
        if not self.modes:
            return
        # 防御：索引越界时回到 0
        if self.current_mode_index < 0 or self.current_mode_index >= len(self.modes):
            self.current_mode_index = 0
        mode = self.modes[self.current_mode_index]
        self.mode_btn.setText(mode["name"])
        self.mode_btn.apply_mode_color(mode["color"])
        # 根据文字宽度自适应按钮宽度
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        metrics = QtGui.QFontMetrics(font)
        if hasattr(metrics, 'horizontalAdvance'):
            text_width = metrics.horizontalAdvance(mode["name"])
        else:
            text_width = metrics.width(mode["name"])
        # 内边距(14*2) + 边框(2*2) + 一点缓冲
        btn_width = max(text_width + 36, 70)
        self.mode_btn.setFixedWidth(btn_width)
        # 如果当前是展开状态，更新窗口宽度以容纳新尺寸
        if self.is_expanded:
            self.update_expanded_width()
    
    def _serialize_button(self, btn):
        """把一个动态按钮对象序列化为可写入【共用】配置的 dict

        仅包含团队共享字段：name / script / description。
        color_level 属于个人状态，由 _collect_user_modes_state() 单独写入个人配置。
        """
        data = {
            "name": btn.text(),
        }
        script = getattr(btn, 'script_path', None)
        if script:
            data["script"] = script
        description = getattr(btn, 'description', None)
        if description:
            data["description"] = description
        return data

    def _collect_current_mode_state(self):
        """采集当前 UI 上动态按钮的【个人状态】：color_levels + button_order

        按按钮显示名 (text()) 作为 key，避免按索引漂移。
        """
        if not (0 <= self.current_mode_index < len(self.modes)):
            return None, None
        color_levels = {}
        button_order = []
        for b in self.dynamic_buttons:
            n = b.text()
            color_levels[n] = getattr(b, 'color_level', 0)
            button_order.append(n)
        return color_levels, button_order

    def _flush_current_mode_state(self):
        """把当前 UI 个人状态写入 self.user_modes_state[当前模式名]"""
        if not (0 <= self.current_mode_index < len(self.modes)):
            return
        mode_name = self.modes[self.current_mode_index]["name"]
        cl, order = self._collect_current_mode_state()
        if cl is None:
            return
        self.user_modes_state[mode_name] = {
            "color_levels": cl,
            "button_order": order,
        }

    def _render_mode_buttons(self, mode_index):
        """把指定模式的 buttons 渲染到 UI

        合并三步逻辑：
          1) 取共用 mode["buttons"] 与个人 user_modes_state[mode_name]
          2) 按个人 button_order 重排（缺失追加到尾部）
          3) 调 add_dynamic_button 创建 UI 控件，使用个人 color_levels 上色
        调用方需自行保证 UI 已被 _clear_dynamic_buttons() 清空。
        """
        if not (0 <= mode_index < len(self.modes)):
            return
        mode = self.modes[mode_index]
        per_mode = self.user_modes_state.get(mode["name"], {})
        color_levels = per_mode.get("color_levels", {}) or {}
        order = per_mode.get("button_order") or []

        by_name = {b.get("name", ""): b for b in mode.get("buttons", []) if isinstance(b, dict)}
        ordered = []
        for n in order:
            if n in by_name:
                ordered.append(by_name.pop(n))
        ordered.extend(by_name.values())

        for btn_data in ordered:
            name = btn_data.get("name", "")
            self.add_dynamic_button(
                name=name,
                color_level=color_levels.get(name, 0),
                script=btn_data.get("script"),
                description=btn_data.get("description"),
                save=False,
            )
        return len(ordered)
    
    def _check_locked(self, action_name="该操作"):
        """统一的锁定检查：仅对【共用配置】写入类操作生效，锁定时打印提示并返回 True"""
        if self.is_locked:
            print(f"[共用配置已锁定] {action_name}已被忽略，请先在模式按钮右键菜单中解锁")
            return True
        return False
    
    def _on_add_button_clicked(self):
        """模式右键菜单"新增按钮"项的回调：锁定时禁止新增（属于共用配置写入）"""
        if self._check_locked("新增按钮"):
            return
        self.add_dynamic_button()
    
    def toggle_lock(self):
        """切换【共用配置】锁定状态（在模式按钮右键菜单中调用）
        
        语义说明：
        - 锁定只针对共用配置 button_config.json（modes / buttons 的结构与命名）；
        - 个人配置 PLT_user_config.json（current_mode_index / layout_orientation /
          modes_state 等）任何时候都可正常写盘，不受此开关影响。

        切换流程：
        - 锁定 → 解锁：先关闭锁，再 _reload_from_disk()，把外部对共用配置的编辑吸纳进来；
        - 解锁 → 锁定：先用 force=True 把当前内存写到磁盘（最后一次同步），再开锁冻结。
        """
        if self.is_locked:
            # 即将解锁：从磁盘 reload，外部对共用配置的编辑会被吃进 PLT
            self.is_locked = False
            self.update_mode_button()
            self._reload_from_disk()
            print("[PLT] 已解锁共用配置，从磁盘重新加载完成（外部编辑已生效）")
        else:
            # 即将锁定：先 flush 内存到磁盘（force=True），再设置锁
            self.save_config(force=True)
            self.is_locked = True
            self.update_mode_button()
            print("[PLT] 共用配置已锁定（button_config.json 冻结；个人配置仍可正常写入）")

    def _reload_from_disk(self):
        """强制从磁盘重新加载共用 + 个人配置，丢弃任何未落盘的内存改动

        调用前不要求处于解锁状态——本身只读取磁盘，不写盘。
        会清空当前 UI 动态按钮并按磁盘内容重新渲染。
        """
        print("[PLT] 从磁盘重新加载配置...")
        self._clear_dynamic_buttons()
        # 显式清空个人状态字典，避免文件不存在时残留旧值
        self.user_modes_state = {}
        # write_back=False 防止 reload 自身又把内存写回磁盘
        self.load_config(write_back=False)
        # 磁盘里的 layout_orientation 若与当前 UI 不一致，按磁盘的重建
        self._ensure_orientation_applied()
    
    def _clear_dynamic_buttons(self):
        """从 UI 移除所有动态按钮（不影响配置数据）"""
        for b in list(self.dynamic_buttons):
            self.content_layout.removeWidget(b)
            b.deleteLater()
        self.dynamic_buttons = []
        self.button_counter = 0  # 重置颜色分配计数
    
    # ============== 布局朝向（水平 / 垂直） ==============
    def _ensure_orientation_applied(self):
        """启动期 load_config 读到磁盘里的朝向后，若与当前 UI 不一致，触发一次重建
        
        load_config 在 setup_ui 之后调用，但 setup_ui 已按默认 horizontal 搭好 UI。
        如果磁盘里写的是 vertical，需要立即把 UI 改建成 vertical。
        setup_ui 末尾会把 _applied_orientation 设为构建时的朝向，这里直接比对即可。
        """
        applied = getattr(self, '_applied_orientation', self.layout_orientation)
        if applied != self.layout_orientation:
            self._rebuild_ui_with_current_orientation(silent=True)
    
    def toggle_layout_orientation(self):
        """切换主布局朝向（水平 <-> 垂直）
        
        - 始终允许（不受 self.is_locked 影响），属于个人显示偏好；
        - 保留动态按钮的数据（name/script/description/color_level/顺序）；
        - 调用 save_config()：个人配置始终写盘，共用配置仅在未锁定时一并写盘。
        """
        new_o = "vertical" if self.layout_orientation == "horizontal" else "horizontal"
        self.layout_orientation = new_o
        self._rebuild_ui_with_current_orientation(silent=False)
        self.save_config()
        print(f"[PLT] 布局已切换为：{new_o}")
    
    def _rebuild_ui_with_current_orientation(self, silent=False):
        """按 self.layout_orientation 重建 UI；保留动态按钮数据 + 模式索引 + 展开状态
        
        silent=True：启动期复位，不打印日志、不写盘；
        silent=False：用户主动触发，正常打印 + 持久化由调用方负责
        """
        # 1) 备份动态按钮数据
        btn_snapshot = []
        for b in self.dynamic_buttons:
            btn_snapshot.append({
                "name": b.text(),
                "color_level": getattr(b, 'color_level', 0),
                "script": getattr(b, 'script_path', None),
                "description": getattr(b, 'description', ''),
            })
        # 同步个人状态（color_level / order）回内存，确保 reload 渲染走个人配置一致路径
        self._flush_current_mode_state()
        
        was_expanded = self.is_expanded
        
        # 2) 拆解旧 UI
        self._teardown_ui()
        
        # 3) 重置展开状态 + 重建
        self.is_expanded = False
        self.dynamic_buttons = []
        self.button_counter = 0
        self.setup_ui()
        self._applied_orientation = self.layout_orientation
        
        # 4) 还原动态按钮（按 snapshot 顺序）
        for d in btn_snapshot:
            self.add_dynamic_button(
                name=d["name"],
                color_level=d["color_level"],
                script=d["script"],
                description=d["description"],
                save=False,
            )
        
        # 5) 若原先展开，立即展开（无动画，免去切换时多余的过渡）
        if was_expanded:
            target_w, target_h = self.calculate_expanded_dimensions()
            self.content_widget.setVisible(True)
            self.is_expanded = True
            self.setMinimumSize(70, 70)
            self.setMaximumSize(5000, 5000)
            self.resize(target_w, target_h)
            self.on_animation_finished(target_w, target_h)
        
        if not silent:
            print(f"[PLT] UI 已按朝向 '{self.layout_orientation}' 重建")
    
    def _teardown_ui(self):
        """拆掉当前所有 child widget + 主布局，让 setup_ui 可以重新 setLayout
        
        Qt 不允许重复 setLayout，必须先把旧 layout 转移到一个临时 widget 让它带走才行。
        """
        # 删除全部 child widget（按钮、容器等），同时停掉它们的定时器
        for child in self.findChildren(QtWidgets.QWidget):
            try:
                child.setParent(None)
            except Exception:
                pass
            try:
                child.deleteLater()
            except Exception:
                pass
        # 把旧 layout 转移到一个临时 widget，self.layout() 即变成 None
        old_layout = self.layout()
        if old_layout is not None:
            try:
                QtWidgets.QWidget().setLayout(old_layout)
            except Exception:
                pass
        # 清掉对旧 widget 的引用，避免后续误用
        self.btn = None
        self.mode_btn = None
        self.content_widget = None
        self.content_layout = None
    
    def _switch_to_mode(self, new_index):
        """切换到指定模式：保存当前 UI(共用+个人) → 清空 UI → 加载新模式

        共用：把按钮 name/script/description 写回旧模式 buttons 数组
        个人：把按钮 color_level/拖动顺序写回 self.user_modes_state[旧模式名]
        新模式渲染时，按个人 button_order 重排，并按 color_levels 上色
        """
        if not (0 <= new_index < len(self.modes)):
            return
        if new_index == self.current_mode_index:
            return
        # 1) 旧模式写回（共用 + 个人）
        if 0 <= self.current_mode_index < len(self.modes):
            self.modes[self.current_mode_index]["buttons"] = [
                self._serialize_button(b) for b in self.dynamic_buttons
            ]
            self._flush_current_mode_state()
        # 2) 切换索引 + 清 UI + 加载新模式
        self.current_mode_index = new_index
        self._clear_dynamic_buttons()
        self._render_mode_buttons(new_index)
        # 3) 刷新模式按钮外观 + 写盘
        self.update_mode_button()
        self.save_config()
        print(f"已切换至: {self.modes[new_index]['name']}")
    
    def cycle_mode(self):
        """左键点击模式按钮：循环切换到下一个模式"""
        if not self.modes:
            return
        new_index = (self.current_mode_index + 1) % len(self.modes)
        self._switch_to_mode(new_index)
    
    def show_mode_menu(self, pos):
        """模式按钮右键菜单：显示所有模式 + 自定义模式管理"""
        menu = QtWidgets.QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #3a3a3a;
                border: 1px solid #555555;
                color: #e0e0e0;
            }
            QMenu::item {
                padding: 5px 25px 5px 25px;
            }
            QMenu::item:selected {
                background-color: #4a4a4a;
            }
            QMenu::separator {
                height: 1px;
                background: #555555;
                margin: 4px 8px;
            }
        """)
        
        # 列出所有模式（可勾选，当前模式打勾）—— 模式切换在锁定时仍允许（仅浏览不修改）
        for i, mode in enumerate(self.modes):
            label = mode["name"]
            if mode["type"] == "custom":
                label += "  (自定义)"
            action = menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(i == self.current_mode_index)
            action.triggered.connect(lambda checked=False, idx=i: self._switch_to_mode(idx))
        
        menu.addSeparator()
        
        # 锁定/解锁开关（始终显示在右键菜单中）
        # 锁定仅作用于共用配置 button_config.json；个人配置不受影响始终可写
        lock_action = menu.addAction("锁定共用配置（保护 button_config.json）")
        lock_action.setCheckable(True)
        lock_action.setChecked(self.is_locked)
        lock_action.triggered.connect(self.toggle_lock)
        
        # 重新加载配置（无论锁定状态都可点；不写盘，只从磁盘读）
        reload_action = menu.addAction("重新加载配置（从磁盘读取最新内容）")
        reload_action.triggered.connect(self._reload_from_disk)
        
        # 切换横/竖布局（个人显示偏好，始终允许）
        next_label = "切换为 垂直布局" if self.layout_orientation == "horizontal" else "切换为 水平布局"
        orient_action = menu.addAction(next_label)
        orient_action.triggered.connect(self.toggle_layout_orientation)
        
        # 修改类操作仅在未锁定时显示
        if not self.is_locked:
            menu.addSeparator()
            
            # 在当前模式中新增一个动态按钮（"+ 按钮"已下沉到此菜单项）
            add_btn_action = menu.addAction("新增按钮")
            add_btn_action.triggered.connect(self._on_add_button_clicked)
            
            # 新增自定义模式
            add_action = menu.addAction("新增自定义模式...")
            add_action.triggered.connect(self.add_custom_mode)
            
            # 仅当前模式为自定义时，可重命名/删除
            cur_mode = self.modes[self.current_mode_index]
            if cur_mode["type"] == "custom":
                rename_action = menu.addAction("重命名当前模式...")
                rename_action.triggered.connect(self.rename_current_mode)
                delete_action = menu.addAction("删除当前模式")
                delete_action.triggered.connect(self.delete_current_mode)
        
        menu.exec_(self.mode_btn.mapToGlobal(pos))
    
    def add_custom_mode(self):
        """新增一个自定义模式"""
        if self._check_locked("新增自定义模式"):
            return
        text, ok = QtWidgets.QInputDialog.getText(
            self, "新增自定义模式", "请输入模式名称:",
            QtWidgets.QLineEdit.Normal, ""
        )
        if not (ok and text.strip()):
            return
        # 检查重名
        name = text.strip()
        if any(m["name"] == name for m in self.modes):
            QtWidgets.QMessageBox.warning(self, "提示", f"模式名 '{name}' 已存在")
            return
        # 自定义模式按已有数量循环选取颜色
        custom_count = sum(1 for m in self.modes if m["type"] == "custom")
        color = self.custom_mode_colors[custom_count % len(self.custom_mode_colors)]
        # 新模式自带空 buttons 列表
        self.modes.append({"name": name, "type": "custom", "color": color, "buttons": []})
        # 通过 _switch_to_mode 安全切到新模式（会保存旧模式按钮、清空并加载新模式空列表）
        self._switch_to_mode(len(self.modes) - 1)
        print(f"已新增自定义模式: {name}")
    
    def rename_current_mode(self):
        """重命名当前自定义模式（默认模式不允许重命名）"""
        if self._check_locked("重命名模式"):
            return
        cur = self.modes[self.current_mode_index]
        if cur["type"] != "custom":
            QtWidgets.QMessageBox.information(self, "提示", "默认模式不可重命名")
            return
        text, ok = QtWidgets.QInputDialog.getText(
            self, "重命名模式", "请输入新名称:",
            QtWidgets.QLineEdit.Normal, cur["name"]
        )
        if not (ok and text.strip()):
            return
        name = text.strip()
        # 重名校验（排除自身）
        for i, m in enumerate(self.modes):
            if i != self.current_mode_index and m["name"] == name:
                QtWidgets.QMessageBox.warning(self, "提示", f"模式名 '{name}' 已存在")
                return
        # 同步迁移个人状态字典里的 key（旧名 → 新名）
        old_name = cur["name"]
        if old_name in self.user_modes_state and old_name != name:
            self.user_modes_state[name] = self.user_modes_state.pop(old_name)
        cur["name"] = name
        self.update_mode_button()
        self.save_config()
        print(f"模式已重命名为: {name}")
    
    def delete_current_mode(self):
        """删除当前自定义模式（同时删除该模式下所有按钮配置）"""
        if self._check_locked("删除模式"):
            return
        cur = self.modes[self.current_mode_index]
        if cur["type"] != "custom":
            QtWidgets.QMessageBox.information(self, "提示", "默认模式不可删除")
            return
        btn_count = len(cur.get("buttons", []))
        reply = QtWidgets.QMessageBox.question(
            self, "确认删除",
            f"确定要删除模式 '{cur['name']}' 吗？\n该模式下的 {btn_count} 个按钮也会被一并删除。",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return
        # 直接删除当前模式（注意：不能调用 _switch_to_mode 把 UI 写回当前模式，因为它即将被删除）
        deleted_index = self.current_mode_index
        deleted_name = self.modes[deleted_index]["name"]
        del self.modes[deleted_index]
        # 同步从个人状态字典中移除该模式的 key
        self.user_modes_state.pop(deleted_name, None)
        # 计算切换目标：优先保留原索引位置（删除后该位置指向后一个模式），越界回退
        new_target = max(0, min(deleted_index, len(self.modes) - 1))
        self.current_mode_index = new_target
        self._clear_dynamic_buttons()
        self._render_mode_buttons(new_target)
        self.update_mode_button()
        self.save_config()
    
    # ============== 其它工具方法 ==============
    def calculate_button_width(self, text):
        """根据按钮文字长度计算合适的按钮宽度"""
        # 使用与按钮样式相同的字号(10pt)测量文本宽度
        font = QtGui.QFont()
        font.setPointSize(10)
        metrics = QtGui.QFontMetrics(font)
        # Qt5.11+ 使用 horizontalAdvance，旧版本回退到 width
        if hasattr(metrics, 'horizontalAdvance'):
            text_width = metrics.horizontalAdvance(text)
        else:
            text_width = metrics.width(text)
        # 加上左右内边距 + 边框 (各10px)
        padding = 20
        # 设置最小宽度，避免名字太短的按钮过于窄小
        min_width = 38
        return max(text_width + padding, min_width)
    
    def add_dynamic_button(self, name=None, color_level=0, script=None, description=None, save=True):
        """新增一个动态按钮
        
        save=False 用于批量加载（如切换模式或读取配置时），跳过逐个写盘
        script: 关联的 .ms 脚本相对路径（相对于本文件目录），点击按钮时会执行
        description: 按钮介绍，鼠标悬停 3 秒后显示
        """
        self.button_counter += 1
        if name is None:
            name = f"未定义{self.button_counter}"
        
        new_btn = DraggableButton(name)
        # 根据按钮名字长度自适应宽度
        btn_width = self.calculate_button_width(name)
        new_btn.setFixedSize(btn_width, 38)
        
        # 为按钮分配颜色（循环使用颜色列表）
        color_index = (self.button_counter - 1) % len(self.button_colors)
        new_btn.base_color = self.button_colors[color_index]
        new_btn.color_level = color_level  # 使用传入的颜色级别
        # 关联脚本路径（用于点击执行）
        new_btn.script_path = script
        # 关联按钮介绍（悬停3秒显示）
        new_btn.description = description or ""
        
        self.update_button_color(new_btn)
        new_btn.clicked.connect(lambda: self.on_dynamic_button_clicked(new_btn))
        
        # 连接右键菜单
        new_btn.customContextMenuRequested.connect(lambda pos, btn=new_btn: self.show_button_context_menu(btn, pos))
        
        self.dynamic_buttons.append(new_btn)
        # 垂直布局下需要居中对齐，否则会左对齐贴边
        if self.layout_orientation == "vertical":
            self.content_layout.addWidget(new_btn, 0, QtCore.Qt.AlignHCenter)
        else:
            self.content_layout.addWidget(new_btn)
        
        # 如果当前是展开状态，更新窗口大小
        if self.is_expanded:
            self.update_expanded_width()
        
        # 保存配置
        if save:
            self.save_config()
    
    def show_button_context_menu(self, button, pos):
        """显示按钮右键菜单"""
        menu = QtWidgets.QMenu(self)
        menu_style = """
            QMenu {
                background-color: #3a3a3a;
                border: 1px solid #555555;
                color: #e0e0e0;
            }
            QMenu::item {
                padding: 5px 25px 5px 20px;
            }
            QMenu::item:selected {
                background-color: #4a4a4a;
            }
            QMenu::separator {
                height: 1px;
                background: #555555;
                margin: 4px 8px;
            }
        """
        menu.setStyleSheet(menu_style)
        
        # 锁定状态下只显示提示，不显示任何修改选项
        if self.is_locked:
            tip = menu.addAction("共用配置已锁定（请先在模式按钮右键解锁）")
            tip.setEnabled(False)
            menu.exec_(button.mapToGlobal(pos))
            return
        
        # 重命名
        rename_action = menu.addAction("重命名")
        rename_action.triggered.connect(lambda: self.rename_button(button))
        
        # 删除
        delete_action = menu.addAction("删除")
        delete_action.triggered.connect(lambda: self.delete_button(button))
        
        # 复制 / 移动到其它模式（仅当存在其它模式时）
        other_mode_indices = [i for i in range(len(self.modes)) if i != self.current_mode_index]
        if other_mode_indices:
            menu.addSeparator()
            
            copy_menu = menu.addMenu("复制到模式")
            copy_menu.setStyleSheet(menu_style)
            move_menu = menu.addMenu("移动到模式")
            move_menu.setStyleSheet(menu_style)
            
            for i in other_mode_indices:
                mode = self.modes[i]
                label = mode["name"]
                if mode["type"] == "custom":
                    label += "  (自定义)"
                
                copy_act = copy_menu.addAction(label)
                copy_act.triggered.connect(
                    lambda checked=False, idx=i, btn=button: self.copy_button_to_mode(btn, idx)
                )
                
                move_act = move_menu.addAction(label)
                move_act.triggered.connect(
                    lambda checked=False, idx=i, btn=button: self.move_button_to_mode(btn, idx)
                )
        
        menu.exec_(button.mapToGlobal(pos))
    
    def copy_button_to_mode(self, button, target_mode_index):
        """把按钮复制到指定模式（追加到目标模式末尾，不影响当前 UI）"""
        if self._check_locked("复制按钮到其它模式"):
            return
        if not (0 <= target_mode_index < len(self.modes)):
            return
        if target_mode_index == self.current_mode_index:
            return
        btn_data = self._serialize_button(button)
        target_mode = self.modes[target_mode_index]
        target_mode.setdefault("buttons", []).append(btn_data)
        self.save_config()
        print(f"已复制 '{button.text()}' 到 '{target_mode['name']}'")
    
    def move_button_to_mode(self, button, target_mode_index):
        """把按钮移动到指定模式（追加到目标模式 + 从当前模式删除）"""
        if self._check_locked("移动按钮到其它模式"):
            return
        if not (0 <= target_mode_index < len(self.modes)):
            return
        if target_mode_index == self.current_mode_index:
            return
        btn_data = self._serialize_button(button)
        target_mode = self.modes[target_mode_index]
        target_mode.setdefault("buttons", []).append(btn_data)
        text = button.text()
        target_name = target_mode["name"]
        # 从当前 UI 删除（delete_button 内部会调用 save_config 同步当前模式）
        self.delete_button(button)
        print(f"已移动 '{text}' 到 '{target_name}'")
    
    def rename_button(self, button):
        """重命名按钮"""
        if self._check_locked("重命名按钮"):
            return
        text, ok = QtWidgets.QInputDialog.getText(
            self, 
            "重命名按钮", 
            "请输入新名称:", 
            QtWidgets.QLineEdit.Normal, 
            button.text()
        )
        if ok and text:
            button.setText(text)
            # 重命名后根据新名字长度调整按钮宽度
            btn_width = self.calculate_button_width(text)
            button.setFixedSize(btn_width, 38)
            print(f"按钮重命名为: {text}")
            # 如果当前是展开状态，更新窗口宽度
            if self.is_expanded:
                self.update_expanded_width()
            # 保存配置
            self.save_config()
    
    def delete_button(self, button):
        """删除指定按钮"""
        if self._check_locked("删除按钮"):
            return
        if button in self.dynamic_buttons:
            self.dynamic_buttons.remove(button)
            self.content_layout.removeWidget(button)
            button.deleteLater()
            print(f"按钮 {button.text()} 已删除")
            
            # 如果当前是展开状态，更新窗口宽度
            if self.is_expanded:
                self.update_expanded_width()
            
            # 保存配置
            self.save_config()
    
    def on_dynamic_button_clicked(self, button):
        """动态按钮点击事件：执行关联脚本 + 增加颜色深度
        
        color_level 属于个人状态，不受"锁定共用配置"影响，始终累加并写入个人配置。
        """
        print(f"按钮 [{button.text()}] 被点击")
        
        # 如果按钮配置了脚本路径，则执行该 .ms 文件
        script_rel = getattr(button, 'script_path', None)
        if script_rel:
            self.run_button_script(script_rel)
        else:
            print(f"  └─ 该按钮未配置脚本路径，请确保 button_config.json 中包含 'script' 字段且已重启工具栏")
        
        # 增加颜色深度级别（视觉反馈，纯个人状态）
        button.color_level = min(button.color_level + 1, 5)
        self.update_button_color(button)
        
        # 保存配置（锁定时只会写个人，不会动共用）
        self.save_config()
    
    def run_button_script(self, script_rel):
        """执行按钮关联的 .ms 脚本（相对路径，相对于本文件所在目录）
        
        使用 MaxScript 原生字符串字面量 @"path" 调用 fileIn，
        以兼容含空格 / 反斜杠 / 中文的路径。
        """
        # 解析为绝对路径（使用模块加载时缓存的 SCRIPT_DIR）
        script_path = os.path.normpath(os.path.join(SCRIPT_DIR, script_rel))
        print(f"[按钮脚本] 准备执行: {script_path}")
        
        if not os.path.exists(script_path):
            print(f"[按钮脚本] !! 文件不存在: {script_path}")
            return
        
        try:
            import pymxs
            rt = pymxs.runtime
            # 用正斜杠避免 MaxScript 中的反斜杠转义问题
            script_path_fwd = script_path.replace('\\', '/')
            # 用 @"..." 原生字符串包裹路径，对空格 / 中文 / 特殊字符最安全
            ms_cmd = 'fileIn @"{}"'.format(script_path_fwd)
            print(f"[按钮脚本] MaxScript: {ms_cmd}")
            rt.execute(ms_cmd)
            print(f"[按钮脚本] 完成: {script_rel}")
        except ImportError:
            print(f"[按钮脚本] 非 3ds Max 环境，跳过: {script_path}")
        except Exception as e:
            import traceback
            print(f"[按钮脚本] !! 执行失败: {e}")
            traceback.print_exc()
    
    def update_button_color(self, button):
        """更新按钮颜色（根据深度级别）"""
        # 解析基础颜色
        base_color = button.base_color
        r = int(base_color[1:3], 16)
        g = int(base_color[3:5], 16)
        b = int(base_color[5:7], 16)
        
        # 反转逻辑：初始暗(0.4)，点击后逐渐变亮(1.0)
        # 级别0=40%亮度，级别5=100%亮度
        factor = 0.4 + (button.color_level * 0.12)
        r = int(r * factor)
        g = int(g * factor)
        b = int(b * factor)
        
        # 计算悬停和按下的颜色
        hover_factor = 1.15
        hover_r = min(int(r * hover_factor), 255)
        hover_g = min(int(g * hover_factor), 255)
        hover_b = min(int(b * hover_factor), 255)
        
        pressed_factor = 0.85
        pressed_r = int(r * pressed_factor)
        pressed_g = int(g * pressed_factor)
        pressed_b = int(b * pressed_factor)
        
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: rgb({r}, {g}, {b});
                border: 2px solid #666666;
                border-radius: 5px;
                color: #e0e0e0;
                font-size: 10pt;
            }}
            QPushButton:hover {{
                background-color: rgb({hover_r}, {hover_g}, {hover_b});
                border: 2px solid #777777;
            }}
            QPushButton:pressed {{
                background-color: rgb({pressed_r}, {pressed_g}, {pressed_b});
            }}
        """)
    
    def calculate_expanded_dimensions(self):
        """返回展开后的 (width, height)，按当前 layout_orientation 计算
        
        水平：高度恒为 70；宽度 = 左右边距 + 光球 + 主间隔 + 模式按钮 + N*间隔 + 各动态宽
        垂直：宽度 = max(光球/模式/动态) + 边距*2；高度 = 上下边距 + 光球 + 主间隔 + 内容高
        """
        MARGIN = 12       # main_layout contentsMargins
        SPACING = 8       # main_layout / content_layout 通用间隔
        ORB = 46
        BTN_H = 38        # 模式按钮 & 动态按钮统一高度
        
        is_vertical = (self.layout_orientation == "vertical")
        mode_width = self.mode_btn.width() if hasattr(self, 'mode_btn') and self.mode_btn else 70
        n_dyn = len(self.dynamic_buttons)
        sum_dyn_w = sum(b.width() for b in self.dynamic_buttons)
        
        if is_vertical:
            # 宽度：所有元素中最宽者 + 左右边距
            widths = [ORB, mode_width]
            widths.extend(btn.width() for btn in self.dynamic_buttons)
            target_w = max(max(widths) + 2 * MARGIN, 70)
            # 高度：上下边距 + 光球 + 主间隔 + 内容高
            # 内容高 = 模式 + N 个动态 + 中间 N 个间隔 = (1+N)*38 + N*spacing
            content_h = (1 + n_dyn) * BTN_H + n_dyn * SPACING
            target_h = max(2 * MARGIN + ORB + SPACING + content_h, 70)
            return (target_w, target_h)
        else:
            # 水平：高度恒为 70
            # content 内部布局：模式按钮 + N 个动态按钮 + 中间 N 个间隔
            content_w = mode_width + sum_dyn_w + n_dyn * SPACING
            # window = 左右边距 + 光球 + 主间隔 + content
            return (2 * MARGIN + ORB + SPACING + content_w, 70)
    
    def calculate_expanded_width(self):
        """[兼容旧名] 返回展开宽度。现在只是 calculate_expanded_dimensions() 的 [0]"""
        return self.calculate_expanded_dimensions()[0]
    
    def update_expanded_width(self):
        """动态按钮 / 模式按钮宽度变化后，同步窗口大小（仅在已展开时调用）"""
        target_w, target_h = self.calculate_expanded_dimensions()
        
        self.setMinimumSize(70, 70)
        self.setMaximumSize(5000, 5000)
        
        self.anim = QtCore.QPropertyAnimation(self, b"size")
        self.anim.setDuration(200)
        self.anim.setStartValue(self.size())
        self.anim.setEndValue(QtCore.QSize(target_w, target_h))
        self.anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self.anim.finished.connect(lambda w=target_w, h=target_h: self.on_animation_finished(w, h))
        self.anim.start()
    
    def on_button_clicked(self):
        """点击光球：展开或收回窗口"""
        if self.is_expanded:
            target_w, target_h = 70, 70
            self.is_expanded = False
            self.content_widget.setVisible(False)
        else:
            target_w, target_h = self.calculate_expanded_dimensions()
            self.is_expanded = True
            self.content_widget.setVisible(True)
        
        # 临时解除大小限制以允许动画（垂直布局时高度也要动）
        self.setMinimumSize(70, 70)
        self.setMaximumSize(5000, 5000)
        
        self.anim = QtCore.QPropertyAnimation(self, b"size")
        self.anim.setDuration(300)
        self.anim.setStartValue(self.size())
        self.anim.setEndValue(QtCore.QSize(target_w, target_h))
        self.anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self.anim.finished.connect(lambda w=target_w, h=target_h: self.on_animation_finished(w, h))
        self.anim.start()
    
    def on_animation_finished(self, width, height):
        """动画完成后固定窗口大小"""
        self.setMinimumSize(width, height)
        self.setMaximumSize(width, height)
    
    def paintEvent(self, event):
        """绘制圆角背景"""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)  # 抗锯齿
        
        # 绘制圆角矩形背景（深色）
        painter.setBrush(QtGui.QBrush(QtGui.QColor(45, 45, 45)))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 14, 14)  # 14像素圆角
    
    def mousePressEvent(self, event):
        """鼠标按下事件，记录拖动起始位置"""
        if event.button() == QtCore.Qt.LeftButton:
            # 检查是否点击在按钮上
            widget = self.childAt(event.pos())
            if widget and isinstance(widget, QtWidgets.QPushButton):
                return  # 如果点击在按钮上，不处理窗口拖动
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件，更新窗口位置"""
        if event.buttons() == QtCore.Qt.LeftButton and self.drag_position is not None:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件，结束拖动"""
        if event.button() == QtCore.Qt.LeftButton:
            self.drag_position = None
    def mouseDoubleClickEvent(self, event):
        """双击窗口空白区域关闭窗口"""
        self.close()
    def _make_drag_ghost(self, button):
        """创建跟随鼠标的浮窗按钮(ghost)"""
        ghost = QtWidgets.QPushButton(button.text())
        # 独立顶层窗口，可超出主窗口范围跟随鼠标
        ghost.setWindowFlags(
            QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.WindowStaysOnTopHint
            | QtCore.Qt.Tool
            | QtCore.Qt.WindowTransparentForInput  # 鼠标事件透传给原按钮
        )
        ghost.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        ghost.setAttribute(QtCore.Qt.WA_ShowWithoutActivating)
        ghost.setFixedSize(button.size())
        
        # 复制按钮配色（所有动态按钮均带 base_color；缺省时走兜底灰底）
        if hasattr(button, 'base_color'):
            base_color = button.base_color
            r = int(base_color[1:3], 16)
            g = int(base_color[3:5], 16)
            b = int(base_color[5:7], 16)
            factor = 0.4 + (button.color_level * 0.12)
            r = int(r * factor)
            g = int(g * factor)
            b = int(b * factor)
            ghost.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgb({r}, {g}, {b});
                    border: 2px solid #ffcc44;
                    border-radius: 5px;
                    color: #ffffff;
                    font-size: 10pt;
                    font-weight: bold;
                }}
            """)
        else:
            ghost.setStyleSheet("""
                QPushButton {
                    background-color: #5a5a5a;
                    border: 2px solid #ffcc44;
                    border-radius: 5px;
                    color: #ffffff;
                    font-size: 14pt;
                    font-weight: bold;
                }
            """)
        
        # 阴影增加"漂浮起来"的视觉感
        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QtGui.QColor(0, 0, 0, 200))
        shadow.setOffset(0, 6)
        ghost.setGraphicsEffect(shadow)
        
        ghost.setWindowOpacity(0.92)
        return ghost
    
    def _set_placeholder_style(self, button):
        """将原位置按钮设为虚线占位符样式"""
        button.setStyleSheet("""
            QPushButton {
                background-color: rgba(70, 70, 70, 120);
                border: 2px dashed #aaaaaa;
                border-radius: 5px;
                color: rgba(180, 180, 180, 80);
                font-size: 10pt;
            }
        """)
    
    def start_button_drag(self, button):
        """开始拖动按钮"""
        self.dragging_button = button
        # 记录原始索引
        button.original_index = self.content_layout.indexOf(button)
        # 记录鼠标点击位置相对按钮左上角的偏移，使ghost跟随时不会"跳变"
        if button.drag_start_position is not None:
            self.drag_offset = QtCore.QPoint(button.drag_start_position)
        else:
            self.drag_offset = QtCore.QPoint(button.width() // 2, button.height() // 2)
        
        # 创建ghost浮窗
        if self.drag_ghost is not None:
            self.drag_ghost.deleteLater()
        self.drag_ghost = self._make_drag_ghost(button)
        # 立刻定位到鼠标位置
        global_pos = QtGui.QCursor.pos()
        self.drag_ghost.move(global_pos - self.drag_offset)
        self.drag_ghost.show()
        self.drag_ghost.raise_()
        
        # 原位置按钮显示为占位符
        self._set_placeholder_style(button)
    
    def update_button_drag(self, button, x_pos, y_pos, global_pos=None):
        """更新拖动位置，并实时调整按钮顺序
        
        水平布局按 x 轴中线判断插入位置，垂直布局按 y 轴中线
        """
        if self.dragging_button != button:
            return
        
        # 1. 让ghost跟随鼠标
        if self.drag_ghost is not None:
            if global_pos is None:
                global_pos = QtGui.QCursor.pos()
            self.drag_ghost.move(global_pos - self.drag_offset)
        
        is_vertical = (self.layout_orientation == "vertical")
        pos_along = y_pos if is_vertical else x_pos
        
        # 2. 计算所有按钮的中心位置（用于判断插入位置）
        button_centers = []
        for i in range(self.content_layout.count()):
            widget = self.content_layout.itemAt(i).widget()
            if widget and widget != button:
                widget_pos = widget.pos()
                if is_vertical:
                    center_along = widget_pos.y() + widget.height() / 2
                else:
                    center_along = widget_pos.x() + widget.width() / 2
                button_centers.append((i, center_along, widget))
        
        # 找到应该插入的位置
        current_index = self.content_layout.indexOf(button)
        target_index = current_index
        
        for i, center_along, widget in button_centers:
            if pos_along < center_along and i < current_index:
                target_index = i
                break
            elif pos_along > center_along and i > current_index:
                target_index = i
        
        # 如果目标位置不同，重新排列按钮
        if target_index != current_index:
            self.content_layout.removeWidget(button)
            # 重新插入时保留 alignment（垂直布局下按钮需居中）
            if is_vertical:
                self.content_layout.insertWidget(target_index, button, 0, QtCore.Qt.AlignHCenter)
            else:
                self.content_layout.insertWidget(target_index, button)
            
            # 更新dynamic_buttons列表
            if button in self.dynamic_buttons:
                self.dynamic_buttons.remove(button)
                # 计算在dynamic_buttons中的新位置
                dynamic_index = 0
                for i in range(target_index):
                    widget = self.content_layout.itemAt(i).widget()
                    if widget in self.dynamic_buttons:
                        dynamic_index += 1
                self.dynamic_buttons.insert(dynamic_index, button)
    
    def end_button_drag(self, button):
        """结束拖动按钮"""
        if self.dragging_button != button:
            return
        
        # 动态按钮恢复到当前颜色级别（已无 + 按钮特例需要处理）
        self.update_button_color(button)
        
        # ghost 飞回按钮原位置后销毁
        if self.drag_ghost is not None:
            ghost = self.drag_ghost
            self.drag_ghost = None
            # 强制刷新布局，确保按钮pos()是最新的
            self.content_widget.adjustSize()
            QtWidgets.QApplication.processEvents()
            target_global = button.mapToGlobal(QtCore.QPoint(0, 0))
            
            self.ghost_anim = QtCore.QPropertyAnimation(ghost, b"pos")
            self.ghost_anim.setDuration(180)
            self.ghost_anim.setStartValue(ghost.pos())
            self.ghost_anim.setEndValue(target_global)
            self.ghost_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
            self.ghost_anim.finished.connect(ghost.deleteLater)
            self.ghost_anim.start()
        
        self.dragging_button = None
        
        # 拖动结束后保存配置
        self.save_config()
    
    def load_config(self, write_back=True):
        """加载共用配置（团队 modes/buttons 模板）+ 个人配置（当前模式/color_levels/拖动顺序）

        兼容多种历史格式：
        - 旧版顶层 buttons 字段 → 迁移到当前模式
        - 共用配置内残留的 color_level / current_mode_index → 一次性迁移到个人配置

        write_back=True：末尾调用一次 save_config(force=True) 把旧格式洗成新格式；
        write_back=False：仅加载，不写盘（用于"重新加载配置"的运行时刷新）。
        """
        # ============================================================
        # 1. 读共用配置
        # ============================================================
        legacy_state_in_shared = {  # 仅迁移用
            "current_mode_index": None,
            "per_mode_color_levels": {},  # {mode_name: {btn_name: level}}
        }
        config = None
        if not os.path.exists(self.config_file):
            print("[PLT] 共用配置不存在，使用默认模式 + 一个空白按钮启动")
            self.add_dynamic_button()
            self._load_user_config()
            # 首次启动写盘一次，让磁盘有可用文件（force=True 绕过启动锁定）
            if write_back:
                self.save_config(force=True)
            return
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            cfg_modes = config.get('modes')
            if isinstance(cfg_modes, list) and cfg_modes:
                valid_modes = []
                for m in cfg_modes:
                    if isinstance(m, dict) and 'name' in m and 'type' in m and 'color' in m:
                        if not isinstance(m.get("buttons"), list):
                            m["buttons"] = []
                        # 抓取该模式下按钮里残留的 color_level（旧版结构）→ 待迁移
                        cl_for_mode = {}
                        for b in m["buttons"]:
                            if isinstance(b, dict) and 'color_level' in b:
                                cl_for_mode[b.get('name', '')] = b.pop('color_level', 0)
                        if cl_for_mode:
                            legacy_state_in_shared["per_mode_color_levels"][m["name"]] = cl_for_mode
                        valid_modes.append(m)
                if valid_modes:
                    self.modes = valid_modes

            # 旧版残留：current_mode_index 写在共用文件里 → 取出待迁移
            if 'current_mode_index' in config:
                legacy_state_in_shared["current_mode_index"] = config.get('current_mode_index')

            # 旧版兼容：顶层 buttons 迁移到当前模式
            legacy_buttons = config.get('buttons')
            if isinstance(legacy_buttons, list) and legacy_buttons:
                cm_idx = legacy_state_in_shared["current_mode_index"] or 0
                if 0 <= cm_idx < len(self.modes):
                    cm = self.modes[cm_idx]
                    if not cm.get("buttons"):
                        cm["buttons"] = legacy_buttons
                        print("[PLT] 检测到旧版顶层 buttons 字段，已迁移到当前模式")
        except Exception as e:
            print(f"[PLT] 读取共用配置失败: {e}")
            self.add_dynamic_button()
            self._load_user_config()
            return

        # ============================================================
        # 2. 读个人配置
        # ============================================================
        self._load_user_config()

        # 老共用配置里发现的状态字段 → 合并进个人状态（仅当个人配置里没有时）
        # 注：is_locked 不参与迁移，每次启动均强制锁定
        if legacy_state_in_shared["current_mode_index"] is not None and not os.path.exists(self.user_config_file):
            self.current_mode_index = legacy_state_in_shared["current_mode_index"]
        for mode_name, cls in legacy_state_in_shared["per_mode_color_levels"].items():
            slot = self.user_modes_state.setdefault(mode_name, {"color_levels": {}, "button_order": []})
            for k, v in cls.items():
                slot["color_levels"].setdefault(k, v)

        # ============================================================
        # 3. 修正 current_mode_index 边界，刷新模式按钮
        # ============================================================
        if self.current_mode_index < 0 or self.current_mode_index >= len(self.modes):
            self.current_mode_index = 0
        self.update_mode_button()

        # ============================================================
        # 4. 加载当前模式按钮到 UI（应用个人 color_level 与 button_order）
        # ============================================================
        loaded_count = self._render_mode_buttons(self.current_mode_index) or 0
        cur_mode_name = self.modes[self.current_mode_index]["name"]
        print(
            f"[PLT] 已加载 {len(self.modes)} 个模式，当前模式 '{cur_mode_name}' "
            f"含 {loaded_count} 个按钮 / 锁定={self.is_locked}"
        )

        # 启动期把旧格式洗到新格式：force=True 绕过锁定。运行时 reload 时跳过本步。
        if write_back:
            self.save_config(force=True)

    def _load_user_config(self):
        """单独从个人配置文件读取个性化状态；缺失则使用默认值"""
        try:
            if not os.path.exists(self.user_config_file):
                print(f"[PLT] 个人配置不存在，将首次写入: {self.user_config_file}")
                return
            with open(self.user_config_file, 'r', encoding='utf-8') as f:
                user_cfg = json.load(f)
            self.current_mode_index = int(user_cfg.get('current_mode_index', self.current_mode_index))
            # locked 字段刻意不再读取：每次启动均强制锁定，由用户主动解锁后再操作
            # 布局朝向：默认 horizontal；其它值视为非法回退
            ori = user_cfg.get('layout_orientation', self.layout_orientation)
            if ori in ('horizontal', 'vertical'):
                self.layout_orientation = ori
            ms = user_cfg.get('modes_state')
            if isinstance(ms, dict):
                cleaned = {}
                for k, v in ms.items():
                    if not isinstance(v, dict):
                        continue
                    cleaned[k] = {
                        "color_levels": v.get("color_levels", {}) if isinstance(v.get("color_levels"), dict) else {},
                        "button_order": v.get("button_order", []) if isinstance(v.get("button_order"), list) else [],
                    }
                self.user_modes_state = cleaned
        except Exception as e:
            print(f"[PLT] 读取个人配置失败: {e}（将使用默认值）")
    
    def save_config(self, force=False):
        """保存配置。锁定语义仅作用于共用配置；个人配置始终写盘。

        共用：modes 结构 + 每模式的 buttons[name/script/description]（团队共享模板）
              - 锁定状态下跳过写盘（保护外部编辑），除非 force=True；
        个人：current_mode_index / layout_orientation / modes_state（color_levels 与 button_order）
              - 任何状态下都立即写盘（个人偏好不参与锁定保护）；

        force=True 仅供启动期一次性迁移与解锁过渡使用，会同时强制写共用配置。
        """
        # 1) 把当前 UI 同步回 self.modes 的 buttons（仅共用字段，仅内存）
        #    即使共用磁盘写盘被锁定也要做：保证内存状态一致，解锁后能正确落盘
        if 0 <= self.current_mode_index < len(self.modes):
            self.modes[self.current_mode_index]["buttons"] = [
                self._serialize_button(b) for b in self.dynamic_buttons
            ]
        # 2) 把当前 UI 的个人状态同步回 self.user_modes_state[当前模式]
        self._flush_current_mode_state()

        # ----- 写共用配置（受锁定保护）-----
        shared_written = False
        if (not self.is_locked) or force:
            shared_payload = {
                'modes': self.modes,
            }
            try:
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(shared_payload, f, ensure_ascii=False, indent=4)
                shared_written = True
            except Exception as e:
                print(f"[PLT] 保存共用配置失败: {e}")

        # ----- 写个人配置（始终允许，不受锁定保护）-----
        # 仅保留 self.modes 里实际存在的模式的 state，避免长期残留
        # 注：locked 字段刻意不写入（启动总是锁定，无需持久化）
        valid_mode_names = {m["name"] for m in self.modes}
        cleaned_state = {
            k: v for k, v in self.user_modes_state.items() if k in valid_mode_names
        }
        user_payload = {
            'current_mode_index': self.current_mode_index,
            'layout_orientation': self.layout_orientation,
            'modes_state': cleaned_state,
        }
        try:
            os.makedirs(os.path.dirname(self.user_config_file), exist_ok=True)
            with open(self.user_config_file, 'w', encoding='utf-8') as f:
                json.dump(user_payload, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"[PLT] 保存个人配置失败: {e}")

        cur_name = (
            self.modes[self.current_mode_index]['name']
            if 0 <= self.current_mode_index < len(self.modes) else 'N/A'
        )
        if shared_written:
            print(
                f"[PLT] 配置已保存：共用 {len(self.modes)} 模式 / 个人 模式='{cur_name}'"
            )
        else:
            print(
                f"[PLT] 个人配置已保存：模式='{cur_name}'（共用配置被锁定，跳过共用写盘）"
            )
    
    def closeEvent(self, event):
        """窗口关闭时保存配置（重载场景下可跳过，避免覆盖磁盘上的新配置）"""
        if not getattr(self, '_skip_save_on_close', False):
            self.save_config()
        # 注意：脚本被 python.executeFile 重载时 PLTWindow 类会被重新定义，
        # 旧实例对 super(PLTWindow, self) 中的 PLTWindow 不再匹配，会报 TypeError。
        # 直接调用基类方法（基类来自 PySide2 模块不会被重定义）规避此问题。
        try:
            QtWidgets.QDialog.closeEvent(self, event)
        except Exception:
            pass

# 显示UI
def show_ui():
    global ui_instance
    try:
        old = ui_instance
    except NameError:
        old = None
    
    if old is not None:
        # 重载脚本时不要让旧 UI 把"内存里的状态"写回磁盘
        try:
            old._skip_save_on_close = True
        except Exception:
            pass
        
        # ============== 重要：给旧实例打猴子补丁 ==============
        # executeFile 重新执行后，模块里的 PLTWindow / AnimatedOrbButton 等类全部被重定义。
        # 旧实例的事件方法体中 super(类名, self) 会查找模块全局名 → 拿到新类 → self 不是新类的实例
        #   → TypeError: super(type, obj): obj must be an instance or subtype of type
        # 这里在 close() 之前，把可能调用 super 的事件处理器全部覆盖为安全 no-op
        _safe_noop = lambda e: (e.accept() if hasattr(e, 'accept') else None)
        for attr in ('closeEvent', 'hideEvent', 'showEvent', 'enterEvent', 'leaveEvent'):
            try:
                setattr(old, attr, _safe_noop)
            except Exception:
                pass
        # 同样处理所有子控件（光球按钮、模式按钮、动态按钮等也有事件 super 调用）
        try:
            for child in old.findChildren(QtWidgets.QWidget):
                for attr in ('hideEvent', 'showEvent', 'enterEvent', 'leaveEvent'):
                    try:
                        setattr(child, attr, _safe_noop)
                    except Exception:
                        pass
        except Exception:
            pass
        # 关闭并销毁旧实例
        try:
            old.close()
        except Exception:
            pass
        try:
            old.deleteLater()
        except Exception:
            pass
    
    ui_instance = PLTWindow()
    ui_instance.show()

# 运行
show_ui()
