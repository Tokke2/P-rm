' Starta_Parmetikett.vbs — Pärmetikett Generator UTAN terminalfönster
' © Copyright Rickard Längkvist - All rights reserved
'
' Dubbelklicka på denna fil så startar appen med pythonw.exe (dolt
' fönster, stil 0) — INGET terminalfönster visas. Filen hittar sin
' egen mapp, så den funkar vart än programmappen ligger.

Option Explicit
Dim sh, fso, katalog
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
katalog = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = katalog
sh.Run "pythonw.exe """ & katalog & "\folder.py""", 0, False
