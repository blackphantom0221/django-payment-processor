""""
Settings:
    pos_id
    second_key
    client_id
    client_secret
"""
import json
import logging
import os
from urllib.parse import urljoin

import requests
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse, reverse_lazy

from getpaid.post_forms import PaymentHiddenInputsPostForm
from getpaid.processor import BaseProcessor
from getpaid.status import PaymentStatus as ps

logger = logging.getLogger(__name__)


class PaymentProcessor(BaseProcessor):
    slug = "dummy"
    display_name = "Dummy"
    accepted_currencies = [
        "PLN",
        "EUR",
    ]
    ok_statuses = [200]
    method = "REST"  # Supported modes: REST, POST, GET
    confirmation_method = "PUSH"  # PUSH or PULL
    post_form_class = PaymentHiddenInputsPostForm
    post_template_name = "dummy/payment_post_form.html"
    _token = None
    standard_url = reverse_lazy("paywall:gateway")
    api_url = reverse_lazy("paywall:api_register")

    def get_method(self):
        return self.get_setting("method", self.method)

    def get_confirmation_method(self):
        return self.get_setting("confirmation_method", self.confirmation_method).upper()

    def get_paywall_baseurl(self, request=None):
        if request is None:
            base = os.environ.get("_PAYWALL_URL")
        else:
            base = os.environ["_PAYWALL_URL"] = request.build_absolute_uri("/")
        if self.get_method() == "REST":
            return urljoin(base, str(self.api_url))
        return urljoin(base, str(self.standard_url))

    def get_params(self):
        base = self.get_paywall_baseurl()
        params = {
            "ext_id": self.payment.id,
            "value": self.payment.amount_required,
            "currency": self.payment.currency,
            "description": self.payment.description,
            "success_url": urljoin(
                base,
                reverse("getpaid:payment-success", kwargs={"pk": str(self.payment.pk)}),
            ),
            "failure_url": urljoin(
                base,
                reverse("getpaid:payment-failure", kwargs={"pk": str(self.payment.pk)}),
            ),
        }
        if self.get_confirmation_method() == "PUSH":
            params["callback"] = urljoin(
                base, reverse("getpaid:callback", kwargs={"pk": str(self.payment.pk)})
            )
        return {k: str(v) for k, v in params.items()}

    # Specifics
    def prepare_transaction(self, request, view=None, **kwargs):
        target_url = self.get_paywall_baseurl(request)
        params = self.get_params()
        method = self.get_method()
        if method == "REST":
            response = requests.post(target_url, json=params)
            return HttpResponseRedirect(response.json()["url"])
        elif method == "POST":
            form = self.get_form(params)
            return TemplateResponse(
                request=request,
                template=self.get_template_names(view=view),
                context={"form": form, "paywall_url": target_url},
            )
        else:
            return HttpResponseRedirect(target_url)

    def handle_paywall_callback(self, request, **kwargs):
        new_status = json.loads(request.body).get("new_status")
        if new_status is None:
            raise ValueError("Got no status")
        elif new_status == ps.FAILED:
            self.payment.fail()
        elif new_status == ps.PRE_AUTH:
            self.payment.confirm_lock()
        elif new_status == ps.PAID:
            self.payment.confirm_payment()
        raise ValueError("Unhandled new status")

    def fetch_payment_status(self):
        base = self.get_paywall_baseurl()
        response = requests.get(
            urljoin(
                base,
                reverse(
                    "paywall:get_status", kwargs={"pk": str(self.payment.external_id)}
                ),
            )
        )
        if response.status_code != 200:
            raise Exception("Error occurred!")
        status = response.json()["payment_status"]
        results = {}
        if status == ps.PAID:
            results["callback"] = "confirm_payment"
        elif status == ps.PRE_AUTH:
            results["callback"] = "confirm_lock"
        elif status == ps.PREPARED:
            results["callback"] = "confirm_prepared"
        elif status == ps.FAILED:
            results["callback"] = "fail"
        return results

    def charge(self, amount=None, **kwargs):
        raise NotImplementedError

    def release_lock(self, **kwargs):
        raise NotImplementedError

    def start_refund(self, amount=None, **kwargs):
        raise NotImplementedError

    def cancel_refund(self):
        raise NotImplementedError
