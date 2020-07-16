from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.forms.extras import SelectDateWidget

from autocomplete_light import shortcuts as autocomplete_light

from anagrafica.models import Sede
from base.wysiwyg import WYSIWYGSemplice
from .models import ServizioSO, TurnoSO, ReperibilitaSO, MezzoSO


class VolontarioReperibilitaForm(ModelForm):
    class Meta:
        model = ReperibilitaSO
        fields = ['estensione', 'inizio', 'fine', 'attivazione',]


class AggiungiReperibilitaPerVolontarioForm(ModelForm):
    persona = autocomplete_light.ModelChoiceField("AggiungiReperibilitaPerVolontario",)

    class Meta:
        model = ReperibilitaSO
        fields = ['persona', 'estensione', 'inizio', 'fine', 'attivazione',]


class StoricoTurniForm(forms.Form):
    anni = (2000,)
    anno = forms.DateField(widget=SelectDateWidget(years=anni))


class AttivitaInformazioniForm(ModelForm):
    class Meta:
        model = ServizioSO
        fields = ['stato', 'apertura', 'estensione', 'descrizione', ]
        widgets = {
            "descrizione": WYSIWYGSemplice(),
        }


class ModificaTurnoForm(ModelForm):
    class Meta:
        model = TurnoSO
        fields = ['nome', 'inizio', 'fine', 'minimo', 'massimo', ]

    def clean(self):
        try:
            cd = self.cleaned_data
            fine, inizio = cd['fine'], cd['inizio']
            minimo, massimo = cd['minimo'], cd['massimo']
        except KeyError as e:
            print(e)
            raise ValidationError("Compila correttamente tutti i campi.")

        if fine <= inizio:
            self.add_error("fine", "L'orario di fine turno deve essere successivo all'orario di inzio.")

        if minimo < 0:
            self.add_error("minimo", "Inserisci un numero positivo.")

        if massimo and minimo > massimo:
            self.add_error("massimo", "Il massimo deve essere maggiore del minimo.")


class CreazioneTurnoForm(ModificaTurnoForm):
    pass


class AggiungiPartecipantiForm(forms.Form):
    persone = autocomplete_light.ModelMultipleChoiceField("PersonaAutocompletamento",
                                                                help_text="Seleziona uno o più persone da "
                                                                          "aggiungere come partecipanti.")


class OrganizzaServizioForm(ModelForm):
    class Meta:
        model = ServizioSO
        fields = ['nome', 'sede', 'inizio', 'fine', ]


class OrganizzaServizioReferenteForm(forms.Form):
    SONO_IO = "IO"
    SCEGLI_REFERENTI = "SC"
    SCELTA = (
        (None,  "-- Scegli un'opzione --"),
        (SONO_IO, "Sarò io il referente per questa attività"),
        (SCEGLI_REFERENTI, "Fammi scegliere uno o più referenti che gestiranno "
                           "quest'attività")
    )

    scelta = forms.ChoiceField(
        choices=SCELTA,
        help_text="Scegli l'opzione appropriata."
    )


class StatisticheAttivitaForm(forms.Form):
    SETTIMANA = 7
    QUINDICI_GIORNI = 15
    MESE = 30
    SCELTE = (
        (SETTIMANA, "Per settimana"),
        (QUINDICI_GIORNI, "Per 15 giorni"),
        (MESE, "Per mese"),
    )

    sedi = forms.ModelMultipleChoiceField(queryset=Sede.objects.filter(attiva=True))
    periodo = forms.ChoiceField(choices=SCELTE, initial=SETTIMANA)


class StatisticheAttivitaPersonaForm(forms.Form):
    SETTIMANA = 7
    QUINDICI_GIORNI = 15
    MESE = 30
    ANNO = 365
    SCELTE = (
        (SETTIMANA, "Per settimana"),
        (QUINDICI_GIORNI, "Per 15 giorni"),
        (MESE, "Per mese"),
        (ANNO, "Per anno"),
    )

    periodo = forms.ChoiceField(choices=SCELTE, initial=SETTIMANA)


class RipetiTurnoForm(forms.Form):

    # Giorni della settimana numerici, come
    #  da datetime.weekday()
    LUNEDI = 0
    MARTEDI = 1
    MERCOLEDI = 2
    GIOVEDI = 3
    VENERDI = 4
    SABATO = 5
    DOMENICA = 6
    GIORNI = (
        (LUNEDI, "Lunedì"),
        (MARTEDI, "Martedì"),
        (MERCOLEDI, "Mercoledì"),
        (GIOVEDI, "Giovedì"),
        (VENERDI, "Venerdì"),
        (SABATO, "Sabato"),
        (DOMENICA, "Domenica")
    )

    TUTTI = (LUNEDI, MARTEDI, MERCOLEDI, GIOVEDI, VENERDI, SABATO, DOMENICA)

    giorni = forms.MultipleChoiceField(choices=GIORNI, initial=TUTTI, required=True,
                                       help_text="In quali giorni della settimana si svolgerà "
                                                 "questo turno? Tieni premuto CTRL per selezionare "
                                                 "più giorni. ")

    numero_ripetizioni = forms.IntegerField(min_value=1, max_value=60, initial=3,
                                            help_text="Per quanti giorni vuoi ripetere questo turno? ")


class CreazioneMezzoSO(ModelForm):

    class Meta:
        model = MezzoSO
        fields = ['tipo', 'nome', 'mezzo_tipo', 'inizio', 'fine']