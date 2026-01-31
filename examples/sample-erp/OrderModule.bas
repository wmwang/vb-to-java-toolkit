' ============================================
' OrderModule.bas - 訂單處理模組
' 範例 VB6 程式碼，用於測試解析器
' ============================================
Option Explicit

' 模組級變數
Private g_Connection As ADODB.Connection
Private Const TAX_RATE As Double = 0.05

' ============================================
' 公開方法
' ============================================

' 建立新訂單
Public Function CreateOrder(ByVal CustomerID As Long, ByRef Items() As OrderItem) As Long
    On Error GoTo ErrorHandler
    
    Dim sql As String
    Dim OrderID As Long
    Dim TotalAmount As Double
    Dim i As Integer
    
    ' 計算訂單總金額
    TotalAmount = 0
    For i = LBound(Items) To UBound(Items)
        TotalAmount = TotalAmount + (Items(i).Quantity * Items(i).UnitPrice)
    Next i
    
    ' 建立訂單主表
    sql = "INSERT INTO Orders (CustomerID, OrderDate, TotalAmount, Status) " & _
          "VALUES (" & CustomerID & ", '" & Format(Now, "yyyy-mm-dd hh:nn:ss") & "', " & _
          TotalAmount & ", 'PENDING')"
    
    g_Connection.Execute sql
    
    ' 取得新建立的訂單 ID
    Dim rs As ADODB.Recordset
    Set rs = g_Connection.Execute("SELECT @@IDENTITY AS NewID")
    OrderID = CLng(rs("NewID"))
    rs.Close
    
    ' 建立訂單明細
    For i = LBound(Items) To UBound(Items)
        sql = "INSERT INTO OrderDetails (OrderID, ProductID, Quantity, UnitPrice) " & _
              "VALUES (" & OrderID & ", " & Items(i).ProductID & ", " & _
              Items(i).Quantity & ", " & Items(i).UnitPrice & ")"
        g_Connection.Execute sql
    Next i
    
    CreateOrder = OrderID
    Exit Function
    
ErrorHandler:
    CreateOrder = 0
    Err.Raise Err.Number, "OrderModule.CreateOrder", Err.Description
End Function

' 計算訂單總金額（含稅）
Public Function CalculateOrderTotal(ByVal OrderID As Long) As Double
    On Error GoTo ErrorHandler
    
    Dim rs As ADODB.Recordset
    Dim sql As String
    Dim Subtotal As Double
    Dim DiscountRate As Double
    Dim Tax As Double
    
    ' 查詢訂單明細
    sql = "SELECT SUM(Quantity * UnitPrice) AS Subtotal " & _
          "FROM OrderDetails WHERE OrderID = " & OrderID
    
    Set rs = g_Connection.Execute(sql)
    
    If Not IsNull(rs("Subtotal")) Then
        Subtotal = CDbl(rs("Subtotal"))
    Else
        Subtotal = 0
    End If
    rs.Close
    
    ' 取得客戶折扣
    sql = "SELECT c.MemberLevel, c.TotalPurchase " & _
          "FROM Orders o " & _
          "INNER JOIN Customers c ON o.CustomerID = c.CustomerID " & _
          "WHERE o.OrderID = " & OrderID
    
    Set rs = g_Connection.Execute(sql)
    
    If Not rs.EOF Then
        DiscountRate = GetDiscountRate(CStr(rs("MemberLevel")), CDbl(rs("TotalPurchase")))
    Else
        DiscountRate = 0
    End If
    rs.Close
    
    ' 計算稅金
    Tax = Subtotal * TAX_RATE
    
    ' 最終金額 = 小計 - 折扣 + 稅金
    CalculateOrderTotal = Subtotal * (1 - DiscountRate) + Tax
    
    Set rs = Nothing
    Exit Function
    
ErrorHandler:
    CalculateOrderTotal = 0
    Set rs = Nothing
End Function

' 取得折扣率（業務規則）
Private Function GetDiscountRate(ByVal MemberLevel As String, ByVal TotalPurchase As Double) As Double
    ' 業務規則：根據會員等級和累計消費計算折扣
    Select Case MemberLevel
        Case "PLATINUM"
            GetDiscountRate = 0.2
        Case "VIP"
            If TotalPurchase > 10000 Then
                GetDiscountRate = 0.15
            Else
                GetDiscountRate = 0.1
            End If
        Case "GOLD"
            GetDiscountRate = 0.05
        Case Else
            GetDiscountRate = 0
    End Select
End Function

' 取消訂單
Public Function CancelOrder(ByVal OrderID As Long) As Boolean
    On Error GoTo ErrorHandler
    
    Dim sql As String
    Dim rs As ADODB.Recordset
    
    ' 檢查訂單狀態
    sql = "SELECT Status FROM Orders WHERE OrderID = " & OrderID
    Set rs = g_Connection.Execute(sql)
    
    If rs.EOF Then
        CancelOrder = False
        Exit Function
    End If
    
    ' 業務規則：只有 PENDING 狀態的訂單可以取消
    If CStr(rs("Status")) <> "PENDING" Then
        CancelOrder = False
        rs.Close
        Exit Function
    End If
    rs.Close
    
    ' 更新訂單狀態
    sql = "UPDATE Orders SET Status = 'CANCELLED', " & _
          "CancelDate = '" & Format(Now, "yyyy-mm-dd hh:nn:ss") & "' " & _
          "WHERE OrderID = " & OrderID
    
    g_Connection.Execute sql
    
    CancelOrder = True
    Exit Function
    
ErrorHandler:
    CancelOrder = False
End Function

' 更新訂單狀態
Public Sub UpdateOrderStatus(ByVal OrderID As Long, ByVal NewStatus As String)
    Dim sql As String
    
    ' 驗證狀態值
    Select Case NewStatus
        Case "PENDING", "PROCESSING", "SHIPPED", "DELIVERED", "CANCELLED"
            ' 有效狀態
        Case Else
            Err.Raise vbObjectError + 1001, "OrderModule.UpdateOrderStatus", "無效的訂單狀態"
    End Select
    
    sql = "UPDATE Orders SET Status = '" & NewStatus & "' WHERE OrderID = " & OrderID
    g_Connection.Execute sql
End Sub

' 查詢客戶訂單
Public Function GetCustomerOrders(ByVal CustomerID As Long) As ADODB.Recordset
    Dim sql As String
    
    sql = "SELECT o.OrderID, o.OrderDate, o.TotalAmount, o.Status, " & _
          "COUNT(od.OrderDetailID) AS ItemCount " & _
          "FROM Orders o " & _
          "LEFT JOIN OrderDetails od ON o.OrderID = od.OrderID " & _
          "WHERE o.CustomerID = " & CustomerID & " " & _
          "GROUP BY o.OrderID, o.OrderDate, o.TotalAmount, o.Status " & _
          "ORDER BY o.OrderDate DESC"
    
    Dim rs As ADODB.Recordset
    Set rs = New ADODB.Recordset
    rs.Open sql, g_Connection, adOpenStatic, adLockReadOnly
    
    Set GetCustomerOrders = rs
End Function

' 初始化模組
Public Sub InitModule(ByRef conn As ADODB.Connection)
    Set g_Connection = conn
End Sub

' 類型定義
Public Type OrderItem
    ProductID As Long
    Quantity As Integer
    UnitPrice As Double
End Type
