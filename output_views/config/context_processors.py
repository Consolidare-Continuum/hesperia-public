import django


def django_version(_request):
    return {"django_version": django.get_version()}
