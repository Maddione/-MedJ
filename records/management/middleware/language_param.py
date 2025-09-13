from django.conf import settings
from django.utils import translation

class LanguageParamMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        lang = request.GET.get("lang") or request.GET.get("language")
        if lang and lang in dict(getattr(settings, "LANGUAGES", ())):
            translation.activate(lang)
            request.LANGUAGE_CODE = lang
            # proceed to view
            response = self.get_response(request)
            # persist choice
            if hasattr(request, "session"):
                request.session[settings.LANGUAGE_COOKIE_NAME] = lang
            response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang, samesite="Lax")
            translation.deactivate()
            return response

        return self.get_response(request)
