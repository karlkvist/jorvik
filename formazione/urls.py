from django.conf.urls import url
from .viste import (formazione, formazione_corsi_base_elenco,
        formazione_corsi_base_domanda, formazione_corsi_base_nuovo,
        formazione_corsi_base_direttori, formazione_corsi_base_fine)

app_label = 'formazione'
urlpatterns = [
    url(r'^$', formazione, name='index'),
    url(r'^corsi-base/elenco/$',
        formazione_corsi_base_elenco,
        name='list_courses'
    ),
    url(r'^corsi-base/domanda/$',
        formazione_corsi_base_domanda,
        name='domanda'
    ),
    url(r'^corsi-base/nuovo/$',
        formazione_corsi_base_nuovo,
        name='new_course'
    ),
    url(r'^corsi-base/(?P<pk>[0-9]+)/direttori/$',
        formazione_corsi_base_direttori,
        name='director'
    ),
    url(r'^corsi-base/(?P<pk>[0-9]+)/fine/$',
        formazione_corsi_base_fine,
        name='end'
    ),
]