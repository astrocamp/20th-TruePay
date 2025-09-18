from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from .models import Customer
from .forms import CustomerRegistrationForm, CustomerLoginForm
from merchant_account.models import Merchant

Member = get_user_model()


class CustomerRegistrationTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.registration_url = reverse('customers_account:register')

    def test_customer_registration_success(self):
        """測試客戶註冊成功"""
        form_data = {
            'email': 'customer@example.com',
            'password': 'testpass123',
            'password_confirm': 'testpass123',
            'name': '測試客戶',
            'id_number': 'A123456789',
            'birth_date': '1990-01-01',
            'phone': '0912345678'
        }

        form = CustomerRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())
        customer = form.save()
        self.assertIsInstance(customer, Customer)
        self.assertEqual(customer.name, '測試客戶')

    def test_customer_birth_date_validation(self):
        """測試生日欄位驗證（不能是未來日期）"""
        future_date = timezone.now().date().replace(year=timezone.now().year + 1)

        form_data = {
            'email': 'customer@example.com',
            'password': 'testpass123',
            'password_confirm': 'testpass123',
            'name': '測試客戶',
            'id_number': 'A123456789',
            'birth_date': future_date.isoformat(),
            'phone': '0912345678'
        }

        form = CustomerRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('生日不能是未來的日期', str(form.errors))

    def test_customer_password_length_validation(self):
        """測試密碼長度驗證（至少8個字元）"""
        form_data = {
            'email': 'customer@example.com',
            'password': '123',  # 少於8個字元
            'password_confirm': '123',
            'name': '測試客戶',
            'id_number': 'A123456789',
            'birth_date': '1990-01-01',
            'phone': '0912345678'
        }

        form = CustomerRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('密碼長度至少需要8個字元', str(form.errors))

    def test_customer_password_confirmation(self):
        """測試密碼確認驗證"""
        form_data = {
            'email': 'customer@example.com',
            'password': 'testpass123',
            'password_confirm': 'differentpass123',  # 不匹配的確認密碼
            'name': '測試客戶',
            'id_number': 'A123456789',
            'birth_date': '1990-01-01',
            'phone': '0912345678'
        }

        form = CustomerRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('密碼確認不相符', str(form.errors))

    def test_customer_id_number_format_validation(self):
        """測試身分證字號格式驗證"""
        form_data = {
            'email': 'customer@example.com',
            'password': 'testpass123',
            'password_confirm': 'testpass123',
            'name': '測試客戶',
            'id_number': '123456789',  # 錯誤格式
            'birth_date': '1990-01-01',
            'phone': '0912345678'
        }

        form = CustomerRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('身分證字號格式不正確', str(form.errors))

    def test_customer_phone_format_validation(self):
        """測試手機號碼格式驗證"""
        form_data = {
            'email': 'customer@example.com',
            'password': 'testpass123',
            'password_confirm': 'testpass123',
            'name': '測試客戶',
            'id_number': 'A123456789',
            'birth_date': '1990-01-01',
            'phone': '123456789'  # 錯誤格式
        }

        form = CustomerRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('手機號碼格式不正確', str(form.errors))

    def test_customer_email_uniqueness(self):
        """測試客戶註冊email唯一性檢查"""
        # 先註冊一個客戶
        member1 = Member.objects.create_user(
            username='customer1@example.com',
            email='customer1@example.com',
            password='testpass123',
            member_type='customer'
        )
        customer1 = Customer.objects.create(
            member=member1,
            name='第一個客戶',
            id_number='A123456789',
            phone='0912345678'
        )

        # 嘗試用同樣的email再註冊（應該失敗）
        form_data = {
            'email': 'customer1@example.com',
            'password': 'testpass123',
            'password_confirm': 'testpass123',
            'name': '第二個客戶',
            'id_number': 'B123456789',
            'birth_date': '1990-01-01',
            'phone': '0987654321'
        }

        form = CustomerRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('此電子郵件已被註冊使用', str(form.errors))


class CustomerLoginLogoutTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.login_url = reverse('customers_account:login')
        self.logout_url = reverse('customers_account:logout')

        # 創建測試客戶
        self.member = Member.objects.create_user(
            username='customer@example.com',
            email='customer@example.com',
            password='testpass123',
            member_type='customer'
        )
        self.customer = Customer.objects.create(
            member=self.member,
            name='測試客戶',
            id_number='A123456789',
            phone='0912345678'
        )

    def test_customer_login_success(self):
        """測試客戶登入成功"""
        response = self.client.post(self.login_url, {
            'email': 'customer@example.com',
            'password': 'testpass123'
        })

        # 應該重導向到marketplace
        self.assertRedirects(response, reverse('pages:marketplace'))

        # 檢查是否已登入
        self.assertTrue(self.client.session.get('_auth_user_id'))

    def test_customer_login_wrong_password(self):
        """測試客戶登入錯誤密碼"""
        response = self.client.post(self.login_url, {
            'email': 'customer@example.com',
            'password': 'wrongpassword'
        })

        # 應該返回登入頁面並顯示錯誤
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'form')

        # 檢查是否未登入
        self.assertIsNone(self.client.session.get('_auth_user_id'))

    def test_customer_duplicate_login_redirect(self):
        """測試已登入客戶再次訪問登入頁面會重導向"""
        # 先登入
        self.client.login(username='customer@example.com', password='testpass123')

        # 再次訪問登入頁面
        response = self.client.get(self.login_url)
        self.assertRedirects(response, reverse('pages:marketplace'))

    def test_customer_logout_when_logged_in(self):
        """測試已登入客戶登出"""
        # 先登入
        self.client.login(username='customer@example.com', password='testpass123')

        # 登出
        response = self.client.get(self.logout_url)
        self.assertRedirects(response, reverse('pages:home'))

        # 檢查是否已登出
        self.assertIsNone(self.client.session.get('_auth_user_id'))

    def test_customer_logout_when_not_logged_in(self):
        """測試未登入狀態下訪問登出頁面"""
        response = self.client.get(self.logout_url)
        self.assertRedirects(response, reverse('customers_account:login'))

    def test_customer_logout_wrong_user_type(self):
        """測試非客戶用戶訪問客戶登出頁面"""
        # 創建並登入商家
        merchant_member = Member.objects.create_user(
            username='merchant@example.com',
            email='merchant@example.com',
            password='testpass123',
            member_type='merchant'
        )
        self.client.login(username='merchant@example.com', password='testpass123')

        # 嘗試訪問客戶登出頁面
        response = self.client.get(self.logout_url)
        self.assertRedirects(response, reverse('customers_account:login'))


class CustomerFormValidationTestCase(TestCase):
    def test_customer_registration_form_required_fields(self):
        """測試客戶註冊表單必填欄位"""
        # 提交空表單
        form = CustomerRegistrationForm(data={})
        self.assertFalse(form.is_valid())

        # 檢查必填欄位錯誤
        required_fields = ['email', 'password', 'name']
        for field in required_fields:
            self.assertIn(field, form.errors)

    def test_customer_login_form_validation(self):
        """測試客戶登入表單驗證"""
        # 先創建一個客戶用於測試
        member = Member.objects.create_user(
            username='test@example.com',
            email='test@example.com',
            password='testpass123',
            member_type='customer'
        )
        customer = Customer.objects.create(
            member=member,
            name='測試客戶',
            id_number='A123456789',
            phone='0912345678'
        )

        # 測試正確的登入資料
        form_data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        form = CustomerLoginForm(data=form_data)
        self.assertTrue(form.is_valid())

        # 測試錯誤的密碼
        form_data['password'] = 'wrongpassword'
        form = CustomerLoginForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('電子郵件或密碼錯誤', str(form.errors))