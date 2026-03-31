/*
    作者: Tennoin
    时间: 2026-03-23
    版本: 3.1
    功能:
        * 膝盖变化修型：通过骨骼夹角驱动旋转/位移脚本控制器，支持输出值钳制。
        * 肩膀距离修型：通过两点距离驱动骨骼链拉伸。
        * 多套修型管理：listbox可视化、单套删除、安全控制器清理。
        * 场景扫描：一键获取场景中已有的修型骨骼。
*/

try(destroyDialog morphToolCombined)catch()

rollout morphToolCombined "修型工具 v3.1"
(
    -- ===== 变量 =====
    local pickedBip01    = undefined
    local pickedBip02    = undefined
    local createdObjects = #()

    local helper1Obj = undefined
    local helper2Obj = undefined
    local kneeSetList = #()   -- #(pitZero, pitRotExp, pitPosExp, bone, isMapped, mode)
    local kneeCount   = 0

    local proxy1Obj = undefined
    local proxy2Obj = undefined
    local shoulderSetList = #()  -- #(bone1, bone2)
    local shoulderCount   = 0

    -- ===== UI =====

    group "骨骼拾取"
    (
        pickButton btnPickBip1  "拾取骨骼1"   width:190 height:26
        pickButton btnPickBip2  "拾取骨骼2"   width:190 height:26
        spinner    spnPointSize "虚拟体大小:"  range:[1, 50, 2] type:#float fieldWidth:50
    )

    group "膝盖变化修型"
    (
        listbox lbxKneeSets    "修型列表:"   height:6
        radioButtons rdoCalcMode "计算模式:" labels:#("膝盖(单轴)", "肘/脊椎(投影)", "肩(Swing-Twist)") default:1 columns:1
        spinner spnWeight      "权重:"       range:[-100, 100, 50]   type:#float fieldWidth:50
        spinner spnMultiplier  "Y轴倍数:"    range:[-10, 10, 1.0]    type:#float fieldWidth:50
        spinner spnClampMin    "角度下限:"    range:[0, 180, 0]    type:#float fieldWidth:50
        spinner spnClampMax    "角度上限:"    range:[0, 180, 100]  type:#float fieldWidth:50
        button  btnCreateKnee      "创建修型"       width:90 height:26 across:2
        button  btnAddKnee         "新增修型"       width:90 height:26
        button  btnCompleteMapping "完成映射(选中)" width:90 height:26 across:2
        button  btnUpdate          "更新参数(选中)" width:90 height:26
        button  btnDeleteKnee      "删除选中"       width:90 height:24 across:2
        button  btnMirror          "镜像"           width:90 height:24
    )

    group "肩膀距离修型"
    (
        listbox lbxShoulderSets "骨骼列表:"  height:6
        spinner spnBoneSize     "骨骼粗细:"  range:[0.1, 20, 2] type:#float fieldWidth:50
        button  btnCreateShoulder "创建虚拟体"    width:90 height:26 across:2
        button  btnCreateBones    "生成骨骼"      width:90 height:26
        button  btnDeleteShoulder "删除选中骨骼"  width:190 height:24
    )

    button btnScanScene "获取场景修型" width:190 height:26
    button btnDeleteAll "删除所有创建的物体" width:190 height:28

    -- ===== 共用函数 =====

    fn FreezeTransform CurObj =
    (
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

    fn CreateProxyPoint pointName parentObj refTransform pointSize useBox wireColor =
    (
        local p = Point()
        p.box       = useBox
        p.cross     = not useBox
        p.size      = pointSize
        p.name      = pointName
        p.parent    = parentObj
        p.transform = refTransform
        p.wirecolor = wireColor
        append createdObjects p
        FreezeTransform p
        return p
    )

    fn getUniqueName baseName =
    (
        if getNodeByName baseName == undefined then return baseName
        local idx = 2
        while getNodeByName (baseName + "_" + idx as string) != undefined do idx += 1
        baseName + "_" + idx as string
    )

    -- ===== 镜像辅助函数 =====

    fn getMirrorName boneName =
    (
        local replacements = #(
            #(" Left ",  " Right "),
            #(" Right ", " Left "),
            #("_Left_",  "_Right_"),
            #("_Right_", "_Left_"),
            #(" L ",     " R "),
            #(" R ",     " L "),
            #("_L_",     "_R_"),
            #("_R_",     "_L_")
        )

        for p in replacements do
        (
            local pos = findString boneName p[1]
            if pos != undefined then
                return (replace boneName pos p[1].count p[2])
        )

        local endPairs = #(
            #("_Left",  "_Right"),
            #("_Right", "_Left"),
            #("_L",     "_R"),
            #("_R",     "_L"),
            #(" L",     " R"),
            #(" R",     " L")
        )
        local nameLen = boneName.count
        for p in endPairs do
        (
            local pLen = p[1].count
            if nameLen >= pLen then
            (
                local tail = substring boneName (nameLen - pLen + 1) pLen
                if tail == p[1] then
                    return (replace boneName (nameLen - pLen + 1) pLen p[2])
            )
        )
        boneName
    )

    fn mirrorPointOffsets srcPoint mirPoint =
    (
        try (
            mirPoint.Position.controller[2].x_Position = -(srcPoint.Position.controller[2].x_Position)
            mirPoint.Position.controller[2].y_Position = srcPoint.Position.controller[2].y_Position
            mirPoint.Position.controller[2].z_Position = srcPoint.Position.controller[2].z_Position
        ) catch ()
    )

    -- ===== Listbox 刷新 =====

    fn refreshKneeList =
    (
        local items = #()
        local modeLabels = #("膝盖", "肘脊椎", "肩")
        for i = 1 to kneeSetList.count do
        (
            local s = kneeSetList[i]
            local tag = if s[5] == true then "[OK] " else "[--] "
            local mTag = ""
            if s.count >= 6 and s[6] > 0 and s[6] <= modeLabels.count then
                mTag = "[" + modeLabels[s[6]] + "]"
            local bname = if s[4] != undefined and isValidNode s[4] then s[4].name else "<invalid>"
            append items (tag + mTag + bname)
        )
        lbxKneeSets.items = items
    )

    fn refreshShoulderList =
    (
        local items = #()
        for i = 1 to shoulderSetList.count do
        (
            local s = shoulderSetList[i]
            local b1 = if s[1] != undefined and isValidNode s[1] then s[1].name else "<invalid>"
            local b2 = if s[2] != undefined and isValidNode s[2] then s[2].name else "<invalid>"
            append items (b1 + " -> " + b2)
        )
        lbxShoulderSets.items = items
    )

    -- ===== 膝盖修型函数 =====

    fn CreateHelpPointer boneObj =
    (
        if boneObj != undefined and isValidNode boneObj then
        (
            local p = Point()
            p.centermarker = true
            p.box          = false
            p.cross        = false
            p.name         = getUniqueName (boneObj.name + "_Helper")
            p.parent       = boneObj
            p.transform    = boneObj.transform
            p.wirecolor    = (color 144 255 2)
            return p
        )
        return undefined
    )

    fn AddRotationScriptController h1 h2 weight cMin cMax boneObj mode =
    (
        local rotScript = Rotation_Script()
        rotScript.addNode     "helper1"  h1
        rotScript.addNode     "helper2"  h2
        rotScript.addConstant "weight"   weight
        rotScript.addConstant "clampMin" cMin
        rotScript.addConstant "clampMax" cMax
        local expr = ""
        case mode of
        (
            1: (
                expr += "v1 = normalize (helper1.transform.row2)\n"
                expr += "v2 = normalize (helper2.transform.row2)\n"
                expr += "dp = amax (-1.0) (amin 1.0 (dot v1 v2))\n"
                expr += "local ang = acos dp\n"
                expr += "ang = amax clampMin (amin clampMax ang) - clampMin\n"
                expr += "local val = (1 - (cos ang)) * weight\n"
                expr += "(eulerAngles 0 0 val)\n"
            )
            2: (
                expr += "v1 = normalize (helper1.transform.row2)\n"
                expr += "v2 = normalize (helper2.transform.row2)\n"
                expr += "local v1p = [0, v1.y, v1.z]\n"
                expr += "local v2p = [0, v2.y, v2.z]\n"
                expr += "local ang = 0\n"
                expr += "if (length v1p) > 0.001 and (length v2p) > 0.001 do (\n"
                expr += "  v1p = normalize v1p\n"
                expr += "  v2p = normalize v2p\n"
                expr += "  ang = atan2 (cross v1p v2p).x (dot v1p v2p)\n"
                expr += ")\n"
                expr += "local absAng = abs ang\n"
                expr += "absAng = amax clampMin (amin clampMax absAng) - clampMin\n"
                expr += "local sgn = if ang >= 0 then 1.0 else -1.0\n"
                expr += "local val = sgn * (1 - (cos absAng)) * weight\n"
                expr += "(eulerAngles 0 0 val)\n"
            )
            3: (
                expr += "relQ = helper2.rotation * (inverse helper1.rotation)\n"
                expr += "local py = relQ.y\n"
                expr += "local pw = relQ.w\n"
                expr += "local tLen = sqrt (py * py + pw * pw)\n"
                expr += "local swQ = relQ\n"
                expr += "if tLen > 0.0001 do (\n"
                expr += "  local it = 1.0 / tLen\n"
                expr += "  local tQ = quat 0 (py * it) 0 (pw * it)\n"
                expr += "  swQ = relQ * (inverse tQ)\n"
                expr += ")\n"
                expr += "local sw = amax (-1.0) (amin 1.0 swQ.w)\n"
                expr += "local ang = 2.0 * (acos sw)\n"
                expr += "ang = amax clampMin (amin clampMax ang) - clampMin\n"
                expr += "local val = (1 - (cos ang)) * weight\n"
                expr += "(eulerAngles 0 0 val)\n"
            )
        )
        rotScript.SetExpression expr
        boneObj.rotation.controller.available.controller = rotScript
        boneObj.rotation.controller.setname 3 "Midpoint Rotation"
    )

    fn AddPositionScriptController h1 h2 multiplier cMin cMax boneObj mode =
    (
        local posScript = Position_Script()
        posScript.addNode     "helper1"    h1
        posScript.addNode     "helper2"    h2
        posScript.addConstant "multiplier" multiplier
        posScript.addConstant "clampMin"   cMin
        posScript.addConstant "clampMax"   cMax
        local expr = ""
        case mode of
        (
            1: (
                expr += "v1 = normalize (helper1.transform.row2)\n"
                expr += "v2 = normalize (helper2.transform.row2)\n"
                expr += "dp = amax (-1.0) (amin 1.0 (dot v1 v2))\n"
                expr += "local ang = acos dp\n"
                expr += "ang = amax clampMin (amin clampMax ang) - clampMin\n"
                expr += "local val = (1 - (cos ang)) * multiplier\n"
                expr += "[0, val, 0]\n"
            )
            2: (
                expr += "v1 = normalize (helper1.transform.row2)\n"
                expr += "v2 = normalize (helper2.transform.row2)\n"
                expr += "local v1p = [0, v1.y, v1.z]\n"
                expr += "local v2p = [0, v2.y, v2.z]\n"
                expr += "local ang = 0\n"
                expr += "if (length v1p) > 0.001 and (length v2p) > 0.001 do (\n"
                expr += "  v1p = normalize v1p\n"
                expr += "  v2p = normalize v2p\n"
                expr += "  ang = atan2 (cross v1p v2p).x (dot v1p v2p)\n"
                expr += ")\n"
                expr += "local absAng = abs ang\n"
                expr += "absAng = amax clampMin (amin clampMax absAng) - clampMin\n"
                expr += "local sgn = if ang >= 0 then 1.0 else -1.0\n"
                expr += "local val = sgn * (1 - (cos absAng)) * multiplier\n"
                expr += "[0, val, 0]\n"
            )
            3: (
                expr += "relQ = helper2.rotation * (inverse helper1.rotation)\n"
                expr += "local py = relQ.y\n"
                expr += "local pw = relQ.w\n"
                expr += "local tLen = sqrt (py * py + pw * pw)\n"
                expr += "local swQ = relQ\n"
                expr += "if tLen > 0.0001 do (\n"
                expr += "  local it = 1.0 / tLen\n"
                expr += "  local tQ = quat 0 (py * it) 0 (pw * it)\n"
                expr += "  swQ = relQ * (inverse tQ)\n"
                expr += ")\n"
                expr += "local sw = amax (-1.0) (amin 1.0 swQ.w)\n"
                expr += "local ang = 2.0 * (acos sw)\n"
                expr += "ang = amax clampMin (amin clampMax ang) - clampMin\n"
                expr += "local val = (1 - (cos ang)) * multiplier\n"
                expr += "[0, val, 0]\n"
            )
        )
        posScript.SetExpression expr
        boneObj.position.controller.available.controller = posScript
        boneObj.position.controller.setname 3 "Corrective Position"
    )

    fn createKneeSetInternal =
    (
        kneeCount += 1
        local suffix = if kneeCount == 1 then "" else ("_" + kneeCount as string)

        local zeroName   = getUniqueName ("Pit_zero_"   + pickedBip02.name + suffix)
        local rotExpName = getUniqueName ("Pit_RotExp_" + pickedBip02.name + suffix)
        local posExpName = getUniqueName ("Pit_PosExp_" + pickedBip02.name + suffix)
        local boneName   = getUniqueName ("Bone_"       + pickedBip02.name + suffix)

        local pitZero   = CreateProxyPoint zeroName \
                              pickedBip02 pickedBip02.transform  spnPointSize.value      false (color 255 200 0)
        local pitRotExp = CreateProxyPoint rotExpName \
                              pitZero     pitZero.transform       (spnPointSize.value + 1) true  (color 0 200 255)
        local pitPosExp = CreateProxyPoint posExpName \
                              pitRotExp   pitZero.transform       (spnPointSize.value + 2) true  (color 255 100 200)

        local newBone = BoneSys.createBone [0,0,0] [0,0,10] [0,1,0]
        newBone.name      = boneName
        newBone.parent    = pickedBip02
        newBone.width     = 2
        newBone.height    = 2
        newBone.wirecolor = (color 255 100 100)
        append createdObjects newBone
        FreezeTransform newBone

        local linkCtrl = Link_Constraint()
        newBone.transform.controller = linkCtrl
        linkCtrl.addTarget pitPosExp 0
        newBone.transform = pitPosExp.transform
        newBone.rotation  = pitPosExp.rotation * ((angleAxis 90 [0,0,1]) as quat)
        newBone.pos       = pitPosExp.pos

        append kneeSetList #(pitZero, pitRotExp, pitPosExp, newBone, false, 0)
        refreshKneeList()
        lbxKneeSets.selection = kneeSetList.count

        print ("膝盖修型创建完成: " + boneName)
    )

    -- ===== 安全删除函数 =====

    fn safeDeleteKneeSet idx =
    (
        if idx < 1 or idx > kneeSetList.count then return false
        local s = kneeSetList[idx]

        try ( if s[4] != undefined and isValidNode s[4] then s[4].transform.controller = PRS() ) catch ()
        try ( if s[2] != undefined and isValidNode s[2] then s[2].rotation.controller  = Euler_XYZ() ) catch ()
        try ( if s[3] != undefined and isValidNode s[3] then s[3].position.controller  = Bezier_Position() ) catch ()

        for i = 4 to 1 by -1 do
        (
            local obj = s[i]
            if obj != undefined and isValidNode obj then
            (
                local ci = findItem createdObjects obj
                if ci > 0 do deleteItem createdObjects ci
                delete obj
            )
        )
        deleteItem kneeSetList idx
        refreshKneeList()
        true
    )

    fn safeDeleteShoulderSet idx =
    (
        if idx < 1 or idx > shoulderSetList.count then return false
        local s = shoulderSetList[idx]

        try
        (
            if s[1] != undefined and isValidNode s[1] then
            (
                s[1].scale.controller    = Bezier_Scale()
                s[1].rotation.controller = Euler_XYZ()
                s[1].position.controller = Bezier_Position()
            )
        ) catch ()
        try ( if s[2] != undefined and isValidNode s[2] then s[2].position.controller = Bezier_Position() ) catch ()

        for i = 2 to 1 by -1 do
        (
            local obj = s[i]
            if obj != undefined and isValidNode obj then
            (
                local ci = findItem createdObjects obj
                if ci > 0 do deleteItem createdObjects ci
                delete obj
            )
        )
        deleteItem shoulderSetList idx
        refreshShoulderList()
        true
    )

    -- ===== 场景扫描 =====

    fn scanSceneCorrectiveSets =
    (
        local kneeFound = 0
        local shoulderFound = 0

        -- 扫描膝盖修型：查找名称为 Bone_* 且带 Link_Constraint 的骨骼
        for obj in objects where (superClassOf obj == GeometryClass) do
        (
            try
            (
                if matchPattern obj.name pattern:"Bone_*" then
                (
                    local tc = obj.transform.controller
                    if classOf tc == Link_Constraint and tc.getNumTargets() > 0 then
                    (
                        local pitPosExp = tc.getNode 1
                        if pitPosExp != undefined and isValidNode pitPosExp and \
                           matchPattern pitPosExp.name pattern:"Pit_PosExp_*" then
                        (
                            local pitRotExp = pitPosExp.parent
                            if pitRotExp != undefined and matchPattern pitRotExp.name pattern:"Pit_RotExp_*" then
                            (
                                local pitZero = pitRotExp.parent
                                if pitZero != undefined and matchPattern pitZero.name pattern:"Pit_zero_*" then
                                (
                                    -- 检查是否已在列表中
                                    local exists = false
                                    for s in kneeSetList where s[4] == obj do exists = true
                                    if not exists then
                                    (
                                        -- 判断映射状态
                                        local isMapped = false
                                        try (
                                            local rc = pitRotExp.rotation.controller
                                            if classOf rc == Rotation_list and rc.count >= 3 then
                                                isMapped = true
                                        ) catch ()

                                        -- 从脚本控制器中提取Helper引用
                                        if isMapped then
                                        (
                                            try (
                                                local h1 = pitRotExp.rotation.controller[3].getNode "helper1"
                                                local h2 = pitRotExp.rotation.controller[3].getNode "helper2"
                                                if h1 != undefined and isValidNode h1 then
                                                (
                                                    helper1Obj = h1
                                                    if findItem createdObjects h1 == 0 do append createdObjects h1
                                                )
                                                if h2 != undefined and isValidNode h2 then
                                                (
                                                    helper2Obj = h2
                                                    if findItem createdObjects h2 == 0 do append createdObjects h2
                                                )
                                            ) catch ()
                                        )

                                        -- 未映射时通过层级查找Helper
                                        if (helper1Obj == undefined or not (isValidNode helper1Obj)) then
                                        (
                                            local bipBone2 = pitZero.parent
                                            if bipBone2 != undefined then
                                            (
                                                for c in bipBone2.children where \
                                                    classOf c == Point and matchPattern c.name pattern:"*_Helper" do
                                                (
                                                    if helper2Obj == undefined or not (isValidNode helper2Obj) then
                                                    (
                                                        helper2Obj = c
                                                        if findItem createdObjects c == 0 do append createdObjects c
                                                    )
                                                )
                                                if bipBone2.parent != undefined then
                                                (
                                                    for c in bipBone2.parent.children where \
                                                        classOf c == Point and matchPattern c.name pattern:"*_Helper" do
                                                    (
                                                        if helper1Obj == undefined or not (isValidNode helper1Obj) then
                                                        (
                                                            helper1Obj = c
                                                            if findItem createdObjects c == 0 do append createdObjects c
                                                        )
                                                    )
                                                )
                                            )
                                        )

                                        for o in #(pitZero, pitRotExp, pitPosExp, obj) do
                                            if findItem createdObjects o == 0 do append createdObjects o

                                        local detectedMode = 0
                                        if isMapped then (
                                            detectedMode = 1
                                            try (
                                                local exprStr = pitRotExp.rotation.controller[3].GetExpression()
                                                if findString exprStr "atan2" != undefined then detectedMode = 2
                                                else if findString exprStr "relQ" != undefined then detectedMode = 3
                                            ) catch ()
                                        )
                                        append kneeSetList #(pitZero, pitRotExp, pitPosExp, obj, isMapped, detectedMode)
                                        kneeFound += 1
                                    )
                                )
                            )
                        )
                    )
                )
            ) catch ()
        )

        -- 恢复拾取骨骼信息
        if kneeSetList.count > 0 then
        (
            local firstZero = kneeSetList[1][1]
            if firstZero != undefined and firstZero.parent != undefined then
            (
                pickedBip02 = firstZero.parent
                btnPickBip2.text = pickedBip02.name
                if pickedBip02.parent != undefined then
                (
                    pickedBip01 = pickedBip02.parent
                    btnPickBip1.text = pickedBip01.name
                )
            )
        )
        kneeCount = kneeSetList.count

        -- 扫描肩膀修型：查找 Proxy 和 Bone 对
        for obj in objects where (classOf obj == Point) do
        (
            if matchPattern obj.name pattern:"Proxy1_*" and \
               (proxy1Obj == undefined or not (isValidNode proxy1Obj)) then
            (
                proxy1Obj = obj
                if findItem createdObjects obj == 0 do append createdObjects obj
            )
            else if matchPattern obj.name pattern:"Proxy2_*" and \
                    (proxy2Obj == undefined or not (isValidNode proxy2Obj)) then
            (
                proxy2Obj = obj
                if findItem createdObjects obj == 0 do append createdObjects obj
            )
        )

        for obj in objects where (superClassOf obj == GeometryClass) and \
                                 (matchPattern obj.name pattern:"Bone1_*") do
        (
            try
            (
                if classOf obj.position.controller == Position_Constraint then
                (
                    local exists = false
                    for s in shoulderSetList where s[1] == obj do exists = true
                    if not exists then
                    (
                        local b2 = undefined
                        for c in obj.children where matchPattern c.name pattern:"Bone2_*" do b2 = c
                        if b2 != undefined then
                        (
                            for o in #(obj, b2) do
                                if findItem createdObjects o == 0 do append createdObjects o
                            append shoulderSetList #(obj, b2)
                            shoulderFound += 1
                        )
                    )
                )
            ) catch ()
        )

        shoulderCount = shoulderSetList.count

        refreshKneeList()
        refreshShoulderList()

        format "场景扫描完成: 膝盖修型 % 套, 肩膀骨骼链 % 套\n" kneeFound shoulderFound
        messageBox ("扫描完成!\n膝盖修型: " + kneeFound as string + " 套\n肩膀骨骼链: " + shoulderFound as string + " 套")
    )

    -- ===== 拾取事件 =====

    on morphToolCombined open do
    (
        try
        (
            pickedBip01 = $'Bip001 L Thigh'
            if pickedBip01 != undefined and isValidNode pickedBip01 then
                btnPickBip1.text = pickedBip01.name
        )
        catch()

        try
        (
            pickedBip02 = $'Bip001 L Calf'
            if pickedBip02 != undefined and isValidNode pickedBip02 then
                btnPickBip2.text = pickedBip02.name
        )
        catch()
    )

    on btnPickBip1 picked obj do
    (
        pickedBip01      = obj
        btnPickBip1.text = obj.name
        if obj.children.count > 0 then
        (
            pickedBip02      = obj.children[1]
            btnPickBip2.text = pickedBip02.name
        )
        else
        (
            pickedBip02      = undefined
            btnPickBip2.text = "拾取骨骼2"
        )
    )

    on btnPickBip2 picked obj do
    (
        pickedBip02      = obj
        btnPickBip2.text = obj.name
    )

    -- ===== Listbox 选中回显 =====

    on lbxKneeSets selected sel do
    (
        if sel >= 1 and sel <= kneeSetList.count then
        (
            local s = kneeSetList[sel]
            if s.count >= 6 and s[6] > 0 then rdoCalcMode.state = s[6]
            if s[5] == true then
            (
                try
                (
                    spnWeight.value     = s[2].rotation.controller[3].getConstant "weight"
                    spnMultiplier.value = s[3].position.controller[3].getConstant "multiplier"
                    spnClampMin.value   = s[2].rotation.controller[3].getConstant "clampMin"
                    spnClampMax.value   = s[2].rotation.controller[3].getConstant "clampMax"
                ) catch ()
            )
        )
    )

    -- ===== 膝盖修型事件 =====

    on btnCreateKnee pressed do
    (
        if pickedBip01 == undefined or pickedBip02 == undefined then
        (
            messageBox "请先拾取两个骨骼！"
            return undefined
        )
        if not (isValidNode pickedBip01) or not (isValidNode pickedBip02) then
        (
            messageBox "骨骼对象无效，请重新拾取！"
            return undefined
        )

        local needH1 = (helper1Obj == undefined) or (not (isValidNode helper1Obj)) or \
                       (helper1Obj.parent != pickedBip01)
        local needH2 = (helper2Obj == undefined) or (not (isValidNode helper2Obj)) or \
                       (helper2Obj.parent != pickedBip02)

        if needH1 then
        (
            helper1Obj = CreateHelpPointer pickedBip01
            if helper1Obj != undefined then append createdObjects helper1Obj
        )
        if needH2 then
        (
            helper2Obj = CreateHelpPointer pickedBip02
            if helper2Obj != undefined then append createdObjects helper2Obj
        )

        createKneeSetInternal()
    )

    on btnAddKnee pressed do
    (
        if helper1Obj == undefined or helper2Obj == undefined or \
           not (isValidNode helper1Obj) or not (isValidNode helper2Obj) then
        (
            messageBox "请先创建膝盖修型（需要Helper）！"
            return undefined
        )
        if pickedBip02 == undefined or not (isValidNode pickedBip02) then
        (
            messageBox "骨骼2无效，请重新拾取！"
            return undefined
        )
        createKneeSetInternal()
    )

    on btnCompleteMapping pressed do
    (
        local sel = lbxKneeSets.selection
        if sel < 1 or sel > kneeSetList.count then
        (
            messageBox "请在列表中选择一个修型！"
            return undefined
        )

        local s = kneeSetList[sel]
        if s[5] == true then
        (
            messageBox "该修型已完成映射，如需调整请用\"更新参数\"。"
            return undefined
        )
        if helper1Obj == undefined or helper2Obj == undefined or \
           not (isValidNode helper1Obj) or not (isValidNode helper2Obj) then
        (
            messageBox "Helper无效，无法映射！"
            return undefined
        )
        if not (isValidNode s[2]) or not (isValidNode s[3]) then
        (
            messageBox "虚拟体无效，请重新创建！"
            return undefined
        )

        local curMode = rdoCalcMode.state
        AddRotationScriptController helper1Obj helper2Obj \
            spnWeight.value spnClampMin.value spnClampMax.value s[2] curMode
        AddPositionScriptController helper1Obj helper2Obj \
            spnMultiplier.value spnClampMin.value spnClampMax.value s[3] curMode

        s[5] = true
        s[6] = curMode
        kneeSetList[sel] = s
        refreshKneeList()
        lbxKneeSets.selection = sel
        messageBox "映射完成！"
    )

    on btnUpdate pressed do
    (
        local sel = lbxKneeSets.selection
        if sel < 1 or sel > kneeSetList.count then
        (
            messageBox "请在列表中选择一个修型！"
            return undefined
        )

        local s = kneeSetList[sel]
        if s[5] != true then
        (
            messageBox "该修型尚未映射，请先完成映射！"
            return undefined
        )
        if not (isValidNode s[2]) or not (isValidNode s[3]) then
        (
            messageBox "虚拟体无效！"
            return undefined
        )

        s[2].rotation.controller[3].setConstant "weight"   spnWeight.value
        s[2].rotation.controller[3].setConstant "clampMin" spnClampMin.value
        s[2].rotation.controller[3].setConstant "clampMax" spnClampMax.value
        s[3].position.controller[3].setConstant "multiplier" spnMultiplier.value
        s[3].position.controller[3].setConstant "clampMin"   spnClampMin.value
        s[3].position.controller[3].setConstant "clampMax"   spnClampMax.value
        print ("参数已更新: weight=" + spnWeight.value as string + \
               "  multiplier=" + spnMultiplier.value as string + \
               "  clamp=[" + spnClampMin.value as string + ", " + spnClampMax.value as string + "]")
    )

    on btnDeleteKnee pressed do
    (
        local sel = lbxKneeSets.selection
        if sel < 1 or sel > kneeSetList.count then
        (
            messageBox "请在列表中选择要删除的修型！"
            return undefined
        )
        safeDeleteKneeSet sel
        print "已删除选中的膝盖修型"
    )

    on btnMirror pressed do
    (
        local sel = lbxKneeSets.selection
        if sel < 1 or sel > kneeSetList.count then
        (
            messageBox "请在列表中选择要镜像的修型！"
            return undefined
        )

        local s = kneeSetList[sel]
        local srcPitZero   = s[1]
        local srcPitRotExp = s[2]
        local srcPitPosExp = s[3]
        local srcBone      = s[4]
        local srcIsMapped  = s[5]
        local srcMode      = if s.count >= 6 then s[6] else 1

        if srcPitZero == undefined or not (isValidNode srcPitZero) then
        (
            messageBox "源修型虚拟体无效！"
            return undefined
        )

        local srcBip02 = srcPitZero.parent
        if srcBip02 == undefined or not (isValidNode srcBip02) then
        (
            messageBox "无法找到源骨骼！"
            return undefined
        )
        local srcBip01 = srcBip02.parent

        -- 查找镜像骨骼
        local mirBip02Name = getMirrorName srcBip02.name
        if mirBip02Name == srcBip02.name then
        (
            messageBox ("骨骼名称中未找到 L/R 关键词:\n" + srcBip02.name)
            return undefined
        )
        local mirBip02 = getNodeByName mirBip02Name
        if mirBip02 == undefined then
        (
            messageBox ("场景中找不到镜像骨骼: " + mirBip02Name)
            return undefined
        )

        local mirBip01 = undefined
        if srcBip01 != undefined and isValidNode srcBip01 then
        (
            local mirBip01Name = getMirrorName srcBip01.name
            mirBip01 = getNodeByName mirBip01Name
        )

        -- 查找或创建镜像 Helper
        local mirHelper1 = undefined
        local mirHelper2 = undefined

        for c in mirBip02.children where classOf c == Point and matchPattern c.name pattern:"*_Helper" do
            if mirHelper2 == undefined then mirHelper2 = c

        if mirBip01 != undefined then
        (
            for c in mirBip01.children where classOf c == Point and matchPattern c.name pattern:"*_Helper" do
                if mirHelper1 == undefined then mirHelper1 = c
        )

        if mirHelper1 == undefined and mirBip01 != undefined then
        (
            mirHelper1 = CreateHelpPointer mirBip01
            if mirHelper1 != undefined then append createdObjects mirHelper1
        )
        if mirHelper2 == undefined then
        (
            mirHelper2 = CreateHelpPointer mirBip02
            if mirHelper2 != undefined then append createdObjects mirHelper2
        )

        -- 创建镜像修型结构
        kneeCount += 1
        local suffix = if kneeCount == 1 then "" else ("_" + kneeCount as string)

        local zeroName   = getUniqueName ("Pit_zero_"   + mirBip02.name + suffix)
        local rotExpName = getUniqueName ("Pit_RotExp_" + mirBip02.name + suffix)
        local posExpName = getUniqueName ("Pit_PosExp_" + mirBip02.name + suffix)
        local boneName   = getUniqueName ("Bone_"       + mirBip02.name + suffix)

        local pitZero   = CreateProxyPoint zeroName \
                              mirBip02  mirBip02.transform   spnPointSize.value       false (color 255 200 0)
        local pitRotExp = CreateProxyPoint rotExpName \
                              pitZero   pitZero.transform    (spnPointSize.value + 1) true  (color 0 200 255)
        local pitPosExp = CreateProxyPoint posExpName \
                              pitRotExp pitZero.transform    (spnPointSize.value + 2) true  (color 255 100 200)

        -- 复制源修型的位置偏移（X轴取反实现镜像）
        mirrorPointOffsets srcPitZero   pitZero
        mirrorPointOffsets srcPitRotExp pitRotExp
        mirrorPointOffsets srcPitPosExp pitPosExp

        local boneW = if srcBone != undefined and isValidNode srcBone then srcBone.width  else 2
        local boneH = if srcBone != undefined and isValidNode srcBone then srcBone.height else 2

        local newBone = BoneSys.createBone [0,0,0] [0,0,10] [0,1,0]
        newBone.name      = boneName
        newBone.parent    = mirBip02
        newBone.width     = boneW
        newBone.height    = boneH
        newBone.wirecolor = (color 255 100 100)
        append createdObjects newBone
        FreezeTransform newBone

        local linkCtrl = Link_Constraint()
        newBone.transform.controller = linkCtrl
        linkCtrl.addTarget pitPosExp 0
        newBone.transform = pitPosExp.transform
        newBone.rotation  = pitPosExp.rotation * ((angleAxis 90 [0,0,1]) as quat)
        newBone.pos       = pitPosExp.pos

        local isMapped = false

        -- 源已映射时，自动映射镜像并复制参数
        if srcIsMapped and mirHelper1 != undefined and mirHelper2 != undefined then
        (
            local mWeight     = spnWeight.value
            local mMultiplier = spnMultiplier.value
            local mClampMin   = spnClampMin.value
            local mClampMax   = spnClampMax.value

            try (
                mWeight     = srcPitRotExp.rotation.controller[3].getConstant "weight"
                mClampMin   = srcPitRotExp.rotation.controller[3].getConstant "clampMin"
                mClampMax   = srcPitRotExp.rotation.controller[3].getConstant "clampMax"
                mMultiplier = srcPitPosExp.position.controller[3].getConstant "multiplier"
            ) catch ()

            AddRotationScriptController mirHelper1 mirHelper2 mWeight mClampMin mClampMax pitRotExp srcMode
            AddPositionScriptController mirHelper1 mirHelper2 mMultiplier mClampMin mClampMax pitPosExp srcMode
            isMapped = true
        )

        append kneeSetList #(pitZero, pitRotExp, pitPosExp, newBone, isMapped, if isMapped then srcMode else 0)
        refreshKneeList()
        lbxKneeSets.selection = kneeSetList.count

        local mapMsg = if isMapped then "（已自动映射）" else "（未映射，请手动完成映射）"
        print ("镜像完成: " + boneName + " " + mapMsg)
        messageBox ("镜像完成！\n" + boneName + "\n" + mapMsg)
    )

    -- ===== 肩膀修型事件 =====

    on btnCreateShoulder pressed do
    (
        if pickedBip01 == undefined or pickedBip02 == undefined then
        (
            messageBox "请先拾取两个骨骼！"
            return undefined
        )
        if not (isValidNode pickedBip01) or not (isValidNode pickedBip02) then
        (
            messageBox "骨骼对象无效，请重新拾取！"
            return undefined
        )

        if proxy1Obj == undefined or not (isValidNode proxy1Obj) then
        (
            proxy1Obj = CreateProxyPoint (getUniqueName ("Proxy1_" + pickedBip01.name)) \
                            pickedBip01 pickedBip01.transform \
                            spnPointSize.value false (color 255 200 0)
        )
        if proxy2Obj == undefined or not (isValidNode proxy2Obj) then
        (
            proxy2Obj = CreateProxyPoint (getUniqueName ("Proxy2_" + pickedBip02.name)) \
                            pickedBip02 pickedBip02.transform \
                            (spnPointSize.value + 1) true (color 0 200 255)
        )

        print ("肩膀虚拟体就绪: " + proxy1Obj.name + " / " + proxy2Obj.name)
    )

    on btnCreateBones pressed do
    (
        if proxy1Obj == undefined or proxy2Obj == undefined then
        (
            messageBox "请先创建肩膀虚拟体！"
            return undefined
        )
        if not (isValidNode proxy1Obj) or not (isValidNode proxy2Obj) then
        (
            messageBox "虚拟体无效，请重新创建！"
            return undefined
        )

        shoulderCount += 1
        local suffix = if shoulderCount == 1 then "" else ("_" + shoulderCount as string)

        local startPos = proxy1Obj.pos
        local endPos   = proxy2Obj.pos
        local boneDir  = normalize (endPos - startPos)

        local zDir = [0, 0, 1]
        if (abs (dot boneDir [0,0,1])) > 0.9 then zDir = [0, 1, 0]
        zDir = normalize (cross boneDir zDir)

        local restDist  = distance startPos endPos
        local bone1Name = getUniqueName ("Bone1_" + pickedBip01.name + suffix)
        local bone2Name = getUniqueName ("Bone2_" + pickedBip02.name + suffix)

        local b1 = BoneSys.createBone startPos endPos zDir
        b1.name      = bone1Name
        b1.parent    = pickedBip01
        b1.width     = spnBoneSize.value
        b1.height    = spnBoneSize.value
        b1.wirecolor = (color 255 150 50)
        append createdObjects b1

        b1.position.controller = Position_Constraint()
        b1.position.controller.appendTarget proxy1Obj 100

        b1.rotation.controller = LookAt_Constraint()
        b1.rotation.controller.appendTarget proxy2Obj 100
        proxy1Obj.transform = b1.transform
        b1.rotation.controller.viewline_length_abs = false
        b1.rotation.controller.upnode_world = false
        b1.rotation.controller.pickUpNode = proxy1Obj

        local scaleScript = Scale_Script()
        scaleScript.addNode     "proxy1"   proxy1Obj
        scaleScript.addNode     "proxy2"   proxy2Obj
        scaleScript.addConstant "restDist" restDist
        scaleScript.SetExpression "local d = (distance proxy1.pos proxy2.pos) / restDist\n[d, 1, 1]"
        b1.scale.controller = scaleScript

        local nubEnd = endPos + boneDir * (spnBoneSize.value * 2)
        local b2 = BoneSys.createBone endPos nubEnd zDir
        b2.name      = bone2Name
        b2.parent    = b1
        b2.width     = spnBoneSize.value * 0.8
        b2.height    = spnBoneSize.value * 0.8
        b2.wirecolor = (color 255 220 120)
        append createdObjects b2

        b2.position.controller = Position_Constraint()
        b2.position.controller.appendTarget proxy2Obj 100

        append shoulderSetList #(b1, b2)
        refreshShoulderList()
        lbxShoulderSets.selection = shoulderSetList.count

        print ("肩膀骨骼链创建完成: " + bone1Name + " -> " + bone2Name)
    )

    on btnDeleteShoulder pressed do
    (
        local sel = lbxShoulderSets.selection
        if sel < 1 or sel > shoulderSetList.count then
        (
            messageBox "请在列表中选择要删除的骨骼！"
            return undefined
        )
        safeDeleteShoulderSet sel
        print "已删除选中的肩膀骨骼链"
    )

    -- ===== 场景扫描 / 删除所有 =====

    on btnScanScene pressed do
    (
        scanSceneCorrectiveSets()
    )

    on btnDeleteAll pressed do
    (
        while kneeSetList.count > 0 do
            safeDeleteKneeSet kneeSetList.count

        while shoulderSetList.count > 0 do
            safeDeleteShoulderSet shoulderSetList.count

        for obj in #(helper1Obj, helper2Obj, proxy1Obj, proxy2Obj) do
        (
            if obj != undefined and isValidNode obj then
            (
                local ci = findItem createdObjects obj
                if ci > 0 do deleteItem createdObjects ci
                delete obj
            )
        )

        for obj in createdObjects where obj != undefined and isValidNode obj do
            delete obj

        createdObjects  = #()
        helper1Obj      = undefined
        helper2Obj      = undefined
        proxy1Obj       = undefined
        proxy2Obj       = undefined
        kneeSetList     = #()
        shoulderSetList = #()
        kneeCount       = 0
        shoulderCount   = 0

        refreshKneeList()
        refreshShoulderList()
        print "已删除所有创建的物体"
    )
)

createDialog morphToolCombined 220 800
