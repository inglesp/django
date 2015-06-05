from __future__ import unicode_literals

import copy
from collections import OrderedDict

from django.core.exceptions import NON_FIELD_ERRORS, NON_FORM_ERRORS, ValidationError
from django.forms import Form
from django.forms.formsets import BaseFormSet
from django.forms.utils import ErrorDict, ErrorList
from django.forms.widgets import MediaDefiningClass
from django.utils import six
from django.utils.encoding import python_2_unicode_compatible
from django.utils.safestring import mark_safe


class DeclarativeFormsMetaclass(MediaDefiningClass):
    """
    Metaclass that collects Forms declared on the base classes.
    """
    def __new__(mcs, name, bases, attrs):
        # Collect form_classes from current class.
        current_form_classes = []
        for key, value in list(attrs.items()):
            if isinstance(value, type) and issubclass(value, (Form, BaseFormSet)):
                current_form_classes.append((key, value))
                attrs.pop(key)
        current_form_classes.sort(key=lambda x: x[1].creation_counter)
        attrs['base_form_classes'] = OrderedDict(current_form_classes)

        new_class = (super(DeclarativeFormsMetaclass, mcs)
            .__new__(mcs, name, bases, attrs))

        # TODO: Walk through the MRO.

        return new_class


@python_2_unicode_compatible
class BaseFormContainer(object):
    def __init__(self, data=None, files=None, initial=None, auto_id='id_%s', error_class=ErrorList):
        self.is_bound = data is not None
        self.data = data or {}
        self.files = files or {}
        self.initial = initial or {}
        self._errors = None
        self.form_classes = copy.deepcopy(self.base_form_classes)
        self.forms = OrderedDict()
        for name, form_class in self.form_classes.items():
            kwargs = {
                'data': data,
                'files': files,
                'prefix': name,
                'initial': self.initial.get(name),
                'auto_id': auto_id,
                'error_class': error_class,
            }
            self.forms[name] = form_class(**kwargs)

    def __str__(self):
        return self.as_table()

    @property
    def errors(self):
        if self._errors is None:
            self.full_clean()
        return self._errors

    def is_valid(self):
        if not self.is_bound:
            return False

        if not self.errors:
            return True

        for value in self.errors.values():
            if isinstance(value, list):
                if any(value):
                    return False
            else:
                return False

        return True

    def full_clean(self):
        self._errors = ErrorDict()
        if not self.is_bound:
            return
        self.cleaned_data = {}

        self._clean_forms()
        self._clean_form_container()
        self._post_clean()

    def _clean_forms(self):
        for form_name, form in self.forms.items():
            if isinstance(form, Form):
                for field_name, error in form.errors.items():
                    self.add_error(form_name, field_name, error)
            elif isinstance(form, BaseFormSet):
                self._errors[form_name] = form.errors
            else:
                assert False

            try:
                self.cleaned_data[form_name] = form.cleaned_data
            except AttributeError:
                # Cannot call cleaned_data on an invalid FormSet
                pass

    def _clean_form_container(self):
        try:
            cleaned_data = self.clean()
        except ValidationError as e:
            self.add_error(None, None, e)
        else:
            if cleaned_data is not None:
                self.cleaned_data = cleaned_data

    def _post_clean(self):
        pass

    def clean(self):
        return self.cleaned_data

    def has_changed(self):
        return any(form.has_changed() for form in self.forms.values())

    def add_error(self, form, field, error):
        if not isinstance(error, ValidationError):
            error = ValidationError(error)

        if form is None:
            if NON_FORM_ERRORS not in self.errors:
                self._errors[NON_FORM_ERRORS] = ErrorList(error_class='nonfield')
            self._errors[NON_FORM_ERRORS].extend(error.error_list)
            return

        if hasattr(error, 'error_dict'):
            if field is not None:
                raise TypeError(
                    "The argument `field` must be `None` when the `error` "
                    "argument contains errors for multiple fields."
                )
            else:
                error = error.error_dict
        else:
            error = {field or NON_FIELD_ERRORS: error.error_list}

        if form not in self.errors:
            self._errors[form] = ErrorDict()

        for field, error_list in error.items():
            if field not in self.errors[form]:
                if field != NON_FIELD_ERRORS and field not in self.forms[form].fields:
                    raise ValueError(
                        "'%s' has no field named '%s'." % (self.forms[form].__class__.__name__, field))
                if field == NON_FIELD_ERRORS:
                    self._errors[form][field] = ErrorList(error_class='nonfield')
                else:
                    self._errors[form][field] = ErrorList()
            self._errors[form][field].extend(error_list)
            try:
                del self.cleaned_data[form][field]
            except KeyError:
                pass

    def as_table(self):
        forms = '\n'.join(form.as_table() for form in self.forms.values())
        return mark_safe(forms)

    def as_p(self):
        forms = '\n'.join(form.as_p() for form in self.forms.values())
        return mark_safe(forms)

    def as_ul(self):
        forms = '\n'.join(form.as_ul() for form in self.forms.values())
        return mark_safe(forms)


class FormContainer(six.with_metaclass(DeclarativeFormsMetaclass, BaseFormContainer)):
    pass
