from django.conf import settings
import sys

def import_backend_modules(submodule=None):
    backends = getattr(settings, 'GETPAID_BACKENDS', [])
    modules = {}
    for backend_name in backends:
        fqmn = backend_name
        if submodule:
            fqmn = '%s.%s' % (fqmn, submodule)
        __import__(fqmn)
        module = sys.modules[fqmn]
        modules[backend_name] = module
    return modules


def get_backend_choices():
    choices = []
    backends = import_backend_modules()
    for name, module in backends.items():
        choices.append((name, module.BACKEND_NAME))
    return choices