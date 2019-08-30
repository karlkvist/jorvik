from django import template
from django.utils.safestring import mark_safe

from base.utils import oggi


register = template.Library()

@register.simple_tag
def titoli_del_corso(persona, cd):
    init_query = persona.titoli_personali_confermati().filter(is_course_title=True)
    lista = init_query.filter(titolo__in=cd['titoli'])

    if cd.get('show_only_active', False):
        lista = lista.filter(data_scadenza__gte=oggi())

    return {
        'lista': lista.order_by('-data_scadenza'),
        'num_of_titles': init_query.count()
    }


@register.simple_tag
def lezione_esonero(lezione, partecipante):
    from ..models import AssenzaCorsoBase

    try:
        a = AssenzaCorsoBase.objects.get(lezione=lezione, persona=partecipante)
        return a if a.is_esonero else None
    except AssenzaCorsoBase.DoesNotExist:
        return None


@register.simple_tag
def lezione_partecipante_pk_shortcut(lezione, partecipante):
    return "%s-%s" % (lezione.pk, partecipante.pk)


@register.simple_tag
def corsi_filter():
    from ..models import Corso

    href = """<a href="?stato=%s">%s</a>"""
    return mark_safe(' '.join([href % (i[0], i[1]) for i in Corso.STATO]))


@register.simple_tag(takes_context=True)
def can_show_button_genera_verbale(context, corso):
    request = context['request']
    num_verbale_da_generare = 2 if 'seconda_data_esame' in request.GET else 1

    if corso.relazione_direttore.is_completed:
        if num_verbale_da_generare == 1:
            return True
        elif num_verbale_da_generare == 2:
            if not corso.has_partecipazioni_confermate_con_assente_motivo:
                return True
    return False


@register.simple_tag(takes_context=True)
def can_show_tab_questionario(context):
    corso, me = context['corso'], context['me']
    if corso.survey and corso.concluso:  # corso.is_nuovo_corso
        return corso.survey.can_vote(me, corso)
    return False