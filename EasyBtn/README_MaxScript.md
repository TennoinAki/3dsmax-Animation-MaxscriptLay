# EasyBtn - MaxScript函数集成说明

## 文件说明

### 1. maxscript.ms
这是MaxScript函数库文件，包含了可以被Python调用的各种MaxScript函数。

**主要功能：**
- 物体选择和管理
- 物体创建（盒子、球体等）
- 变换操作（位置、旋转、缩放）
- 动画关键帧设置
- 场景信息获取
- 时间轴控制

### 2. 2026.01.09 easyBtn2.py
这是主UI程序，现在集成了MaxScript调用功能。

## 使用方法

### 在3ds Max中运行

1. **确保pymxs模块可用**
   - 3ds Max 2020及以上版本自带pymxs模块

2. **运行Python脚本**
   ```python
   # 在3ds Max的Python监听器中执行
   exec(open(r"d:\3dsmaxScript\GitHub\3dsmax-Animation-MaxscriptLay\EasyBtn\2026.01.09 easyBtn2.py", encoding="utf-8").read())
   ```

3. **UI操作**
   - 点击圆形按钮展开/收起工具栏
   - 点击"+"按钮添加新按钮
   - 右键点击按钮弹出菜单：
     - **重命名**：修改按钮名称
     - **绑定MaxScript函数**：选择要绑定的函数
     - **执行**：手动执行绑定的函数
     - **删除**：删除该按钮
   - 左键点击按钮：
     - 执行绑定的MaxScript函数（如果已绑定）
     - 增加按钮颜色亮度

### MaxScript函数列表

#### 基础函数
- `testFunction` - 测试函数，返回消息
- `printInfo` - 打印信息到监听器

#### 选择操作
- `getSelectedNames` - 获取选中物体的名称列表
- `getSelectedCount` - 获取选中物体的数量
- `selectAll` - 选择所有物体
- `clearSelection` - 清空选择

#### 物体创建
- `createBox` - 创建盒子
  - 参数：name, length, width, height
- `createSphere` - 创建球体
  - 参数：name, radius

#### 物体操作
- `deleteSelected` - 删除选中的物体
- `setPosition` - 设置物体位置
  - 参数：objName, pos
- `setRotation` - 设置物体旋转
  - 参数：objName, rot
- `setScale` - 设置物体缩放
  - 参数：objName, scale

#### 场景信息
- `getAllObjectNames` - 获取场景中所有物体名称
- `getSceneStats` - 获取场景统计信息

#### 时间轴控制
- `getTimeRange` - 获取时间轴范围
- `setTimeRange` - 设置时间轴范围
- `getCurrentTime` - 获取当前时间（帧）
- `setCurrentTime` - 设置当前时间（帧）

#### 动画关键帧
- `setPositionKey` - 在当前帧设置位置关键帧
- `setRotationKey` - 在当前帧设置旋转关键帧
- `setScaleKey` - 在当前帧设置缩放关键帧

#### 其他
- `saveScene` - 保存场景
- `showMessage` - 显示消息框

## Python代码中调用MaxScript函数

如果你想在Python代码中直接调用MaxScript函数，可以使用以下方法：

```python
from pymxs import runtime as mxs

# 加载maxscript.ms
mxs.fileIn(r"d:\3dsmaxScript\GitHub\3dsmax-Animation-MaxscriptLay\EasyBtn\maxscript.ms")

# 调用函数
result = mxs.EasyBtnFunctions.testFunction("Hello!")
print(result)

# 获取选中物体
names = mxs.EasyBtnFunctions.getSelectedNames()
print(names)

# 创建盒子
mxs.EasyBtnFunctions.createBox(name="MyBox", length=100, width=100, height=100)
```

## 添加自定义函数

在maxscript.ms文件中添加新函数：

```maxscript
-- 在EasyBtnFunctions_Struct结构体中添加
fn myCustomFunction param1 param2 =
(
    -- 你的代码
    local result = param1 + param2
    format "结果: %\n" result
    result
),
```

然后在easyBtn2.py的`bind_script_function`方法中添加函数到列表：

```python
available_functions = [
    # ...其他函数
    "myCustomFunction - 我的自定义函数",
]
```

## 配置文件

按钮配置保存在 `button_config.json` 文件中，包含：
- 按钮名称
- 颜色级别
- 绑定的脚本函数

## 注意事项

1. MaxScript函数只能在3ds Max环境中运行
2. 确保maxscript.ms文件与Python脚本在同一目录
3. 如果pymxs模块不可用，MaxScript功能将被禁用，但UI仍可正常使用
4. 函数执行结果会打印到3ds Max的监听器窗口

## 故障排除

**问题：MaxScript未初始化**
- 检查是否在3ds Max中运行
- 检查pymxs模块是否可用
- 检查maxscript.ms文件路径是否正确

**问题：函数执行失败**
- 检查监听器窗口的错误信息
- 确认函数参数是否正确
- 确认场景状态是否满足函数要求（如选择物体）
