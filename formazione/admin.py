from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline

from anagrafica.admin import RAW_ID_FIELDS_DELEGA
from anagrafica.models import Delega
from base.admin import InlineAutorizzazione
from gruppi.readonly_admin import ReadonlyAdminMixin
from .models import (CorsoBase, CorsoFile,  CorsoLink, Aspirante,
    PartecipazioneCorsoBase, AssenzaCorsoBase, LezioneCorsoBase,
    InvitoCorsoBase, FormazioneTitleGoal, FormazioneTitleLevel, FormazioneTitle)


__author__ = 'alfioemanuele'

RAW_ID_FIELDS_CORSOBASE = ['sede', 'locazione',]
RAW_ID_FIELDS_PARTECIPAZIONECORSOBASE = ['persona', 'corso', 'destinazione',]
RAW_ID_FIELDS_INVITOCORSOBASE = ['persona', 'corso', 'invitante',]
RAW_ID_FIELDS_LEZIONECORSOBASE = ['corso',]
RAW_ID_FIELDS_ASSENZACORSOBASE = ['lezione', 'persona', 'registrata_da',]
RAW_ID_FIELDS_ASPIRANTE = ['persona', 'locazione',]


@admin.register(FormazioneTitle)
class AdminTitle(admin.ModelAdmin):
    list_display = ['name', 'livello_name', 'goal_obbiettivo_stragetico',
                    'goal_propedeuticita', 'goal_unit_reference']
    list_filter = ['livello__goal__unit_reference',]

    def livello_name(self, obj):
        return obj.livello.name

    def goal_obbiettivo_stragetico(self, obj):
        return obj.livello.goal_obbiettivo_stragetico

    def goal_propedeuticita(self, obj):
        return obj.livello.goal_propedeuticita

    def goal_unit_reference(self, obj):
        return obj.livello.goal_unit_reference


@admin.register(FormazioneTitleLevel)
class AdminTitleLevel(admin.ModelAdmin):
    list_display = ['name', 'goal_obbiettivo_stragetico',
                    'goal_propedeuticita', 'goal_unit_reference']
    list_filter = ['goal',]


@admin.register(FormazioneTitleGoal)
class AdminTitleGoal(admin.ModelAdmin):
    list_display = ['__str__', 'obbiettivo_stragetico', 'propedeuticita', 'unit_reference']
    list_filter = ['unit_reference',]


class InlineDelegaCorsoBase(ReadonlyAdminMixin, GenericTabularInline):
    model = Delega
    raw_id_fields = RAW_ID_FIELDS_DELEGA
    ct_field = 'oggetto_tipo'
    ct_fk_field = 'oggetto_id'
    extra = 0


class InlinePartecipazioneCorsoBase(ReadonlyAdminMixin, admin.TabularInline):
    model = PartecipazioneCorsoBase
    raw_id_fields = RAW_ID_FIELDS_PARTECIPAZIONECORSOBASE
    extra = 0


class InlineInvitoCorsoBase(ReadonlyAdminMixin, admin.TabularInline):
    model = InvitoCorsoBase
    raw_id_fields = RAW_ID_FIELDS_INVITOCORSOBASE
    extra = 0


class InlineLezioneCorsoBase(ReadonlyAdminMixin, admin.TabularInline):
    model = LezioneCorsoBase
    raw_id_fields = RAW_ID_FIELDS_LEZIONECORSOBASE
    extra = 0


class InlineAssenzaCorsoBase(ReadonlyAdminMixin, admin.TabularInline):
    model = AssenzaCorsoBase
    raw_id_fields = RAW_ID_FIELDS_ASSENZACORSOBASE
    extra = 0


def admin_corsi_base_attivi_invia_messaggi(modeladmin, request, queryset):
    corsi = queryset.filter(stato=CorsoBase.ATTIVO)
    for corso in corsi:
        corso._invia_email_agli_aspiranti()
admin_corsi_base_attivi_invia_messaggi.short_description = "(Solo corsi attivi) Reinvia messaggio di attivazione agli " \
                                                           "aspiranti nelle vicinanze"


@admin.register(CorsoBase)
class AdminCorsoBase(ReadonlyAdminMixin, admin.ModelAdmin):
    search_fields = ['sede__nome', 'sede__genitore__nome', 'progressivo', 'anno', ]
    list_display = ['progressivo', 'anno', 'stato', 'sede', 'data_inizio', 'data_esame', ]
    list_filter = ['anno', 'creazione', 'stato', 'data_inizio', ]
    raw_id_fields = RAW_ID_FIELDS_CORSOBASE
    inlines = [InlineDelegaCorsoBase, InlinePartecipazioneCorsoBase, InlineInvitoCorsoBase, InlineLezioneCorsoBase]
    actions = [admin_corsi_base_attivi_invia_messaggi]


@admin.register(CorsoFile)
class AdminCorsoFile(admin.ModelAdmin):
    list_display = ['__str__', 'file', 'is_enabled', 'corso',]
    list_filter = ['is_enabled',]
    raw_id_fields = ('corso',)


@admin.register(CorsoLink)
class AdminCorsoLink(admin.ModelAdmin):
    list_display = ['link', 'is_enabled', 'corso',]
    list_filter = ['is_enabled', ]
    raw_id_fields = ('corso',)


@admin.register(PartecipazioneCorsoBase)
class AdminPartecipazioneCorsoBase(ReadonlyAdminMixin, admin.ModelAdmin):
    search_fields = ['persona__nome', 'persona__cognome', 'persona__codice_fiscale', 'corso__progressivo', ]
    list_display = ['persona', 'corso', 'esito', 'creazione', ]
    raw_id_fields = RAW_ID_FIELDS_PARTECIPAZIONECORSOBASE
    inlines = [InlineAutorizzazione]


@admin.register(LezioneCorsoBase)
class AdminLezioneCorsoBase(ReadonlyAdminMixin, admin.ModelAdmin):
    search_fields = ['nome', 'corso__progressivo', 'corso__sede__nome', ]
    list_display = ['corso', 'nome', 'inizio', 'fine', ]
    raw_id_fields = RAW_ID_FIELDS_LEZIONECORSOBASE
    inlines = [InlineAssenzaCorsoBase,]


@admin.register(AssenzaCorsoBase)
class AdminAssenzaCorsoBase(ReadonlyAdminMixin, admin.ModelAdmin):
    search_fields = ['persona__nome', 'persona__cognome', 'persona__codice_fiscale', 'lezione__corso__progressivo',
                     'lezione__corso__sede__nome']
    list_display = ['persona', 'lezione', 'creazione', ]
    raw_id_fields = RAW_ID_FIELDS_ASSENZACORSOBASE


def ricalcola_raggio(modeladmin, request, queryset):
    for a in queryset:
        a.calcola_raggio()
ricalcola_raggio.short_description = "Ricalcola il raggio per gli aspiranti selezionati"

@admin.register(Aspirante)
class AdminAspirante(ReadonlyAdminMixin, admin.ModelAdmin):
    search_fields = ['persona__nome', 'persona__cognome', 'persona__codice_fiscale']
    list_display = ['persona', 'creazione', ]
    raw_id_fields = RAW_ID_FIELDS_ASPIRANTE
    actions = [ricalcola_raggio,]
