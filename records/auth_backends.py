from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

class EmailOrUsernameBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        ident = username or kwargs.get(User.USERNAME_FIELD)
        if not ident or not password:
            return None
        qs = User.objects
        user = None
        if "@" in ident:
            try:
                user = qs.get(email__iexact=ident)
            except User.DoesNotExist:
                return None
        else:
            try:
                user = qs.get(username__iexact=ident)
            except User.DoesNotExist:
                try:
                    user = qs.get(email__iexact=ident)
                except User.DoesNotExist:
                    return None
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
