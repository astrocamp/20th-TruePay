// src/scripts/embed-product.js

export function productCard(productId, canManage, manageToken) {
    return {
        // 狀態
        editMode: false,
        saving: false,
        message: '',
        messageType: '',
        // 商品資料
        productId: productId,
        canManage: canManage,
        manageToken: manageToken,
        productData: {},
        editData: {
            name: '',
            description: '',
            price: 0,
            stock: 0,
            is_active: false
        },
        // 初始化
        init() {
            // 預設把 productData 複製到 editData
            this.editData = {
                name: this.productData.name || '',
                description: this.productData.description || '',
                price: this.productData.price || 0,
                stock: this.productData.stock || 0,
                is_active: this.productData.is_active || false
            };
        },
        toggleEditMode() {
            this.editMode = !this.editMode;
            if (this.editMode) {
                // 進入編輯時同步資料
                this.editData = {
                    name: this.productData.name,
                    description: this.productData.description,
                    price: this.productData.price,
                    stock: this.productData.stock,
                    is_active: this.productData.is_active
                };
            }
        },
        cancelEdit() {
            this.editMode = false;
            this.message = '';
            this.messageType = '';
        },
        async saveProduct() {
            this.saving = true;
            this.message = '';
            this.messageType = '';
            try {
                // 這裡可根據實際 API 實作 PATCH 請求
                // ...
                this.productData = { ...this.editData };
                this.editMode = false;
                this.message = '儲存成功';
                this.messageType = 'success';
            } catch (e) {
                this.message = '儲存失敗';
                this.messageType = 'error';
            } finally {
                this.saving = false;
            }
        }
    };
}

// 若要全域註冊給 Alpine 用
import Alpine from 'alpinejs';
window.productCard = productCard;
Alpine.data('productCard', productCard);
