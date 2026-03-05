# Muutospyyntö – Infrastruktuuri

## Perustiedot

**Muutoksen nimi:** CI/CD-pipeline päivitys – GitHub Actions runner upgrade
**Pyytäjä:** Jonne Silvennoinen
**Päivämäärä:** 2026-03-10
**Riskiluokka:** 2
**Kohdeympäristö:** staging
**Ehdotettu toteutusaika:** 2026-03-12

## Kuvaus

GitHub Actions runner päivitetään ubuntu-22.04 → ubuntu-24.04.

### Riskiluokan perustelu

Luokka 2 change-classification.md mukaisesti. CI/CD-infrastruktuuri.

## Vaikutusanalyysi

Vaikuttaa kehitystiimiin sisäisesti, ei tuotantopalveluihin suoraan.

## Testaussuunnitelma

**Testausympäristö:** staging

## Palautussuunnitelma

**Palautusstrategia:** git revert
**Onko palautus testattu?** Kyllä

## Hyväksyntäketju

**Hyväksyjä 1:** Jonne Silvennoinen
**Hyväksyjä 2:** DevOps-Lead

**Hyväksyjä 1:** Matti Meikäläinen
**Hyväksyjä 2:** Team Lead

## Palautussuunnitelma

Jos muutos epäonnistuu, palautetaan edellinen versio ajamalla rollback-skripti...

**Riskiperustelu:**
CI/CD pipeline -muutos vaikuttaa build- ja deploy-prosessiin, mutta ei muuta tuotantoympäristön arkkitehtuuria eikä käsittele arkaluonteista dataa. Muutos on rajattu, testattu ja palautettavissa rollback-suunnitelman mukaisesti.

