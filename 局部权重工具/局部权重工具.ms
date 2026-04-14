/*
    作者: Tennoin
    时间: 2026-04-14
    版本: 2.0 (性能优化版)
    功能:
        * 在Skin修改器的顶点子对象模式下选中部分顶点
        * 提取选中顶点所构成的完整面，生成新的可编辑多边形
        * 新模型带有Skin修改器，权重与原模型一致
        * 可将提取模型上修改过的权重粘贴回原模型对应顶点
    优化:
        * disableSceneRedraw + with redraw off 避免视口刷新
        * StringStream 替代字符串拼接，序列化从 O(n²) 降至 O(n)
        * 缓存 polyOp.getFaceVerts 避免重复调用
        * try/catch 移出循环体，仅做一次兼容性检测
        * 进度条反馈长时间操作
*/

try(destroyDialog rlSkinMeshExtract)catch()

rollout rlSkinMeshExtract "局部权重工具 v2.1" width:260 height:210
(
    button btnExtract   "提取Skin网格"       width:230 height:36 tooltip:"在Skin顶点模式下选择顶点后点击，提取选中区域的网格并保留权重"
    checkbox chkHide     "提取时隐藏原模型对应面" checked:false
    button btnPasteBack "权重粘贴回原模型"   width:230 height:36 tooltip:"选中_SkinExtract模型，将其权重写回原始模型对应的顶点"
    checkbox chkDeleteExt "粘贴后删除提取模型" checked:false
    progressBar pbProgress width:230 height:8 value:0 color:green

    fn findSkinMod obj =
    (
        for m in obj.modifiers where classOf m == Skin do return m
        undefined
    )

    fn setProgress pb val =
    (
        pb.value = val
        windows.processPostedMessages()
    )

    -- ===================== 提取 =====================
    on btnExtract pressed do
    (
        if selection.count != 1 then
        (
            messageBox "请先选择一个带有Skin修改器的模型" title:"提示"
            return()
        )

        local srcObj = selection[1]
        local skinMod = findSkinMod srcObj

        if skinMod == undefined then
        (
            messageBox "选中的模型没有Skin修改器" title:"提示"
            return()
        )

        local t1 = timeStamp()

        undo "Extract Skin Mesh" on
        (
            select srcObj
            max modify mode
            modPanel.setCurrentObject skinMod
            subObjectLevel = 1

            local numVerts = skinOps.GetNumberVertices skinMod

            -- 获取选中顶点（try 只包一次，用于兼容性检测）
            local selVerts = #{}
            local selSupported = true
            try (skinOps.IsVertexSelected skinMod 1) catch (selSupported = false)

            if selSupported then
            (
                for v = 1 to numVerts do
                    if (skinOps.IsVertexSelected skinMod v) == 1 then selVerts[v] = true
            )

            if selVerts.isEmpty then
            (
                messageBox "Skin中没有选中任何顶点\n请先在Skin的顶点子对象模式下选择顶点" title:"提示"
                return()
            )

            setProgress pbProgress 5

            -- 收集骨骼节点
            local numBones = skinOps.GetNumberBones skinMod
            local boneNodes = #()
            boneNodes.count = numBones
            for i = 1 to numBones do
                boneNodes[i] = getNodeByName (skinOps.GetBoneName skinMod i 0) exact:true

            -- 收集选中顶点的权重（预分配数组）
            local vertBoneIDs = #()
            local vertWeights = #()
            vertBoneIDs.count = numVerts
            vertWeights.count = numVerts
            local selArr = selVerts as array
            local selCount = selArr.count
            for idx = 1 to selCount do
            (
                local v = selArr[idx]
                local wCount = skinOps.GetVertexWeightCount skinMod v
                local bIDs = #()
                local wVals = #()
                bIDs.count = wCount
                wVals.count = wCount
                for w = 1 to wCount do
                (
                    bIDs[w] = skinOps.GetVertexWeightBoneID skinMod v w
                    wVals[w] = skinOps.GetVertexWeight skinMod v w
                )
                vertBoneIDs[v] = bIDs
                vertWeights[v] = wVals
                if mod idx 2000 == 0 then setProgress pbProgress (5 + 25.0 * idx / selCount)
            )

            setProgress pbProgress 30

            -- 快照绑定姿态
            subObjectLevel = 0
            disableSceneRedraw()
            try
            (
                skinMod.enabled = false
                local newObj = snapshot srcObj
                skinMod.enabled = true
                convertToPoly newObj
                newObj.name = srcObj.name + "_SkinExtract"

                setProgress pbProgress 40

                -- 缓存所有面的顶点列表，避免重复调用 polyOp
                local numFaces = polyOp.getNumFaces newObj
                local allFaceVerts = #()
                allFaceVerts.count = numFaces
                for f = 1 to numFaces do allFaceVerts[f] = polyOp.getFaceVerts newObj f

                setProgress pbProgress 50

                -- 筛选面 + 收集保留顶点（单次遍历）
                local facesToKeep = #{}
                local keptVerts = #{}
                for f = 1 to numFaces do
                (
                    local fVerts = allFaceVerts[f]
                    local allSel = true
                    for fv in fVerts where not selVerts[fv] do (allSel = false; exit)
                    if allSel then
                    (
                        facesToKeep[f] = true
                        for fv in fVerts do keptVerts[fv] = true
                    )
                )

                if facesToKeep.isEmpty then
                (
                    delete newObj
                    enableSceneRedraw()
                    completeRedraw()
                    setProgress pbProgress 0
                    messageBox "选中的顶点无法构成完整的面，无法提取" title:"提示"
                    return()
                )

                setProgress pbProgress 55

                -- 建立旧→新、新→旧顶点映射
                local totalVerts = polyOp.getNumVerts newObj
                local oldToNew = #()
                oldToNew.count = totalVerts
                local newVIdx = 0
                for v = 1 to totalVerts do
                (
                    if keptVerts[v] then
                    (
                        newVIdx += 1
                        oldToNew[v] = newVIdx
                    )
                    else
                        oldToNew[v] = 0
                )

                local newToOld = #()
                newToOld.count = newVIdx
                for v = 1 to totalVerts do
                    if oldToNew[v] > 0 then newToOld[oldToNew[v]] = v

                -- 删除多余面
                local facesToDel = #{1..numFaces} - facesToKeep
                if not facesToDel.isEmpty then
                    polyOp.deleteFaces newObj facesToDel delIsoVerts:true
                free allFaceVerts

                setProgress pbProgress 60

                -- 添加Skin并绑定骨骼
                select newObj
                max modify mode
                local newSkin = Skin()
                addModifier newObj newSkin
                newSkin.filter_vertices = on
                newSkin.showNoEnvelopes = on
                modPanel.setCurrentObject newSkin

                local boneIDMap = #()
                boneIDMap.count = numBones
                local newBIdx = 0
                for i = 1 to numBones do
                (
                    if boneNodes[i] != undefined then
                    (
                        skinOps.addBone newSkin boneNodes[i] 0
                        newBIdx += 1
                        boneIDMap[i] = newBIdx
                    )
                    else
                        boneIDMap[i] = 0
                )

                enableSceneRedraw()
                completeRedraw()
                disableSceneRedraw()

                setProgress pbProgress 70

                -- 传输权重
                for idx = 1 to selCount do
                (
                    local oldV = selArr[idx]
                    local nv = oldToNew[oldV]
                    if nv != undefined and nv > 0 and vertBoneIDs[oldV] != undefined then
                    (
                        local srcBIDs = vertBoneIDs[oldV]
                        local srcWts  = vertWeights[oldV]
                        local newBIDs = #()
                        local newWts  = #()
                        local wc = srcBIDs.count
                        newBIDs.count = wc
                        newWts.count = wc
                        local ni = 0
                        for w = 1 to wc do
                        (
                            local mb = boneIDMap[srcBIDs[w]]
                            if mb != undefined and mb > 0 then
                            (
                                ni += 1
                                newBIDs[ni] = mb
                                newWts[ni]  = srcWts[w]
                            )
                        )
                        if ni > 0 then
                        (
                            newBIDs.count = ni
                            newWts.count  = ni
                            skinOps.ReplaceVertexWeights newSkin nv newBIDs newWts
                        )
                    )
                    if mod idx 2000 == 0 then setProgress pbProgress (70 + 20.0 * idx / selCount)
                )

                setProgress pbProgress 90

                -- 用 StringStream 序列化映射（O(n) 替代 O(n²) 字符串拼接）
                local ss = StringStream ""
                for i = 1 to newToOld.count do
                (
                    format "%" (newToOld[i] as string) to:ss
                    if i < newToOld.count then format "," to:ss
                )
                setUserProp newObj "SkinExtract_Source"  srcObj.name
                setUserProp newObj "SkinExtract_VertMap" (ss as string)
                free ss

                enableSceneRedraw()
                completeRedraw()

                -- 隐藏原模型对应面
                local didHide = false
                if chkHide.checked and classOf srcObj.baseObject == Editable_Poly then
                (
                    local srcNumFaces = polyOp.getNumFaces srcObj
                    local srcFacesToHide = #{}
                    for f = 1 to srcNumFaces do
                    (
                        local fVerts = polyOp.getFaceVerts srcObj f
                        local allSel = true
                        for fv in fVerts where not selVerts[fv] do (allSel = false; exit)
                        if allSel then srcFacesToHide[f] = true
                    )
                    if not srcFacesToHide.isEmpty then
                    (
                        select srcObj
                        max modify mode
                        modPanel.setCurrentObject srcObj.baseObject
                        subObjectLevel = 4
                        polyOp.setFaceSelection srcObj srcFacesToHide
                        srcObj.EditablePoly.hide #Face
                        polyOp.setFaceSelection srcObj #{}
                        subObjectLevel = 0
                        didHide = true
                    )
                )
                if didHide then
                    setUserProp newObj "SkinExtract_HidFaces" "1"

                select newObj
                completeRedraw()
                setProgress pbProgress 100

                local elapsed = (timeStamp() - t1) / 1000.0
                local extractedFaces = facesToKeep.numberSet
                local extractedVerts = keptVerts.numberSet
                local msg = "提取完成!  (" + (elapsed as string) + "s)\n\n新模型: " + newObj.name + "\n提取面数: " + extractedFaces as string + "\n提取顶点: " + extractedVerts as string + "\n骨骼数: " + numBones as string
                if didHide then msg += "\n\n已隐藏原模型对应面"
                messageBox msg title:"完成"
            )
            catch
            (
                enableSceneRedraw()
                completeRedraw()
                messageBox ("提取过程中出错:\n" + (getCurrentException())) title:"错误"
            )
            setProgress pbProgress 0
        )
    )

    -- ===================== 粘贴回原模型 =====================
    on btnPasteBack pressed do
    (
        if selection.count != 1 then
        (
            messageBox "请选择一个 _SkinExtract 模型" title:"提示"
            return()
        )

        local extObj = selection[1]
        local srcName = getUserProp extObj "SkinExtract_Source"
        local mapStr  = getUserProp extObj "SkinExtract_VertMap"

        if srcName == undefined or mapStr == undefined or srcName == "" or mapStr == "" then
        (
            messageBox "选中的模型不是通过本工具提取的，缺少映射数据" title:"提示"
            return()
        )

        local srcObj = getNodeByName srcName exact:true
        if srcObj == undefined then
        (
            messageBox ("找不到原始模型: " + srcName + "\n请确认原始模型未被删除或重命名") title:"提示"
            return()
        )

        local extSkin = findSkinMod extObj
        local srcSkin = findSkinMod srcObj

        if extSkin == undefined then
        (
            messageBox "提取模型没有Skin修改器" title:"提示"
            return()
        )
        if srcSkin == undefined then
        (
            messageBox ("原始模型 \"" + srcName + "\" 没有Skin修改器") title:"提示"
            return()
        )

        local t1 = timeStamp()

        undo "Paste Skin Weights Back" on
        (
            -- 用 StringStream 解析映射（比 filterString 更省内存）
            setProgress pbProgress 5
            local newToOld = #()
            local ss = StringStream mapStr
            while not eof ss do
            (
                local tok = readDelimitedString ss ","
                if tok.count > 0 then append newToOld (tok as integer)
            )
            free ss
            setProgress pbProgress 15

            -- 读取提取模型的Skin数据
            select extObj
            max modify mode
            modPanel.setCurrentObject extSkin

            local extNumBones = skinOps.GetNumberBones extSkin
            local extNumVerts = skinOps.GetNumberVertices extSkin

            if extNumVerts != newToOld.count then
            (
                messageBox ("顶点数不匹配!\n提取模型顶点: " + extNumVerts as string + "\n映射记录: " + newToOld.count as string + "\n\n提取后可能修改了拓扑，无法粘贴") title:"错误"
                setProgress pbProgress 0
                return()
            )

            local extBoneNames = #()
            extBoneNames.count = extNumBones
            for i = 1 to extNumBones do
                extBoneNames[i] = skinOps.GetBoneName extSkin i 0

            -- 批量读取权重（预分配子数组）
            local extVertBIDs = #()
            local extVertWts  = #()
            extVertBIDs.count = extNumVerts
            extVertWts.count  = extNumVerts
            for v = 1 to extNumVerts do
            (
                local wCount = skinOps.GetVertexWeightCount extSkin v
                local bIDs = #()
                local wVals = #()
                bIDs.count = wCount
                wVals.count = wCount
                for w = 1 to wCount do
                (
                    bIDs[w] = skinOps.GetVertexWeightBoneID extSkin v w
                    wVals[w] = skinOps.GetVertexWeight extSkin v w
                )
                extVertBIDs[v] = bIDs
                extVertWts[v]  = wVals
                if mod v 2000 == 0 then setProgress pbProgress (15 + 35.0 * v / extNumVerts)
            )

            setProgress pbProgress 50

            -- 切换到原始模型，建立骨骼名称映射
            select srcObj
            max modify mode
            modPanel.setCurrentObject srcSkin

            local srcNumBones = skinOps.GetNumberBones srcSkin
            local srcBoneNames = #()
            srcBoneNames.count = srcNumBones
            for i = 1 to srcNumBones do
                srcBoneNames[i] = skinOps.GetBoneName srcSkin i 0

            local boneMap = #()
            boneMap.count = extNumBones
            for i = 1 to extNumBones do
                boneMap[i] = findItem srcBoneNames extBoneNames[i]

            setProgress pbProgress 55

            -- 逐顶点写回权重
            disableSceneRedraw()
            try
            (
                local appliedCount = 0
                local total = newToOld.count
                for newV = 1 to total do
                (
                    local oldV = newToOld[newV]
                    if oldV > 0 then
                    (
                        local eBIDs = extVertBIDs[newV]
                        local eWts  = extVertWts[newV]
                        local wc = eBIDs.count
                        local srcBIDs = #()
                        local srcWts  = #()
                        srcBIDs.count = wc
                        srcWts.count  = wc
                        local ni = 0
                        for w = 1 to wc do
                        (
                            local mBID = boneMap[eBIDs[w]]
                            if mBID > 0 then
                            (
                                ni += 1
                                srcBIDs[ni] = mBID
                                srcWts[ni]  = eWts[w]
                            )
                        )
                        if ni > 0 then
                        (
                            srcBIDs.count = ni
                            srcWts.count  = ni
                            skinOps.ReplaceVertexWeights srcSkin oldV srcBIDs srcWts
                            appliedCount += 1
                        )
                    )
                    if mod newV 2000 == 0 then setProgress pbProgress (55 + 40.0 * newV / total)
                )

                enableSceneRedraw()
                completeRedraw()

                -- 恢复原模型被隐藏的面（无论是否有标记都尝试恢复，确保安全）
                local didUnhide = false
                if classOf srcObj.baseObject == Editable_Poly then
                (
                    select srcObj
                    max modify mode
                    modPanel.setCurrentObject srcObj.baseObject
                    subObjectLevel = 4
                    srcObj.EditablePoly.unhideAll #Face
                    polyOp.setFaceSelection srcObj #{}
                    subObjectLevel = 0
                    didUnhide = true
                )

                -- 切回Skin修改器，确保视口正确显示
                select srcObj
                max modify mode
                modPanel.setCurrentObject srcSkin

                -- 删除提取模型
                local didDelete = false
                if chkDeleteExt.checked then
                (
                    delete extObj
                    didDelete = true
                )

                completeRedraw()
                redrawViews()
                setProgress pbProgress 100

                local elapsed = (timeStamp() - t1) / 1000.0
                local msg = "权重粘贴完成!  (" + (elapsed as string) + "s)\n\n目标模型: " + srcObj.name + "\n更新顶点数: " + appliedCount as string
                if didUnhide then msg += "\n已恢复隐藏的面"
                if didDelete then msg += "\n已删除提取模型"
                messageBox msg title:"完成"
            )
            catch
            (
                enableSceneRedraw()
                completeRedraw()
                messageBox ("粘贴过程中出错:\n" + (getCurrentException())) title:"错误"
            )
            setProgress pbProgress 0
        )
    )
)

createDialog rlSkinMeshExtract
