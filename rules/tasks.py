import io
import re
import os
import yara

from collections import defaultdict
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.contrib.auth.models import Group
from django.conf import settings
from celery import Task

from .services import build_yarafile
from .REST_filters import YaraRuleFilter
from .models import YaraRule, YaraTestFolder


class TestRule(Task):

    def run(self, group_name, query_params, folder_name, submitter_email, **kwargs):
        try:
            folder_object = YaraTestFolder.objects.get(name=folder_name)
            group_object = Group.objects.get(name=group_name)

            if os.path.exists(folder_object.path):
                queryset = YaraRule.objects.filter(owner=group_context)
                queryset = YaraRuleFilter(query_params, queryset=queryset).qs
                ruleset = build_yarafile(queryset).getvalue()
                externals = kwargs.get('externals', {})

                rules = yara.compile(source=ruleset,
                                     externals=externals)

                match_mapping = defaultdict(list)
                rule_count = queryset.count()
                file_count = 0

                for root, dirs, files in os.walk(folder_object.path):
                    for name in files:
                        file_count += 1
                        filepath = os.path.join(root, name)
                        for match in rules.match(filepath):
                            match_mapping[match].append(filepath)

                self.send_results(ruleset, submitter_email,
                                  matches=match_mapping,
                                  externals=externals,
                                  rule_count=rule_count,
                                  file_count=file_count,
                                  folder_name=folder_object.name,
                                  folder_description=folder_object.description)
            else:
                raise ObjectDoesNotExist

        except ObjectDoesNotExist:
            self.notify_failure(submitter_email,
                                group=group_name,
                                folder=folder_name,
                                reason='Unable to access folder')

        except yara.SyntaxError:
            self.notify_failure(submitter_email,
                                group=group_name,
                                folder=folder_name,
                                reason='Syntax error in ruleset')

        except Exception:
            self.notify_failure(submitter_email,
                                group=group_name,
                                folder=folder_name,
                                reason='Unknown error occurred')

        def send_results(self, ruleset, recipient, **template_context):
            plaintext_template = get_template('emails/YaraTestResultsEmail.txt')
            html_template = get_template('emails/YaraTestResultsEmail.html')

            message = EmailMultiAlternatives('YaraGuardian Ruleset Test Results',
                                             plaintext_template.render(template_context),
                                             settings.DEFAULT_FROM_EMAIL,
                                             [recipient])

            message.attach_alternative(html_template.render(template_context), 'text/html')
            message.attach('ruleset.yara', ruleset, 'text/plain')
            message.send()

        def notify_failure(self, recipient, **template_context):
            plaintext_template = get_template('emails/YaraTestFailureEmail.txt')
            html_template = get_template('emails/YaraTestFailureEmail.html')

            message = EmailMultiAlternatives('YaraGuardian Ruleset Test Failure',
                                             plaintext_template.render(template_context),
                                             settings.DEFAULT_FROM_EMAIL,
                                             [recipient])

            message.attach_alternative(html_template.render(template_context), 'text/html')

            message.send()
