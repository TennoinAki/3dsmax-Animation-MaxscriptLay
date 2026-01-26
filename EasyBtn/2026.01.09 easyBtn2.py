# -*- coding: utf-8 -*-
"""
简单单按钮UI界面
"""
from PySide2 import QtWidgets, QtCore, QtGui
import json
import os

# MaxScript集成模块
class MaxScriptHelper:
    """MaxScript辅助类，用于Python调用MaxScript函数"""
    def __init__(self):
        self.mxs = None
        self.functions = None
        self.initialized = False
        self.init_maxscript()
    
    def init_maxscript(self):
        """初始化MaxScript模块"""
        try:
            from pymxs import runtime as mxs
            self.mxs = mxs
            
            # 加载maxscript.ms文件
            script_dir = os.path.dirname(__file__)
            script_path = os.path.join(script_dir, "maxscript.ms").replace("\\", "/")
            
            if os.path.exists(script_path):
                self.mxs.fileIn(script_path)
                self.functions = self.mxs.EasyBtnFunctions
                self.initialized = True
                print(f"MaxScript函数库已加载: {script_path}")
            else:
                print(f"警告: maxscript.ms文件不存在: {script_path}")
        except ImportError:
            print("警告: pymxs模块未找到，MaxScript功能不可用")
        except Exception as e:
            print(f"初始化MaxScript失败: {e}")
    
    def call(self, func_name, *args, **kwargs):
        """调用MaxScript函数"""
        if not self.initialized or self.functions is None:
            print("MaxScript未初始化或函数库未加载")
            return None
        
        try:
            # 获取函数
            func = getattr(self.functions, func_name, None)
            if func is None:
                print(f"函数 {func_name} 不存在")
                return None
            
            # 调用函数
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            print(f"调用MaxScript函数 {func_name} 失败: {e}")
            return None
    
    def test_connection(self):
        """测试MaxScript连接"""
        result = self.call("testFunction", "Hello from Python!")
        if result:
            print(f"测试成功: {result}")
            return True
        return False

# 创建全局MaxScript辅助实例
ms_helper = MaxScriptHelper()

class DraggableButton(QtWidgets.QPushButton):
    """可拖动的按钮类"""
    def __init__(self, text, parent=None):
        super(DraggableButton, self).__init__(text, parent)
        self.drag_start_position = None
        self.is_dragging = False
        self.original_index = -1
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
    
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.drag_start_position = event.pos()
            self.is_dragging = False
        super(DraggableButton, self).mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if not (event.buttons() & QtCore.Qt.LeftButton):
            return
        if self.drag_start_position is None:
            return
        if (event.pos() - self.drag_start_position).manhattanLength() < QtWidgets.QApplication.startDragDistance():
            return
        
        if not self.is_dragging:
            self.is_dragging = True
            # 通知父窗口开始拖动
            parent = self.parent()
            while parent:
                if isinstance(parent, SimpleUI):
                    parent.start_button_drag(self)
                    break
                parent = parent.parent()
        
        # 通知父窗口更新拖动位置
        parent = self.parent()
        while parent:
            if isinstance(parent, SimpleUI):
                # 转换为全局坐标再转换为父容器坐标
                global_pos = self.mapToGlobal(event.pos())
                parent_pos = parent.content_widget.mapFromGlobal(global_pos)
                parent.update_button_drag(self, parent_pos.x())
                break
            parent = parent.parent()
    
    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            if self.is_dragging:
                # 通知父窗口结束拖动
                parent = self.parent()
                while parent:
                    if isinstance(parent, SimpleUI):
                        parent.end_button_drag(self)
                        break
                    parent = parent.parent()
            self.is_dragging = False
            self.drag_start_position = None
        super(DraggableButton, self).mouseReleaseEvent(event)

class SimpleUI(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(SimpleUI, self).__init__(parent)
        # 设置无边框和透明背景
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)  # 透明背景用于圆角
        self.setWindowTitle("简单按钮界面")
        self.drag_position = None  # 初始化拖动位置
        self.is_expanded = False  # 窗口展开状态
        self.dynamic_buttons = []  # 存储动态按钮列表
        self.button_counter = 0  # 按钮计数器
        self.dragging_button = None  # 当前拖动的按钮
        self.button_positions = []  # 按钮位置列表
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
        # 配置文件路径
        self.config_file = os.path.join(os.path.dirname(__file__), "button_config.json")
        self.setup_ui()
        self.load_config()  # 加载配置
    
    def setup_ui(self):
        # 主水平布局
        main_layout = QtWidgets.QHBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # 左侧圆形按钮
        self.btn = QtWidgets.QPushButton("")
        self.btn.setFixedSize(50, 50)  # 宽50，高50
        self.btn.clicked.connect(self.on_button_clicked)
        
        # 设置圆形按钮样式
        self.btn.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a;
                border: 2px solid #555555;
                border-radius: 25px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                border: 2px solid #666666;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
        """)
        
        main_layout.addWidget(self.btn)
        
        # 右侧内容容器（水平布局）
        self.content_widget = QtWidgets.QWidget()
        self.content_layout = QtWidgets.QHBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(10)
        
        # 添加按钮
        self.add_btn = DraggableButton("+")
        self.add_btn.setFixedSize(50, 50)
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a4a4a;
                border: 2px solid #666666;
                border-radius: 5px;
                color: #e0e0e0;
                font-size: 16pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
                border: 2px solid #777777;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
        """)
        self.add_btn.clicked.connect(self.add_dynamic_button)
        self.content_layout.addWidget(self.add_btn)
        
        # 不再添加默认按钮，改由load_config处理
        
        self.content_widget.setLayout(self.content_layout)
        self.content_widget.setVisible(False)  # 初始隐藏
        main_layout.addWidget(self.content_widget)
        
        self.setLayout(main_layout)
        # 设置窗口初始大小为80*80
        self.resize(80, 80)
        self.setMinimumSize(80, 80)
        self.setMaximumSize(80, 80)
    
    def add_dynamic_button(self, name=None, color_level=0, script_function=None):
        """新增一个动态按钮"""
        self.button_counter += 1
        if name is None:
            name = f"未定义{self.button_counter}"
        
        new_btn = DraggableButton(name)
        new_btn.setFixedSize(70, 50)
        
        # 为按钮分配颜色（循环使用颜色列表）
        color_index = (self.button_counter - 1) % len(self.button_colors)
        new_btn.base_color = self.button_colors[color_index]
        new_btn.color_level = color_level  # 使用传入的颜色级别
        new_btn.script_function = script_function  # 绑定的MaxScript函数
        
        # 设置提示文本
        if script_function:
            new_btn.setToolTip(f"绑定函数: {script_function}")
        else:
            new_btn.setToolTip("未绑定函数")
        
        self.update_button_color(new_btn)
        new_btn.clicked.connect(lambda: self.on_dynamic_button_clicked(new_btn))
        
        # 连接右键菜单
        new_btn.customContextMenuRequested.connect(lambda pos, btn=new_btn: self.show_button_context_menu(btn, pos))
        
        self.dynamic_buttons.append(new_btn)
        self.content_layout.addWidget(new_btn)
        
        # 如果当前是展开状态，更新窗口宽度
        if self.is_expanded:
            self.update_expanded_width()
        
        # 保存配置
        self.save_config()
    
    def show_button_context_menu(self, button, pos):
        """显示按钮右键菜单"""
        menu = QtWidgets.QMenu(self)
        
        # 设置菜单样式
        menu.setStyleSheet("""
            QMenu {
                background-color: #3a3a3a;
                border: 1px solid #555555;
                color: #e0e0e0;
            }
            QMenu::item {
                padding: 5px 20px;
            }
            QMenu::item:selected {
                background-color: #4a4a4a;
            }
        """)
        
        # 重命名选项
        rename_action = menu.addAction("重命名")
        rename_action.triggered.connect(lambda: self.rename_button(button))
        
        # 绑定脚本函数选项
        bind_script_action = menu.addAction("绑定MaxScript函数")
        bind_script_action.triggered.connect(lambda: self.bind_script_function(button))
        
        # 测试函数选项（如果已绑定）
        if hasattr(button, 'script_function') and button.script_function:
            test_action = menu.addAction(f"执行: {button.script_function}")
            test_action.triggered.connect(lambda: self.execute_script_function(button))
        
        # 删除选项
        menu.addSeparator()
        delete_action = menu.addAction("删除")
        delete_action.triggered.connect(lambda: self.delete_button(button))
        
        # 显示菜单
        menu.exec_(button.mapToGlobal(pos))
    
    def rename_button(self, button):
        """重命名按钮"""
        text, ok = QtWidgets.QInputDialog.getText(
            self, 
            "重命名按钮", 
            "请输入新名称:", 
            QtWidgets.QLineEdit.Normal, 
            button.text()
        )
        if ok and text:
            button.setText(text)
            # 保持tooltip显示绑定的函数信息
            if hasattr(button, 'script_function') and button.script_function:
                button.setToolTip(f"绑定函数: {button.script_function}")
            else:
                button.setToolTip("未绑定函数")
            print(f"按钮重命名为: {text}")
            # 保存配置
            self.save_config()
    
    def bind_script_function(self, button):
        """为按钮绑定MaxScript函数"""
        # 从MaxScript获取可用的函数列表
        available_functions = []
        
        if ms_helper.initialized:
            try:
                # 调用MaxScript函数获取函数列表
                func_list = ms_helper.call("getAvailableFunctions")
                if func_list:
                    # 转换为Python可用的格式
                    for item in func_list:
                        func_name = str(item[0])
                        func_desc = str(item[1])
                        available_functions.append(f"{func_name} - {func_desc}")
            except Exception as e:
                print(f"获取函数列表失败: {e}")
        
        # 如果无法从MaxScript获取，使用默认列表
        if not available_functions:
            available_functions = [
                "testFunction - 测试函数",
                "getSelectedNames - 获取选中物体名称",
                "getSelectedCount - 获取选中物体数量",
                "selectAll - 选择所有物体",
                "clearSelection - 清空选择",
                "createBox - 创建盒子",
                "createSphere - 创建球体",
                "deleteSelected - 删除选中物体",
                "getAllObjectNames - 获取所有物体名称",
                "getTimeRange - 获取时间轴范围",
                "getCurrentTime - 获取当前时间",
                "getSceneStats - 获取场景统计信息",
                "showMessage - 显示消息框",
            ]
        
        text, ok = QtWidgets.QInputDialog.getItem(
            self,
            "绑定MaxScript函数",
            "选择要绑定的函数:",
            available_functions,
            0,
            False
        )
        
        if ok and text:
            # 提取函数名（去掉描述）
            func_name = text.split(" - ")[0]
            button.script_function = func_name
            # 将按钮名称替换为函数名
            button.setText(func_name)
            # 更新提示文本
            button.setToolTip(f"绑定函数: {func_name}")
            print(f"按钮已绑定函数并重命名为: {func_name}")
            # 保存配置
            self.save_config()
    
    def execute_script_function(self, button):
        """执行按钮绑定的MaxScript函数"""
        if not hasattr(button, 'script_function') or not button.script_function:
            print("按钮未绑定任何函数")
            return
        
        func_name = button.script_function
        print(f"执行MaxScript函数: {func_name}")
        
        try:
            result = ms_helper.call(func_name)
            if result is not None:
                # 根据结果类型显示不同的消息
                if isinstance(result, (list, tuple)):
                    result_str = ", ".join(str(item) for item in result)
                    print(f"函数 {func_name} 返回: [{result_str}]")
                else:
                    print(f"函数 {func_name} 返回: {result}")
        except Exception as e:
            print(f"执行函数 {func_name} 时出错: {e}")
    
    def delete_button(self, button):
        """删除指定按钮"""
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
        """动态按钮点击事件，增加颜色深度或执行绑定的函数"""
        print(f"按钮 {button.text()} 被点击")
        
        # 如果绑定了脚本函数，执行它
        if hasattr(button, 'script_function') and button.script_function:
            self.execute_script_function(button)
        
        # 增加颜色深度级别
        button.color_level = min(button.color_level + 1, 5)
        self.update_button_color(button)
        
        # 保存配置
        self.save_config()
    
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
    
    def remove_dynamic_button(self):
        """删除最后一个动态按钮"""
        if self.dynamic_buttons:
            btn = self.dynamic_buttons.pop()
            self.content_layout.removeWidget(btn)
            btn.deleteLater()
            
            # 如果当前是展开状态，更新窗口宽度
            if self.is_expanded:
                self.update_expanded_width()
    
    def handle_button_drop(self, target_btn, source_btn):
        """处理按钮拖放，交换两个按钮的位置"""
        if target_btn == source_btn:
            return
        
        # 获取所有按钮在布局中的索引
        target_index = self.content_layout.indexOf(target_btn)
        source_index = self.content_layout.indexOf(source_btn)
        
        if target_index == -1 or source_index == -1:
            return
        
        # 从布局中移除两个按钮
        self.content_layout.removeWidget(target_btn)
        self.content_layout.removeWidget(source_btn)
        
        # 交换在dynamic_buttons列表中的位置（如果都在列表中）
        if source_btn in self.dynamic_buttons and target_btn in self.dynamic_buttons:
            src_list_idx = self.dynamic_buttons.index(source_btn)
            tgt_list_idx = self.dynamic_buttons.index(target_btn)
            self.dynamic_buttons[src_list_idx], self.dynamic_buttons[tgt_list_idx] = \
                self.dynamic_buttons[tgt_list_idx], self.dynamic_buttons[src_list_idx]
        
        # 重新插入到布局中（交换位置）
        if source_index < target_index:
            self.content_layout.insertWidget(source_index, target_btn)
            self.content_layout.insertWidget(target_index, source_btn)
        else:
            self.content_layout.insertWidget(target_index, source_btn)
            self.content_layout.insertWidget(source_index, target_btn)
    
    def calculate_expanded_width(self):
        """计算展开后的宽度"""
        # 基础宽度：左边圆形按钮(50) + 边距(15*2) + 间隔(10)
        base_width = 50 + 30 + 10
        # 新增按钮：50 + 间隔(10)
        control_width = 50 + 10
        # 动态按钮：70 * 数量 + 间隔(10 * 数量)
        dynamic_width = (70 + 10) * len(self.dynamic_buttons)
        
        return base_width + control_width + dynamic_width
    
    def update_expanded_width(self):
        """更新展开状态的窗口宽度"""
        target_width = self.calculate_expanded_width()
        
        # 临时解除大小限制
        self.setMinimumSize(80, 80)
        self.setMaximumSize(5000, 80)
        
        # 创建宽度动画
        self.anim = QtCore.QPropertyAnimation(self, b"size")
        self.anim.setDuration(200)
        self.anim.setStartValue(self.size())
        self.anim.setEndValue(QtCore.QSize(target_width, 80))
        self.anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self.anim.finished.connect(lambda: self.on_animation_finished(target_width))
        self.anim.start()
    
    def on_button_clicked(self):
        """点击按钮展开或收回窗口"""
        if self.is_expanded:
            # 收回窗口
            target_width = 80
            self.is_expanded = False
            # 隐藏内容
            self.content_widget.setVisible(False)
        else:
            # 展开窗口
            target_width = self.calculate_expanded_width()
            self.is_expanded = True
            # 显示内容
            self.content_widget.setVisible(True)
        
        # 临时解除大小限制以允许动画
        self.setMinimumSize(80, 80)
        self.setMaximumSize(5000, 80)  # Qt最大宽度
        
        # 创建宽度动画
        self.anim = QtCore.QPropertyAnimation(self, b"size")
        self.anim.setDuration(300)  # 动画时长300毫秒
        self.anim.setStartValue(self.size())
        self.anim.setEndValue(QtCore.QSize(target_width, 80))
        self.anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self.anim.finished.connect(lambda: self.on_animation_finished(target_width))
        self.anim.start()
    
    def on_animation_finished(self, width):
        """动画完成后固定窗口大小"""
        self.setMinimumSize(width, 80)
        self.setMaximumSize(width, 80)
    
    def paintEvent(self, event):
        """绘制圆角背景"""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)  # 抗锯齿
        
        # 绘制圆角矩形背景（深色）
        painter.setBrush(QtGui.QBrush(QtGui.QColor(45, 45, 45)))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 15, 15)  # 15像素圆角
    
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
    def start_button_drag(self, button):
        """开始拖动按钮"""
        self.dragging_button = button
        # 记录原始索引
        button.original_index = self.content_layout.indexOf(button)
        # 设置拖动时的样式
        button.setStyleSheet(button.styleSheet() + """
            QPushButton {
                opacity: 0.7;
                border: 2px solid #888888 !important;
            }
        """)
    
    def update_button_drag(self, button, x_pos):
        """更新拖动位置，并实时调整按钮顺序"""
        if self.dragging_button != button:
            return
        
        # 计算所有按钮的中心位置
        button_centers = []
        for i in range(self.content_layout.count()):
            widget = self.content_layout.itemAt(i).widget()
            if widget and widget != button:
                widget_pos = widget.pos()
                center_x = widget_pos.x() + widget.width() / 2
                button_centers.append((i, center_x, widget))
        
        # 找到应该插入的位置
        current_index = self.content_layout.indexOf(button)
        target_index = current_index
        
        for i, center_x, widget in button_centers:
            if x_pos < center_x and i < current_index:
                target_index = i
                break
            elif x_pos > center_x and i > current_index:
                target_index = i
        
        # 如果目标位置不同，重新排列按钮
        if target_index != current_index:
            self.content_layout.removeWidget(button)
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
        
        # 恢复按钮样式
        if button == self.add_btn:
            button.setStyleSheet("""
                QPushButton {
                    background-color: #4a4a4a;
                    border: 2px solid #666666;
                    border-radius: 5px;
                    color: #e0e0e0;
                    font-size: 16pt;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #5a5a5a;
                    border: 2px solid #777777;
                }
                QPushButton:pressed {
                    background-color: #3a3a3a;
                }
            """)
        else:
            # 动态按钮，恢复到当前颜色级别
            self.update_button_color(button)
        
        self.dragging_button = None
        
        # 拖动结束后保存配置
        self.save_config()
    
    def load_config(self):
        """从配置文件加载按钮"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    buttons = config.get('buttons', [])
                    
                    # 加载每个按钮
                    for btn_data in buttons:
                        self.add_dynamic_button(
                            name=btn_data.get('name', f'未定义{self.button_counter + 1}'),
                            color_level=btn_data.get('color_level', 0),
                            script_function=btn_data.get('script_function', None)
                        )
                    print(f"已加载 {len(buttons)} 个按钮配置")
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                # 如果加载失败，添加一个默认按钮
                self.add_dynamic_button()
        else:
            # 配置文件不存在，创建默认按钮
            print("配置文件不存在，创建默认按钮")
            self.add_dynamic_button()
    
    def save_config(self):
        """保存按钮配置到文件"""
        config = {
            'buttons': []
        }
        
        # 保存所有动态按钮的信息
        for btn in self.dynamic_buttons:
            btn_config = {
                'name': btn.text(),
                'color_level': btn.color_level
            }
            # 保存绑定的脚本函数（如果有）
            if hasattr(btn, 'script_function') and btn.script_function:
                btn_config['script_function'] = btn.script_function
            config['buttons'].append(btn_config)
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            print(f"配置已保存: {len(self.dynamic_buttons)} 个按钮")
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
    def closeEvent(self, event):
        """窗口关闭时保存配置"""
        self.save_config()
        QtWidgets.QDialog.closeEvent(self, event)

# 显示UI
def show_ui():
    global ui_instance
    try:
        ui_instance.close()
    except:
        pass
    ui_instance = SimpleUI()
    ui_instance.show()

# 运行
show_ui()
