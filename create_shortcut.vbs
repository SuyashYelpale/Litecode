Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = oWS.SpecialFolders("Desktop") & "\LiteCode.lnk"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = oWS.CurrentDirectory & "\dist\LiteCode\LiteCode.exe"
oLink.WorkingDirectory = oWS.CurrentDirectory & "\dist\LiteCode"
oLink.IconLocation = oWS.CurrentDirectory & "\app\static\app.ico"
oLink.Description = "LiteCode Application"
oLink.Save