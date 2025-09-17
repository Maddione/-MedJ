import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE","medj.settings")
import django; django.setup()
from django.test import Client
from django.contrib.auth import get_user_model

u="apiadmin"; p="Pass123!"
User=get_user_model()
obj,created=User.objects.get_or_create(username=u,defaults={"email":"api@local"})
if created:
    obj.set_password(p); obj.is_staff=True; obj.is_superuser=True; obj.save()

c=Client(); assert c.login(username=u,password=p)
payload = {"text":"Еритроцити 4.87 T/L 3.70-5.4\nХемоглобин 142 g/L 115-160","specialty_id":1}
r=c.post("/api/upload/analyze/", data=payload, content_type="application/json")
print("STATUS:", r.status_code)
print("BODY:", r.content.decode()[:800])
