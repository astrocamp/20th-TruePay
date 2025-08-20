# TruePay 元件樣式系統

這是一個基於 Django + Tailwind CSS + DaisyUI 的元件樣式系統，讓你可以輕鬆在模板中重複使用一致的 UI 元件。

## 按鈕元件 (Button Component)

### 基本使用

```django
{% include "components/button.html" with label="按鈕文字" %}
```

### 完整參數

```django
{% include "components/button.html" with 
    label="按鈕文字" 
    type="button"
    variant="primary"
    size="md"
    disabled=False
    class="額外的CSS類別"
%}
```

### 參數說明

| 參數 | 類型 | 預設值 | 說明 |
|------|------|--------|------|
| `label` | string | "" | 按鈕顯示的文字 |
| `type` | string | "button" | 按鈕類型：button, submit, reset |
| `variant` | string | "primary" | 樣式變體：primary, secondary, danger, success, outline |
| `size` | string | "md" | 尺寸：sm, md, lg |
| `disabled` | boolean | False | 是否禁用按鈕 |
| `class` | string | "" | 額外的 CSS 類別 |

### 樣式變體

#### Primary (主要)
- 藍色背景 (#007AFF)
- 白色文字
- 適用於主要動作

```django
{% include "components/button.html" with label="主要按鈕" variant="primary" %}
```

#### Secondary (次要)
- 灰色背景
- 深灰色文字
- 適用於次要動作

```django
{% include "components/button.html" with label="次要按鈕" variant="secondary" %}
```

#### Danger (危險)
- 紅色背景
- 白色文字
- 適用於危險操作（刪除等）

```django
{% include "components/button.html" with label="刪除" variant="danger" %}
```

#### Success (成功)
- 綠色背景
- 白色文字
- 適用於成功操作（確認等）

```django
{% include "components/button.html" with label="確認" variant="success" %}
```

#### Outline (外框)
- 白色背景
- 灰色邊框
- 適用於較不突出的動作

```django
{% include "components/button.html" with label="取消" variant="outline" %}
```

### 尺寸選項

#### Small (sm)
- 較小的內距 (px-3 py-2)
- 小字體 (text-sm)

```django
{% include "components/button.html" with label="小按鈕" size="sm" %}
```

#### Medium (md) - 預設
- 標準內距 (px-4 py-2)
- 標準字體

```django
{% include "components/button.html" with label="中按鈕" size="md" %}
```

#### Large (lg)
- 較大內距 (px-6 py-3)
- 大字體 (text-lg)

```django
{% include "components/button.html" with label="大按鈕" size="lg" %}
```

### 實際使用範例

#### 表單提交按鈕
```django
<form>
  <!-- 表單欄位 -->
  {% include "components/button.html" with 
      label="送出" 
      type="submit" 
      variant="primary" 
      size="lg" 
  %}
</form>
```

#### 操作按鈕組
```django
<div class="flex gap-4">
  {% include "components/button.html" with label="儲存" variant="success" %}
  {% include "components/button.html" with label="取消" variant="outline" %}
  {% include "components/button.html" with label="刪除" variant="danger" %}
</div>
```

#### 禁用狀態
```django
{% include "components/button.html" with 
    label="處理中..." 
    disabled=True 
    variant="primary" 
%}
```

## 開發新元件的建議

1. **一致性**: 遵循相同的參數命名慣例
2. **彈性**: 提供 `class` 參數允許額外自定義
3. **預設值**: 為所有參數提供合理的預設值
4. **文件化**: 在元件檔案頂部添加註釋說明

## 技術架構

- **前端**: Tailwind CSS 4.x + DaisyUI 5.x
- **後端**: Django 5.2
- **構建工具**: Vite 7.x
- **JavaScript**: Alpine.js + HTMX

## 開發工作流程

1. 設計元件 → `templates/components/`
2. 構建前端資源 → `npm run build`
3. 在模板中使用 → `{% include "components/..." %}`
4. 測試和調整 → 檢查 `http://127.0.0.1:8000`