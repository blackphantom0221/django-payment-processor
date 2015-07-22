# encoding: utf8
from django import forms
from django.utils import six

from . import PaymentProcessor


if six.PY3:
    unicode = str


class CurrencyField(forms.Field):

    def to_python(self, value):
        try:
            val_int = int(value)
            currency = PaymentProcessor.get_currency_by_number(val_int)
            if currency:
                return currency
        except (ValueError, TypeError):
            pass

        val = unicode(value).upper()
        if PaymentProcessor.get_number_for_currency(val):
            return val

    def validate(self, value):

        try:
            val_int = int(value)
            if PaymentProcessor.get_currency_by_number(val_int):
                return
        except (ValueError, TypeError):
            pass

        try:
            val = unicode(value).upper()
            if PaymentProcessor.get_number_for_currency(val):
                return
        except:
            pass

        raise forms.ValidationError("currency not found")


class EpaydkOnlineForm(forms.Form):
    """
        Available params:

        txnid    Integer    Transaction identifier which is created with the
            payment in ePay's system. Your reference to the payment
            in ePay.    Yes
        orderid    String    Order ID linked to the payment in ePay. Your
            reference to the payment in your own system.    Yes
        amount    Integer    Amount authorised on the customer’s credit card.
            Minor units    Yes
        currency    Integer    Currency code of the payment.    Yes
        date    Date    The date of the payment in the format (YYYYMMDD).
                Yes
        time    Integer    Timestamp for the completion of the payment.
            For instance, the value "1223" equals 12:23 (a.m.).    Yes
        hash    String    MD5 stamp generated by the values of all accept
            parameters + secret key.    Yes
        fraud    Integer    This parameter is only transmitted if you've
            enabled Fraud Fighter. If Fraud Fighter is enabled, this value
            is 0 if no fraud is detected, and 1 if there is any suspicion 
            that fraud in involved.    No
        payercountry    String    If Fraud Fighter is enabled, the country
            code of the payer is returned in ISO 3166 format (AN2).    No
        issuercountry    String    If Fraud Fighter is enabled, the country
            code of card issuer is returned in ISO 3166 format (AN2)    No
        txnfee    Integer    The transaction fee placed on the customer
            (in minor units). If no fee is added, the value is 0.    Yes
        subscriptionid    Integer    If the parameter subscription is set
            to 1 and the subscription is created, this will contain the
            unique identifier for the subscription.    No
        paymenttype    Integer    The payment type of the payment.    Yes
        cardno    String    Truncated card number formatted like
            444444XXXXXX4444.    No

        @see http://tech.epay.dk/en/specification
        @see http://tech.epay.dk/en/accept-callback-parameters
    """

    txnid = forms.IntegerField(required=True)
    orderid = forms.CharField(required=True)
    amount = forms.IntegerField(required=True)
    currency = CurrencyField(required=True)
    date = forms.DateField(required=True, input_formats=['%Y-%m-%d', '%Y%m%d'])
    time = forms.TimeField(required=True, input_formats=['%H%M', '%H%M%S'])
    hash = forms.CharField(required=True, max_length=32)
    fraud = forms.IntegerField(required=False)
    payercountry = forms.CharField(required=False, max_length=2)
    issuercountry = forms.CharField(required=False, max_length=2)
    txnfee = forms.IntegerField(required=True)
    subscriptionid = forms.IntegerField(required=False)
    paymenttype = forms.IntegerField(required=True)
    cardno = forms.CharField(required=False)


class EpaydkCancellForm(forms.Form):
    orderid = forms.IntegerField(required=True)
    error = forms.IntegerField(required=False)
