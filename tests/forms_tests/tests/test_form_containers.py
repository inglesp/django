from __future__ import unicode_literals

import json

from django.forms import CharField, Form, ValidationError
from django.forms.form_containers import FormContainer
from django.forms.formsets import formset_factory
from django.test import TestCase


class PersonForm(Form):
    first_name = CharField(required=True)
    last_name = CharField()


class PhoneNumberForm(Form):
    phone_number = CharField(min_length=2)


PhoneNumbersFormSet = formset_factory(PhoneNumberForm)


class PersonWithPhoneNumbersFormContainer(FormContainer):
    person = PersonForm
    phone_numbers = PhoneNumbersFormSet


def build_data():
    return {
        'person-first_name': 'John',
        'person-last_name': 'Smith',
        'phone_numbers-TOTAL_FORMS': '2',
        'phone_numbers-INITIAL_FORMS': '1',
        'phone_numbers-0-phone_number': '12345',
        'phone_numbers-1-phone_number': '23456',
    }


class FormContainersTestCase(TestCase):
    def test_is_bound(self):
        f = PersonWithPhoneNumbersFormContainer()
        self.assertFalse(f.is_bound)

        data = build_data()
        f = PersonWithPhoneNumbersFormContainer(data)
        self.assertTrue(f.is_bound)

        f = PersonWithPhoneNumbersFormContainer({})
        self.assertTrue(f.is_bound)

    def test_is_valid(self):
        data = build_data()
        f = PersonWithPhoneNumbersFormContainer(data)
        self.assertTrue(f.is_valid())

        data = build_data()
        del data['person-first_name']
        f = PersonWithPhoneNumbersFormContainer(data)
        self.assertFalse(f.is_valid())

        data = build_data()
        data['phone_numbers-1-phone_number'] = '2'
        f = PersonWithPhoneNumbersFormContainer(data)
        self.assertFalse(f.is_valid())

    def test_errors(self):
        data = build_data()
        del data['person-first_name']
        data['phone_numbers-1-phone_number'] = '2'
        f = PersonWithPhoneNumbersFormContainer(data)
        self.assertEqual(f.errors, {
            'person': {'first_name': ['This field is required.']},
            'phone_numbers': [{}, {'phone_number': ['Ensure this value has at least 2 characters (it has 1).']}]
        })

    def test_errors_as_json(self):
        data = build_data()
        del data['person-first_name']
        data['phone_numbers-1-phone_number'] = '2'
        f = PersonWithPhoneNumbersFormContainer(data)
        errors = json.loads(f.errors.as_json())
        # Fails because:
        #   AttributeError: 'list' object has no attribute 'get_json_data'

    def test_clean(self):
        class PersonWithPhoneNumbersFormContainer(FormContainer):
            person = PersonForm
            phone_numbers = PhoneNumbersFormSet

            def clean(self):
                raise ValidationError('error!')

        data = build_data()
        f = PersonWithPhoneNumbersFormContainer(data)
        self.assertEqual(f.errors, {'phone_numbers': [{}, {}], '__all__': [u'error!']})

    def test_add_error(self):
        data = build_data()
        f = PersonWithPhoneNumbersFormContainer(data)
        f.add_error('person', 'first_name', 'error!')
        self.assertEqual(
            f.errors,
            {
                'person': {'first_name': ['error!']},
                'phone_numbers': [{}, {}]
            }
        )

        f = PersonWithPhoneNumbersFormContainer(data)
        f.add_error('person', None, 'error!')
        self.assertEqual(
            f.errors,
            {
                'person': {'__all__': ['error!']},
                'phone_numbers': [{}, {}]
            }
        )

        f = PersonWithPhoneNumbersFormContainer(data)
        f.add_error(None, None, 'error!')
        self.assertEqual(
            f.errors,
            {
                '__all__': ['error!'],
                'phone_numbers': [{}, {}]
            }
        )

    def test_cleaned_data(self):
        data = build_data()
        f = PersonWithPhoneNumbersFormContainer(data)
        self.assertTrue(f.is_valid())  # cleaned_data is not populated until validation
        self.assertEqual(
            f.cleaned_data,
            {
                'person': {'first_name': 'John', 'last_name': 'Smith'},
                'phone_numbers': [{'phone_number': '12345'}, {'phone_number': '23456'}],
            }
        )

    def test_has_changed(self):
        initial = {
            'person': {'first_name': 'John', 'last_name': 'Smith'},
            'phone_numbers': [{'phone_number': '12345'}, {'phone_number': '23456'}],
        }

        data = build_data()
        f = PersonWithPhoneNumbersFormContainer(data, initial=initial)
        self.assertFalse(f.has_changed())

        data = build_data()
        data['person-first_name'] = 'Johannes'
        data['person-last_name'] = 'Schmidt'
        f = PersonWithPhoneNumbersFormContainer(data, initial=initial)
        self.assertTrue(f.has_changed())

        data = build_data()
        data['phone_numbers-0-phone_number'] = '54321'
        f = PersonWithPhoneNumbersFormContainer(data, initial=initial)
        self.assertTrue(f.has_changed())

    def test_as_table(self):
        data = build_data()
        f = PersonWithPhoneNumbersFormContainer(data)
        self.assertHTMLEqual(f.as_table(), '<tr><th><label for="id_person-first_name">First name:</label></th><td><input id="id_person-first_name" name="person-first_name" type="text" value="John" /></td></tr><tr><th><label for="id_person-last_name">Last name:</label></th><td><input id="id_person-last_name" name="person-last_name" type="text" value="Smith" /></td></tr><input id="id_phone_numbers-TOTAL_FORMS" name="phone_numbers-TOTAL_FORMS" type="hidden" value="2" /><input id="id_phone_numbers-INITIAL_FORMS" name="phone_numbers-INITIAL_FORMS" type="hidden" value="1" /><input id="id_phone_numbers-MIN_NUM_FORMS" name="phone_numbers-MIN_NUM_FORMS" type="hidden" /><input id="id_phone_numbers-MAX_NUM_FORMS" name="phone_numbers-MAX_NUM_FORMS" type="hidden" /><tr><th><label for="id_phone_numbers-0-phone_number">Phone number:</label></th><td><input id="id_phone_numbers-0-phone_number" name="phone_numbers-0-phone_number" type="text" value="12345" /></td></tr><tr><th><label for="id_phone_numbers-1-phone_number">Phone number:</label></th><td><input id="id_phone_numbers-1-phone_number" name="phone_numbers-1-phone_number" type="text" value="23456" /></td></tr>')

    def test_as_p(self):
        data = build_data()
        f = PersonWithPhoneNumbersFormContainer(data)
        self.assertHTMLEqual(f.as_p(), '<p><label for="id_person-first_name">First name:</label><input id="id_person-first_name" name="person-first_name" type="text" value="John" /></p><p><label for="id_person-last_name">Last name:</label><input id="id_person-last_name" name="person-last_name" type="text" value="Smith" /></p><input id="id_phone_numbers-TOTAL_FORMS" name="phone_numbers-TOTAL_FORMS" type="hidden" value="2" /><input id="id_phone_numbers-INITIAL_FORMS" name="phone_numbers-INITIAL_FORMS" type="hidden" value="1" /><input id="id_phone_numbers-MIN_NUM_FORMS" name="phone_numbers-MIN_NUM_FORMS" type="hidden" /><input id="id_phone_numbers-MAX_NUM_FORMS" name="phone_numbers-MAX_NUM_FORMS" type="hidden" /><p><label for="id_phone_numbers-0-phone_number">Phone number:</label><input id="id_phone_numbers-0-phone_number" name="phone_numbers-0-phone_number" type="text" value="12345" /></p><p><label for="id_phone_numbers-1-phone_number">Phone number:</label><input id="id_phone_numbers-1-phone_number" name="phone_numbers-1-phone_number" type="text" value="23456" /></p>')

    def test_as_ul(self):
        data = build_data()
        f = PersonWithPhoneNumbersFormContainer(data)
        self.assertHTMLEqual(f.as_ul(), '<li><label for="id_person-first_name">First name:</label><input id="id_person-first_name" name="person-first_name" type="text" value="John" /></li><li><label for="id_person-last_name">Last name:</label><input id="id_person-last_name" name="person-last_name" type="text" value="Smith" /></li><input id="id_phone_numbers-TOTAL_FORMS" name="phone_numbers-TOTAL_FORMS" type="hidden" value="2" /><input id="id_phone_numbers-INITIAL_FORMS" name="phone_numbers-INITIAL_FORMS" type="hidden" value="1" /><input id="id_phone_numbers-MIN_NUM_FORMS" name="phone_numbers-MIN_NUM_FORMS" type="hidden" /><input id="id_phone_numbers-MAX_NUM_FORMS" name="phone_numbers-MAX_NUM_FORMS" type="hidden" /><li><label for="id_phone_numbers-0-phone_number">Phone number:</label><input id="id_phone_numbers-0-phone_number" name="phone_numbers-0-phone_number" type="text" value="12345" /></li><li><label for="id_phone_numbers-1-phone_number">Phone number:</label><input id="id_phone_numbers-1-phone_number" name="phone_numbers-1-phone_number" type="text" value="23456" /></li>')
