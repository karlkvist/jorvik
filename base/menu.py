"""
Questa pagina contiene i vari menu che vengono mostrati nella barra laterale dei template.
La costante MENU è accessibile attraverso "menu" nei template.
"""

from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse

from anagrafica.costanti import REGIONALE  #TERRITORIALE, LOCALE
from anagrafica.permessi.applicazioni import (PRESIDENTE, UFFICIO_SOCI, RUBRICHE_TITOLI, COMMISSARIO)
from anagrafica.permessi.costanti import (GESTIONE_ATTIVITA, GESTIONE_ATTIVITA_AREA,
    ELENCHI_SOCI, GESTIONE_AREE_SEDE, GESTIONE_ATTIVITA_SEDE, EMISSIONE_TESSERINI,
    GESTIONE_POTERI_CENTRALE_OPERATIVA_SEDE)
from anagrafica.models import Sede

from .utils import remove_none
from .models import Menu
from formazione.menus import formazione_menu


def menu(request):
    """ Ottiene il menu per una data richiesta. """

    # from base.viste import ORDINE_ASCENDENTE, ORDINE_DISCENDENTE, ORDINE_DEFAULT

    me = request.me if hasattr(request, 'me') else None
    deleghe_attuali = None

    if me:
        deleghe_normali = me.deleghe_attuali().exclude(tipo=PRESIDENTE)
        sedi_deleghe_normali = me.sedi_deleghe_attuali(deleghe=deleghe_normali) if me else Sede.objects.none()
        sedi_deleghe_normali = [sede.pk for sede in sedi_deleghe_normali if sede.comitati_sottostanti().exists() or sede.unita_sottostanti().exists()]
        presidente = me.deleghe_attuali(tipo=PRESIDENTE)
        sedi_deleghe_presidente = me.sedi_deleghe_attuali(deleghe=presidente) if me else Sede.objects.none()
        sedi_presidenti_sottostanti = [sede.pk for sede in sedi_deleghe_presidente if sede.comitati_sottostanti().exists()]
        sedi_deleghe_presidente = list(sedi_deleghe_presidente.values_list('pk', flat=True))
        sedi = sedi_deleghe_normali + sedi_deleghe_presidente
        deleghe_attuali = me.deleghe_attuali(
            oggetto_tipo=ContentType.objects.get_for_model(Sede),
            oggetto_id__in=sedi
        ).distinct().values_list('tipo', flat=True)

    RUBRICA_BASE = [
        ("Referenti", "fa-book", "/utente/rubrica/referenti/"),
        ("Volontari", "fa-book", "/utente/rubrica/volontari/"),
    ]

    if deleghe_attuali:
        rubriche = []
        for slug, informazioni in RUBRICHE_TITOLI.items():
            delega, titolo, espandi = informazioni
            if titolo not in rubriche:
                rubriche.append(titolo)
                if (delega in deleghe_attuali or
                    UFFICIO_SOCI in deleghe_attuali or
                    PRESIDENTE in deleghe_attuali or
                    COMMISSARIO in deleghe_attuali):
                    if UFFICIO_SOCI in deleghe_attuali and (delega == COMMISSARIO or delega == PRESIDENTE):
                        continue
                    RUBRICA_BASE.append(
                        (titolo, "fa-book", "".join(("/utente/rubrica/", slug, '/')))
                    )

    ME_VOLONTARIO = me and (me.volontario or me.dipendente)
    VOCE_PERSONA = ("Persona", (
        ("Benvenuto", "fa-bolt", "/utente/"),
        ("Anagrafica", "fa-edit", "/utente/anagrafica/"),
        ("Storico", "fa-clock-o", "/utente/storico/"),
        ("Documenti", "fa-folder", "/utente/documenti/") if ME_VOLONTARIO else None,
        ("Contatti", "fa-envelope", "/utente/contatti/"),
        ("Fotografie", "fa-credit-card", "/utente/fotografia/"),
    ))

    VOCE_VOLONTARIO = ("Volontario", (
        ("Corsi di formazione", "fa-list", reverse('aspirante:corsi_base')),
        ("Estensione", "fa-random", "/utente/estensione/"),
        ("Trasferimento", "fa-arrow-right", "/utente/trasferimento/"),
        ("Riserva", "fa-pause", "/utente/riserva/"),
    )) if me and me.volontario else None

    VOCE_RUBRICA = ("Rubrica", (
        RUBRICA_BASE
    ))

    VOCE_CV = ("Curriculum", (
        # Competenze personali commentate per non visuallizarle
        #("Competenze personali", "fa-suitcase", "/utente/curriculum/CP/"),
        ("Patenti Civili", "fa-car", "/utente/curriculum/PP/"),
        ("Patenti CRI", "fa-ambulance", "/utente/curriculum/PC/") if ME_VOLONTARIO else None,
        ("Titoli di Studio", "fa-graduation-cap", "/utente/curriculum/TS/"),
        ("Titoli CRI", "fa-plus-square-o", "/utente/curriculum/TC/") if ME_VOLONTARIO else None,
    ))

    VOCE_DONATORE = ("Donatore", (
        ("Profilo Donatore", "fa-user", "/utente/donazioni/profilo/"),
        ("Donazioni di Sangue", "fa-flask", "/utente/donazioni/sangue/")
            if hasattr(me, 'donatore') else None,
    )) if me and me.volontario else None

    VOCE_SICUREZZA = ("Sicurezza", (
        ("Cambia password", "fa-key", "/utente/cambia-password/"),
        ("Impostazioni Privacy", "fa-cogs", "/utente/privacy/"),
    ))

    VOCE_LINKS = ("Links", tuple((link.name, link.icon_class, link.url)
        for link in Menu.objects.filter(is_active=True).order_by('order')))

    VOCE_MONITORAGGIO = ("Monitoraggio", (
        ("Monitoraggio 2019 (dati 2018)", 'fa-user', reverse('pages:monitoraggio')),
    ))

    elementi = {
        "utente": (VOCE_PERSONA, VOCE_VOLONTARIO, VOCE_RUBRICA, VOCE_CV,
                   VOCE_DONATORE, VOCE_SICUREZZA, VOCE_LINKS, VOCE_MONITORAGGIO) \
                    if me and not hasattr(me, 'aspirante') else None,
        "posta": (
            ("Posta", (
                ("Scrivi", "fa-pencil", "/posta/scrivi/"),
                ("In arrivo", "fa-inbox", "/posta/in-arrivo/"),
                ("In uscita", "fa-mail-forward", "/posta/in-uscita/"),
            )),
        ),
        "veicoli": (
            ("Veicoli", (
                ("Dashboard", "fa-gears", "/veicoli/"),
                ("Veicoli", "fa-car", "/veicoli/elenco/"),
                ("Autoparchi", "fa-dashboard", "/veicoli/autoparchi/"),
            )),
        ),
        "attivita": (
            ("Attività", (
                ("Calendario", "fa-calendar", "/attivita/calendario/"),
                ("Miei turni", "fa-list", "/attivita/storico/"),
                ("Gruppi di lavoro", "fa-users", "/attivita/gruppi/"),
                ("Reperibilità", "fa-thumb-tack", "/attivita/reperibilita/"),
            )),
            ("Gestione", (
                ("Gruppi di lavoro", "fa-pencil", "/attivita/gruppo/") if me and me.oggetti_permesso(GESTIONE_ATTIVITA_AREA).exists() else None,
                ("Organizza attività", "fa-asterisk", "/attivita/organizza/") if me and me.oggetti_permesso(GESTIONE_ATTIVITA_AREA).exists() else None,
                ("Elenco attività", "fa-list", "/attivita/gestisci/") if me and me.oggetti_permesso(GESTIONE_ATTIVITA).exists() else None,
                ("Aree di intervento", "fa-list", "/attivita/aree/") if me and me.oggetti_permesso(GESTIONE_AREE_SEDE).exists() else None,
                ("Statistiche", "fa-bar-chart", "/attivita/statistiche/") if me and me.oggetti_permesso(GESTIONE_ATTIVITA_SEDE).exists() else None,
            ))
        ) if me and me.volontario else None,
        "autorizzazioni": (
            ("Richieste", (
                ("In attesa", "fa-user-plus", "/autorizzazioni/"),
                ("Storico", "fa-clock-o", "/autorizzazioni/storico/"),
            )),
            ("Ordina", (
                ("Dalla più recente", "fa-sort-numeric-desc", "?ordine=DESC",
                 request.GET.get('ordine', default="DESC") == "DESC"),
                ("Dalla più vecchia", "fa-sort-numeric-asc", "?ordine=ASC",
                 request.GET.get('ordine', default="DESC") == "ASC"),
            )),
        ),
        "presidente": (
            ("Sedi CRI", (
                ("Elenco", "fa-list", "/presidente/"),
            )),
        ),
        "us": (
            ("Elenchi", (
                ("Volontari", "fa-list", "/us/elenchi/volontari/"),
                ("Vol. giovani", "fa-list", "/us/elenchi/giovani/"),
                ("Estesi", "fa-list", "/us/elenchi/estesi/"),
                ("IV e CM", "fa-list", "/us/elenchi/ivcm/"),
                ("In Riserva", "fa-list", "/us/elenchi/riserva/"),
                ("Zero turni", "fa-list", "/us/elenchi/senza-turni/"),
                ("Soci", "fa-list", "/us/elenchi/soci/"),
                ("Sostenitori", "fa-list", "/us/elenchi/sostenitori/"),
                ("Ex Sostenitori", "fa-list", "/us/elenchi/ex-sostenitori/"),
                ("Dipendenti", "fa-list", "/us/elenchi/dipendenti/"),
                ("Dimessi", "fa-list", "/us/elenchi/dimessi/"),
                ("Trasferiti", "fa-list", "/us/elenchi/trasferiti/"),
                ("Ordinari", "fa-list", "/us/elenchi/ordinari/") if me and me.oggetti_permesso(ELENCHI_SOCI).filter(estensione=REGIONALE).exists() else None,
                ("Elettorato", "fa-list", "/us/elenchi/elettorato/"),
                ("Tesserini", "fa-list", "/us/tesserini/"),
                ("Per Titoli", "fa-search", "/us/elenchi/titoli/"),
                ("Scarica elenchi richiesti", "fa-download", reverse('ufficio_soci:elenchi_richiesti_download'), '', True),
            )),
            ("Aggiungi", (
                ("Persona", "fa-plus-square", "/us/aggiungi/"),
                ("Reclama Persona", "fa-plus-square", "/us/reclama/"),
            )),
            ("Pratiche", (
                ("Nuovo trasferimento", "fa-file-o", "/us/trasferimento/"),
                ("Nuova estensione", "fa-file-o", "/us/estensione/"),
                ("Messa in riserva", "fa-file-o", "/us/riserva/"),
                ("Nuovo provvedimento", "fa-file-o", "/us/provvedimento/"),
            )),
            ("Quote e ricevute", (
                ("Registra Quota Associativa", "fa-plus-square", "/us/quote/nuova/"),
                ("Quote associative", "fa-money", "/us/quote/"),
                # ("Ricerca quote", "fa-search", "/us/quote/ricerca/"),
                ("Registra Ricevuta", "fa-plus-square", "/us/ricevute/nuova/"),
                ("Elenco ricevute", "fa-list", "/us/ricevute/"),
            )),
            ("Tesserini", (
                ("Emissione", "fa-cogs", "/us/tesserini/emissione/"),
            )) if me and me.oggetti_permesso(EMISSIONE_TESSERINI).exists() else None,
        ),
        "co": (
            ("Centrale Operativa", (
                ("Reperibilità", "fa-clock-o", "/centrale-operativa/reperibilita/"),
                ("Turni", "fa-calendar", "/centrale-operativa/turni/"),
                ("Poteri", "fa-magic", "/centrale-operativa/poteri/")
                if me and me.oggetti_permesso(GESTIONE_POTERI_CENTRALE_OPERATIVA_SEDE).exists() else None,
            )),
        ),
        'formazione': formazione_menu('formazione', me),
        'aspirante': formazione_menu('aspirante') if me and hasattr(me, 'aspirante') else (
            ("Corsi di formazione", (
                ("Elenco Corsi", "fa-list", reverse('formazione:list_courses')),
            )),
        ),
    }
    if me and hasattr(me, 'aspirante'):
        elementi['elementi_anagrafica'] = elementi['aspirante']
    else:
        elementi['elementi_anagrafica'] = elementi['utente']
    return remove_none(elementi)
