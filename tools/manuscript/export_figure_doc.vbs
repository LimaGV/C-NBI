Option Explicit
Dim word, doc, path, pdf
path = CreateObject("Scripting.FileSystemObject").GetParentFolderName(CreateObject("Scripting.FileSystemObject").GetParentFolderName(CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName))) & "\Papper\Manuscript - CNBI - Section 2 with Figure.docx"
pdf = CreateObject("Scripting.FileSystemObject").GetParentFolderName(CreateObject("Scripting.FileSystemObject").GetParentFolderName(CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName))) & "\Papper\Manuscript - CNBI - Section 2 with Figure QA.pdf"
Set word = CreateObject("Word.Application")
word.Visible = False
word.DisplayAlerts = 0
Set doc = word.Documents.Open(path, False, True, False)
doc.ExportAsFixedFormat pdf, 17
doc.Close False
word.Quit
WScript.Echo pdf
