from django.utils.translation import ugettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices


class Archiefnominatie(DjangoChoices):
    blijvend_bewaren = ChoiceItem(
        "blijvend_bewaren",
        _(
            "Het zaakdossier moet bewaard blijven en op de Archiefactiedatum overgedragen worden naar een "
            "archiefbewaarplaats."
        ),
    )
    vernietigen = ChoiceItem(
        "vernietigen",
        _("Het zaakdossier moet op of na de Archiefactiedatum vernietigd worden."),
    )


class BrondatumArchiefprocedureAfleidingswijze(DjangoChoices):
    afgehandeld = ChoiceItem(
        "afgehandeld",
        _("Afgehandeld"),
        description=_(
            "De termijn start op de datum waarop de zaak is "
            "afgehandeld (ZAAK.Einddatum in het RGBZ)."
        ),
    )
    ander_datumkenmerk = ChoiceItem(
        "ander_datumkenmerk",
        _("Ander datumkenmerk"),
        description=_(
            "De termijn start op de datum die is vastgelegd in een "
            "ander datumveld dan de datumvelden waarop de overige "
            "waarden (van deze attribuutsoort) betrekking hebben. "
            "`Objecttype`, `Registratie` en `Datumkenmerk` zijn niet "
            "leeg."
        ),
    )
    eigenschap = ChoiceItem(
        "eigenschap",
        _("Eigenschap"),
        description=_(
            "De termijn start op de datum die vermeld is in een "
            "zaaktype-specifieke eigenschap (zijnde een `datumveld`). "
            "`ResultaatType.ZaakType` heeft een `Eigenschap`; "
            "`Objecttype`, en `Datumkenmerk` zijn niet leeg."
        ),
    )
    gerelateerde_zaak = ChoiceItem(
        "gerelateerde_zaak",
        _("Gerelateerde zaak"),
        description=_(
            "De termijn start op de datum waarop de gerelateerde "
            "zaak is afgehandeld (`ZAAK.Einddatum` of "
            "`ZAAK.Gerelateerde_zaak.Einddatum` in het RGBZ). "
            "`ResultaatType.ZaakType` heeft gerelateerd `ZaakType`"
        ),
    )
    hoofdzaak = ChoiceItem(
        "hoofdzaak",
        _("Hoofdzaak"),
        description=_(
            "De termijn start op de datum waarop de gerelateerde "
            "zaak is afgehandeld, waarvan de zaak een deelzaak is "
            "(`ZAAK.Einddatum` van de hoofdzaak in het RGBZ). "
            "ResultaatType.ZaakType is deelzaaktype van ZaakType."
        ),
    )
    ingangsdatum_besluit = ChoiceItem(
        "ingangsdatum_besluit",
        _("Ingangsdatum besluit"),
        description=_(
            "De termijn start op de datum waarop het besluit van "
            "kracht wordt (`BESLUIT.Ingangsdatum` in het RGBZ).	"
            "ResultaatType.ZaakType heeft relevant BesluitType"
        ),
    )
    termijn = ChoiceItem(
        "termijn",
        _("Termijn"),
        description=_(
            "De termijn start een vast aantal jaren na de datum "
            "waarop de zaak is afgehandeld (`ZAAK.Einddatum` in het "
            "RGBZ)."
        ),
    )
    vervaldatum_besluit = ChoiceItem(
        "vervaldatum_besluit",
        _("Vervaldatum besluit"),
        description=_(
            "De termijn start op de dag na de datum waarop het "
            "besluit vervalt (`BESLUIT.Vervaldatum` in het RGBZ). "
            "ResultaatType.ZaakType heeft relevant BesluitType"
        ),
    )
    zaakobject = ChoiceItem(
        "zaakobject",
        _("Zaakobject"),
        description=_(
            "De termijn start op de einddatum geldigheid van het "
            "zaakobject waarop de zaak betrekking heeft "
            "(bijvoorbeeld de overlijdendatum van een Persoon). "
            "M.b.v. de attribuutsoort `Objecttype` wordt vastgelegd "
            "om welke zaakobjecttype het gaat; m.b.v. de "
            "attribuutsoort `Datumkenmerk` wordt vastgelegd welke "
            "datum-attribuutsoort van het zaakobjecttype het betreft."
        ),
    )
