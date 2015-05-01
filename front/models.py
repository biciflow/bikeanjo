# -*- coding: utf-8 -*-
import json
from datetime import datetime, date
from collections import OrderedDict
from django.contrib.auth.models import AbstractUser
from django.contrib.gis.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

GENDER = (
    ('male', _('Male')),
    ('female', _('Female')),
)

CYCLIST_ROLES = (
    ('volunteer', _('Volunteer')),
    ('requester', _('Requester')),
)


HELP_OFFER = (
    (1, _('Teach someone to ride a bike')),  # Ensinando alguém a pedalar
    (2, _('Follow beginners on cycling')),  # Acompanhando iniciantes nas pedaladas
    (4, _('Advice about safe routes')),  # Recomendando rotas mais seguras
    (8, _('Participating in the events of Bike Anjos')),  # Participando dos eventos dos Bikes Anjos
)

HELP_REQUEST = (
    (16, _('Learn to ride a bike')),  # Aprender a pedalar
    (32, _('Pratice cycling')),  # Praticar pedaladas
    (64, _('Monitoring on traffic')),  # Acompanhamento no trânsito
    (128, _('Route recomendation')),  # Recomendar rota
)

HELP = HELP_OFFER + HELP_REQUEST

VOLUNTEER_EXPERIENCE = (
    ('less than 1 year', _('Less than 1 year')),
    ('from 1 to 2 years', _('From 1 to 2 years')),
    ('from 2 to 4 years', _('From 2 to 4 years')),
    ('more than 4 years', _('More than 4 years')),
)

REQUESTER_EXPERIENCE = (
    ('do not know pedaling yet', _('I do not know pedaling yet')),
    ('no experience in traffic', _('I know cycling, but have no experience in traffic')),
    ('already ride a long time', _('Already ride a long time but not daily')),
    ('use bike almost every day', _('I use bike almost every day')),
)

EXPERIENCE = VOLUNTEER_EXPERIENCE + REQUESTER_EXPERIENCE

BIKE_USE = (
    ('everyday', _('Everyday'),),
    ('just few days a week/month', _('Just few days a week/month'),),
    ('once a week', _('Once a week'),),
    ('no, i use for leisure', _('No, I use for leisure'),),
)


class BaseModel(models.Model):
    """
    All models here should extends this. All models will have
    the created_date and modified_date properties
    """
    created_date = models.DateTimeField(_('created date'), auto_now_add=True, editable=False)
    modified_date = models.DateTimeField(_('modified date'), auto_now=True, editable=False)

    class Meta:
        abstract = True


class User(AbstractUser):
    country = models.CharField(max_length=32, blank=True)
    city = models.CharField(max_length=32, blank=True)
    gender = models.CharField(max_length=24, blank=True)
    birthday = models.DateField(default=date.today, null=True)
    ride_experience = models.CharField(choices=EXPERIENCE, max_length=32, blank=True)
    bike_use = models.CharField(choices=BIKE_USE, max_length=32, blank=True)
    help_with = models.IntegerField(default=0)  # choices=HELP
    initiatives = models.CharField(max_length=256, blank=True)
    role = models.CharField(choices=CYCLIST_ROLES, max_length=32, blank=True)

    def get_avatar_url(self):
        social = self.socialaccount_set.first()
        if social:
            return social.get_avatar_url()
        # TODO: avatar field
        return 'http://placehold.it/85x85'

    def help_labels(self):
        for code, label in HELP:
            if self.help_with >= code:
                break
            if self.help_with & code:
                yield label


class HelpStatusQuerySet(models.QuerySet):
    def active(self):
        return self.filter(status__in=['new', 'assigned'])

    def new(self):
        return self.filter(status='new')

    def assigned(self):
        return self.filter(status='assigned')

    def closed(self):
        return self.filter(status__in=['canceled', 'attended'])

    def canceled(self):
        return self.filter(status='canceled')

    def attended(self):
        return self.filter(status='attended')


class HelpRequest(BaseModel):
    STATUS = OrderedDict((
        ('new', _('New')),
        ('assigned', _('Assigned')),
        ('canceled', _('Canceled')),
        ('finished', _('Finished')),
    ))
    HELP_OPTIONS = dict(HELP_REQUEST)

    requester = models.ForeignKey(User, related_name='helprequested_set')
    volunteer = models.ForeignKey(User, related_name='helpvolunteered_set', null=True)
    help_with = models.IntegerField(default=0)  # choices=HELP_REQUEST
    status = models.CharField(max_length=16, choices=STATUS.items(), default='new')
    last_access = models.DateTimeField(_('access date'), default=timezone.now, editable=False)

    objects = HelpStatusQuerySet.as_manager()

    def has_updates(self):
        return self.last_access < self.modified_date

    def get_help_label(self):
        return HelpRequest.HELP_OPTIONS.get(self.help_with, '')

    def help_labels(self):
        for code, label in HELP:
            if self.help_with >= code:
                break
            if self.help_with & code:
                yield label


class HelpReply(BaseModel):
    INTENTION = (
        ('answer', _('Answer')),
        ('finish', _('Finish')),
        ('cancel', _('Cancel')),
    )
    author = models.ForeignKey(User)
    helprequest = models.ForeignKey(HelpRequest)
    message = models.TextField(_('message'))
    intention = models.CharField(_('intention'), max_length=16,
                                 choices=INTENTION, default='answer')


class Track(BaseModel):
    user = models.ForeignKey(User)
    start = models.CharField(max_length=128)
    end = models.CharField(max_length=128)
    track = models.LineStringField()

    def json(self):
        d = {
            'type': 'LineString',
            'coordinates': [p for p in self.track],
            'properties': {
                'start': self.start,
                'end': self.end,
            },
        }
        if self.id:
            d['properties']['id'] = self.id
        return d


class Point(BaseModel):
    user = models.ForeignKey(User)
    address = models.CharField(max_length=128)
    coords = models.PointField()

    def json(self):
        d = {
            'type': 'LineString',
            'coordinates': self.coords.get_coords(),
            'properties': {
                'address': self.address,
            },
        }
        if self.id:
            d['properties']['id'] = self.id
        return d
