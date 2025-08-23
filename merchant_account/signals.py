from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Merchant


@receiver(post_save, sender=Merchant)
def send_welcome_mail(sender, instance, created, **kwargs):
    if created:
        subject = "歡迎加入 TruePay！"
        message = f"""
  親愛的 {instance.Name}，

  歡迎加入 TruePay 平台！

  您的商家資訊：
  - 商家名稱：{instance.ShopName}
  - 負責人姓名：{instance.Name}
  - 電子郵件：{instance.Email}
  - 專屬網址：{instance.subdomain}.truepay.com

  您現在可以：
  1. 登入商家後台管理商品
  2. 設定自訂域名功能
  3. 開始建立您的商品頁面

  如有任何問題，請聯繫我們的客服團隊。

  祝您使用愉快！
  TruePay 團隊
          """
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [instance.Email],
                fail_silently=False,
            )
            print(f"✅ 歡迎郵件已發送給 {instance.Email}")
        except Exception as e:
            print(f"❌ 郵件發送失敗：{e}")
