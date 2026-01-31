# 範例 ERP 系統

這是一個模擬的 VB6 ERP 系統，用於測試 VB 到 Java 遷移工具。

## 檔案說明

| 檔案 | 類型 | 說明 |
|------|------|------|
| `Customer.cls` | Class | 客戶資料類別，包含 CRUD 和會員等級邏輯 |
| `OrderModule.bas` | Module | 訂單處理模組，包含複雜的計價邏輯 |
| `ProductForm.frm` | Form | 商品管理表單，包含 UI 事件 |

## 涵蓋的資料表

從程式碼可推斷出以下資料表：
- `Customers` - 客戶資料
- `Orders` - 訂單主表
- `OrderDetails` - 訂單明細
- `Products` - 商品資料

## 業務規則

1. **會員折扣計算**
   - PLATINUM: 20%
   - VIP + 消費 > 10000: 15%
   - VIP: 10%
   - GOLD: 5%
   - 其他: 0%

2. **訂單狀態流程**
   - PENDING → PROCESSING → SHIPPED → DELIVERED
   - PENDING → CANCELLED

3. **庫存管理**
   - 庫存不能為負數
   - 出貨前需驗證庫存
