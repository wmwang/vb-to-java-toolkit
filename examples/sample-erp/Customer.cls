' ============================================
' Customer.cls - 客戶資料類別
' 範例 VB6 程式碼，用於測試解析器
' ============================================
Option Explicit

' 類別屬性
Private m_CustomerID As Long
Private m_CustomerName As String
Private m_Email As String
Private m_MemberLevel As String
Private m_CreateDate As Date
Private m_TotalPurchase As Double

' 資料庫連線
Private m_Connection As ADODB.Connection

' ============================================
' 屬性存取器
' ============================================
Public Property Get CustomerID() As Long
    CustomerID = m_CustomerID
End Property

Public Property Let CustomerID(ByVal Value As Long)
    m_CustomerID = Value
End Property

Public Property Get CustomerName() As String
    CustomerName = m_CustomerName
End Property

Public Property Let CustomerName(ByVal Value As String)
    m_CustomerName = Value
End Property

Public Property Get MemberLevel() As String
    MemberLevel = m_MemberLevel
End Property

Public Property Let MemberLevel(ByVal Value As String)
    m_MemberLevel = Value
End Property

' ============================================
' 公開方法
' ============================================

' 從資料庫載入客戶資料
Public Function LoadFromDB(ByVal CustomerID As Long) As Boolean
    On Error GoTo ErrorHandler
    
    Dim rs As ADODB.Recordset
    Dim sql As String
    
    sql = "SELECT CustomerID, CustomerName, Email, MemberLevel, CreateDate, TotalPurchase " & _
          "FROM Customers WHERE CustomerID = " & CustomerID
    
    Set rs = New ADODB.Recordset
    rs.Open sql, m_Connection, adOpenForwardOnly, adLockReadOnly
    
    If Not rs.EOF Then
        m_CustomerID = CLng(rs("CustomerID"))
        m_CustomerName = CStr(rs("CustomerName"))
        m_Email = CStr(rs("Email"))
        m_MemberLevel = CStr(rs("MemberLevel"))
        m_CreateDate = CDate(rs("CreateDate"))
        
        If Not IsNull(rs("TotalPurchase")) Then
            m_TotalPurchase = CDbl(rs("TotalPurchase"))
        Else
            m_TotalPurchase = 0
        End If
        
        LoadFromDB = True
    Else
        LoadFromDB = False
    End If
    
    rs.Close
    Set rs = Nothing
    Exit Function
    
ErrorHandler:
    LoadFromDB = False
    Err.Raise Err.Number, "Customer.LoadFromDB", Err.Description
End Function

' 儲存客戶資料到資料庫
Public Function SaveToDB() As Boolean
    On Error GoTo ErrorHandler
    
    Dim sql As String
    
    If m_CustomerID = 0 Then
        ' 新增客戶
        sql = "INSERT INTO Customers (CustomerName, Email, MemberLevel, CreateDate, TotalPurchase) " & _
              "VALUES ('" & m_CustomerName & "', '" & m_Email & "', '" & m_MemberLevel & "', " & _
              "'" & Format(m_CreateDate, "yyyy-mm-dd") & "', " & m_TotalPurchase & ")"
    Else
        ' 更新客戶
        sql = "UPDATE Customers SET " & _
              "CustomerName = '" & m_CustomerName & "', " & _
              "Email = '" & m_Email & "', " & _
              "MemberLevel = '" & m_MemberLevel & "', " & _
              "TotalPurchase = " & m_TotalPurchase & " " & _
              "WHERE CustomerID = " & m_CustomerID
    End If
    
    m_Connection.Execute sql
    SaveToDB = True
    Exit Function
    
ErrorHandler:
    SaveToDB = False
    Err.Raise Err.Number, "Customer.SaveToDB", Err.Description
End Function

' 計算客戶折扣率
Public Function CalculateDiscount() As Double
    ' 業務規則：根據會員等級和消費金額計算折扣
    If m_MemberLevel = "VIP" And m_TotalPurchase > 10000 Then
        CalculateDiscount = 0.15  ' VIP 且消費超過 10000，享 15% 折扣
    ElseIf m_MemberLevel = "VIP" Then
        CalculateDiscount = 0.1   ' VIP 會員享 10% 折扣
    ElseIf m_TotalPurchase > 5000 Then
        CalculateDiscount = 0.05  ' 消費超過 5000 享 5% 折扣
    Else
        CalculateDiscount = 0     ' 無折扣
    End If
End Function

' 升級會員等級
Public Sub UpgradeMemberLevel()
    ' 業務規則：根據消費金額自動升級會員等級
    Select Case m_TotalPurchase
        Case Is >= 50000
            m_MemberLevel = "PLATINUM"
        Case Is >= 20000
            m_MemberLevel = "VIP"
        Case Is >= 5000
            m_MemberLevel = "GOLD"
        Case Else
            m_MemberLevel = "STANDARD"
    End Select
End Sub

' ============================================
' 類別初始化與終止
' ============================================
Private Sub Class_Initialize()
    m_CustomerID = 0
    m_CustomerName = ""
    m_Email = ""
    m_MemberLevel = "STANDARD"
    m_CreateDate = Now
    m_TotalPurchase = 0
End Sub

Private Sub Class_Terminate()
    Set m_Connection = Nothing
End Sub

Public Sub SetConnection(ByRef conn As ADODB.Connection)
    Set m_Connection = conn
End Sub
