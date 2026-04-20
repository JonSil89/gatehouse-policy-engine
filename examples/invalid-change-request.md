# Muutospyyntö: Järjestelmäpäivitys ja konfiguraatiomuutos

## Perustiedot
| Kenttä | Arvo |
| :--- | :--- |
| Muutoksen nimi | Gatehouse-validointikorjaus |
| Pyytäjä | Jonne |
| Päivämäärä | 2026-04-20 |
| Riskiluokka | 1 |
| Kohdeympäristö | Production |

## Kuvaus
Tämä muutos korjaa aiemmin hylätyn muutospyynnön rakenteen. Päivityksessä varmistetaan, että kaikki ISO 27001 -standardin vaatimat dokumentaatiokentät on täytetty oikein automaattista tarkistusta varten.

## Vaikutusanalyysi
- **Palvelun tila:** Ei katkoja.
- **Kriittisyys:** Matala, muutos koskee vain dokumentaatiorakenteen validointia.
- **Resurssit:** Tehdään kehittäjän toimesta osana CI/CD-putken parantamista.

## Palautussuunnitelma
Mikäli muutos aiheuttaa virheitä validointimoottorissa, palautetaan tiedosto aiempaan versioon komennolla `git checkout HEAD^ examples/invalid-change-request.md`.

## Hyväksynnät
- [x] @JonSil89 (Kehittäjä)
- [x] @Gatehouse-Bot (Automaattinen tarkistus)

---
*Dokumentti on Gatehouse Policy Enginen vaatimusten mukainen.*
