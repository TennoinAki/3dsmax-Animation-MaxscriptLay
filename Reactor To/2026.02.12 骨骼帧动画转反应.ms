/*
	骨骼动画转反应管理器
	作者:Tennoin
	创建时间:2025.08.18
	最后修改:2026.02.12
	版本:2.1
	
	功能描述:
	- 将骨骼动画转换为反应管理器系统
	- 支持位移、旋转、缩放三种变换类型
	- 支持四方向控制(上下左右)
	- 自动创建滑条控制器
	
	支持对象类型:
	- 骨骼(BoneGeometry)
	- 样条线(SplineShape)
*/


try(destroydialog 骨骼动画转反应管理器)catch()

rollout 骨骼动画转反应管理器 "骨骼动画转反应管理器" width:800 height:700
(
	-- 左侧：骨骼列表区域
	groupBox 'grpBones' "骨骼管理" pos:[10,10] width:280 height:430 align:#left
	button 'btnGetBones' "获取选中骨骼" pos:[20,30] width:120 height:35 align:#left toolTip:"选中骨骼后点击记录基准帧"
	button 'btnClearBones' "清空列表" pos:[145,30] width:80 height:35 align:#left toolTip:"清空骨骼列表"
	button 'btnSelectBones' "选中列表骨骼" pos:[230,30] width:50 height:35 align:#left toolTip:"选中列表中的骨骼对象"
	listBox 'lbxBoneList' "" pos:[20,75] width:260 height:29 align:#left
	
	-- 右侧上部：方向数据记录区域
	groupBox 'grpDirections' "方向数据记录" pos:[300,10] width:490 height:270 align:#left
	
	label 'lblUp' "上方向:" pos:[320,40] width:60 height:20 align:#left
	button 'btnUp' "记录上" pos:[385,35] width:80 height:30 align:#left toolTip:"跳转到目标帧后点击记录"
	editText 'edtUpFrame' "" pos:[470,35] width:150 height:25 align:#left readOnly:true
	button 'btnClearUp' "×" pos:[625,35] width:30 height:30 align:#left toolTip:"清空上方向数据"
	progressBar 'pbUp' pos:[660,40] width:120 height:20 color:green align:#left
	
	label 'lblDown' "下方向:" pos:[320,85] width:60 height:20 align:#left
	button 'btnDown' "记录下" pos:[385,80] width:80 height:30 align:#left
	editText 'edtDownFrame' "" pos:[470,80] width:150 height:25 align:#left readOnly:true
	button 'btnClearDown' "×" pos:[625,80] width:30 height:30 align:#left toolTip:"清空下方向数据"
	progressBar 'pbDown' pos:[660,85] width:120 height:20 color:green align:#left
	
	label 'lblLeft' "左方向:" pos:[320,130] width:60 height:20 align:#left
	button 'btnLeft' "记录左" pos:[385,125] width:80 height:30 align:#left
	editText 'edtLeftFrame' "" pos:[470,125] width:150 height:25 align:#left readOnly:true
	button 'btnClearLeft' "×" pos:[625,125] width:30 height:30 align:#left toolTip:"清空左方向数据"
	progressBar 'pbLeft' pos:[660,130] width:120 height:20 color:green align:#left
	
	label 'lblRight' "右方向:" pos:[320,175] width:60 height:20 align:#left
	button 'btnRight' "记录右" pos:[385,170] width:80 height:30 align:#left
	editText 'edtRightFrame' "" pos:[470,170] width:150 height:25 align:#left readOnly:true
	button 'btnClearRight' "×" pos:[625,170] width:30 height:30 align:#left toolTip:"清空右方向数据"
	progressBar 'pbRight' pos:[660,175] width:120 height:20 color:green align:#left
	
	label 'lblInfo' "提示：先获取骨骼列表，跳转到不同帧记录各方向数据" pos:[320,220] width:450 height:20 align:#left
	label 'lblInfo2' "支持类型：骨骼(BoneGeometry) / 样条线(SplineShape)" pos:[320,245] width:450 height:20 align:#left
	
	-- 右侧中部：变换类型选择
	groupBox 'grpTransform' "变换类型" pos:[300,290] width:490 height:70 align:#left
	checkBox 'chk_position' "位移 (Position)" pos:[330,315] width:120 height:25 align:#left checked:true
	checkBox 'chk_rotation' "旋转 (Rotation)" pos:[470,315] width:120 height:25 align:#left checked:true
	checkBox 'chk_scale' "缩放 (Scale)" pos:[610,315] width:120 height:25 align:#left checked:false
	
	-- 右侧下部：创建按钮
	groupBox 'grpCreate' "创建反应系统" pos:[300,370] width:490 height:70 align:#left
	button 'btnCreateReaction' "生成反应管理器" pos:[320,395] width:450 height:35 align:#left toolTip:"根据记录的数据创建反应系统"
	
	-- 底部：日志区域
	groupBox 'grpLog' "操作日志" pos:[10,450] width:780 height:230 align:#left
	editText 'edtLog' "" pos:[20,470] width:760 height:200 align:#left readOnly:true
	button 'btnClearLog' "清除日志" pos:[680,650] width:100 height:30 align:#left toolTip:"清除所有日志内容"
	
	local selectedBones = #()
	local baseBoneTransforms = #()
	local upTransforms = #()
	local downTransforms = #()
	local leftTransforms = #()
	local rightTransforms = #()
	local mixSlider = undefined
	local logText = ""

	-- 日志函数
	fn addLog txt = (
		logText += txt + "\n"
		edtLog.text = logText
	)

	-- 更新进度条
	fn updateProgressBars = (
		pbUp.value = if upTransforms.count > 0 then 100 else 0
		pbDown.value = if downTransforms.count > 0 then 100 else 0
		pbLeft.value = if leftTransforms.count > 0 then 100 else 0
		pbRight.value = if rightTransforms.count > 0 then 100 else 0
	)

	-- 获取目标控制器
	fn getTargetController targetObject axis = (
		try (
			case axis of (
				1: targetObject.pos.controller.Zero_Pos_XYZ.controller.X_Position.controller
				2: targetObject.pos.controller.Zero_Pos_XYZ.controller.Y_Position.controller
				default: undefined
			)
		) catch (
			targetObject.pos.controller = Position_XYZ()
			case axis of (
				1: targetObject.pos.controller.X_Position.controller
				2: targetObject.pos.controller.Y_Position.controller
				default: undefined
			)
		)
	)

	-- 通用：创建反应控制器并建立关联 transformType: #position | #rotation | #scale
	fn createReactorControllers targetObject boneNames axis transformType = (
		local hasData = if axis == 2 then (upTransforms.count > 0 or downTransforms.count > 0)
						else (leftTransforms.count > 0 or rightTransforms.count > 0)
		if not hasData do return undefined

		local targetController = getTargetController targetObject axis
		if targetController == undefined do return undefined

		local reactors = for name in boneNames collect (
			local node = getNodeByName name
			case transformType of (
				#position: (
					if classof node.position.controller != Position_List do node.position.controller = Position_List()
					node.position.controller.available.controller = position_reactor()
				)
				#rotation: (
					if classof node.rotation.controller != Rotation_List do node.rotation.controller = Rotation_List()
					node.rotation.controller.available.controller = rotation_reactor()
				)
				#scale: (
					if classof node.scale.controller != Scale_List do node.scale.controller = Scale_List()
					node.scale.controller.available.controller = scale_reactor()
				)
			)
		)
		for reactor in reactors where reactor != undefined do reactTo reactor targetController
		reactors
	)

	-- 冻结变换
	fn FreezeTransform CurObj = (
		suspendEditing which:#motion
		CurObj.rotation.controller = Euler_Xyz()
		CurObj.rotation.controller = Rotation_list()
		CurObj.rotation.controller.available.controller = Euler_xyz()
		CurObj.rotation.controller.setname 1 "Frozen Rotation"
		CurObj.rotation.controller.setname 2 "Zero Euler XYZ"
		CurObj.rotation.controller.SetActive 2

		CurObj.position.controller = Bezier_Position()
		CurObj.position.controller = position_list()
		CurObj.position.controller.available.controller = Position_XYZ()
		CurObj.position.controller.setname 1 "Frozen Position"
		CurObj.position.controller.setname 2 "Zero Pos XYZ"
		CurObj.position.controller.SetActive 2

		CurObj.Position.controller[2].x_Position = 0
		CurObj.Position.controller[2].y_Position = 0
		CurObj.Position.controller[2].z_Position = 0
		resumeEditing which:#motion
	)

	-- 创建滑条
	fn CreateMixSlider = (
		-- 检查并关闭自动关键帧
		if animButtonState then (
			animButtonState = false
			addLog "✓ 已自动关闭自动关键帧"
		)
		
		local sz = 10
		local cpBase = yellow
		local cpSlider = red
		local hasUp = upTransforms.count > 0
		local hasDown = downTransforms.count > 0
		local hasLeft = leftTransforms.count > 0
		local hasRight = rightTransforms.count > 0

		if not (hasUp or hasDown or hasLeft or hasRight) do return undefined

		sbase = rectangle width:sz length:sz wireColor:cpBase
		s = donut radius1:0.1 radius2:(sz/4) wireColor:cpSlider
		FreezeTransform s
		s.parent = sbase
		setTransformLockFlags s (#{1..9} - #{1, 2})

		local subaniX = s[#transform][#position][2][#X_position]
		local subaniY = s[#transform][#position][2][#Y_position]
		local ncX = Float_Limit upper_limit:0 lower_limit:0
		local ncY = Float_Limit upper_limit:0 lower_limit:0
		subaniX.controller = ncX
		subaniY.controller = ncY

		fn makeWing sbase sz cpBase dir = (
			local rect = rectangle parent:sbase length:sz wireColor:cpBase
			rect.pivot.y = -sz / 2
			rect.pos.y = 0
			if dir != 0 do rotate rect (angleaxis dir [0,0,1])
			rect
		)

		if hasUp do (
			local r = makeWing sbase sz cpBase 0
			ncY.upper_limit = sz
			paramWire.connect subaniY r.baseObject[#width] "Y_位置/2+0.1"
			sbase.length = sz * 2
		)
		if hasDown do (
			local r = makeWing sbase sz cpBase 180
			ncY.lower_limit = -sz
			paramWire.connect subaniY r.baseObject[#width] "Y_位置/-2+0.1"
			sbase.length = sz * 2
		)
		if hasLeft do (
			local r = makeWing sbase sz cpBase 90
			ncX.lower_limit = -sz
			paramWire.connect subaniX r.baseObject[#width] "X_位置/-2+0.1"
			sbase.width = sz * 2
		)
		if hasRight do (
			local r = makeWing sbase sz cpBase -90
			ncX.upper_limit = sz
			paramWire.connect subaniX r.baseObject[#width] "X_位置/2+0.1"
			sbase.width = sz * 2
		)

		sbase.pos = [14, 0, 170]
		rotate sbase (angleaxis 90 [1,0,0])
		s
	)

	-- 获取骨骼层级深度
	fn getBoneDepth bone = (
		local depth = 0
		local cur = bone
		while cur.parent != undefined do (depth += 1; cur = cur.parent)
		depth
	)

	-- 获取骨骼局部变换
	fn getBoneLocalTransform b = (
		local tm = b.transform
		if b.parent != undefined do tm = b.transform * (inverse b.parent.transform)
		#(b.name, tm.translation, tm.rotation as eulerAngles, tm.scale)
	)

	-- 获取当前帧变换变化（按层级排序）
	fn getBoneTransformsWithChange bones baseData =
	(
		local targets = for b in bones collect getBoneLocalTransform b
		local changes = #()
		for i = 1 to bones.count do (
			local bd = baseData[i]
			local td = targets[i]
			local depth = getBoneDepth bones[i]
			local posC = td[2] - bd[2]
			local rotC = eulerAngles (td[3].x - bd[3].x) (td[3].y - bd[3].y) (td[3].z - bd[3].z)
			local scaC = td[4]
			append changes #(bd[1], bd[2], bd[3], bd[4], posC, rotC, scaC, depth)
		)
		qsort changes (fn cmp a b = if a[8]<b[8] then -1 else if a[8]>b[8] then 1 else 0)
		changes
	)

	-- 通用：设置反应状态 transformType: #position | #rotation | #scale
	fn setReactionStates targetObject transformsData isPositive axis stateIndex transformType =
	(
		local posCtrl = targetObject.pos.controller[2]
		local offsetVal = 10.0

		local val = if isPositive then offsetVal else -offsetVal
		if axis == 2 then posCtrl.Y_Position = val else posCtrl.X_Position = val

		for boneData in transformsData do (
			local boneNode = getNodeByName boneData[1]
			local listCtrl = case transformType of (
				#position: boneNode.position.controller
				#rotation: boneNode.rotation.controller
				#scale:    boneNode.scale.controller
			)
			local reactorClass = case transformType of (
				#position: position_reactor
				#rotation: rotation_reactor
				#scale:    scale_reactor
			)

			local reactor = undefined
			for idx = listCtrl.count to 1 by -1 do (
				if isKindOf listCtrl[idx] reactorClass do (reactor = listCtrl[idx]; exit)
			)

			local stateVal = case transformType of (
				#position: boneData[5]
				#rotation: (boneData[6] as quat)
				#scale:    boneData[7]
			)
			createReaction reactor
			setReactionState reactor stateIndex stateVal
		)

		if axis == 2 then posCtrl.Y_Position = 0 else posCtrl.X_Position = 0
	)

		-- 获取骨骼列表
		on btnGetBones pressed do (
			selectedBones = #()
			baseBoneTransforms = #()
			local boneNames = #()
			local skippedBones = #()
			sliderTime = 0

			for obj in selection where (classof obj == BoneGeometry or classof obj == SplineShape) do (
				-- 检查是否有父级
				if obj.parent == undefined then (
					append skippedBones obj.name
				) else (
					append selectedBones obj
					append boneNames obj.name
					append baseBoneTransforms (getBoneLocalTransform obj)
				)
			)

			-- 显示跳过的骨骼信息
			if skippedBones.count > 0 then (
				local skippedMsg = "以下骨骼没有父级,已跳过:\n" + (skippedBones as string) + "\n\n"
				skippedMsg += "提示: 请为这些骨骼添加父级对象后再添加到列表中。\n"
				if boneNames.count > 0 do skippedMsg += "其它骨骼已正常添加到列表中。"
				messageBox skippedMsg title:"跳过无父级骨骼"
				addLog ("⚠ 跳过 " + skippedBones.count as string + " 个无父级骨骼: " + (skippedBones as string))
			)

			if boneNames.count > 0 then (
				lbxBoneList.items = boneNames
				addLog ("✓ 找到 " + boneNames.count as string + " 个骨骼,已记录第0帧基准")
			) else (
				lbxBoneList.items = #("未选中任何骨骼")
				addLog "✗ 未选中任何骨骼对象"
			)
			updateProgressBars()
		)


	-- 清空骨骼列表
	on btnClearBones pressed do (
		selectedBones = #()
		baseBoneTransforms = #()
		upTransforms = #()
		downTransforms = #()
		leftTransforms = #()
		rightTransforms = #()
		lbxBoneList.items = #()
		edtUpFrame.text = ""
		edtDownFrame.text = ""
		edtLeftFrame.text = ""
		edtRightFrame.text = ""
		updateProgressBars()
		addLog "✓ 已清空所有数据"
	)

	-- 选中列表骨骼
	on btnSelectBones pressed do (
		if selectedBones.count == 0 do (addLog "✗ 骨骼列表为空"; return undefined)
		clearSelection()
		for bone in selectedBones where isValidNode bone do selectMore bone
		addLog ("✓ 已选中 " + selectedBones.count as string + " 个骨骼")
	)

	-- 方向记录通用处理
	fn recordDirection &transforms edtFrame dirName = (
		
		-- 使用骨骼列表中的骨骼，不依赖当前选择
		local validBones = for bone in selectedBones where isValidNode bone collect bone
		if validBones.count == 0 do (addLog "✗ 骨骼列表中的对象无效"; return undefined)
		
		transforms = getBoneTransformsWithChange validBones baseBoneTransforms
		local f = currentTime as integer / ticksperframe as integer
		edtFrame.text = "帧: " + f as string + " | 骨骼数: " + transforms.count as string
		addLog ("✓ 记录'" + dirName + "'方向，帧:" + f as string)
		updateProgressBars()
	)


	on btnUp pressed do recordDirection &upTransforms edtUpFrame "上"
	on btnDown pressed do recordDirection &downTransforms edtDownFrame "下"
	on btnLeft pressed do recordDirection &leftTransforms edtLeftFrame "左"
	on btnRight pressed do recordDirection &rightTransforms edtRightFrame "右"

	-- 清空方向数据
	on btnClearUp pressed do (upTransforms = #(); edtUpFrame.text = ""; updateProgressBars(); addLog "✓ 清空上方向数据")
	on btnClearDown pressed do (downTransforms = #(); edtDownFrame.text = ""; updateProgressBars(); addLog "✓ 清空下方向数据")
	on btnClearLeft pressed do (leftTransforms = #(); edtLeftFrame.text = ""; updateProgressBars(); addLog "✓ 清空左方向数据")
	on btnClearRight pressed do (rightTransforms = #(); edtRightFrame.text = ""; updateProgressBars(); addLog "✓ 清空右方向数据")

	-- 创建反应管理
	on btnCreateReaction pressed do (


		addLog "========== 开始创建反应系统 =========="
		mixSlider = CreateMixSlider()
		if mixSlider == undefined do (addLog "✗ 无方向数据，无法创建"; return undefined)

		local boneNames = lbxBoneList.items
		local types = #()
		if chk_position.checked do append types #position
		if chk_rotation.checked do append types #rotation
		if chk_scale.checked do append types #scale

		if types.count == 0 do (addLog "✗ 请至少选择一种变换类型"; return undefined)

		local axisPairs = #(
			#(2, upTransforms, downTransforms, "上", "下"),
			#(1, rightTransforms, leftTransforms, "右", "左")
		)

		for pair in axisPairs do (
			local ax = pair[1]
			local posData = pair[2]
			local negData = pair[3]
			local posName = pair[4]
			local negName = pair[5]
			local hasPos = posData.count > 0
			local hasNeg = negData.count > 0
			if not (hasPos or hasNeg) do continue

			addLog ("  处理" + (if ax==2 then "Y轴" else "X轴") + "...")
			for t in types do (
				createReactorControllers mixSlider boneNames ax t
				if hasPos do (
					setReactionStates mixSlider posData true ax 2 t
					addLog ("    ✓ " + t as string + " - " + posName + "方向")
				)
				if hasNeg do (
					local negIdx = if hasPos then 1 else 2
					setReactionStates mixSlider negData false ax negIdx t
					addLog ("    ✓ " + t as string + " - " + negName + "方向")
				)
			)
		)
		sliderTime = 0
		addLog "========== 反应系统创建完成 =========="
	)

	-- 清除日志按钮事件
	on btnClearLog pressed do (
		logText = ""
		edtLog.text = ""
		addLog "欢迎使用骨骼动画转反应管理器"
		addLog "操作流程: 1.选中骨骼 → 2.获取列表 → 3.记录方向 → 4.创建反应"	
	)

	-- 初始化
	on 骨骼动画转反应管理器 open do (
		updateProgressBars()
		addLog "欢迎使用骨骼动画转反应管理器"
		addLog "操作流程: 1.选中骨骼 → 2.获取列表 → 3.记录方向 → 4.创建反应"
		addLog "-----------------------------------"
		addLog "日志已经清空"
	)
)
createDialog 骨骼动画转反应管理器
