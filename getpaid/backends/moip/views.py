import logging
from django.urls import reverse
from django import http
from django.views.generic import DetailView
from django.views.generic.base import View
from getpaid.backends.moip import PaymentProcessor
from getpaid.models import Payment

logger = logging.getLogger('getpaid.backends.moip')


class NotificationsView(View):
    """
    This view answers on Moip notifications requests.
    See http://labs.moip.com.br/referencia/nasp/

    The most important logic of this view is delegated to the
    ``PaymentProcessor.processNotification()`` method
    """
    def post(self, request, *args, **kwargs):
        try:
            params = {
                'id': request.POST['id_transacao'],
                'amount': request.POST['valor'],
                'status': request.POST['status_pagamento'],
                'moip_id': request.POST['cod_moip'],
                'email': request.POST['email_consumidor'],
            }
        except KeyError:
            logger.warning('Got malformed POST request: %s' % str(request.POST))
            return http.HttpResponseBadRequest("MALFORMED")

        PaymentProcessor.process_notification(params)
        return http.HttpResponse("OK")


class SuccessView(DetailView):
    """
    This view just redirects to standard backend success link.
    """
    model = Payment

    def render_to_response(self, context, **response_kwargs):
        return http.HttpResponseRedirect(reverse('getpaid:success-fallback', kwargs={'pk': self.object.pk}))
