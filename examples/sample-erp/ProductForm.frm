' ============================================
' ProductForm.frm - 商品管理表單
' 範例 VB6 程式碼，用於測試解析器
' ============================================
VERSION 5.00
Begin VB.Form frmProduct 
   Caption         =   "商品管理"
   ClientHeight    =   4800
   ClientLeft      =   120
   ClientTop       =   450
   ClientWidth     =   7200
   LinkTopic       =   "Form1"
   ScaleHeight     =   4800
   ScaleWidth      =   7200
End
Attribute VB_Name = "frmProduct"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Option Explicit

' 表單級變數
Private m_Connection As ADODB.Connection
Private m_CurrentProductID As Long

' ============================================
' 表單事件
' ============================================

Private Sub Form_Load()
    ' 初始化表單
    Call LoadProducts
    m_CurrentProductID = 0
End Sub

Private Sub cmdSave_Click()
    ' 儲存商品資料
    On Error GoTo ErrorHandler
    
    Dim sql As String
    
    If m_CurrentProductID = 0 Then
        ' 新增商品
        sql = "INSERT INTO Products (ProductName, CategoryID, UnitPrice, StockQuantity, IsActive) " & _
              "VALUES ('" & txtProductName.Text & "', " & cboCategory.ItemData(cboCategory.ListIndex) & ", " & _
              CDbl(txtPrice.Text) & ", " & CInt(txtStock.Text) & ", " & IIf(chkActive.Value = 1, 1, 0) & ")"
    Else
        ' 更新商品
        sql = "UPDATE Products SET " & _
              "ProductName = '" & txtProductName.Text & "', " & _
              "CategoryID = " & cboCategory.ItemData(cboCategory.ListIndex) & ", " & _
              "UnitPrice = " & CDbl(txtPrice.Text) & ", " & _
              "StockQuantity = " & CInt(txtStock.Text) & ", " & _
              "IsActive = " & IIf(chkActive.Value = 1, 1, 0) & " " & _
              "WHERE ProductID = " & m_CurrentProductID
    End If
    
    m_Connection.Execute sql
    
    MsgBox "儲存成功！", vbInformation
    Call LoadProducts
    Call ClearForm
    Exit Sub
    
ErrorHandler:
    MsgBox "儲存失敗：" & Err.Description, vbCritical
End Sub

Private Sub cmdDelete_Click()
    ' 刪除商品
    On Error GoTo ErrorHandler
    
    If m_CurrentProductID = 0 Then
        MsgBox "請先選擇要刪除的商品", vbExclamation
        Exit Sub
    End If
    
    If MsgBox("確定要刪除此商品嗎？", vbQuestion + vbYesNo) = vbYes Then
        Dim sql As String
        sql = "DELETE FROM Products WHERE ProductID = " & m_CurrentProductID
        m_Connection.Execute sql
        
        MsgBox "刪除成功！", vbInformation
        Call LoadProducts
        Call ClearForm
    End If
    Exit Sub
    
ErrorHandler:
    MsgBox "刪除失敗：" & Err.Description, vbCritical
End Sub

Private Sub lstProducts_Click()
    ' 載入選中的商品
    If lstProducts.ListIndex < 0 Then Exit Sub
    
    Dim ProductID As Long
    ProductID = CLng(lstProducts.ItemData(lstProducts.ListIndex))
    Call LoadProductDetail(ProductID)
End Sub

' ============================================
' 私有方法
' ============================================

Private Sub LoadProducts()
    ' 載入商品清單
    Dim rs As ADODB.Recordset
    Dim sql As String
    
    sql = "SELECT ProductID, ProductName, UnitPrice, StockQuantity " & _
          "FROM Products WHERE IsActive = 1 ORDER BY ProductName"
    
    Set rs = New ADODB.Recordset
    rs.Open sql, m_Connection, adOpenForwardOnly, adLockReadOnly
    
    lstProducts.Clear
    
    Do While Not rs.EOF
        lstProducts.AddItem rs("ProductName") & " - $" & Format(rs("UnitPrice"), "#,##0.00")
        lstProducts.ItemData(lstProducts.NewIndex) = CLng(rs("ProductID"))
        rs.MoveNext
    Loop
    
    rs.Close
    Set rs = Nothing
End Sub

Private Sub LoadProductDetail(ByVal ProductID As Long)
    ' 載入商品詳細資料
    Dim rs As ADODB.Recordset
    Dim sql As String
    
    sql = "SELECT ProductID, ProductName, CategoryID, UnitPrice, StockQuantity, IsActive " & _
          "FROM Products WHERE ProductID = " & ProductID
    
    Set rs = New ADODB.Recordset
    rs.Open sql, m_Connection, adOpenForwardOnly, adLockReadOnly
    
    If Not rs.EOF Then
        m_CurrentProductID = CLng(rs("ProductID"))
        txtProductName.Text = CStr(rs("ProductName"))
        txtPrice.Text = CStr(rs("UnitPrice"))
        txtStock.Text = CStr(rs("StockQuantity"))
        chkActive.Value = IIf(CBool(rs("IsActive")), 1, 0)
        
        ' 設定分類
        Dim i As Integer
        For i = 0 To cboCategory.ListCount - 1
            If cboCategory.ItemData(i) = CLng(rs("CategoryID")) Then
                cboCategory.ListIndex = i
                Exit For
            End If
        Next i
    End If
    
    rs.Close
    Set rs = Nothing
End Sub

Private Sub ClearForm()
    ' 清空表單
    m_CurrentProductID = 0
    txtProductName.Text = ""
    txtPrice.Text = ""
    txtStock.Text = ""
    chkActive.Value = 1
    cboCategory.ListIndex = -1
End Sub

' 驗證庫存是否足夠
Public Function CheckStock(ByVal ProductID As Long, ByVal RequiredQty As Integer) As Boolean
    Dim rs As ADODB.Recordset
    Dim sql As String
    
    sql = "SELECT StockQuantity FROM Products WHERE ProductID = " & ProductID
    Set rs = New ADODB.Recordset
    rs.Open sql, m_Connection, adOpenForwardOnly, adLockReadOnly
    
    If Not rs.EOF Then
        CheckStock = (CInt(rs("StockQuantity")) >= RequiredQty)
    Else
        CheckStock = False
    End If
    
    rs.Close
    Set rs = Nothing
End Function

' 更新庫存
Public Sub UpdateStock(ByVal ProductID As Long, ByVal Quantity As Integer)
    Dim sql As String
    
    ' 業務規則：庫存不能為負數
    If Quantity < 0 Then
        ' 檢查現有庫存
        If Not CheckStock(ProductID, Abs(Quantity)) Then
            Err.Raise vbObjectError + 1002, "ProductForm.UpdateStock", "庫存不足"
        End If
    End If
    
    sql = "UPDATE Products SET StockQuantity = StockQuantity + " & Quantity & _
          " WHERE ProductID = " & ProductID
    m_Connection.Execute sql
End Sub

Public Sub SetConnection(ByRef conn As ADODB.Connection)
    Set m_Connection = conn
End Sub
