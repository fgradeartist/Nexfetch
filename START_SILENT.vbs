Set fso   = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
' 0 = hidden window, False = don't wait
shell.Run "python """ & dir & "\NexFetch.py""", 0, False
