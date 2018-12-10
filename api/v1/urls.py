from django.conf.urls import url

from ..v1 import views

urlpatterns = [
    url(r'^me/anagrafica/base/', views.MiaAnagraficaBase.as_view()),
    url(r'^me/anagrafica/completa/', views.MiaAnagraficaCompleta.as_view()),
    url(r'^me/appartenenze/attuali/', views.MieAppartenenzeAttuali.as_view()),
    url(r'^me/appartenenza/completa/', views.MiaAppartenenzaCompleta.as_view()),
]
