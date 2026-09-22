Option Explicit
Dim word, doc, path, pdf, tbl, label, rng, n, om
path = CreateObject("Scripting.FileSystemObject").GetParentFolderName(CreateObject("Scripting.FileSystemObject").GetParentFolderName(CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName))) & "\Papper\Manuscript - CNBI - Section 2.docx"
pdf = CreateObject("Scripting.FileSystemObject").GetParentFolderName(CreateObject("Scripting.FileSystemObject").GetParentFolderName(CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName))) & "\Papper\Manuscript - CNBI - Section 2 QA.pdf"
Set word = GetObject(, "Word.Application")
word.DisplayAlerts = 0
Set doc = word.Documents.Open(path, False, False, False)
On Error Resume Next
doc.Windows(1).Visible = False
On Error GoTo 0
n = 0
For Each tbl In doc.Tables
  If tbl.Columns.Count = 3 Then
    label = tbl.Cell(1,3).Range.Text
    label = Replace(label, Chr(13), "")
    label = Replace(label, Chr(7), "")
    If Left(label,1) = "(" And Right(label,1) = ")" Then
      Set rng = tbl.Cell(1,2).Range
      rng.End = rng.End - 2
      If Len(Trim(rng.Text)) > 0 And rng.OMaths.Count = 0 Then
        doc.OMaths.Add rng
        n = n + 1
      End If
    End If
  End If
Next
For Each om In doc.OMaths
  om.BuildUp
Next
doc.Save
doc.ExportAsFixedFormat pdf, 17
doc.Close False
WScript.Echo "converted=" & n
