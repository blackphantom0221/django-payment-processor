import uuid

import pendulum
import swapper
from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from . import signals
from .registry import registry

PAYMENT_STATUS_CHOICES = (
    ('new', _("new")),
    ('in_progress', _("in progress")),
    ('accepted_for_proc', _("accepted for processing")),
    ('partially_paid', _("partially paid")),
    ('paid', _("paid")),
    ('cancelled', _("cancelled")),
    ('failed', _("failed")),
)


class AbstractOrder(models.Model):
    class Meta:
        abstract = True

    def get_redirect_url(self, *args, success=None, **kwargs):
        """
        Method used to determine the final url the client should see after
        returning from gateway. Client will be redirected to this url after
        backend handled the original callback (i.e. updated payment status)
        and only if SUCCESS_URL or FAILURE_URL settings are NOT set.
        By default it returns the result of `get_absolute_url`
        """
        return self.get_absolute_url()

    def get_absolute_url(self):
        raise NotImplementedError

    def is_ready_for_payment(self):
        """Most of the validation is made in PaymentMethodForm using but if you
        need any extra validation. For example you most probably want to disable
        making another payment for order that is already paid."""
        return True

    def get_items(self):
        """
        There are backends that require some sort of item list to be attached
        to the payment. But it's up to you if the list is real or contains only
        one item called "Payment for stuff in {myshop}" ;)
        :return: List of {"name": str, "quantity": Decimal, "unit_price": Decimal} dicts.
        """
        raise NotImplementedError

    def get_total_amount(self):
        """
        This method must return the total value of the Order.
        :return: Decimal object
        """
        raise NotImplementedError

    def get_user_info(self):
        """
        This method should return dict with necessary user info.
        For most backends email should be sufficient.
        Expected field names: `email`, `first_name`, `last_name`, `phone`
        :return:
        """
        raise NotImplementedError

    def get_description(self):
        raise NotImplementedError


class AbstractPayment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(swapper.get_model_name('getpaid', 'Order'), verbose_name=_("order"),
                              on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(_("amount"), decimal_places=4, max_digits=20)
    currency = models.CharField(_("currency"), max_length=3)
    status = models.CharField(_("status"), max_length=20, choices=PAYMENT_STATUS_CHOICES, default='new', db_index=True)
    backend = models.CharField(_("backend"), max_length=50)
    created_on = models.DateTimeField(_("created on"), auto_now_add=True, db_index=True)
    paid_on = models.DateTimeField(_("paid on"), blank=True, null=True, default=None, db_index=True)
    amount_paid = models.DecimalField(_("amount paid"), decimal_places=4, max_digits=20, default=0)
    external_id = models.CharField(_("external id"), max_length=64, blank=True, null=True)
    description = models.CharField(_("description"), max_length=128, blank=True, null=True)

    class Meta:
        abstract = True
        ordering = ['-created_on']
        verbose_name = _('Payment')
        verbose_name_plural = _('Payments')

    def __str__(self):
        return "Payment #{self.id}".format(self=self)

    def get_processor(self):
        processor = registry[self.backend]
        return processor(self)

    def change_status(self, new_status):
        """
        Always change payment status via this method. Otherwise the signal
        will not be emitted.
        """
        if self.status != new_status:
            # do anything only when status is really changed
            old_status = self.status
            self.status = new_status
            self.save()
            signals.payment_status_changed.send(
                sender=self.__class__, instance=self,
                old_status=old_status, new_status=new_status
            )

    def on_success(self, amount=None):
        """
        Called when payment receives successful balance income. It defaults to
        complete payment, but can optionally accept received amount as a parameter
        to handle partial payments.

        Returns boolean value if payment was fully paid
        """
        if getattr(settings, 'USE_TZ', False):
            self.paid_on = pendulum.now('UTC')
        else:
            timezone = getattr(settings, 'TIME_ZONE', 'local')
            self.paid_on = pendulum.now(timezone)
        if amount:
            self.amount_paid = amount
        else:
            self.amount_paid = self.amount
        fully_paid = (self.amount_paid >= self.amount)
        if fully_paid:
            self.change_status('paid')
        else:
            self.change_status('partially_paid')
        return fully_paid

    def on_failure(self):
        """
        Called when payment has failed
        """
        self.change_status('failed')

    def get_redirect_params(self):
        return self.get_processor().get_redirect_params()

    def get_redirect_url(self):
        return self.get_processor().get_redirect_url()

    def get_redirect_method(self):
        return self.get_processor().get_redirect_method()

    def get_form(self, *args, **kwargs):
        return self.get_processor().get_form(*args, **kwargs)

    def handle_callback(self, request, *args, **kwargs):
        return self.get_processor().handle_callback(request, *args, **kwargs)

    def get_items(self):
        """
        Some backends require the list of items to be added to Payment.
        Because both Order and Payment can be customized, let Order handle this.
        """
        return self.order.get_items()

    def fetch_status(self):
        """
        See BaseProcessor.fetch_status
        """
        return self.get_processor().fetch_status()

    def fetch_and_update_status(self):
        remote_status = self.fetch_status()
        status = remote_status.get('status', None)
        amount = remote_status.get('amount', None)
        if (status is not None and 'paid' in status) or amount is not None:
            self.on_success(amount)
        elif status == 'failed':
            self.on_failure()
        elif status is not None:
            self.change_status(status)

    def get_template_names(self, view=None):
        return self.get_processor().get_template_names(view=view)


class Payment(AbstractPayment):
    class Meta(AbstractPayment.Meta):
        swappable = swapper.swappable_setting('getpaid', 'Payment')
