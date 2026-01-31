# 業務規則

## LoadProductDetail 決策邏輯

**來源**: ProductForm.frm / LoadProductDetail

### 決策表

| 條件 | 結果 |
|------|------|
| Not rs.EOF | m_CurrentProductID = CLng(rs("ProductID")) |

### 偽代碼
```
IF Not rs.EOF THEN
    m_CurrentProductID = CLng(rs("ProductID"))
END IF
```
---


---

## CheckStock 決策邏輯

**來源**: ProductForm.frm / CheckStock

### 決策表

| 條件 | 結果 |
|------|------|
| Not rs.EOF | CheckStock = (CInt(rs("StockQuantity")) >= RequiredQty) |
| 其他情況 | CheckStock = False |

### 偽代碼
```
IF Not rs.EOF THEN
    CheckStock = (CInt(rs("StockQuantity")) >= RequiredQty)
ELSE
    CheckStock = False
END IF
```
---

## UpdateStock 決策邏輯

**來源**: ProductForm.frm / UpdateStock

### 決策表

| 條件 | 結果 |
|------|------|
| Quantity < 0 | If Not CheckStock(ProductID, Abs(Quantity)) Then |

### 偽代碼
```
IF Quantity < 0 THEN
    If Not CheckStock(ProductID, Abs(Quantity)) Then
END IF
```
---


---


---

## SaveToDB 決策邏輯

**來源**: Customer.cls / SaveToDB

### 決策表

| 條件 | 結果 |
|------|------|
| m_CustomerID = 0 | sql = "INSERT INTO Customers (CustomerName, Email, MemberLevel, CreateDate, TotalPurchase) " & _ |
| 其他情況 | sql = "UPDATE Customers SET " & _ |

### 偽代碼
```
IF m_CustomerID = 0 THEN
    sql = "INSERT INTO Customers (CustomerName, Email, MemberLevel, CreateDate, TotalPurchase) " & _
ELSE
    sql = "UPDATE Customers SET " & _
END IF
```
---

## CalculateDiscount 決策邏輯

**來源**: Customer.cls / CalculateDiscount

### 決策表

| 條件 | 結果 |
|------|------|
| m_MemberLevel = "VIP" And m_TotalPurchase > 10000 | CalculateDiscount = 0.15  ' VIP 且消費超過 10000，享 15% 折扣 |
| m_MemberLevel = "VIP" | CalculateDiscount = 0.1   ' VIP 會員享 10% 折扣 |
| m_TotalPurchase > 5000 | CalculateDiscount = 0.05  ' 消費超過 5000 享 5% 折扣 |
| 其他情況 | CalculateDiscount = 0     ' 無折扣 |

### 偽代碼
```
IF m_MemberLevel = "VIP" And m_TotalPurchase > 10000 THEN
    CalculateDiscount = 0.15  ' VIP 且消費超過 10000，享 15% 折扣
ELSE IF m_MemberLevel = "VIP" THEN
    CalculateDiscount = 0.1   ' VIP 會員享 10% 折扣
ELSE IF m_TotalPurchase > 5000 THEN
    CalculateDiscount = 0.05  ' 消費超過 5000 享 5% 折扣
ELSE
    CalculateDiscount = 0     ' 無折扣
END IF
```
---

## UpgradeMemberLevel 狀態邏輯 (m_TotalPurchase)

**來源**: Customer.cls / UpgradeMemberLevel

### 決策表

| 條件 | 結果 |
|------|------|
| m_TotalPurchase = Is >= 50000 | m_MemberLevel = "PLATINUM" |
| m_TotalPurchase = Is >= 20000 | m_MemberLevel = "VIP" |
| m_TotalPurchase = Is >= 5000 | m_MemberLevel = "GOLD" |
| m_TotalPurchase = Else | m_MemberLevel = "STANDARD" |

### 偽代碼
```
IF m_TotalPurchase = Is >= 50000 THEN
    m_MemberLevel = "PLATINUM"
ELSE IF m_TotalPurchase = Is >= 20000 THEN
    m_MemberLevel = "VIP"
ELSE IF m_TotalPurchase = Is >= 5000 THEN
    m_MemberLevel = "GOLD"
ELSE IF m_TotalPurchase = Else THEN
    m_MemberLevel = "STANDARD"
END IF
```
---


---

## CalculateOrderTotal 決策邏輯

**來源**: OrderModule.bas / CalculateOrderTotal

### 決策表

| 條件 | 結果 |
|------|------|
| Not IsNull(rs("Subtotal")) | Subtotal = CDbl(rs("Subtotal")) |
| 其他情況 | Subtotal = 0 |

### 偽代碼
```
IF Not IsNull(rs("Subtotal")) THEN
    Subtotal = CDbl(rs("Subtotal"))
ELSE
    Subtotal = 0
END IF
```
---

## CalculateOrderTotal 決策邏輯

**來源**: OrderModule.bas / CalculateOrderTotal

### 決策表

| 條件 | 結果 |
|------|------|
| Not rs.EOF | DiscountRate = GetDiscountRate(CStr(rs("MemberLevel")), CDbl(rs("TotalPurchase"))) |
| 其他情況 | DiscountRate = 0 |

### 偽代碼
```
IF Not rs.EOF THEN
    DiscountRate = GetDiscountRate(CStr(rs("MemberLevel")), CDbl(rs("TotalPurchase")))
ELSE
    DiscountRate = 0
END IF
```
---


---


---


---


---

## GetDiscountRate 決策邏輯

**來源**: OrderModule.bas / GetDiscountRate

### 決策表

| 條件 | 結果 |
|------|------|
| TotalPurchase > 10000 | GetDiscountRate = 0.15 |
| 其他情況 | GetDiscountRate = 0.1 |

### 偽代碼
```
IF TotalPurchase > 10000 THEN
    GetDiscountRate = 0.15
ELSE
    GetDiscountRate = 0.1
END IF
```
---

## GetDiscountRate 狀態邏輯 (MemberLevel)

**來源**: OrderModule.bas / GetDiscountRate

### 決策表

| 條件 | 結果 |
|------|------|
| MemberLevel = "PLATINUM" | GetDiscountRate = 0.2 |
| MemberLevel = "VIP" | GetDiscountRate = 0.15 |
| MemberLevel = "GOLD" | GetDiscountRate = 0.05 |
| MemberLevel = Else | GetDiscountRate = 0 |

### 偽代碼
```
IF MemberLevel = "PLATINUM" THEN
    GetDiscountRate = 0.2
ELSE IF MemberLevel = "VIP" THEN
    GetDiscountRate = 0.15
ELSE IF MemberLevel = "GOLD" THEN
    GetDiscountRate = 0.05
ELSE IF MemberLevel = Else THEN
    GetDiscountRate = 0
END IF
```
---

