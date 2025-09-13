from django.conf import settings
from django.utils import translation

class LanguageParamMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        lang = request.GET.get("lang") or request.GET.get("language")
        if lang:
            try:
                lang = translation.get_supported_language_variant(lang)
            except LookupError:
                lang = None
        if lang:
            translation.activate(lang)
            request.LANGUAGE_CODE = lang
            response = self.get_response(request)
            if hasattr(request, "session"):
                request.session[settings.LANGUAGE_COOKIE_NAME] = lang
            response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang, samesite="Lax")
            translation.deactivate()
            return response

        return self.get_response(request)