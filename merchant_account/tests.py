from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from .models import Merchant
from .forms import RegisterForm, LoginForm, MerchantProfileUpdateForm
from customers_account.models import Customer

Member = get_user_model()


class MerchantRegistrationTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.registration_url = reverse('merchant_account:register')

    def test_merchant_registration_email_uniqueness(self):
        """測試商家註冊email唯一性檢查"""
        # 第一次註冊商家
        form_data = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'ShopName': '測試商店',
            'UnifiedNumber': '12345678',
            'NationalNumber': 'A123456789',
            'Name': '測試負責人',
            'Address': '測試地址',
            'Cellphone': '0912345678'
        }

        form1 = RegisterForm(data=form_data)
        self.assertTrue(form1.is_valid())
        merchant1 = form1.save()
        self.assertIsInstance(merchant1, Merchant)

        # 嘗試用同樣的email再註冊一個商家（應該失敗）
        form_data['ShopName'] = '另一個商店'
        form2 = RegisterForm(data=form_data)
        self.assertFalse(form2.is_valid())
        self.assertIn('此電子郵件已被商家註冊使用', str(form2.errors))

    def test_merchant_customer_email_cross_check(self):
        """測試商家註冊不能使用客戶已註冊的email"""
        # 先註冊一個客戶
        customer_member = Member.objects.create_user(
            username='customer@example.com',
            email='customer@example.com',
            password='testpass123',
            member_type='customer'
        )
        customer = Customer.objects.create(
            member=customer_member,
            name='測試客戶',
            id_number='A123456789',
            phone='0912345678'
        )

        # 嘗試用客戶的email註冊商家（應該失敗）
        form_data = {
            'email': 'customer@example.com',  # 使用客戶已註冊的email
            'password': 'testpass123',
            'ShopName': '測試商店',
            'UnifiedNumber': '12345678',
            'NationalNumber': 'B123456789',
            'Name': '測試負責人',
            'Address': '測試地址',
            'Cellphone': '0987654321'
        }

        form = RegisterForm(data=form_data)
        self.assertTrue(form.is_valid())  # 現在允許商家使用客戶的email註冊


class MerchantVerificationTestCase(TestCase):
    def setUp(self):
        self.member = Member.objects.create_user(
            username='test@example.com',
            email='test@example.com',
            password='testpass123',
            member_type='merchant'
        )
        self.merchant = Merchant.objects.create(
            member=self.member,
            ShopName='測試商店',
            UnifiedNumber='12345678',
            NationalNumber='A123456789',
            Name='測試負責人',
            Address='測試地址',
            Cellphone='0912345678',
            subdomain='testshop'
        )

    def test_merchant_initial_status_is_pending(self):
        """測試新註冊商家初始狀態為待審核"""
        self.assertEqual(self.merchant.verification_status, 'pending')
        self.assertFalse(self.merchant.is_verified())
        self.assertFalse(self.merchant.can_operate())

    def test_merchant_approval_process(self):
        """測試商家審核通過流程"""
        self.merchant.approve_verification()

        self.assertEqual(self.merchant.verification_status, 'approved')
        self.assertTrue(self.merchant.is_verified())
        self.assertTrue(self.merchant.can_operate())
        self.assertIsNotNone(self.merchant.verified_at)

    def test_merchant_rejection_process(self):
        """測試商家審核拒絕流程"""
        reason = '資料不完整'
        self.merchant.reject_verification(reason)

        self.assertEqual(self.merchant.verification_status, 'rejected')
        self.assertFalse(self.merchant.is_verified())
        self.assertFalse(self.merchant.can_operate())
        self.assertEqual(self.merchant.rejection_reason, reason)

    def test_merchant_suspension(self):
        """測試商家暫停營業"""
        # 先通過審核
        self.merchant.approve_verification()
        self.assertTrue(self.merchant.can_operate())

        # 暫停營業
        reason = '違反服務條款'
        self.merchant.suspend_merchant(reason)

        self.assertEqual(self.merchant.verification_status, 'suspended')
        self.assertFalse(self.merchant.can_operate())
        self.assertEqual(self.merchant.rejection_reason, reason)


class MerchantLoginLogoutTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.login_url = reverse('merchant_account:login')
        self.logout_url = reverse('merchant_account:logout')

        # 創建測試商家
        self.member = Member.objects.create_user(
            username='merchant@example.com',
            email='merchant@example.com',
            password='testpass123',
            member_type='merchant'
        )
        self.merchant = Merchant.objects.create(
            member=self.member,
            ShopName='測試商店',
            UnifiedNumber='12345678',
            NationalNumber='A123456789',
            Name='測試負責人',
            Address='測試地址',
            Cellphone='0912345678',
            subdomain='testshop'
        )

    def test_merchant_login_success(self):
        """測試商家登入成功"""
        response = self.client.post(self.login_url, {
            'email': 'merchant@example.com',
            'password': 'testpass123'
        })

        # 應該重導向到dashboard
        self.assertRedirects(response, reverse('merchant_account:dashboard', kwargs={'subdomain': 'testshop'}))

        # 檢查是否已登入
        self.assertTrue(self.client.session.get('_auth_user_id'))

    def test_merchant_duplicate_login_redirect(self):
        """測試已登入商家再次訪問登入頁面會重導向"""
        # 先登入
        self.client.login(username='merchant@example.com', password='testpass123')

        # 再次訪問登入頁面
        response = self.client.get(self.login_url)
        self.assertRedirects(response, reverse('merchant_account:dashboard', kwargs={'subdomain': 'testshop'}))

    def test_merchant_logout_when_logged_in(self):
        """測試已登入商家登出"""
        # 先登入
        self.client.login(username='merchant@example.com', password='testpass123')

        # 登出
        response = self.client.get(self.logout_url)
        self.assertRedirects(response, reverse('merchant_account:login'))

        # 檢查是否已登出
        self.assertIsNone(self.client.session.get('_auth_user_id'))

    def test_merchant_logout_when_not_logged_in(self):
        """測試未登入狀態下訪問登出頁面"""
        response = self.client.get(self.logout_url)
        self.assertRedirects(response, reverse('merchant_account:login'))

    def test_merchant_logout_wrong_user_type(self):
        """測試非商家用戶訪問商家登出頁面"""
        # 創建並登入客戶
        customer_member = Member.objects.create_user(
            username='customer@example.com',
            email='customer@example.com',
            password='testpass123',
            member_type='customer'
        )
        self.client.login(username='customer@example.com', password='testpass123')

        # 嘗試訪問商家登出頁面
        response = self.client.get(self.logout_url)
        self.assertRedirects(response, reverse('merchant_account:login'))


class MerchantAutoApprovalTestCase(TestCase):
    def setUp(self):
        self.member = Member.objects.create_user(
            username='test@example.com',
            email='test@example.com',
            password='testpass123',
            member_type='merchant'
        )

    def test_auto_approval_with_valid_data(self):
        """測試有效資料的自動審核通過"""
        merchant = Merchant.objects.create(
            member=self.member,
            ShopName='優質商店',
            UnifiedNumber='12345678',  # 8位數字
            NationalNumber='A123456789',  # 正確格式
            Name='張三',
            Address='台北市中正區中山南路1號',  # 超過5字元
            Cellphone='0912345678',  # 正確格式
            subdomain='testshop'
        )

        eligible, checks = merchant.check_auto_approval_eligibility()
        self.assertTrue(eligible)

        # 嘗試自動審核
        success, message = merchant.attempt_auto_approval()
        self.assertTrue(success)
        self.assertEqual(merchant.verification_status, 'approved')
        self.assertIsNotNone(merchant.verified_at)

    def test_auto_approval_with_invalid_unified_number(self):
        """測試統一編號格式錯誤的自動審核失敗"""
        merchant = Merchant.objects.create(
            member=self.member,
            ShopName='測試商店',
            UnifiedNumber='123456',  # 錯誤：少於8位
            NationalNumber='A123456789',
            Name='張三',
            Address='台北市中正區中山南路1號',
            Cellphone='0912345678',
            subdomain='testshop'
        )

        eligible, checks = merchant.check_auto_approval_eligibility()
        self.assertFalse(eligible)

        # 檢查具體錯誤
        failed_checks = [check for check in checks if check['status'] == 'failed']
        unified_number_checks = [check for check in failed_checks if check['field'] == 'UnifiedNumber']
        self.assertTrue(len(unified_number_checks) > 0)

    def test_auto_approval_with_invalid_national_number(self):
        """測試身分證字號格式錯誤的自動審核失敗"""
        merchant = Merchant.objects.create(
            member=self.member,
            ShopName='測試商店',
            UnifiedNumber='12345678',
            NationalNumber='123456789',  # 錯誤：沒有英文字母開頭
            Name='張三',
            Address='台北市中正區中山南路1號',
            Cellphone='0912345678',
            subdomain='testshop'
        )

        eligible, checks = merchant.check_auto_approval_eligibility()
        self.assertFalse(eligible)

        # 檢查具體錯誤
        failed_checks = [check for check in checks if check['status'] == 'failed']
        national_number_checks = [check for check in failed_checks if check['field'] == 'NationalNumber']
        self.assertTrue(len(national_number_checks) > 0)

    def test_auto_approval_with_invalid_cellphone(self):
        """測試手機號碼格式錯誤的自動審核失敗"""
        merchant = Merchant.objects.create(
            member=self.member,
            ShopName='測試商店',
            UnifiedNumber='12345678',
            NationalNumber='A123456789',
            Name='張三',
            Address='台北市中正區中山南路1號',
            Cellphone='1234567890',  # 錯誤：沒有09開頭
            subdomain='testshop'
        )

        eligible, checks = merchant.check_auto_approval_eligibility()
        self.assertFalse(eligible)

        # 檢查具體錯誤
        failed_checks = [check for check in checks if check['status'] == 'failed']
        cellphone_checks = [check for check in failed_checks if check['field'] == 'Cellphone']
        self.assertTrue(len(cellphone_checks) > 0)

    def test_auto_approval_with_short_address(self):
        """測試地址過短的自動審核失敗"""
        merchant = Merchant.objects.create(
            member=self.member,
            ShopName='測試商店',
            UnifiedNumber='12345678',
            NationalNumber='A123456789',
            Name='張三',
            Address='台北',  # 錯誤：少於5字元
            Cellphone='0912345678',
            subdomain='testshop'
        )

        eligible, checks = merchant.check_auto_approval_eligibility()
        self.assertFalse(eligible)

        # 檢查具體錯誤
        failed_checks = [check for check in checks if check['status'] == 'failed']
        address_checks = [check for check in failed_checks if check['field'] == 'Address']
        self.assertTrue(len(address_checks) > 0)

    def test_auto_approval_with_short_shop_name(self):
        """測試商店名稱過短的自動審核失敗"""
        merchant = Merchant.objects.create(
            member=self.member,
            ShopName='店',  # 錯誤：少於2字元
            UnifiedNumber='12345678',
            NationalNumber='A123456789',
            Name='張三',
            Address='台北市中正區中山南路1號',
            Cellphone='0912345678',
            subdomain='testshop'
        )

        eligible, checks = merchant.check_auto_approval_eligibility()
        self.assertFalse(eligible)

        # 檢查具體錯誤
        failed_checks = [check for check in checks if check['status'] == 'failed']
        shop_name_checks = [check for check in failed_checks if check['field'] == 'ShopName']
        self.assertTrue(len(shop_name_checks) > 0)

    def test_duplicate_unified_number_rejection(self):
        """測試重複統一編號的自動審核失敗"""
        # 創建第一個商家
        merchant1 = Merchant.objects.create(
            member=self.member,
            ShopName='第一家店',
            UnifiedNumber='12345678',
            NationalNumber='A123456789',
            Name='張三',
            Address='台北市中正區中山南路1號',
            Cellphone='0912345678',
            subdomain='testshop1'
        )

        # 創建第二個商家使用相同統一編號
        member2 = Member.objects.create_user(
            username='test2@example.com',
            email='test2@example.com',
            password='testpass123',
            member_type='merchant'
        )
        merchant2 = Merchant.objects.create(
            member=member2,
            ShopName='第二家店',
            UnifiedNumber='12345678',  # 重複的統一編號
            NationalNumber='B123456789',
            Name='李四',
            Address='台北市大安區忠孝東路1號',
            Cellphone='0987654321',
            subdomain='testshop2'
        )

        eligible, checks = merchant2.check_auto_approval_eligibility()
        self.assertFalse(eligible)

        # 檢查重複統一編號錯誤
        failed_checks = [check for check in checks if check['status'] == 'failed']
        duplicate_checks = [check for check in failed_checks if '已被其他商家使用' in check['message']]
        self.assertTrue(len(duplicate_checks) > 0)

    def test_get_verification_issues_structure(self):
        """測試取得審核問題的資料結構"""
        merchant = Merchant.objects.create(
            member=self.member,
            ShopName='測試商店',
            UnifiedNumber='12345678',
            NationalNumber='A123456789',
            Name='張三',
            Address='台北市中正區中山南路1號',
            Cellphone='0912345678',
            subdomain='testshop'
        )

        verification_info = merchant.get_verification_issues()

        # 檢查回傳資料結構
        self.assertIn('is_approved', verification_info)
        self.assertIn('can_auto_approve', verification_info)
        self.assertIn('checks', verification_info)
        self.assertIsInstance(verification_info['checks'], list)

        # 檢查每個check的結構
        for check in verification_info['checks']:
            self.assertIn('field', check)
            self.assertIn('status', check)
            self.assertIn('message', check)
            self.assertIn(check['status'], ['passed', 'failed', 'disabled'])


class MerchantRegistrationAutoApprovalTestCase(TestCase):
    def test_registration_with_valid_data_auto_approves(self):
        """測試註冊時有效資料自動通過審核"""
        form_data = {
            'email': 'goodmerchant@example.com',
            'password': 'testpass123',
            'ShopName': '優質商店',
            'UnifiedNumber': '12345678',
            'NationalNumber': 'A123456789',
            'Name': '張三',
            'Address': '台北市中正區中山南路1號',
            'Cellphone': '0912345678'
        }

        form = RegisterForm(data=form_data)
        self.assertTrue(form.is_valid(), f"表單驗證失敗：{form.errors}")

        merchant = form.save()

        # 檢查是否自動通過審核
        self.assertEqual(merchant.verification_status, 'approved')
        self.assertIsNotNone(merchant.verified_at)

    def test_registration_with_invalid_data_stays_rejected(self):
        """測試註冊時無效資料保持拒絕狀態"""
        form_data = {
            'email': 'badmerchant@example.com',
            'password': 'testpass123',
            'ShopName': '店',  # 過短
            'UnifiedNumber': '123',  # 錯誤格式
            'NationalNumber': '123456789',  # 錯誤格式
            'Name': '張三',
            'Address': '台北',  # 過短
            'Cellphone': '1234567890'  # 錯誤格式
        }

        form = RegisterForm(data=form_data)
        self.assertTrue(form.is_valid(), "表單本身應該通過基本驗證")

        merchant = form.save()

        # 檢查是否被拒絕
        self.assertEqual(merchant.verification_status, 'rejected')
        self.assertIsNone(merchant.verified_at)
        self.assertIn('自動審核未通過', merchant.rejection_reason)

    def test_registration_auto_approval_with_partial_valid_data(self):
        """測試部分有效資料的註冊審核結果"""
        form_data = {
            'email': 'partialmerchant@example.com',
            'password': 'testpass123',
            'ShopName': '測試商店',  # 正確
            'UnifiedNumber': '12345678',  # 正確
            'NationalNumber': 'A123456789',  # 正確
            'Name': '張三',  # 正確
            'Address': '台北',  # 錯誤：過短
            'Cellphone': '0912345678'  # 正確
        }

        form = RegisterForm(data=form_data)
        self.assertTrue(form.is_valid())

        merchant = form.save()

        # 檢查審核狀態
        self.assertEqual(merchant.verification_status, 'rejected')

        # 檢查審核問題詳情
        verification_info = merchant.get_verification_issues()
        self.assertFalse(verification_info['can_auto_approve'])

        # 應該有地址相關的錯誤
        failed_checks = [check for check in verification_info['checks'] if check['status'] == 'failed']
        address_errors = [check for check in failed_checks if check['field'] == 'Address']
        self.assertTrue(len(address_errors) > 0)


class MerchantProfileUpdateAutoApprovalTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.member = Member.objects.create_user(
            username='updatetest@example.com',
            email='updatetest@example.com',
            password='testpass123',
            member_type='merchant'
        )
        self.merchant = Merchant.objects.create(
            member=self.member,
            ShopName='測試商店',
            UnifiedNumber='123456',  # 錯誤格式，待修正
            NationalNumber='A123456789',
            Name='張三',
            Address='台北',  # 過短，待修正
            Cellphone='0912345678',
            subdomain='updatetest',
            verification_status='rejected',  # 初始為拒絕狀態
            rejection_reason='自動審核未通過：統一編號格式不正確；地址資訊不完整'
        )

    def test_profile_update_fixes_issues_and_auto_approves(self):
        """測試資料更新修正問題後自動通過審核"""
        # 確認初始狀態
        self.assertEqual(self.merchant.verification_status, 'rejected')

        # 模擬表單更新（修正所有問題）
        form_data = {
            'email': 'updatetest@example.com',
            'ShopName': '測試商店',
            'UnifiedNumber': '12345678',  # 修正：改為8位數字
            'NationalNumber': 'A123456789',
            'Name': '張三',
            'Address': '台北市中正區中山南路1號',  # 修正：改為完整地址
            'Cellphone': '0912345678'
        }

        form = MerchantProfileUpdateForm(
            data=form_data,
            instance=self.merchant,
            user=self.member
        )

        self.assertTrue(form.is_valid(), f"表單驗證失敗：{form.errors}")

        # 保存更新
        old_status = self.merchant.verification_status
        updated_merchant = form.save()

        # 檢查是否自動通過審核
        self.assertEqual(old_status, 'rejected')
        self.assertEqual(updated_merchant.verification_status, 'approved')
        self.assertIsNotNone(updated_merchant.verified_at)

    def test_profile_update_partial_fix_stays_rejected(self):
        """測試資料更新只修正部分問題仍保持拒絕狀態"""
        # 確認初始狀態
        self.assertEqual(self.merchant.verification_status, 'rejected')

        # 模擬表單更新（只修正部分問題）
        form_data = {
            'email': 'updatetest@example.com',
            'ShopName': '測試商店',
            'UnifiedNumber': '12345678',  # 修正了統一編號
            'NationalNumber': 'A123456789',
            'Name': '張三',
            'Address': '台北',  # 仍然過短，未修正
            'Cellphone': '0912345678'
        }

        form = MerchantProfileUpdateForm(
            data=form_data,
            instance=self.merchant,
            user=self.member
        )

        self.assertTrue(form.is_valid())

        # 保存更新
        updated_merchant = form.save()

        # 檢查仍為拒絕狀態（因為地址問題未解決）
        self.assertEqual(updated_merchant.verification_status, 'rejected')
        self.assertIsNone(updated_merchant.verified_at)

        # 檢查審核問題詳情
        verification_info = updated_merchant.get_verification_issues()
        failed_checks = [check for check in verification_info['checks'] if check['status'] == 'failed']

        # 應該還有地址相關的錯誤
        address_errors = [check for check in failed_checks if check['field'] == 'Address']
        self.assertTrue(len(address_errors) > 0)

    def test_approved_merchant_update_stays_approved(self):
        """測試已通過審核的商家更新資料後狀態不變"""
        # 設置為已通過審核狀態
        self.merchant.verification_status = 'approved'
        self.merchant.verified_at = timezone.now()
        self.merchant.save()

        form_data = {
            'email': 'updatetest@example.com',
            'ShopName': '新店名',  # 更新店名
            'UnifiedNumber': '87654321',  # 更新統一編號
            'NationalNumber': 'A123456789',
            'Name': '張三',
            'Address': '台北市大安區忠孝東路1號',  # 更新地址
            'Cellphone': '0987654321'  # 更新手機
        }

        form = MerchantProfileUpdateForm(
            data=form_data,
            instance=self.merchant,
            user=self.member
        )

        self.assertTrue(form.is_valid())

        # 保存更新
        updated_merchant = form.save()

        # 檢查狀態保持已通過審核（因為原本就是approved，不會重審）
        self.assertEqual(updated_merchant.verification_status, 'approved')