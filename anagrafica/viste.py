import codecs
import csv
import datetime
from collections import OrderedDict

from django.contrib.contenttypes.models import ContentType
from django.db.models.loading import get_model
from django.http import HttpResponse
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.contrib.auth import login

# Le viste base vanno qui.
from django.views.generic import ListView
from django.utils import timezone

from anagrafica.costanti import TERRITORIALE, REGIONALE
from anagrafica.forms import ModuloStepComitato, ModuloStepCredenziali, ModuloModificaAnagrafica, ModuloModificaAvatar, \
    ModuloCreazioneDocumento, ModuloModificaPassword, ModuloModificaEmailAccesso, ModuloModificaEmailContatto, \
    ModuloCreazioneTelefono, ModuloCreazioneEstensione, ModuloCreazioneTrasferimento, ModuloCreazioneDelega, \
    ModuloDonatore, ModuloDonazione, ModuloNuovaFototessera, ModuloProfiloModificaAnagrafica, \
    ModuloProfiloTitoloPersonale, ModuloUtenza, ModuloCreazioneRiserva, ModuloModificaPrivacy, ModuloPresidenteSede, \
    ModuloImportVolontari, ModuloModificaDataInizioAppartenenza
from anagrafica.forms import ModuloStepCodiceFiscale
from anagrafica.forms import ModuloStepAnagrafica

# Tipi di registrazione permessi
from anagrafica.importa import VALIDAZIONE_ERRORE, VALIDAZIONE_AVVISO, VALIDAZIONE_OK, import_import_volontari
from anagrafica.models import Persona, Documento, Telefono, Estensione, Delega, Appartenenza, Trasferimento, \
    ProvvedimentoDisciplinare, Sede, Riserva
from anagrafica.permessi.applicazioni import PRESIDENTE, UFFICIO_SOCI, PERMESSI_NOMI_DICT, DELEGATO_OBIETTIVO_1, \
    DELEGATO_OBIETTIVO_2, DELEGATO_OBIETTIVO_3, DELEGATO_OBIETTIVO_4, DELEGATO_OBIETTIVO_5, DELEGATO_OBIETTIVO_6, \
    RESPONSABILE_FORMAZIONE, RESPONSABILE_AUTOPARCO, DELEGATO_CO, UFFICIO_SOCI_UNITA, DELEGHE_RUBRICA
from anagrafica.permessi.costanti import ERRORE_PERMESSI, COMPLETO, MODIFICA, LETTURA, GESTIONE_SEDE, GESTIONE, \
    ELENCHI_SOCI
from anagrafica.permessi.incarichi import INCARICO_GESTIONE_RISERVE, INCARICO_GESTIONE_TITOLI, \
    INCARICO_GESTIONE_FOTOTESSERE
from attivita.models import Partecipazione
from attivita.viste import attivita_storico_excel
from autenticazione.funzioni import pagina_anonima, pagina_privata
from autenticazione.models import Utenza
from base.errori import errore_generico, errore_nessuna_appartenenza, messaggio_generico
from base.files import Zip
from base.models import Log
from base.notifiche import NOTIFICA_INVIA
from base.stringhe import genera_uuid_casuale
from base.utils import remove_none, poco_fa
from curriculum.forms import ModuloNuovoTitoloPersonale, ModuloDettagliTitoloPersonale
from curriculum.models import Titolo, TitoloPersonale
from posta.models import Messaggio
from posta.utils import imposta_destinatari_e_scrivi_messaggio
from sangue.models import Donatore, Donazione

TIPO_VOLONTARIO = 'volontario'
TIPO_ASPIRANTE = 'aspirante'
TIPO_DIPENDENTE = 'dipendente'
TIPO = (TIPO_VOLONTARIO, TIPO_ASPIRANTE, TIPO_DIPENDENTE )

# I vari step delle registrazioni
STEP_COMITATO = 'comitato'
STEP_CODICE_FISCALE = 'codice_fiscale'
STEP_ANAGRAFICA = 'anagrafica'
STEP_CREDENZIALI = 'credenziali'
STEP_FINE = 'fine'

STEP_NOMI = {
    STEP_COMITATO: 'Selezione Comitato',
    STEP_CODICE_FISCALE: 'Codice Fiscale',
    STEP_ANAGRAFICA: 'Dati anagrafici',
    STEP_CREDENZIALI: 'Credenziali',
    STEP_FINE: 'Conferma',
}

# Definisce i vari step di registrazione, in ordine, per ogni tipo di registrazione.
STEP = {
    TIPO_VOLONTARIO: [STEP_COMITATO, STEP_CODICE_FISCALE, STEP_ANAGRAFICA, STEP_CREDENZIALI, STEP_FINE],
    TIPO_ASPIRANTE: [STEP_CODICE_FISCALE, STEP_ANAGRAFICA, STEP_CREDENZIALI, STEP_FINE],
    TIPO_DIPENDENTE: [STEP_COMITATO, STEP_CODICE_FISCALE, STEP_ANAGRAFICA, STEP_CREDENZIALI, STEP_FINE],
}

MODULI = {
    STEP_COMITATO: ModuloStepComitato,
    STEP_CODICE_FISCALE: ModuloStepCodiceFiscale,
    STEP_ANAGRAFICA: ModuloStepAnagrafica,
    STEP_CREDENZIALI: ModuloStepCredenziali,
    STEP_FINE: None,
}

@pagina_anonima
def registrati(request, tipo, step=None):
    """
    La vista per tutti gli step della registrazione.
    """

    # Controlla che il tipo sia valido (/registrati/<tipo>/)
    if tipo not in TIPO:
        return redirect('/errore/')  # Altrimenti porta ad errore generico

    # Se nessuno step, assume il primo step per il tipo
    # es. /registrati/volontario/ => /registrati/volontario/comitato/
    if not step:
        step = STEP[tipo][0]
        # Ricomincia, quindi svuoto la sessione!
        request.session['registrati'] = {}

    try:
        sessione = request.session['registrati'].copy()
    except KeyError:
        sessione = {}

    lista_step = [
        # Per ogni step:
        #  nome: Il nome completo dello step (es. "Selezione Comitato")
        #  slug: Il nome per il link (es. "comitato" per /registrati/<tipo>/comitato/")
        #  completato: True se lo step e' stato completato o False se futuro o attuale
        {'nome': STEP_NOMI[x], 'slug': x,
         'completato': (STEP[tipo].index(x) < STEP[tipo].index(step)),
         'attuale': (STEP[tipo].index(x) == STEP[tipo].index(step)),
         'modulo': MODULI[x](initial=sessione) if MODULI[x] else None,
         }
        for x in STEP[tipo]
    ]

    # Controlla se e' l'ultimo step
    if STEP[tipo].index(step) == len(STEP[tipo]) - 1:
        step_successivo = None
    else:
        step_successivo = STEP[tipo][STEP[tipo].index(step) + 1]

    step_modulo = MODULI[step]

    # Se questa e' la ricezione dello step compilato
    if request.method == 'POST':
        modulo = step_modulo(request.POST)
        if modulo.is_valid():

            # TODO MEMORIZZA

            for k in modulo.data:
                sessione[k] = modulo.data[k]
            request.session['registrati'] = sessione

            return redirect("/registrati/%s/%s/" % (tipo, step_successivo,))

    else:
        if step_modulo:
            modulo = step_modulo(initial=sessione)
        else:
            modulo = None

    contesto = {
        'attuale_nome': STEP_NOMI[step],
        'attuale_slug': step,
        'lista_step': lista_step,
        'step_successivo': step_successivo,
        'tipo': tipo,
        'modulo': modulo,
    }

    return 'anagrafica_registrati_step_' + step + '.html', contesto

@pagina_anonima
def registrati_conferma(request, tipo):
    """
    Controlla che tutti i parametri siano corretti in sessione ed effettua
    la registrazione vera e propria!
    """

    # Controlla che il tipo sia valido (/registrati/<tipo>/)
    if tipo not in TIPO:
        return redirect('/errore/')  # Altrimenti porta ad errore generico

    try:
        sessione = request.session['registrati'].copy()
    except KeyError:
        sessione = {}

    print(sessione)

    dati = {}

    # Carica tutti i moduli inviati da questo tipo di registrazione
    for (k, modulo) in [(x, MODULI[x](data=sessione)) for x in STEP[tipo] if MODULI[x] is not None]:

        # Controlla nuovamente la validita'
        if not modulo.is_valid():
            raise ValueError("Errore nella validazione del sub-modulo %s" % (k, ))

        # Aggiunge tutto a "dati"
        dati.update(modulo.cleaned_data)

    # Quali di questi campi vanno nella persona?
    campi_persona = [str(x.name) for x in Persona._meta.get_fields() if not x.is_relation]
    dati_persona = {x: dati[x] for x in dati if x in campi_persona}

    # Crea la persona
    p = Persona(**dati_persona)
    p.email_contatto = dati['email']
    p.save()

    # Associa l'utenza
    u = Utenza(persona=p, email=dati['email'])
    u.set_password(dati['password'])
    u.save()

    # Effettua il login!
    u.backend = 'django.contrib.auth.backends.ModelBackend'
    login(request, u)

    # Da' il benvenuto all'utente
    p.invia_email_benvenuto_registrazione(tipo=tipo)

    redirect_url = "/utente/"

    if tipo == TIPO_ASPIRANTE:
        #  Genera semplicemente oggetto aspirante.
        p.ottieni_o_genera_aspirante()
        redirect_url = "/aspirante/"

    elif tipo == TIPO_VOLONTARIO:
        #  Richiede appartenenza come Volontario.
        a = Appartenenza(
            persona=p,
            inizio=dati['inizio'],
            sede=dati['sede'],
            membro=Appartenenza.VOLONTARIO,
        )
        a.save()
        a.richiedi()

    elif tipo == TIPO_DIPENDENTE:
        #  Richiede appartenenza come Dipendente.
        a = Appartenenza(
            persona=p,
            inizio=dati['inizio'],
            sede=dati['sede'],
            membro=Appartenenza.DIPENDENTE,
        )
        a.save()
        a.richiedi()

    else:
        raise ValueError("Non so come gestire questa iscrizione.")

    return redirect(redirect_url)


@pagina_privata
def utente(request, me):
    return 'anagrafica_utente_home.html'

@pagina_privata
def utente_anagrafica(request, me):

    contesto = {
        "delegati": me.deleghe_anagrafica(),
    }

    modulo_dati = ModuloModificaAnagrafica(request.POST or None, instance=me)

    if request.POST:

        if modulo_dati.is_valid():
            modulo_dati.save()

    else:

        modulo_dati = ModuloModificaAnagrafica(instance=me)

    contesto.update({
        "modulo_dati": modulo_dati,
    })

    return 'anagrafica_utente_anagrafica.html', contesto

@pagina_privata
def utente_fotografia(request, me):
   return redirect("/utente/fotografia/avatar/")

@pagina_privata
def utente_fotografia_avatar(request, me):

    modulo_avatar = ModuloModificaAvatar(request.POST or None, request.FILES or None, instance=me)

    if request.POST:
        if modulo_avatar.is_valid():
            modulo_avatar.save()

    contesto = {
        "modulo_avatar": modulo_avatar
    }

    return 'anagrafica_utente_fotografia_avatar.html', contesto

@pagina_privata
def utente_fotografia_fototessera(request, me):

    modulo_fototessera = ModuloNuovaFototessera(request.POST or None, request.FILES or None)

    sede = me.comitato_riferimento()

    if not sede:
        return errore_nessuna_appartenenza(
            request, me, torna_url="/utente/fotografia/avatar/"
        )

    if request.POST:

        if modulo_fototessera.is_valid():

            # Ritira eventuali richieste in attesa
            if me.fototessere_pending().exists():
                for x in me.fototessere_pending():
                    x.autorizzazioni_ritira()

            # Crea la fototessera
            fototessera = modulo_fototessera.save(commit=False)
            fototessera.persona = me
            fototessera.save()

            # Richiede l'autorizzazione
            fototessera.autorizzazione_richiedi_sede_riferimento(
                me, INCARICO_GESTIONE_FOTOTESSERE,
                invia_notifica_ufficio_soci=True,
                invia_notifica_presidente=True
            )


    contesto = {
        "modulo_fototessera": modulo_fototessera
    }

    return 'anagrafica_utente_fotografia_fototessera.html', contesto

@pagina_privata
def utente_documenti(request, me):

    contesto = {
        "documenti": me.documenti.all()
    }

    if request.method == "POST":

        nuovo_doc = Documento(persona=me)
        modulo_aggiunta = ModuloCreazioneDocumento(request.POST, request.FILES, instance=nuovo_doc)

        if modulo_aggiunta.is_valid():
            modulo_aggiunta.save()

    else:

        modulo_aggiunta = ModuloCreazioneDocumento()

    contesto.update({"modulo_aggiunta": modulo_aggiunta})

    return 'anagrafica_utente_documenti.html', contesto


@pagina_privata
def utente_documenti_cancella(request, me, pk):

    doc = get_object_or_404(Documento, pk=pk)

    if not doc.persona == me:
        return redirect('/errore/permessi/')

    doc.delete()
    return redirect('/utente/documenti/')


@pagina_privata
def utente_documenti_zip(request, me):

    if not me.documenti.exists():
        return redirect('/utente/documenti')

    z = Zip(oggetto=me)
    for d in me.documenti.all():
        z.aggiungi_file(d.file.path)
    z.comprimi_e_salva(nome='Documenti.zip')

    return redirect(z.download_url)

@pagina_privata
def utente_storico(request, me):

    contesto = {
        "appartenenze": me.appartenenze.all(),
        "deleghe": me.deleghe.all()
    }

    return 'anagrafica_utente_storico.html', contesto


@pagina_privata
def utente_privacy(request, me):

    modulo = ModuloModificaPrivacy(request.POST or None, instance=me)

    if modulo.is_valid():
        modulo.save()

    contesto = {
        "modulo": modulo
    }
    return 'anagrafica_utente_privacy.html', contesto


@pagina_privata
def utente_contatti(request, me):

    if request.method == "POST":

        modulo_email_accesso = ModuloModificaEmailAccesso(request.POST, instance=me.utenza)
        modulo_email_contatto = ModuloModificaEmailContatto(request.POST, instance=me)
        modulo_numero_telefono = ModuloCreazioneTelefono(request.POST)

        if modulo_email_accesso.is_valid():
            modulo_email_accesso.save()

        if modulo_email_contatto.is_valid():
            modulo_email_contatto.save()

        if modulo_numero_telefono.is_valid():
            me.aggiungi_numero_telefono(
                modulo_numero_telefono.data['numero_di_telefono'],
                modulo_numero_telefono.data['tipologia'] == modulo_numero_telefono.SERVIZIO
            )

    else:

        modulo_email_accesso = ModuloModificaEmailAccesso(instance=me.utenza)
        modulo_email_contatto = ModuloModificaEmailContatto(instance=me)
        modulo_numero_telefono = ModuloCreazioneTelefono()

    numeri = me.numeri_telefono.all()
    contesto = {
        "modulo_email_accesso": modulo_email_accesso,
        "modulo_email_contatto": modulo_email_contatto,
        "modulo_numero_telefono": modulo_numero_telefono,
        "numeri": numeri
    }

    return 'anagrafica_utente_contatti.html', contesto


@pagina_privata
def utente_rubrica_referenti(request, me):
    sedi_volontario = Sede.objects.filter(pk__in=me.sedi_attuali(membro__in=Appartenenza.MEMBRO_RUBRICA).values_list("id", flat=True))
    referenti = Persona.objects.filter(
        Delega.query_attuale(
            oggetto_tipo=ContentType.objects.get_for_model(Sede),
            oggetto_id__in=sedi_volontario,
            tipo__in=DELEGHE_RUBRICA,
        ).via("delega")
    ).order_by('nome', 'cognome', 'codice_fiscale')\
        .distinct('nome', 'cognome', 'codice_fiscale')

    contesto = {
        "referenti": referenti,
    }
    return 'anagrafica_utente_rubrica_referenti.html', contesto


@pagina_privata
def utente_rubrica_volontari(request, me):
    sedi_volontario = Sede.objects.filter(pk__in=me.sedi_attuali(membro__in=Appartenenza.MEMBRO_RUBRICA).values_list("id", flat=True))
    sedi_gestione = me.oggetti_permesso(ELENCHI_SOCI)
    volontari_volontario = Persona.objects.filter(
        Appartenenza.query_attuale(membro__in=Appartenenza.MEMBRO_RUBRICA, sede__in=sedi_volontario).via("appartenenze"),
        privacy_contatti__gte=Persona.POLICY_SEDE,
    )
    #volontari_gestione = Persona.objects.filter(
    #    Appartenenza.query_attuale(membro__in=Appartenenza.MEMBRO_RUBRICA, sede__in=sedi_gestione).via("appartenenze"),
    #    privacy_contatti__gte=Persona.POLICY_RISTRETTO,
    #)
    volontari = volontari_volontario #  | volontari_gestione
    volontari = volontari\
        .prefetch_related('appartenenze', 'fototessere')\
        .order_by('nome', 'cognome', 'codice_fiscale')\
        .distinct('nome', 'cognome', 'codice_fiscale')
    ci_sono = volontari_volontario.filter(pk=me.pk).exists()

    contesto = {
        "volontari": volontari,
        "ci_sono": ci_sono,
    }
    return 'anagrafica_utente_rubrica_volontari.html', contesto


@pagina_privata
def utente_contatti_cancella_numero(request, me, pk):

    tel = get_object_or_404(Telefono, pk=pk)

    if not tel.persona == me:
        return redirect('/errore/permessi/')

    tel.delete()
    return redirect('/utente/contatti/')

@pagina_privata
def utente_donazioni_profilo(request, me):

    modulo = ModuloDonatore(request.POST or None, instance=me.donatore if hasattr(me, 'donatore') else None)

    if modulo.is_valid():

        if hasattr(me, 'donatore'):
            modulo.save()

        else:
            donatore = modulo.save(commit=False)
            donatore.persona = me
            donatore.save()

    contesto = {
        "modulo": modulo
    }
    return 'anagrafica_utente_donazioni_profilo.html', contesto

@pagina_privata
def utente_donazioni_sangue(request, me):
    modulo = ModuloDonazione(request.POST or None)

    if modulo.is_valid():

        donazione = modulo.save(commit=False)
        donazione.persona = me
        donazione.save()
        donazione.richiedi()

    donazioni = me.donazioni_sangue.all()

    contesto = {
        "modulo": modulo,
        "donazioni": donazioni
    }
    return 'anagrafica_utente_donazioni_sangue.html', contesto

@pagina_privata
def utente_donazioni_sangue_cancella(request, me, pk):
    donazione = get_object_or_404(Donazione, pk=pk)
    if not donazione.persona == me:
        return redirect(ERRORE_PERMESSI)

    donazione.delete()
    return redirect("/utente/donazioni/sangue/")

@pagina_privata
def utente_estensione(request, me):
    if not me.sede_riferimento():
        return errore_nessuna_appartenenza(request, me)
    storico = me.estensioni.all()
    modulo = ModuloCreazioneEstensione(request.POST or None)
    if modulo.is_valid():
        est = modulo.save(commit=False)
        if est.destinazione in me.sedi_attuali():
            modulo.add_error('destinazione', 'Sei già appartenente a questa sede.')
        elif est.destinazione in [x.destinazione for x in me.estensioni_attuali_e_in_attesa()]:
            modulo.add_error('destinazione', 'Estensione già richiesta a questa sede.')
        else:
            est.richiedente = me
            est.persona = me
            est.save()
            est.richiedi()
            # Messaggio.costruisci_e_invia(
            #     oggetto="Richiesta di estensione",
            #     modello="email_richiesta_estensione.html",
            #     corpo={
            #         "trasferimento": est,
            #     },
            #     mittente=None,
            #     destinatari=[
            #         est.persona,
            #     ]
            # )
            # Messaggio.costruisci_e_invia(
            #     oggetto="Richiesta di estensione",
            #     modello="email_richiesta_estensione_cc.html",
            #     corpo={
            #         "trasferimento": est,
            #     },
            #     mittente=None,
            #     destinatari=[
            #         ##presidente sede di estensione
            #     ]
            # )
            # Messaggio.costruisci_e_invia(
            #     oggetto="Richiesta di estensione",
            #     modello="email_richiesta_estensione_presidente.html",
            #     corpo={
            #         "trasferimento": est,
            #     },
            #     mittente=None,
            #     destinatari=[
            #         ##presidente sede riferimento
            #     ]
            # )

    contesto = {
        "modulo": modulo,
        "storico": storico,
        "attuali": me.estensioni_attuali()
    }
    return "anagrafica_utente_estensione.html", contesto

@pagina_privata()
def utente_estensione_termina(request, me, pk):
    estensione = get_object_or_404(Estensione, pk=pk)
    if not estensione.persona == me:
        return redirect(ERRORE_PERMESSI)
    else:
        estensione.termina()
        return redirect('/utente/')

def utente_trasferimento_termina(request, me, pk):
    trasferimento = get_object_or_404(Trasferimento, pk=pk)
    if not trasferimento.persona == me:
        return redirect(ERRORE_PERMESSI)
    else:
        trasferimento.ritira()
        return redirect('/utente/trasferimento/')


@pagina_privata
def utente_trasferimento(request, me):
    if not me.sede_riferimento():
        return errore_nessuna_appartenenza(request, me)
    storico = me.trasferimenti.all()

    modulo = ModuloCreazioneTrasferimento(request.POST or None)
    if modulo.is_valid():
        trasf = modulo.save(commit=False)
        if trasf.destinazione in me.sedi_attuali():
            modulo.add_error('destinazione', 'Sei già appartenente a questa sede.')
        elif trasf.destinazione.comitato != me.sede_riferimento().comitato and True:##che in realta' e' il discriminatore delle elezioni
            return errore_generico(request, me, messaggio="Non puoi richiedere un trasferimento tra comitati durante il periodo elettorale")
        elif me.trasferimento:
            return errore_generico(request, me, messaggio="Non puoi richiedere piú di un trasferimento alla volta")
        else:
            trasf.persona = me
            trasf.richiedente = me
            trasf.save()
            trasf.richiedi()
            Messaggio.costruisci_e_invia(
                oggetto="Richiesta di trasferimento",
                modello="email_richiesta_trasferimento.html",
                corpo={
                    "trasferimento": trasf,
                },
                mittente=None,
                destinatari=[
                    trasf.persona,
                ]
            )
            Messaggio.costruisci_e_invia(
                oggetto="Richiesta di trasferimento",
                modello="email_richiesta_trasferimento_cc.html",
                corpo={
                    "trasferimento": trasf,
                },
                mittente=None,
                destinatari=[
                    trasf.destinazione.presidente()
                ]
            )
            Messaggio.costruisci_e_invia(
                oggetto="Richiesta di trasferimento",
                modello="email_richiesta_trasferimento_presidente.html",
                corpo={
                    "trasferimento": trasf,
                },
                mittente=None,
                destinatari=[
                    trasf.persona.sede_riferimento().presidente()
                ]
            )

    contesto = {
        "modulo": modulo,
        "storico": storico
    }
    return "anagrafica_utente_trasferimento.html", contesto

@pagina_privata
def utente_riserva(request, me):
    if not me.appartenenze_attuali() or not me.sede_riferimento():
        return errore_generico(titolo="Errore", messaggio="Si è verificato un errore generico.", request=request)
    storico = me.riserve.all()
    modulo = ModuloCreazioneRiserva(request.POST or None)
    if modulo.is_valid():
        r = modulo.save(commit=False)
        r.persona = me
        r.appartenenza = me.appartenenze_attuali().first()
        r.save()
        r.invia_mail()
        r.autorizzazione_richiedi_sede_riferimento(
            me, INCARICO_GESTIONE_RISERVE,
            invia_notifica_presidente=True,
        )

        return messaggio_generico(request, me, titolo="Riserva registrata",
                                      messaggio="La riserva è stato registrata con successo",
                                      torna_titolo="Torna alla dash",
                                      torna_url="/utente/")
    contesto = {
        "modulo": modulo,
        "storico": storico,
    }
    return "anagrafica_utente_riserva.html", contesto


@pagina_privata
def utente_riserva_ritira(request, me, pk):
    riserva = get_object_or_404(Riserva, pk=pk)
    print(riserva)
    print(riserva.esito)
    if not riserva.persona == me:
        return redirect(ERRORE_PERMESSI)
    riserva.autorizzazioni_ritira()
    print(riserva.esito)
    Messaggio.costruisci_e_invia(
           oggetto="Riserva terminata",
           modello="email_richiesta_riserva_terminata.html",
           corpo={
               "riserva": riserva,
           },
           mittente=riserva.persona,
           destinatari=[
                riserva.persona.sede_riferimento().presidente()
           ]
        )
    return redirect("/utente/")

@pagina_privata
def utente_riserva_termina(request, me, pk):
    riserva = get_object_or_404(Riserva, pk=pk)
    if not riserva.persona == me:
        return redirect(ERRORE_PERMESSI)
    riserva.termina()
    return redirect("/utente/")


@pagina_privata
def utente_estensione_estendi(request, me, pk):
    estensione = get_object_or_404(Estensione, pk=pk)
    if not estensione.persona == me:
        return redirect(ERRORE_PERMESSI)
    estensione.appartenenza.fine = datetime.date.today()+datetime.timedelta(days=365)
    estensione.appartenenza.save()
    return redirect("/utente/estensione")


@pagina_privata
def utente_trasferimento_ritira(request, me, pk):
    trasf = get_object_or_404(Trasferimento, pk=pk)
    if not trasf.persona == me:
        return redirect(ERRORE_PERMESSI)
    trasf.autorizzazioni_ritira()
    return redirect("/utente/trasferimento/")


@pagina_privata
def profilo_messaggio(request, me, pk=None):
    persona = get_object_or_404(Persona, pk=pk)
    qs = Persona.objects.filter(pk=persona.pk)
    return imposta_destinatari_e_scrivi_messaggio(request, qs)


@pagina_privata
def profilo_turni_foglio(request, me, pk=None):
    persona = get_object_or_404(Persona, pk=pk)
    if not me.permessi_almeno(persona, LETTURA):
        return redirect(ERRORE_PERMESSI)
    excel = persona.genera_foglio_di_servizio()
    return redirect(excel.download_url)


@pagina_privata
def strumenti_delegati(request, me):
    app_label = request.session['app_label']
    model = request.session['model']
    pk = int(request.session['pk'])
    continua_url = request.session['continua_url']
    almeno = request.session['almeno']
    delega = request.session['delega']
    oggetto = get_model(app_label, model)
    oggetto = oggetto.objects.get(pk=pk)

    modulo = ModuloCreazioneDelega(request.POST or None, initial={
        "inizio": datetime.date.today(),
    })

    if modulo.is_valid():
        d = modulo.save(commit=False)

        if oggetto.deleghe.all().filter(Delega.query_attuale().q, tipo=delega, persona=d.persona).exists():
            return errore_generico(
                request, me,
                titolo="%s è già delegato" % (d.persona.nome_completo,),
                messaggio="%s ha già una delega attuale come %s per %s" % (d.persona.nome_completo, PERMESSI_NOMI_DICT[delega], oggetto),
                torna_titolo="Torna indietro",
                torna_url="/strumenti/delegati/",
            )

        d.inizio = poco_fa()
        d.firmatario = me
        d.tipo = delega
        d.oggetto = oggetto
        d.save()
        d.invia_notifica_creazione()

    deleghe = oggetto.deleghe.filter(tipo=delega)
    deleghe_attuali = oggetto.deleghe_attuali(tipo=delega)

    contesto = {
        "continua_url": continua_url,
        "almeno": almeno,
        "delega": PERMESSI_NOMI_DICT[delega],
        "modulo": modulo,
        "oggetto": oggetto,
        "deleghe": deleghe,
        "deleghe_attuali": deleghe_attuali,
    }

    return 'anagrafica_strumenti_delegati.html', contesto


@pagina_privata
def strumenti_delegati_termina(request, me, delega_pk=None):
    app_label = request.session['app_label']
    model = request.session['model']
    pk = int(request.session['pk'])
    continua_url = request.session['continua_url']
    almeno = request.session['almeno']
    delega = request.session['delega']
    oggetto = get_model(app_label, model)
    oggetto = oggetto.objects.get(pk=pk)

    delega = get_object_or_404(Delega, pk=delega_pk)
    if not me.permessi_almeno(delega.oggetto, GESTIONE):
        return redirect(ERRORE_PERMESSI)

    delega.fine = poco_fa()
    delega.save()
    delega.invia_notifica_terminazione(me)

    return redirect("/strumenti/delegati/")


@pagina_privata
def utente_curriculum(request, me, tipo=None):

    if not tipo:
        return redirect("/utente/curriculum/CP/")

    if tipo not in dict(Titolo.TIPO):  # Tipo permesso?
        redirect(ERRORE_PERMESSI)

    passo = 1
    tipo_display = dict(Titolo.TIPO)[tipo]
    request.session['titoli_tipo'] = tipo

    titolo_selezionato = None
    modulo = ModuloNuovoTitoloPersonale(tipo, tipo_display, request.POST or None)
    valida_secondo_form = True
    if modulo.is_valid():
        titolo_selezionato = modulo.cleaned_data['titolo']
        passo = 2
        valida_secondo_form = False

    if 'titolo_selezionato_id' in request.POST:
        titolo_selezionato = Titolo.objects.get(pk=request.POST['titolo_selezionato_id'])
        passo = 2

    if passo == 2:
        modulo = ModuloDettagliTitoloPersonale(request.POST if request.POST and valida_secondo_form else None)

        if not titolo_selezionato.richiede_data_ottenimento:
            del modulo.fields['data_ottenimento']

        if not titolo_selezionato.richiede_data_scadenza:
            del modulo.fields['data_scadenza']

        if not titolo_selezionato.richiede_luogo_ottenimento:
            del modulo.fields['luogo_ottenimento']

        if not titolo_selezionato.richiede_codice:
            del modulo.fields['codice']

        if modulo.is_valid():

            tp = modulo.save(commit=False)
            tp.persona = me
            tp.titolo = titolo_selezionato
            tp.save()

            if titolo_selezionato.richiede_conferma:
                sede_attuale = me.sede_riferimento()
                if not sede_attuale:
                    tp.delete()
                    return errore_nessuna_appartenenza(
                        request, me,
                        torna_url="/utente/curriculum/%s/" % (tipo,),
                    )

                tp.autorizzazione_richiedi_sede_riferimento(
                    me, INCARICO_GESTIONE_TITOLI
                )

            return redirect("/utente/curriculum/%s/?inserimento=ok" % (tipo,))

    titoli = me.titoli_personali.all().filter(titolo__tipo=tipo)

    contesto = {
        "tipo": tipo,
        "tipo_display": tipo_display,
        "passo": passo,
        "modulo": modulo,
        "titoli": titoli,
        "titolo": titolo_selezionato
    }
    return 'anagrafica_utente_curriculum.html', contesto

@pagina_privata
def utente_curriculum_cancella(request, me, pk=None):

    titolo_personale = get_object_or_404(TitoloPersonale, pk=pk)
    if not titolo_personale.persona == me:
        return redirect(ERRORE_PERMESSI)

    tipo = titolo_personale.titolo.tipo
    titolo_personale.delete()

    return redirect("/utente/curriculum/%s/" % (tipo,))


def _profilo_anagrafica(request, me, persona):
    puo_modificare = me.permessi_almeno(persona, MODIFICA)
    modulo = ModuloProfiloModificaAnagrafica(request.POST or None, instance=persona, prefix="anagrafica")
    modulo_numero_telefono = ModuloCreazioneTelefono(request.POST or None, prefix="telefono")
    if puo_modificare and modulo.is_valid():
        Log.registra_modifiche(me, modulo)
        modulo.save()

    if puo_modificare and modulo_numero_telefono.is_valid():
        persona.aggiungi_numero_telefono(
            modulo_numero_telefono.cleaned_data.get('numero_di_telefono'),
            modulo_numero_telefono.cleaned_data.get('tipologia') == modulo_numero_telefono.SERVIZIO,
        )

    contesto = {
        "modulo": modulo,
        "modulo_numero_telefono": modulo_numero_telefono,
    }
    return 'anagrafica_profilo_anagrafica.html', contesto


def _profilo_appartenenze(request, me, persona):
    puo_modificare = me.permessi_almeno(persona, MODIFICA)

    moduli = []
    for app in persona.appartenenze.all():
        modulo = None
        if puo_modificare and app.attuale():
            modulo = ModuloModificaDataInizioAppartenenza(request.POST or None,
                                                          instance=app,
                                                          prefix="%d" % (app.pk,))
            if ("%s-inizio" % (app.pk,)) in request.POST and modulo.is_valid():
                modulo.save()

        moduli += [modulo]

    appartenenze = zip(persona.appartenenze.all(), moduli)

    contesto = {
        "appartenenze": appartenenze
    }

    return 'anagrafica_profilo_appartenenze.html', contesto


def _profilo_fototessera(request, me, persona):
    puo_modificare = me.permessi_almeno(persona, MODIFICA)

    modulo = ModuloNuovaFototessera(request.POST or None, request.FILES or None)
    if modulo.is_valid():
        fototessera = modulo.save(commit=False)
        fototessera.persona = persona
        fototessera.save()

        # Ritira eventuali fototessere in attesa
        if persona.fototessere_pending().exists():
            for x in persona.fototessere_pending():
                x.autorizzazioni_ritira()

        Log.crea(me, fototessera)

    contesto = {
        "puo_modificare": puo_modificare,
        "modulo": modulo,
    }
    return 'anagrafica_profilo_fototessera.html', contesto


def _profilo_deleghe(request, me, persona):
    return 'anagrafica_profilo_deleghe.html', {}


def _profilo_turni(request, me, persona):
    storico = Partecipazione.objects.filter(persona=persona).order_by('-turno__inizio')
    contesto = {
        "storico": storico,
    }
    return 'anagrafica_profilo_turni.html', contesto


def _profilo_riserve(request, me, persona):

    riserve = Riserva.objects.filter(persona=persona)

    contesto = {
        "riserve": riserve,
    }


    return 'anagrafica_profilo_riserve.html', contesto


def _profilo_curriculum(request, me, persona):
    modulo = ModuloProfiloTitoloPersonale(request.POST or None)

    if modulo.is_valid():
        tp = modulo.save(commit=False)
        tp.persona = persona
        tp.save()

    contesto = {
        "modulo": modulo,
    }
    return 'anagrafica_profilo_curriculum.html', contesto


def _profilo_sangue(request, me, persona):
    modulo_donatore = ModuloDonatore(request.POST or None, prefix="donatore", instance=Donatore.objects.filter(persona=persona).first())
    modulo_donazione = ModuloDonazione(request.POST or None, prefix="donazione")

    if modulo_donatore.is_valid():
        donatore = modulo_donatore.save(commit=False)
        donatore.persona = persona
        donatore.save()

    if modulo_donazione.is_valid():
        donazione = modulo_donazione.save(commit=False)
        donazione.persona = persona
        r = donazione.save()
        print(r)

    contesto = {
        "modulo_donatore": modulo_donatore,
        "modulo_donazione": modulo_donazione,
    }

    return 'anagrafica_profilo_sangue.html', contesto


def _profilo_documenti(request, me, persona):
    puo_modificare = me.permessi_almeno(persona, MODIFICA)
    modulo = ModuloCreazioneDocumento(request.POST or None, request.FILES or None)
    if puo_modificare and modulo.is_valid():
        f = modulo.save(commit=False)
        f.persona = persona
        f.save()

    contesto = {
        "modulo": modulo,
    }
    return 'anagrafica_profilo_documenti.html', contesto

def _profilo_provvedimenti(request, me, persona):
        provvedimenti = ProvvedimentoDisciplinare.objects.filter(persona=persona)
        contesto = {
            "provvedimenti": provvedimenti,
        }

        return 'anagrafica_profilo_provvedimenti.html', contesto

def _profilo_quote(request, me, persona):
    contesto = {}
    return 'anagrafica_profilo_quote.html', contesto


def _profilo_credenziali(request, me, persona):
    utenza = Utenza.objects.filter(persona=persona).first()

    modulo_utenza = None
    if not utenza:
        modulo_utenza = ModuloUtenza(request.POST or None, instance=utenza, initial={"email": persona.email_contatto})

    if modulo_utenza and modulo_utenza.is_valid():
        utenza = modulo_utenza.save(commit=False)
        utenza.persona = persona
        utenza.save()
        utenza.genera_credenziali()
        return redirect(persona.url_profilo_credenziali)

    contesto = {
        "utenza": utenza,
        "modulo": modulo_utenza,

    }
    return 'anagrafica_profilo_credenziali.html', contesto


@pagina_privata
def profilo_documenti_cancella(request, me, pk, documento_pk):
    persona = get_object_or_404(Persona, pk=pk)
    documento = get_object_or_404(Documento, pk=documento_pk)
    if (not me.permessi_almeno(persona, MODIFICA)) or not (documento.persona == persona):
        return redirect(ERRORE_PERMESSI)
    documento.delete()
    return redirect("/profilo/%d/documenti/" % (persona.pk,))


@pagina_privata
def profilo_curriculum_cancella(request, me, pk, tp_pk):
    persona = get_object_or_404(Persona, pk=pk)
    titolo_personale = get_object_or_404(TitoloPersonale, pk=tp_pk)
    if (not me.permessi_almeno(persona, MODIFICA)) or not (titolo_personale.persona == persona):
        return redirect(ERRORE_PERMESSI)
    titolo_personale.delete()
    return redirect("/profilo/%d/curriculum/" % (persona.pk,))


@pagina_privata
def profilo_sangue_cancella(request, me, pk, donazione_pk):
    persona = get_object_or_404(Persona, pk=pk)
    donazione = get_object_or_404(Donazione, pk=donazione_pk)
    if (not me.permessi_almeno(persona, MODIFICA)) or not (donazione.persona == persona):
        return redirect(ERRORE_PERMESSI)
    donazione.delete()
    return redirect("/profilo/%d/sangue/" % (persona.pk,))


@pagina_privata
def profilo_telefono_cancella(request, me, pk, tel_pk):
    persona = get_object_or_404(Persona, pk=pk)
    telefono = get_object_or_404(Telefono, pk=tel_pk)
    if (not me.permessi_almeno(persona, MODIFICA)) or not (telefono.persona == persona):
        return redirect(ERRORE_PERMESSI)
    telefono.delete()
    return redirect("/profilo/%d/anagrafica/" % (persona.pk,))


def _sezioni_profilo(puo_leggere, puo_modificare):
    r = (
        # (path, (
        #   nome, icona, _funzione, permesso?,
        # ))
        ('anagrafica', (
            'Anagrafica', 'fa-edit', _profilo_anagrafica, puo_leggere
        )),
        ('appartenenze', (
            'Appartenenze', 'fa-clock-o', _profilo_appartenenze, puo_leggere
        )),
        ('deleghe', (
            'Deleghe', 'fa-clock-o', _profilo_deleghe, puo_leggere
        )),
        ('turni', (
            'Turni', 'fa-calendar', _profilo_turni, puo_leggere
        )),
        ('riserve', (
            'Riserve', 'fa-pause', _profilo_riserve, puo_leggere
        )),
        ('fototessera', (
            'Fototessera', 'fa-photo', _profilo_fototessera, puo_leggere
        )),
        ('documenti', (
            'Documenti', 'fa-folder', _profilo_documenti, puo_leggere
        )),
        ('curriculum', (
            'Curriculum', 'fa-list', _profilo_curriculum, puo_leggere
        )),
        ('sangue', (
            'Sangue', 'fa-flask', _profilo_sangue, puo_modificare
        )),
        ('quote', (
            'Quote/Ricevute', 'fa-money', _profilo_quote, puo_leggere
        )),
        ('provvedimenti', (
            'Provvedimenti', 'fa-legal', _profilo_provvedimenti, puo_leggere
        )),
        ('credenziali', (
            'Credenziali', 'fa-key', _profilo_credenziali, puo_modificare
        )),
    )
    return (x for x in r if len(x[1]) < 4 or x[1][3] == True)

@pagina_privata
def profilo(request, me, pk, sezione=None):
    persona = get_object_or_404(Persona, pk=pk)
    puo_modificare = me.permessi_almeno(persona, MODIFICA)
    puo_leggere = me.permessi_almeno(persona, LETTURA)
    sezioni = OrderedDict(_sezioni_profilo(puo_leggere, puo_modificare))

    contesto = {
        "persona": persona,
        "puo_modificare": puo_modificare,
        "puo_leggere": puo_leggere,
        "sezioni": sezioni,
        "attuale": sezione,
    }

    if not sezione:  # Prima pagina
        return 'anagrafica_profilo_profilo.html', contesto

    else:  # Sezione aperta

        if sezione not in sezioni:
            return redirect(ERRORE_PERMESSI)

        s = sezioni[sezione]
        risposta = s[2](request, me, persona)

        try:
            f_template, f_contesto = risposta
            contesto.update(f_contesto)
            return f_template, contesto

        except ValueError:
            return risposta

@pagina_privata
def presidente(request, me):
    sedi = me.oggetti_permesso(GESTIONE_SEDE)
    contesto = {
        "sedi": sedi
    }
    return 'anagrafica_presidente.html', contesto


def _presidente_sede_ruoli(sede):

    sezioni = OrderedDict()

    sezioni.update({
        "Obiettivi Strategici": [
            (DELEGATO_OBIETTIVO_1, "Obiettivo Strategico I", sede.delegati_attuali(tipo=DELEGATO_OBIETTIVO_1).count()),
            (DELEGATO_OBIETTIVO_2, "Obiettivo Strategico II", sede.delegati_attuali(tipo=DELEGATO_OBIETTIVO_2).count()),
            (DELEGATO_OBIETTIVO_3, "Obiettivo Strategico III", sede.delegati_attuali(tipo=DELEGATO_OBIETTIVO_3).count()),
            (DELEGATO_OBIETTIVO_4, "Obiettivo Strategico IV", sede.delegati_attuali(tipo=DELEGATO_OBIETTIVO_4).count()),
            (DELEGATO_OBIETTIVO_5, "Obiettivo Strategico V", sede.delegati_attuali(tipo=DELEGATO_OBIETTIVO_5).count()),
            (DELEGATO_OBIETTIVO_6, "Obiettivo Strategico VI", sede.delegati_attuali(tipo=DELEGATO_OBIETTIVO_6).count()),
        ]

    })

    sezioni.update({
        "Responsabili": [
            (UFFICIO_SOCI, "Ufficio Soci", sede.delegati_attuali(tipo=UFFICIO_SOCI).count()),
            (UFFICIO_SOCI_UNITA, "Ufficio Soci per Unità territoriale", sede.delegati_attuali(tipo=UFFICIO_SOCI_UNITA).count()),
            (RESPONSABILE_FORMAZIONE, "Formazione", sede.delegati_attuali(tipo=RESPONSABILE_FORMAZIONE).count()),
            (RESPONSABILE_AUTOPARCO, "Autoparco", sede.delegati_attuali(tipo=RESPONSABILE_AUTOPARCO).count()),
            (DELEGATO_CO, "Centrale Operativa", sede.delegati_attuali(tipo=DELEGATO_CO).count()),
        ]
    })

    return sezioni




@pagina_privata
def presidente_sede(request, me, sede_pk):
    sede = get_object_or_404(Sede, pk=sede_pk)
    if not me.permessi_almeno(sede, MODIFICA):
        return redirect(ERRORE_PERMESSI)

    modulo = ModuloPresidenteSede(request.POST or None, instance=sede)
    if modulo.is_valid():
        modulo.save()

    sezioni = _presidente_sede_ruoli(sede)

    contesto = {
        "sede": sede,
        "modulo": modulo,
        "sezioni": sezioni,
    }
    return 'anagrafica_presidente_sede.html', contesto


@pagina_privata
def presidente_sede_delegati(request, me, sede_pk, delega):
    sede = get_object_or_404(Sede, pk=sede_pk)
    if not me.permessi_almeno(sede, MODIFICA):
        return redirect(ERRORE_PERMESSI)

    contesto = {
        "sede": sede,
        "delega": delega,
        "continua_url": "/presidente/sedi/%d/" % (sede.pk,),
    }
    return 'anagrafica_presidente_sede_delegati.html', contesto


def handle_uploaded_file(f):
    nome = '/tmp/csv-%s.txt' % (genera_uuid_casuale(),)
    with open(nome, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)
    return nome

@pagina_privata
def admin_import_volontari(request, me):
    from anagrafica.importa import import_valida_volontari
    if not me.utenza.is_staff:
        return redirect(ERRORE_PERMESSI)

    risultati = []
    modulo = ModuloImportVolontari(request.POST or None, request.FILES or None)
    righe = []

    importati = 0

    def unicode_csv_reader(utf8_data, dialect=csv.excel, **kwargs):
        csv_reader = csv.reader(utf8_data, dialect=dialect, **kwargs)
        for row in csv_reader:
            yield [cell.decode('UTF-8') if hasattr(cell, 'decode') else cell for cell in row]

    if modulo.is_valid():


        nome_file = handle_uploaded_file(request.FILES['file_csv'])
        with codecs.open(nome_file, encoding="utf-8") as csvfile:
            riga = unicode_csv_reader(csvfile, delimiter=modulo.cleaned_data['delimitatore'])
            intestazione = True
            for r in riga:
                if intestazione:
                    intestazione = False
                    continue
                righe += [r]

        try:
            risultati = import_valida_volontari(righe)
            if modulo.cleaned_data['azione'] == modulo.IMPORTA:
                importati = import_import_volontari(risultati)

        except IndexError:
            return errore_generico(request, me, titolo="Delimitatore errato",
                                   messaggio="File non valido o delimitatore errato")

        risultati = zip(righe, risultati)
    contesto = {
        "modulo": modulo,
        "risultati": risultati,
        "ERRORE": VALIDAZIONE_ERRORE,
        "AVVISO": VALIDAZIONE_AVVISO,
        "OK": VALIDAZIONE_OK,
        "importati": importati,
    }
    return 'admin_import_volontari.html', contesto


@pagina_privata
def admin_statistiche(request, me):
    if not me.utenza.is_staff:
        return redirect(ERRORE_PERMESSI)

    oggi = datetime.date.today()
    nascita_minima_35 = datetime.date(oggi.year - 36, oggi.month, oggi.day)
    persone = Persona.objects.all()
    soci = Persona.objects.filter(
        Appartenenza.query_attuale(membro__in=Appartenenza.MEMBRO_SOCIO).via("appartenenze")
    )
    soci_giovani_35 = soci.filter(
        data_nascita__gt=nascita_minima_35,
    )
    sedi = Sede.objects.filter(attiva=True)

    regione_soci_volontari = []
    for regione in Sede.objects.filter(estensione=REGIONALE):
        regione_soci_volontari += [
            (
                regione,
                regione.membri_attuali(figli=True, membro__in=Appartenenza.MEMBRO_SOCIO).count(),
                regione.membri_attuali(figli=True, membro=Appartenenza.VOLONTARIO).count()
            ),
        ]

    contesto = {
        "persone_numero": persone.count(),
        "soci_numero": soci.count(),
        "soci_percentuale": soci.count() / persone.count() * 100,
        "soci_giovani_35_numero": soci_giovani_35.count(),
        "soci_giovani_35_percentuale": soci_giovani_35.count() / soci.count() * 100,
        "sedi_numero": sedi.count(),
        "ora": timezone.now(),
        "regione_soci_volontari": regione_soci_volontari,
    }
    return 'admin_statistiche.html', contesto
