/*
    简化版单向反应管理器
    作者:Tennoin
    时间:2026.02.05
*/
/*
    功能描述:
    简化版的骨骼动画转反应管理器，只支持单一方向的映射
    
    主要功能:
    1. 自动记录第0帧作为基准
    2. 点击按钮记录当前帧的骨骼变换
    3. 计算与第0帧的相对位置和旋转差异（局部空间）
    4. 按骨骼层级深度排序（从父到子）
    5. 创建单向滑条控制器
    6. 自动创建反应管理器系统并按层级顺序应用
    
    工作流程:
    1. 选中需要控制的骨骼对象（支持多个）
    2. 在第0帧确保骨骼在基准pose
    3. 跳转到目标帧（如第10帧）
    4. 点击"创建单向反应管理"按钮
    5. 系统自动按层级深度排序并创建反应器
    6. 自动完成所有位移和旋转的反应设置
    
    技术特点:
    - 使用局部变换计算，确保层级关系正确
    - 按骨骼深度排序，避免父子依赖问题
    - 自动处理位置和旋转的反应器
    - 单向滑条范围 0-10
*/

try(destroydialog 简化版单向反应管理器)catch()

rollout 简化版单向反应管理器 "简化版单向反应管理器" width:400 height:300
(
	label 'lblInstruction1' "说明：" pos:[20,20] width:360 height:20 align:#left
	label 'lblInstruction2' "1. 在第0帧选中骨骼" pos:[20,40] width:360 height:20 align:#left
	label 'lblInstruction3' "2. 跳转到目标帧" pos:[20,60] width:360 height:20 align:#left
	label 'lblInstruction4' "3. 点击下方按钮创建" pos:[20,80] width:360 height:20 align:#left
	
	button 'btnCreate' "创建单向反应管理" pos:[50,120] width:300 height:80 align:#left
	
	label 'lblStatus' "" pos:[20,220] width:360 height:60 align:#left
	
	-- 全局变量
	local selectedBones = #()
	local baseBoneTransforms = #()
	local targetTransforms = #()
	local mixSlider = undefined
	
	-- 获取骨骼局部变换函数
	fn getBoneLocalTransform bone = (
		local localTM = if bone.parent != undefined then 
			(bone.transform * (inverse bone.parent.transform))
		else
			bone.transform
		
		return #(bone.name, localTM.translation, (localTM.rotation as eulerAngles), localTM.scale)
	)
	
	-- 计算骨骼层级深度函数（从根到当前骨骼的距离）
	fn getBoneDepth bone = (
		local depth = 0
		local currentNode = bone
		
		-- 向上遍历直到根节点
		while currentNode.parent != undefined do (
			depth += 1
			currentNode = currentNode.parent
		)
		
		return depth
	)
	
	-- 记录骨骼变换并按层级排序的函数
	fn recordBoneTransformsWithDepth bones = (
		local currentFrame = currentTime as integer / ticksperframe as integer
		
		-- 记录当前帧的变换数据
		local targetTransforms = #()
		for bone in bones do (
			append targetTransforms (getBoneLocalTransform bone)
		)
		
		-- 跳转到第0帧记录基准数据
		sliderTime = 0
		local baseBoneTransforms = #()
		for bone in bones do (
			append baseBoneTransforms (getBoneLocalTransform bone)
		)
		
		-- 计算变化并添加层级信息
		local transformChanges = #()
		for i = 1 to bones.count do (
			local bone = bones[i]
			local baseData = baseBoneTransforms[i]
			local targetData = targetTransforms[i]
			local boneDepth = getBoneDepth bone
			
			local posChange = targetData[2] - baseData[2]
			-- 旋转变化：目标旋转减去基准旋转
			local rotChange = eulerAngles (targetData[3].x - baseData[3].x) (targetData[3].y - baseData[3].y) (targetData[3].z - baseData[3].z)
			
			-- 返回数据：#(骨骼名称, 位置变化, 旋转变化, 层级深度)
			append transformChanges #(baseData[1], posChange, rotChange, boneDepth)
			
			print ("骨骼: " + baseData[1] + " | 层级深度: " + boneDepth as string)
			print ("  位置变化: " + posChange as string)
			print ("  旋转变化: " + rotChange as string)
		)
		
		-- 按层级深度排序（从小到大，即从父骨骼到子骨骼）
		qsort transformChanges (fn compareFn a b = (
			if a[4] < b[4] then -1 
			else if a[4] > b[4] then 1 
			else 0
		))
		
		print ("\n===== 按层级深度排序后 =====\n")
		for changeData in transformChanges do (
			print ("骨骼: " + changeData[1] + " | 层级: " + changeData[4] as string)
		)
		
		-- 返回到原来的帧
		sliderTime = currentFrame * ticksPerFrame
		
		return transformChanges
	)
	
	-- 创建简单滑条控制器
	fn CreateSimpleSlider = (
		local sliderSize = 10
		
		-- 创建基座
		local sbase = rectangle()
		sbase.width = sliderSize
		sbase.length = sliderSize * 2  -- 单向，长度为2倍
		sbase.wireColor = yellow
		
		-- 创建滑块
		local s = donut()
		s.radius1 = 0.1
		s.radius2 = sliderSize / 4
		s.wireColor = red
		
		-- 冻结滑块变换
		s.rotation.controller = Euler_Xyz()
		s.rotation.controller = Rotation_list()
		s.rotation.controller.available.controller = Euler_xyz()
		s.rotation.controller.setname 1 "Frozen Rotation"
		s.rotation.controller.setname 2 "Zero Euler XYZ"
		s.rotation.controller.SetActive 2
		
		s.position.controller = Bezier_Position()
		s.position.controller = position_list()
		s.position.controller.available.controller = Position_XYZ()
		s.position.controller.setname 1 "Frozen Position"
		s.position.controller.setname 2 "Zero Pos XYZ"
		s.position.controller.SetActive 2
		s.Position.controller[2].x_Position = 0
		s.Position.controller[2].y_Position = 0
		s.Position.controller[2].z_Position = 0
		
		s.parent = sbase
		setTransformLockFlags s (#{1..9} - #{2})  -- 只允许Y轴移动
		
		-- 设置Y轴控制器限制
		local subaniY = s[#transform][#position][2][#Y_position]
		local ncY = Float_Limit()
		ncY.lower_limit = 0
		ncY.upper_limit = sliderSize
		subaniY.controller = ncY
		
		-- 创建指示矩形
		local rect = rectangle()
		rect.parent = sbase
		rect.length = sliderSize
		rect.wireColor = yellow
		rect.pivot.y = -sliderSize / 2
		rect.pos.y = 0
		
		-- 连接宽度与Y位置
		paramWire.connect subaniY rect.baseObject[#width] ("Y_位置/2+0.1")
		
		-- 定位滑条
		sbase.pos.x = 12
		sbase.pos.y = 0
		sbase.pos.z = 22
		rotate sbase (angleaxis 90 [1, 0, 0])
		
		return s  -- 返回滑块对象
	)
	
	-- 获取目标控制器
	fn getTargetController targetObject = (
		try (
			return targetObject.pos.controller.Zero_Pos_XYZ.controller.Y_Position.controller
		) catch (
			targetObject.pos.controller = Position_XYZ()
			return targetObject.pos.controller.Y_Position.controller
		)
	)
	
	-- 创建位移反应控制器
	fn createPositionReactor boneName targetController = (
		local node = getNodeByName boneName
		if classof node.position.controller != Position_List do (
			node.position.controller = Position_List()
		)
		local reactor = node.position.controller.available.controller = position_reactor()
		reactTo reactor targetController
		return reactor
	)
	
	-- 创建旋转反应控制器
	fn createRotationReactor boneName targetController = (
		local node = getNodeByName boneName
		if classof node.rotation.controller != Rotation_List do (
			node.rotation.controller = Rotation_List()
		)
		local reactor = node.rotation.controller.available.controller = rotation_reactor()
		reactTo reactor targetController
		return reactor
	)
	
	-- 设置位移反应状态
	fn setPositionReaction targetObject boneName posChange = (
		local node = getNodeByName boneName
		local posListController = node.position.controller
		
		-- 找到最新的 position_reactor
		local reactorController = undefined
		for idx = posListController.count to 1 by -1 do (
			if isKindOf posListController[idx] position_reactor then (
				reactorController = posListController[idx]
				exit
			)
		)
		
		if reactorController != undefined then (
			-- 移动到最大位置创建反应
			move targetObject [0,0,10]
			createReaction reactorController
			setReactionState reactorController 2 posChange
			-- 移回原位
			move targetObject [0,0,-10]
		)
	)
	
	-- 设置旋转反应状态
	fn setRotationReaction targetObject boneName rotChange = (
		local node = getNodeByName boneName
		local rotListController = node.rotation.controller
		
		-- 找到最新的 rotation_reactor
		local reactorController = undefined
		for idx = rotListController.count to 1 by -1 do (
			if isKindOf rotListController[idx] rotation_reactor then (
				reactorController = rotListController[idx]
				exit
			)
		)
		
		if reactorController != undefined then (
			local quatRotation = rotChange as quat
			-- 移动到最大位置创建反应
			move targetObject [0,0,10]
			createReaction reactorController
			setReactionState reactorController 2 quatRotation
			-- 移回原位
			move targetObject [0,0,-10]
		)
	)
	
	-- 主按钮事件
	on btnCreate pressed do
	(
		-- 检查是否有选中的骨骼
		if selection.count == 0 then (
			lblStatus.text = "错误：请先选中骨骼对象！"
			messageBox "请先选中需要控制的骨骼对象！" title:"错误"
			return false
		)
		
		-- 记录当前帧
		local currentFrame = currentTime as integer / ticksperframe as integer
		if currentFrame == 0 then (
			lblStatus.text = "错误：请先跳转到目标帧（不能是第0帧）！"
			messageBox "请先跳转到目标帧（例如第10帧）！" title:"错误"
			return false
		)
		
		lblStatus.text = "正在处理...\n当前帧: " + currentFrame as string
		
		-- 收集选中的骨骼
		selectedBones = #()
		for obj in selection do (
			if classof obj == BoneGeometry do (
				append selectedBones obj
			)
		)
		
		if selectedBones.count == 0 then (
			lblStatus.text = "错误：选中的对象中没有骨骼！"
			messageBox "选中的对象中没有骨骼！请选择BoneGeometry对象。" title:"错误"
			return false
		)
		
		print ("===== 开始创建单向反应管理器 =====")
		print ("选中骨骼数量: " + selectedBones.count as string)
		print ("当前帧: " + currentFrame as string)
		
		-- 使用新函数记录骨骼变换并按层级排序
		local transformChanges = recordBoneTransformsWithDepth selectedBones
		
		-- 创建滑条
		print ("\n创建滑条控制器...")
		mixSlider = CreateSimpleSlider()
		
		if mixSlider != undefined then (
			local targetController = getTargetController mixSlider
			
			-- 为每个骨骼创建反应控制器（按层级深度顺序）
			print ("\n创建反应控制器（按层级深度顺序）...")
			for changeData in transformChanges do (
				local boneName = changeData[1]
				local boneDepth = changeData[4]
				
				print ("处理骨骼: " + boneName + " | 层级: " + boneDepth as string)
				
				-- 创建位移反应器
				createPositionReactor boneName targetController
				-- 创建旋转反应器
				createRotationReactor boneName targetController
			)
			
			-- 设置反应状态（按层级深度顺序）
			print ("\n设置反应状态（按层级深度顺序）...")
			for changeData in transformChanges do (
				local boneName = changeData[1]
				local posChange = changeData[2]
				local rotChange = changeData[3]
				local boneDepth = changeData[4]
				
				print ("应用变化: " + boneName + " | 层级: " + boneDepth as string)
				
				-- 设置位移反应
				setPositionReaction mixSlider boneName posChange
				-- 设置旋转反应
				setRotationReaction mixSlider boneName rotChange
			)
			
			lblStatus.text = "成功！\n已为 " + selectedBones.count as string + " 个骨骼创建反应管理器"
			messageBox ("成功创建单向反应管理器！\n处理骨骼数: " + selectedBones.count as string) title:"完成"
			print ("===== 创建完成 =====")
		)
		else (
			lblStatus.text = "错误：滑条创建失败！"
			messageBox "滑条控制器创建失败！" title:"错误"
		)
	)
)

-- 创建界面
createDialog 简化版单向反应管理器
