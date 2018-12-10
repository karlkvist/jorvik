from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response

from oauth2_provider.ext.rest_framework import TokenHasScope
from anagrafica.permessi.applicazioni import PERMESSI_NOMI_DICT
from api.settings import (SCOPE_ANAGRAFICA_LETTURA_BASE,
    SCOPE_ANAGRAFICA_LETTURA_COMPLETA, SCOPE_APPARTENENZE_LETTURA)
from ..v1 import serializzatori


# /me/anagrafica/base/
class MiaAnagraficaBase(APIView):
    """ Una vista che ritorna informazioni sulla persona identificata. """
    permission_classes = (permissions.IsAuthenticated,
                          TokenHasScope)
    required_scopes = [SCOPE_ANAGRAFICA_LETTURA_BASE]

    def get(self, request, format=None):
        dati = serializzatori.persona_anagrafica_base(request.user.persona)
        return Response(dati)


# /me/anagrafica/completa/
class MiaAnagraficaCompleta(APIView):
    """
    Una vista che ritorna l'anagrafica completa della persona identificata
     (anagrafica base, più dati aggiuntivi).
    """

    permission_classes = (permissions.IsAuthenticated,
                          TokenHasScope)
    required_scopes = [SCOPE_ANAGRAFICA_LETTURA_BASE,
                       SCOPE_ANAGRAFICA_LETTURA_COMPLETA]

    def get(self, request, format=None):
        dati = serializzatori.persona_anagrafica_completa(request.user.persona)
        return Response(dati)


# /me/appartenenze/attuali/
class MieAppartenenzeAttuali(APIView):
    """ Una vista che ritorna informazioni sulle appartenenze attuali. """
    required_scopes = [SCOPE_APPARTENENZE_LETTURA]

    def get(self, request, format=None):
        me = request.user.persona
        appartenenze = me.appartenenze_attuali()
        appartenenze = [serializzatori.appartenenza(i) for i in appartenenze]
        dati = {"appartenenze": appartenenze}
        return Response(dati)


# /me/appartenenze/completa/
class MiaAppartenenzaCompleta(APIView):
    """
    ID utente: Persona\n
    nome: Persona\n
    cognome: Persona\n
    indirizzo mail di contatto: Persona\n
    rispettiva sede di appartenenza: Persona\n
    ID comitato\n
    nome comitato\n
    estensione del comitato R/P/L/T\n
    delega\n
    """
    permission_classes = (permissions.IsAuthenticated,
                          TokenHasScope)
    required_scopes = [SCOPE_ANAGRAFICA_LETTURA_BASE,
                       SCOPE_ANAGRAFICA_LETTURA_COMPLETA,
                       SCOPE_APPARTENENZE_LETTURA]

    def get(self, request, format=None):
        user = request.user
        if user.persona is None or not hasattr(user, 'persona'):
            return Response({'id_persona': None}, status=status.HTTP_404_NOT_FOUND)
        else:
            me = user.persona

        comitati_all = list()

        # Persona
        dati = {
            'id_persona': me.pk,
            'nome': me.nome,
            'cognome': me.cognome,
            'data_di_nascita': me.data_nascita,
            'codice_fiscale': me.codice_fiscale,
        }
        if me.email is not None:
            dati['email'] = me.email

        # Deleghe
        list_deleghe = list()
        for delega in me.deleghe_attuali().order_by('-creazione'):
            if not delega.tipo in PERMESSI_NOMI_DICT:
                continue

            oggetto = delega.oggetto
            sede = oggetto.sede if hasattr(oggetto, 'sede') else oggetto

            list_deleghe.append({
                'id': delega.id,
                'tipo': PERMESSI_NOMI_DICT[delega.tipo],
                'comitato': {
                    'id': sede.estensione,
                    'nome': sede.comitato.nome,
                    'descrizione': sede.get_estensione_display(),
                },
            })
            comitati_all.append(sede.comitato.nome)
        dati['deleghe'] = list_deleghe

        # Appartenenze
        list_appartenenze = list()
        for appartenenza in me.appartenenze_attuali().order_by('-creazione'):
            comitato = appartenenza.sede
            list_appartenenze.append({
                'id': comitato.id,
                'descrizione': appartenenza.get_membro_display(),
                'tipo': appartenenza.membro,
                'comitato': {
                    'nome': comitato.nome,
                    'id': comitato.estensione,
                    'descrizione': comitato.get_estensione_display()
                },
            })
            comitati_all.append(comitato.nome)
        dati['appartenenze'] = list_appartenenze

        # Tutti i comitati
        dati['comitati_all'] = set(comitati_all)

        return Response(dati)

#serializzatori._campo(comitato.estensione, comitato.get_estensione_display())
