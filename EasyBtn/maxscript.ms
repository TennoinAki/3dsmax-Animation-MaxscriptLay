-- -*- coding: utf-8 -*-
--==============================================================================
-- EasyBtn MaxScript 函数库
-- 用于提供Python调用的MaxScript功能函数
--==============================================================================

-- 全局结构体，用于组织所有函数
global EasyBtnFunctions
struct EasyBtnFunctions_Struct
(
    -- 获取可用函数列表（供UI绑定使用）
    fn getAvailableFunctions =
    (
        #(
            #("testFunction", "测试函数"),
            #("getSelectedNames", "获取选中物体名称"),
            #("getSelectedCount", "获取选中物体数量"),
            #("selectAll", "选择所有物体"),
            #("clearSelection", "清空选择"),
            #("createBox", "创建盒子"),
            #("createSphere", "创建球体"),
            #("deleteSelected", "删除选中物体"),
            #("getAllObjectNames", "获取所有物体名称"),
            #("getTimeRange", "获取时间轴范围"),
            #("getCurrentTime", "获取当前时间"),
            #("setCurrentTime", "设置当前时间"),
            #("getSceneStats", "获取场景统计信息"),
            #("showMessage", "显示消息框"),
            #("setPositionKey", "设置位置关键帧"),
            #("setRotationKey", "设置旋转关键帧"),
            #("setScaleKey", "设置缩放关键帧")
        )
    ),
    
    -- 测试函数：返回一个简单的消息
    fn testFunction msg:"Hello from MaxScript" =
    (
        local result = "MaxScript says: " + msg
        format "% \n" result
        result
    ),
    
    -- 获取选中物体的名称列表
    fn getSelectedNames =
    (
        local names = #()
        for obj in selection do
        (
            append names obj.name
        )
        if names.count == 0 then
            #("没有选中任何物体")
        else
            names
    ),
    
    -- 获取选中物体的数量
    fn getSelectedCount =
    (
        selection.count
    ),
    
    -- 选择所有物体
    fn selectAll =
    (
        select objects
        format "已选中 % 个物体\n" objects.count
        objects.count
    ),
    
    -- 清空选择
    fn clearSelection =
    (
        clearSelection()
        format "已清空选择\n"
        true
    ),
    
    -- 创建一个盒子
    fn createBox name:"MyBox" length:50 width:50 height:50 =
    (
        local newBox = Box length:length width:width height:height name:name
        format "创建了盒子: %\n" name
        newBox
    ),
    
    -- 创建一个球体
    fn createSphere name:"MySphere" radius:25 =
    (
        local newSphere = Sphere radius:radius name:name
        format "创建了球体: %\n" name
        newSphere
    ),
    
    -- 删除选中的物体
    fn deleteSelected =
    (
        local count = selection.count
        if count > 0 then
        (
            delete selection
            format "已删除 % 个物体\n" count
        )
        else
        (
            format "没有选中任何物体\n"
        )
        count
    ),
    
    -- 设置物体的位置
    fn setPosition objName pos:#(0,0,0) =
    (
        local obj = getNodeByName objName
        if obj != undefined then
        (
            obj.pos = pos
            format "设置物体 % 的位置为 %\n" objName pos
            true
        )
        else
        (
            format "未找到物体: %\n" objName
            false
        )
    ),
    
    -- 设置物体的旋转
    fn setRotation objName rot:#(0,0,0) =
    (
        local obj = getNodeByName objName
        if obj != undefined then
        (
            obj.rotation = (eulerAngles rot.x rot.y rot.z)
            format "设置物体 % 的旋转为 %\n" objName rot
            true
        )
        else
        (
            format "未找到物体: %\n" objName
            false
        )
    ),
    
    -- 设置物体的缩放
    fn setScale objName scale:#(1,1,1) =
    (
        local obj = getNodeByName objName
        if obj != undefined then
        (
            obj.scale = scale
            format "设置物体 % 的缩放为 %\n" objName scale
            true
        )
        else
        (
            format "未找到物体: %\n" objName
            false
        )
    ),
    
    -- 获取场景中所有物体的名称
    fn getAllObjectNames =
    (
        local names = #()
        for obj in objects do
        (
            append names obj.name
        )
        names
    ),
    
    -- 获取当前时间轴范围
    fn getTimeRange =
    (
        #(animationRange.start.frame, animationRange.end.frame)
    ),
    
    -- 设置时间轴范围
    fn setTimeRange startFrame:0 endFrame:100 =
    (
        animationRange = interval startFrame endFrame
        format "设置时间轴范围: % 到 %\n" startFrame endFrame
        true
    ),
    
    -- 获取当前时间（帧）
    fn getCurrentTime =
    (
        currentTime.frame as integer
    ),
    
    -- 设置当前时间（帧）
    fn setCurrentTime frame:0 =
    (
        sliderTime = frame
        format "设置当前时间为第 % 帧\n" frame
        true
    ),
    
    -- 在当前帧设置位置关键帧
    fn setPositionKey objName =
    (
        local obj = getNodeByName objName
        if obj != undefined then
        (
            with animate on
            (
                at time currentTime
                (
                    obj.pos = obj.pos  -- 设置关键帧
                )
            )
            format "在第 % 帧为物体 % 设置了位置关键帧\n" currentTime.frame objName
            true
        )
        else
        (
            format "未找到物体: %\n" objName
            false
        )
    ),
    
    -- 在当前帧设置旋转关键帧
    fn setRotationKey objName =
    (
        local obj = getNodeByName objName
        if obj != undefined then
        (
            with animate on
            (
                at time currentTime
                (
                    obj.rotation = obj.rotation  -- 设置关键帧
                )
            )
            format "在第 % 帧为物体 % 设置了旋转关键帧\n" currentTime.frame objName
            true
        )
        else
        (
            format "未找到物体: %\n" objName
            false
        )
    ),
    
    -- 在当前帧设置缩放关键帧
    fn setScaleKey objName =
    (
        local obj = getNodeByName objName
        if obj != undefined then
        (
            with animate on
            (
                at time currentTime
                (
                    obj.scale = obj.scale  -- 设置关键帧
                )
            )
            format "在第 % 帧为物体 % 设置了缩放关键帧\n" currentTime.frame objName
            true
        )
        else
        (
            format "未找到物体: %\n" objName
            false
        )
    ),
    
    -- 获取场景统计信息
    fn getSceneStats =
    (
        #(
            #("物体数量", objects.count),
            #("几何体数量", geometry.count),
            #("灯光数量", lights.count),
            #("摄像机数量", cameras.count),
            #("辅助物体数量", helpers.count)
        )
    ),
    
    -- 保存场景
    fn saveScene filename:"" =
    (
        try
        (
            if filename != "" then
                saveMaxFile filename
            else
                saveMaxFile maxFileName
            format "场景已保存\n"
            true
        )
        catch
        (
            format "保存场景失败: %\n" (getCurrentException())
            false
        )
    ),
    
    -- 自定义消息框
    fn showMessage msg title:"提示" =
    (
        messageBox msg title:title
        true
    ),
    
    -- 打印信息到监听器
    fn printInfo msg =
    (
        format "Info: %\n" msg
        true
    )
)

-- 创建全局实例
EasyBtnFunctions = EasyBtnFunctions_Struct()

-- 打印加载信息
format "\n==============================================\n"
format "EasyBtn MaxScript 函数库已加载\n"
format "使用方法: python.execute(\"EasyBtnFunctions.functionName()\")\n"
format "==============================================\n\n"

-- 返回函数库实例（供Python调用）
EasyBtnFunctions
