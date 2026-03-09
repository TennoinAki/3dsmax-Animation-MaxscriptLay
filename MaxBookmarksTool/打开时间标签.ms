-- ============================================================
-- Timeline Bookmarks 启动器 v2
-- 拖拽此文件到 Max 视口即可启动 / Drag into Max viewport to launch
-- by：一方狂三
-- ============================================================
(
    -- 获取本 ms 文件所在目录
    local msDir      = getFilenamePath (getSourceFileName())
    local scriptPath = msDir + "MaxBookmarksTool.py"

    if not (doesFileExist scriptPath) then
    (
        messageBox ("找不到脚本文件：\n" + scriptPath + "\n\n请确认 MaxBookmarksTool.py 与本文件在同一目录。") \
            title:"Timeline Bookmarks"
    )
    else
    (
        -- ★ 复制到纯 ASCII 临时路径，彻底解决中文目录编码问题
        local tempDir  = sysInfo.tempDir
        local tempPath = tempDir + "MaxBookmarksTool_launcher.py"

        copyFile scriptPath tempPath

        -- 统一正斜杠，防止 Python 字符串转义问题
        local pyPath = substituteString tempPath "\\" "/"

        -- 用 importlib 方式读取，保证 utf-8 编码正确
        local pyCmd = "exec(open(r'" + pyPath + "', encoding='utf-8').read())"

        try
        (
            python.execute pyCmd
        )
        catch
        (
            local err = getCurrentException()
            messageBox ("启动失败：\n" + err) title:"Timeline Bookmarks"
        )
    )
)
